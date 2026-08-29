from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_local_web_source_package_is_self_contained_and_desktop_free(tmp_path: Path) -> None:
    archive = tmp_path / "Smart-Label-Local-Web-Source.zip"
    subprocess.run(["bash", "scripts/create_local_web_package.sh", str(archive)], cwd=ROOT, check=True)
    with zipfile.ZipFile(archive) as package:
        names = set(package.namelist())

    required = {
        "Smart-Label-Web/README.md",
        "Smart-Label-Web/docs/local-web.md",
        "Smart-Label-Web/models/mobile_sam.pt",
        "Smart-Label-Web/requirements-web.txt",
        "Smart-Label-Web/requirements-ai.txt",
        "Smart-Label-Web/setup_web.sh",
        "Smart-Label-Web/run_web.sh",
        "Smart-Label-Web/setup_web.ps1",
        "Smart-Label-Web/run_web.ps1",
        "Smart-Label-Web/smart_labelimg/web_app.py",
        "Smart-Label-Web/smart_labelimg/web_service.py",
        "Smart-Label-Web/smart_labelimg/web/static/index.html",
        "Smart-Label-Web/smart_labelimg/web/static/app.js",
        "Smart-Label-Web/smart_labelimg/web/static/styles.css",
    }
    assert required <= names
    assert not any(".app/" in name or name.endswith(".icns") for name in names)
    assert "Smart-Label-Web/smart_labelimg/app.py" not in names
    assert "Smart-Label-Web/requirements.txt" not in names
