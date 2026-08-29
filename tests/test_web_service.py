from __future__ import annotations

from pathlib import Path
from threading import Event, Thread

import cv2
import numpy as np
import pytest
import smart_labelimg.web_service as web_service_module
from fastapi.testclient import TestClient

from smart_labelimg.annotation import Box, load_voc_xml, load_yolo
from smart_labelimg.web_service import AnnotationWriteRequest, BoxPayload, create_app


def _write_image(path: Path, color: tuple[int, int, int] = (0, 0, 0)) -> None:
    image = np.full((60, 80, 3), color, dtype=np.uint8)
    assert cv2.imwrite(str(path), image)


def test_open_dataset_lists_images_and_reads_yolo_annotations(tmp_path: Path):
    _write_image(tmp_path / "b.png")
    _write_image(tmp_path / "a.jpg")
    (tmp_path / "ignore.txt").write_text("not an image", encoding="utf-8")
    (tmp_path / "classes.txt").write_text("person\ncar\n", encoding="utf-8")
    (tmp_path / "a.txt").write_text("1 0.500000 0.500000 0.500000 0.500000\n", encoding="utf-8")

    client = TestClient(create_app())
    opened = client.post("/api/dataset/open", json={"path": str(tmp_path), "format": "yolo"})

    assert opened.status_code == 200
    assert opened.json()["images"] == ["a.jpg", "b.png"]
    assert opened.json()["labels"] == ["person", "car"]
    assert opened.json()["currentIndex"] == 0

    current = client.get("/api/images/0")
    assert current.status_code == 200
    assert current.json()["name"] == "a.jpg"
    assert current.json()["width"] == 80
    assert current.json()["height"] == 60
    assert current.json()["boxes"] == [
        {"label": "car", "x1": 20, "y1": 15, "x2": 60, "y2": 45, "score": None}
    ]


def test_save_yolo_is_labelimg_compatible_and_updates_classes(tmp_path: Path):
    _write_image(tmp_path / "frame.jpg")
    client = TestClient(create_app(initial_dataset=tmp_path))
    session_id = client.get("/api/dataset").json()["sessionId"]

    response = client.put(
        "/api/images/0/annotations",
        json={
            "sessionId": session_id,
            "format": "yolo",
            "labels": ["object", "car"],
            "boxes": [{"label": "car", "x1": 8, "y1": 6, "x2": 40, "y2": 30}],
        },
    )

    assert response.status_code == 200
    assert (tmp_path / "classes.txt").read_text(encoding="utf-8") == "object\ncar\n"
    assert load_yolo(tmp_path / "frame.txt", ["object", "car"], (80, 60)) == [
        Box("car", 8, 6, 40, 30)
    ]


def test_save_and_read_voc_annotations(tmp_path: Path):
    _write_image(tmp_path / "frame.png")
    client = TestClient(create_app(initial_dataset=tmp_path))
    session_id = client.get("/api/dataset").json()["sessionId"]

    response = client.put(
        "/api/images/0/annotations",
        json={
            "sessionId": session_id,
            "format": "voc_xml",
            "labels": ["person"],
            "boxes": [{"label": "person", "x1": 4, "y1": 5, "x2": 30, "y2": 40}],
        },
    )

    assert response.status_code == 200
    assert load_voc_xml(tmp_path / "frame.xml") == [Box("person", 4, 5, 30, 40)]
    loaded = client.get("/api/images/0")
    assert loaded.json()["format"] == "voc_xml"
    assert loaded.json()["boxes"][0]["label"] == "person"


def test_image_content_and_indices_are_limited_to_open_session(tmp_path: Path):
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    _write_image(dataset / "inside.jpg", (10, 20, 30))
    _write_image(tmp_path / "outside.jpg", (40, 50, 60))
    client = TestClient(create_app(initial_dataset=dataset))

    content = client.get("/api/images/0/content")
    assert content.status_code == 200
    assert content.headers["content-type"] == "image/jpeg"
    assert client.get("/api/images/1/content").status_code == 404
    assert client.get("/api/images/-1/content").status_code == 404


