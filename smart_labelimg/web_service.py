"""Local-only HTTP API for the browser annotation interface.

The API deliberately exposes images by their position in an opened dataset
session.  Browser requests never contain a path that is used for subsequent
file access, which keeps reads and writes inside the resolved dataset root.
"""

from __future__ import annotations

import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock, RLock
from typing import Literal
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET
from uuid import uuid4

import cv2
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse
from pydantic import BaseModel, Field

from smart_labelimg.ai_backend import MobileSamBackend
from smart_labelimg.annotation import (
    AnnotationFormat,
    Box,
    load_annotation,
    load_voc_xml,
    save_annotation,
)
from smart_labelimg.labels import SIMPLE_LABELS
from smart_labelimg.paths import resource_path
from smart_labelimg.propagation import PropagationCandidate, propagate_boxes


IMAGE_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"})
ApiFormat = Literal["auto", "yolo", "voc_xml"]


class DatasetOpenRequest(BaseModel):
    path: str
    format: ApiFormat = "auto"


class BoxPayload(BaseModel):
    label: str
    x1: int
    y1: int
    x2: int
    y2: int
    score: float | None = None

    def to_box(self) -> Box:
        return Box(self.label.strip() or "object", self.x1, self.y1, self.x2, self.y2, self.score)


class AnnotationWriteRequest(BaseModel):
    sessionId: str
    boxes: list[BoxPayload] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    format: ApiFormat = "auto"


class RefineRequest(BaseModel):
    box: BoxPayload
    label: str | None = None


class PropagateRequest(BaseModel):
    boxes: list[BoxPayload] | None = None
    acceptThreshold: float = Field(default=0.78, ge=0.0, le=1.0)


def _box_payload(box: Box) -> dict[str, object]:
    score = None if box.score is None else max(0.0, min(1.0, float(box.score)))
    return {
        "label": box.label,
        "x1": box.x1,
        "y1": box.y1,
        "x2": box.x2,
        "y2": box.y2,
        "score": score,
    }


