from pathlib import Path

from fastapi.testclient import TestClient

from smart_labelimg.web_service import create_app


ROOT = Path(__file__).resolve().parents[1]


def test_local_web_launchers_are_loopback_only_and_use_separate_environment() -> None:
    launcher = (ROOT / "smart_labelimg" / "web_app.py").read_text(encoding="utf-8")
    setup_windows = (ROOT / "setup_web.ps1").read_text(encoding="utf-8")
    run_windows = (ROOT / "run_web.ps1").read_text(encoding="utf-8")
    setup_macos = (ROOT / "setup_web.sh").read_text(encoding="utf-8")
    run_macos = (ROOT / "run_web.sh").read_text(encoding="utf-8")

    assert 'host="127.0.0.1"' in launcher
    assert "webbrowser.open" in launcher
    assert ".venv-web" in setup_windows and ".venv-web" in run_windows
    assert ".venv-web" in setup_macos and ".venv-web" in run_macos
    assert "requirements-web.txt" in setup_windows
    assert "requirements-web.txt" in setup_macos
    assert "--dataset" in run_windows
    assert "--dataset" in run_macos


def test_web_requirements_do_not_install_desktop_qt() -> None:
    requirements = (ROOT / "requirements-web.txt").read_text(encoding="utf-8").lower()
    assert "fastapi" in requirements
    assert "uvicorn" in requirements
    assert "pyside" not in requirements


def test_local_web_root_serves_the_annotation_interface() -> None:
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="annotation-canvas"' in response.text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/styles.css").status_code == 200