def test_open_rejects_a_file_and_dataset_without_images(tmp_path: Path):
    empty = tmp_path / "empty"
    empty.mkdir()
    regular_file = tmp_path / "file.txt"
    regular_file.write_text("x", encoding="utf-8")
    client = TestClient(create_app())

    assert client.post("/api/dataset/open", json={"path": str(regular_file), "format": "auto"}).status_code == 400
    assert client.post("/api/dataset/open", json={"path": str(empty), "format": "auto"}).status_code == 400


class _RefiningBackend:
    def refine_from_box(self, image, query_box, label):
        x1, y1, x2, y2 = query_box
        return [Box(label, x1 + 1, y1 + 2, x2 - 1, y2 - 2, score=0.91)]


def test_refine_uses_injected_mobile_sam_compatible_backend(tmp_path: Path):
    _write_image(tmp_path / "frame.jpg")
    app = create_app(initial_dataset=tmp_path)
    app.state.web_service.backend = _RefiningBackend()
    client = TestClient(app)

    response = client.post(
        "/api/images/0/refine",
        json={"label": "car", "box": {"label": "car", "x1": 5, "y1": 6, "x2": 40, "y2": 45}},
    )

    assert response.status_code == 200
    assert response.json()["boxes"] == [
        {"label": "car", "x1": 6, "y1": 8, "x2": 39, "y2": 43, "score": 0.91}
    ]


def test_propagate_loads_previous_boxes_and_returns_result(tmp_path: Path):
    previous = np.zeros((60, 80, 3), dtype=np.uint8)
    current = previous.copy()
    previous[15:35, 20:45] = 255
    current[18:38, 25:50] = 255
    assert cv2.imwrite(str(tmp_path / "01.png"), previous)
    assert cv2.imwrite(str(tmp_path / "02.png"), current)
    (tmp_path / "classes.txt").write_text("car\n", encoding="utf-8")
    (tmp_path / "01.txt").write_text("0 0.406250 0.416667 0.312500 0.333333\n", encoding="utf-8")
    app = create_app(initial_dataset=tmp_path)
    app.state.web_service.backend = _RefiningBackend()
    client = TestClient(app)

    response = client.post("/api/images/1/propagate")

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidates"] == []
    assert len(payload["boxes"]) == 1
    assert payload["boxes"][0]["label"] == "car"


def test_previous_boxes_are_loaded_by_index_without_changing_current_image(tmp_path: Path):
    _write_image(tmp_path / "01.png")
    _write_image(tmp_path / "02.png")
    (tmp_path / "classes.txt").write_text("car\n", encoding="utf-8")
    (tmp_path / "01.txt").write_text("0 0.500000 0.500000 0.500000 0.500000\n", encoding="utf-8")
    app = create_app(initial_dataset=tmp_path)
    client = TestClient(app)
    assert client.get("/api/images/1").status_code == 200

    response = client.get("/api/images/1/previous")

    assert response.status_code == 200
    assert response.json()["boxes"][0]["label"] == "car"
    assert app.state.web_service.current_index == 1