class LocalDatasetService:
    def __init__(self) -> None:
        self.dataset_path: Path | None = None
        self.images: list[Path] = []
        self.labels: list[str] = list(SIMPLE_LABELS)
        self.format = AnnotationFormat.YOLO
        self.current_index = 0
        self.session_id: str | None = None
        self.backend = None
        self.backend_lock = Lock()
        self.session_lock = RLock()

    def open_dataset(self, raw_path: str | Path, requested_format: ApiFormat = "auto") -> dict[str, object]:
        try:
            root = Path(raw_path).expanduser().resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise HTTPException(status_code=400, detail=f"Dataset directory is unavailable: {exc}") from exc
        if not root.is_dir():
            raise HTTPException(status_code=400, detail="Dataset path must be a directory")

        try:
            images = sorted(
                (
                    resolved
                    for candidate in root.rglob("*")
                    if candidate.is_file() and candidate.suffix.lower() in IMAGE_SUFFIXES
                    if _is_within(resolved := candidate.resolve(strict=True), root)
                ),
                key=lambda candidate: candidate.relative_to(root).as_posix().casefold(),
            )
        except (OSError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=f"Unable to scan dataset: {exc}") from exc
        # A symlinked image may resolve outside the selected directory.  It is
        # excluded instead of becoming an escape hatch for the content route.
        images = [candidate for candidate in images if _is_within(candidate, root)]
        if not images:
            raise HTTPException(status_code=400, detail="Dataset does not contain a supported image")

        selected_format = self._resolve_format(requested_format, root, images)
        labels = self._load_labels(root, images, selected_format)

        # Commit all session fields while saves are excluded from the transition.
        with self.session_lock:
            self.dataset_path = root
            self.images = images
            self.format = selected_format
            self.labels = labels
            self.current_index = 0
            self.session_id = uuid4().hex
            return self.dataset_payload()

    def dataset_payload(self) -> dict[str, object]:
        root = self._require_dataset()
        return {
            "path": str(root),
            "images": [image.relative_to(root).as_posix() for image in self.images],
            "currentIndex": self.current_index,
            "labels": list(self.labels),
            "format": self.format.value,
            "sessionId": self.session_id,
        }

    def image_payload(self, index: int) -> dict[str, object]:
        image_path = self.image_at(index)
        image = self.read_image(index)
        height, width = image.shape[:2]
        boxes = self.load_boxes(index)
        self.current_index = index
        root = self._require_dataset()
        return {
            "name": image_path.relative_to(root).as_posix(),
            "width": width,
            "height": height,
            "boxes": [_box_payload(box) for box in boxes],
            "labels": list(self.labels),
            "format": self.format.value,
        }

    def image_at(self, index: int) -> Path:
        self._require_dataset()
        if index < 0 or index >= len(self.images):
            raise HTTPException(status_code=404, detail="Image index is outside the dataset")
        image = self.images[index]
        root = self._require_dataset()
        if not _is_within(image, root) or not image.is_file():
            raise HTTPException(status_code=404, detail="Image is no longer available")
        return image

    def read_image(self, index: int):
        image_path = self.image_at(index)
        bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if bgr is None:
            raise HTTPException(status_code=422, detail=f"Unable to decode image: {image_path.name}")
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    def load_boxes(self, index: int) -> list[Box]:
        image_path = self.image_at(index)
        image = self.read_image(index)
        annotation_path = self._annotation_path(image_path, self.format)
        if not annotation_path.exists():
            return []
        try:
            return load_annotation(annotation_path, self.labels, (image.shape[1], image.shape[0]))
        except (OSError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=f"Unable to load {annotation_path.name}: {exc}") from exc

    def save_boxes(self, index: int, request: AnnotationWriteRequest) -> dict[str, object]:
        with self.session_lock:
            return self._save_boxes_locked(index, request)

    def _save_boxes_locked(self, index: int, request: AnnotationWriteRequest) -> dict[str, object]:
        if not self.session_id or request.sessionId != self.session_id:
            raise HTTPException(status_code=409, detail="Dataset session changed; reload before saving")
        image_path = self.image_at(index)
        image = self.read_image(index)
        selected_format = self.format if request.format == "auto" else AnnotationFormat(request.format)
        labels = _clean_labels(request.labels) or list(self.labels)
        boxes = [payload.to_box() for payload in request.boxes]
        unknown = sorted({box.label for box in boxes if box.label not in labels})
        if unknown:
            raise HTTPException(status_code=422, detail=f"Boxes use labels not present in labels: {', '.join(unknown)}")

        target = self._annotation_path(image_path, selected_format)
        self._assert_session_path(target)
        try:
            if selected_format == AnnotationFormat.YOLO:
                root = self._require_dataset()
                class_targets = {root / "classes.txt", target.parent / "classes.txt"}
                _transactional_save_yolo(
                    target,
                    boxes,
                    labels,
                    (image.shape[1], image.shape[0]),
                    image_path,
                    class_targets,
                )
            else:
                _atomic_save_annotation(
                    target,
                    boxes,
                    labels,
                    (image.shape[1], image.shape[0]),
                    image_path,
                )
        except OSError as exc:
            raise HTTPException(status_code=500, detail=f"Unable to save annotation: {exc}") from exc

        self.labels = labels
        self.format = selected_format
        self.current_index = index
        return {
            "saved": True,
            "name": target.name,
            "boxes": [_box_payload(box) for box in boxes],
            "labels": list(labels),
            "format": selected_format.value,
        }

    def refine(self, index: int, request: RefineRequest) -> list[Box]:
        image = self.read_image(index)
        source = request.box.to_box().clipped((image.shape[1], image.shape[0]))
        label = (request.label or source.label).strip() or "object"
        try:
            with self.backend_lock:
                return self._get_backend().refine_from_box(
                    image,
                    (source.x1, source.y1, source.x2, source.y2),
                    label,
                )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"MobileSAM refinement failed: {exc}") from exc

    def propagate(self, index: int, request: PropagateRequest) -> tuple[list[Box], list[PropagationCandidate]]:
        if index <= 0:
            raise HTTPException(status_code=400, detail="Propagation requires a previous image")
        previous = self.read_image(index - 1)
        current = self.read_image(index)
        boxes = [box.to_box() for box in request.boxes] if request.boxes is not None else self.load_boxes(index - 1)
        with self.backend_lock:
            result = propagate_boxes(
                previous,
                current,
                boxes,
                self._get_backend(),
                accept_threshold=request.acceptThreshold,
            )
        self.current_index = index
        return list(result.committed), list(result.candidates)

    def _get_backend(self):
        if self.backend is None:
            checkpoint = resource_path("models/mobile_sam.pt")
            if not checkpoint.is_file():
                raise HTTPException(status_code=503, detail="MobileSAM checkpoint is not installed")
            try:
                self.backend = MobileSamBackend(str(checkpoint))
            except Exception as exc:
                raise HTTPException(status_code=503, detail=f"MobileSAM is unavailable: {exc}") from exc
        return self.backend

    def _resolve_format(self, requested: ApiFormat, root: Path, images: list[Path]) -> AnnotationFormat:
        if requested != "auto":
            return AnnotationFormat(requested)
        for image in images:
            xml_path = image.with_suffix(".xml")
            try:
                resolved_xml = xml_path.resolve(strict=True)
            except OSError:
                continue
            if _is_within(resolved_xml, root):
                return AnnotationFormat.VOC_XML
        return AnnotationFormat.YOLO

    def _load_labels(
        self,
        root: Path,
        images: list[Path],
        annotation_format: AnnotationFormat,
    ) -> list[str]:
        candidates = [root / "classes.txt"]
        candidates.extend(image.parent / "classes.txt" for image in images)
        for candidate in candidates:
            if candidate.is_file() and _is_within(candidate.resolve(), root):
                try:
                    labels = _clean_labels(candidate.read_text(encoding="utf-8").splitlines())
                except (OSError, UnicodeDecodeError):
                    continue
                if labels:
                    return labels
        if annotation_format == AnnotationFormat.VOC_XML:
            labels: list[str] = []
            for image in images:
                xml_path = image.with_suffix(".xml")
                try:
                    resolved_xml = xml_path.resolve(strict=True)
                except OSError:
                    continue
                if not _is_within(resolved_xml, root):
                    continue
                try:
                    boxes = load_voc_xml(resolved_xml)
                except (OSError, ET.ParseError):
                    continue
                for box in boxes:
                    if box.label not in labels:
                        labels.append(box.label)
            if labels:
                return labels
        return list(SIMPLE_LABELS)

    def _annotation_path(self, image_path: Path, annotation_format: AnnotationFormat) -> Path:
        suffix = ".txt" if annotation_format == AnnotationFormat.YOLO else ".xml"
        path = image_path.with_suffix(suffix)
        self._assert_session_path(path)
        return path

    def _assert_session_path(self, path: Path) -> None:
        root = self._require_dataset()
        if not _is_within(path.resolve(), root):
            raise HTTPException(status_code=403, detail="Path is outside the opened dataset")

    def _require_dataset(self) -> Path:
        if self.dataset_path is None:
            raise HTTPException(status_code=409, detail="Open a dataset first")
        return self.dataset_path


