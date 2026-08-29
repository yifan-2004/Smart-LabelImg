from pathlib import Path
import runpy
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]


def test_pyinstaller_spec_is_windows_safe_and_bundles_mobile_sam(tmp_path, monkeypatch):
    checkpoint = tmp_path / "models" / "mobile_sam.pt"
    checkpoint.parent.mkdir()
    checkpoint.write_bytes(b"checkpoint")
    captured = {}

    def analysis(*args, **kwargs):
        captured["datas"] = kwargs["datas"]
        return SimpleNamespace(
            pure=[], scripts=[], binaries=[], datas=kwargs["datas"]
        )

    def exe(*args, **kwargs):
        captured["target_arch"] = kwargs["target_arch"]
        return object()

    def bundle(*args, **kwargs):
        raise AssertionError("Windows builds must not create a macOS app bundle")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.platform", "win32")
    runpy.run_path(
        str(ROOT / "smart-labelimg.spec"),
        init_globals={
            "Analysis": analysis,
            "PYZ": lambda *args, **kwargs: object(),
            "EXE": exe,
            "COLLECT": lambda *args, **kwargs: object(),
            "BUNDLE": bundle,
        },
    )

    assert captured["target_arch"] is None
    assert captured["datas"] == [(str(checkpoint), "models")]


def test_windows_scripts_validate_python_and_propagate_native_failures():
    setup = (ROOT / "setup.ps1").read_text(encoding="utf-8")
    run = (ROOT / "run.ps1").read_text(encoding="utf-8")
    build = (ROOT / "build_app.ps1").read_text(encoding="utf-8")

    assert "sys.version_info[:2] == (3, 11)" in setup
    assert "if ($LASTEXITCODE -ne 0)" in setup
    assert "if ($LASTEXITCODE -ne 0)" in run
    assert "if ($LASTEXITCODE -ne 0)" in build


def test_pyinstaller_spec_requires_macos_release_assets():
    spec = (ROOT / "smart-labelimg.spec").read_text(encoding="utf-8")

    assert "models/mobile_sam.pt is required" in spec
    assert "assets/AppIcon.icns is required" in spec
    assert 'target_arch="arm64"' in spec
    assert 'bundle_identifier="com.smartlabelimg.app"' in spec
    assert '"CFBundleShortVersionString": "0.1.0"' in spec
    assert '"LSMinimumSystemVersion": "12.0"' in spec


def test_release_scripts_define_expected_artifact_names():
    build = (ROOT / "build_app.sh").read_text(encoding="utf-8")
    verify = (ROOT / "scripts" / "verify_macos_release.sh").read_text(encoding="utf-8")

    assert "Smart-LabelImg-macOS-Apple-Silicon.zip" in build
    assert "Smart-LabelImg-macOS-Apple-Silicon.zip" in verify
    assert "pytest -q" in build
    assert "shasum -a 256 -c" in verify