def test_save_rejects_a_stale_dataset_session(tmp_path: Path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    _write_image(first / "frame.png")
    _write_image(second / "frame.png")
    client = TestClient(create_app(initial_dataset=first))
    stale_session = client.get("/api/dataset").json()["sessionId"]
    assert client.post("/api/dataset/open", json={"path": str(second), "format": "yolo"}).status_code == 200

    response = client.put(
        "/api/images/0/annotations",
        json={"sessionId": stale_session, "format": "yolo", "labels": ["object"], "boxes": []},
    )

    assert response.status_code == 409
    assert not (second / "frame.txt").exists()


def test_yolo_save_rolls_back_annotation_when_classes_commit_fails(tmp_path: Path, monkeypatch):
    _write_image(tmp_path / "frame.png")
    (tmp_path / "classes.txt").write_text("object\n", encoding="utf-8")
    (tmp_path / "frame.txt").write_text("0 0.500000 0.500000 0.250000 0.250000\n", encoding="utf-8")
    client = TestClient(create_app(initial_dataset=tmp_path))
    session_id = client.get("/api/dataset").json()["sessionId"]
    real_replace = web_service_module.os.replace
    failed = False

    def fail_first_classes_replace(source, destination):
        nonlocal failed
        if Path(destination).name == "classes.txt" and not failed:
            failed = True
            raise OSError("simulated class-map failure")
        return real_replace(source, destination)

    monkeypatch.setattr(web_service_module.os, "replace", fail_first_classes_replace)
    response = client.put(
        "/api/images/0/annotations",
        json={
            "sessionId": session_id,
            "format": "yolo",
            "labels": ["object", "car"],
            "boxes": [{"label": "car", "x1": 10, "y1": 10, "x2": 40, "y2": 40}],
        },
    )

    assert response.status_code == 500
    assert (tmp_path / "classes.txt").read_text(encoding="utf-8") == "object\n"
    assert (tmp_path / "frame.txt").read_text(encoding="utf-8") == "0 0.500000 0.500000 0.250000 0.250000\n"


def test_failed_dataset_scan_keeps_the_previous_session(tmp_path: Path, monkeypatch):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    _write_image(first / "frame.png")
    _write_image(second / "frame.png")
    app = create_app(initial_dataset=first)
    service = app.state.web_service
    old_path, old_session = service.dataset_path, service.session_id
    monkeypatch.setattr(service, "_load_labels", lambda *_args: (_ for _ in ()).throw(UnicodeDecodeError("utf-8", b"x", 0, 1, "bad")))

    with pytest.raises(UnicodeDecodeError):
        TestClient(app).post("/api/dataset/open", json={"path": str(second), "format": "auto"})

    assert service.dataset_path == old_path
    assert service.session_id == old_session


def test_auto_format_ignores_voc_symlink_outside_dataset(tmp_path: Path):
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    _write_image(dataset / "frame.png")
    outside = tmp_path / "outside.xml"
    outside.write_text("<annotation />", encoding="utf-8")
    (dataset / "frame.xml").symlink_to(outside)

    response = TestClient(create_app()).post(
        "/api/dataset/open",
        json={"path": str(dataset), "format": "auto"},
    )

    assert response.status_code == 200
    assert response.json()["format"] == "yolo"


def test_dataset_switch_waits_for_an_inflight_save(tmp_path: Path, monkeypatch):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    _write_image(first / "frame.png")
    _write_image(second / "frame.png")
    app = create_app(initial_dataset=first)
    service = app.state.web_service
    entered_save = Event()
    release_save = Event()
    real_save = web_service_module._transactional_save_yolo

    def blocking_save(*args, **kwargs):
        entered_save.set()
        assert release_save.wait(timeout=3)
        return real_save(*args, **kwargs)

    monkeypatch.setattr(web_service_module, "_transactional_save_yolo", blocking_save)
    request = AnnotationWriteRequest(
        sessionId=service.session_id,
        format="yolo",
        labels=["object"],
        boxes=[BoxPayload(label="object", x1=5, y1=5, x2=30, y2=30)],
    )
    save_thread = Thread(target=service.save_boxes, args=(0, request))
    open_thread = Thread(target=service.open_dataset, args=(second, "yolo"))
    save_thread.start()
    assert entered_save.wait(timeout=3)
    open_thread.start()

    assert service.dataset_path == first.resolve()
    release_save.set()
    save_thread.join(timeout=3)
    open_thread.join(timeout=3)

    assert not save_thread.is_alive() and not open_thread.is_alive()
    assert (first / "frame.txt").exists()
    assert not (second / "frame.txt").exists()
    assert service.dataset_path == second.resolve()