def create_app(initial_dataset: Path | None = None) -> FastAPI:
    """Create the local annotation API without binding a network interface."""

    app = FastAPI(title="Smart LabelImg Local Web", docs_url="/api/docs", redoc_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])

    @app.middleware("http")
    async def require_local_origin(request, call_next):
        origin = request.headers.get("origin")
        if origin and urlsplit(origin).netloc != request.headers.get("host"):
            return JSONResponse({"detail": "Cross-origin access is not allowed"}, status_code=403)
        return await call_next(request)

    service = LocalDatasetService()
    app.state.web_service = service

    if initial_dataset is not None:
        service.open_dataset(initial_dataset, "auto")

    @app.post("/api/dataset/open")
    def open_dataset(request: DatasetOpenRequest):
        return service.open_dataset(request.path, request.format)

    @app.get("/api/dataset")
    def get_dataset():
        return service.dataset_payload()

    @app.get("/api/images/{index}")
    def get_image(index: int):
        return service.image_payload(index)

    @app.get("/api/images/{index}/content")
    def get_image_content(index: int):
        image = service.image_at(index)
        return FileResponse(image)

    @app.get("/api/images/{index}/previous")
    def get_previous_annotations(index: int):
        if index <= 0:
            raise HTTPException(status_code=400, detail="The first image has no previous annotation")
        boxes = service.load_boxes(index - 1)
        return {"boxes": [_box_payload(box) for box in boxes]}

    @app.put("/api/images/{index}/annotations")
    def put_annotations(index: int, request: AnnotationWriteRequest):
        return service.save_boxes(index, request)

    @app.post("/api/images/{index}/refine")
    def refine_image(index: int, request: RefineRequest):
        return {"boxes": [_box_payload(box) for box in service.refine(index, request)]}

    @app.post("/api/images/{index}/propagate")
    def propagate_image(index: int, request: PropagateRequest | None = None):
        committed, candidates = service.propagate(index, request or PropagateRequest())
        return {
            "boxes": [_box_payload(box) for box in committed],
            "candidates": [
                {
                    "box": _box_payload(candidate.box),
                    "confidence": candidate.confidence,
                    "requiresConfirmation": candidate.requires_confirmation,
                }
                for candidate in candidates
            ],
        }

    static_dir = Path(__file__).resolve().parent / "web" / "static"
    if (static_dir / "index.html").is_file():
        @app.get("/", include_in_schema=False)
        def get_web_interface():
            return FileResponse(static_dir / "index.html")

        app.mount("/static", StaticFiles(directory=static_dir), name="static")
    return app


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _clean_labels(labels: list[str]) -> list[str]:
    cleaned: list[str] = []
    for raw_label in labels:
        label = raw_label.strip()
        if label and label not in cleaned:
            cleaned.append(label)
    return cleaned


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _atomic_save_annotation(
    path: Path,
    boxes: list[Box],
    labels: list[str],
    image_size: tuple[int, int],
    image_path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with NamedTemporaryFile(dir=path.parent, prefix=f".{path.stem}.", suffix=path.suffix, delete=False) as handle:
            temporary = Path(handle.name)
        save_annotation(temporary, boxes, labels, image_size, image_path=image_path)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _transactional_save_yolo(
    annotation_path: Path,
    boxes: list[Box],
    labels: list[str],
    image_size: tuple[int, int],
    image_path: Path,
    class_targets: set[Path],
) -> None:
    """Commit the YOLO file and class maps together, restoring old files on failure."""

    targets = [annotation_path, *sorted(class_targets)]
    backups = {target: target.read_bytes() if target.exists() else None for target in targets}
    staged: dict[Path, Path] = {}
    committed: list[Path] = []
    try:
        with NamedTemporaryFile(
            dir=annotation_path.parent,
            prefix=f".{annotation_path.stem}.",
            suffix=annotation_path.suffix,
            delete=False,
        ) as handle:
            staged[annotation_path] = Path(handle.name)
        save_annotation(staged[annotation_path], boxes, labels, image_size, image_path=image_path)

        classes_payload = "".join(f"{label}\n" for label in labels)
        for target in sorted(class_targets):
            target.parent.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=target.parent,
                prefix=f".{target.name}.",
                delete=False,
            ) as handle:
                staged[target] = Path(handle.name)
                handle.write(classes_payload)
                handle.flush()
                os.fsync(handle.fileno())

        for target in targets:
            os.replace(staged[target], target)
            committed.append(target)
    except OSError:
        for target in reversed(committed):
            previous = backups[target]
            if previous is None:
                target.unlink(missing_ok=True)
            else:
                _atomic_write_bytes(target, previous)
        raise
    finally:
        for temporary in staged.values():
            temporary.unlink(missing_ok=True)


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    temporary: Path | None = None
    try:
        with NamedTemporaryFile("wb", dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
