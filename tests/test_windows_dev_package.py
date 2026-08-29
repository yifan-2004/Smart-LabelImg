from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_windows_development_archive_contains_only_transfer_files(tmp_path: Path) -> None:
    archive = tmp_path / "Smart-Label-Windows-Development-Source.zip"
    untracked_secret = ROOT / "temporary-transfer-secret.txt"
    untracked_secret.write_text("must not be packaged", encoding="utf-8")
    try:
        subprocess.run(
            ["bash", "scripts/create_windows_dev_package.sh", str(archive)],
            cwd=ROOT,
            check=True,
        )
    finally:
        untracked_secret.unlink(missing_ok=True)

    with zipfile.ZipFile(archive) as package:
        names = set(package.namelist())

    required = {
        "Smart-Label/README.md",
        "Smart-Label/WINDOWS-DEVELOPMENT.md",
        "Smart-Label/setup_windows.bat",
        "Smart-Label/setup_windows.ps1",
        "Smart-Label/run_windows.bat",
        "Smart-Label/run_windows.ps1",
        "Smart-Label/build_windows.bat",
        "Smart-Label/build_windows.ps1",
        "Smart-Label/setup.ps1",
        "Smart-Label/run.ps1",
        "Smart-Label/build_app.ps1",
        "Smart-Label/smart-labelimg.spec",
        "Smart-Label/requirements.txt",
        "Smart-Label/requirements-ai.txt",
        "Smart-Label/requirements-build.txt",
        "Smart-Label/pyproject.toml",
        "Smart-Label/smart_labelimg/app.py",
        "Smart-Label/tests/test_app_smoke.py",
        "Smart-Label/assets/AppIcon-1024.png",
        "Smart-Label/models/mobile_sam.pt",
        "Smart-Label/requirements-web.txt",
        "Smart-Label/setup_web.ps1",
        "Smart-Label/run_web.ps1",
        "Smart-Label/smart_labelimg/web_app.py",
        "Smart-Label/smart_labelimg/web_service.py",
        "Smart-Label/smart_labelimg/web/static/index.html",
        "Smart-Label/smart_labelimg/web/static/app.js",
        "Smart-Label/smart_labelimg/web/static/styles.css",
    }
    assert required <= names

    forbidden_parts = {".git", ".worktrees", ".venv", "build", "dist", "release", "__pycache__"}
    assert not any(forbidden_parts.intersection(Path(name).parts) for name in names)
    assert not any(name.endswith((".app/", ".command", ".icns")) for name in names)
    assert "Smart-Label/build_app.sh" not in names
    assert "Smart-Label/scripts/verify_macos_release.sh" not in names
    assert "Smart-Label/temporary-transfer-secret.txt" not in names
