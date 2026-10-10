# Local web guide

## Install and launch

Use Python 3.11 or newer for manual annotation. Python 3.11 is the tested AI configuration. Setup creates an isolated `.venv-web` environment in the project folder; it does not install a desktop application.

| System | Setup | Start |
|---|---|---|
| macOS / Linux | `./setup_web.sh` | `./run_web.sh` |
| Windows PowerShell | `.\setup_web.ps1` | `.\run_web.ps1` |
| Windows batch | `setup_web.bat` | `run_web.bat` |

Install AI dependencies with `./setup_web.sh --ai` or `.\setup_web.ps1 -AI`. They include PyTorch, torchvision, timm, and MobileSAM from a pinned upstream commit. The repository includes the original MobileSAM checkpoint. Manual annotation does not load it.

To open the demo immediately:

```bash
./run_web.sh examples/web-demo
```

For another port or to suppress automatic browser opening:

```bash
.venv-web/bin/python -m smart_labelimg.web_app --port 7861 --no-browser
```

On Windows, replace `.venv-web/bin/python` with `.\.venv-web\Scripts\python.exe`. Stop with `Ctrl+C`.

## Data and annotation

Enter a folder path on the computer running Python. Relative paths resolve from the project directory when launched with the supplied scripts. Supported images: JPG, JPEG, PNG, BMP, WEBP, TIF, and TIFF. Subdirectories are scanned recursively.

YOLO saves same-stem `.txt` files and `classes.txt`; VOC saves same-stem `.xml` files. Use a consistent class order and save format within each dataset. Copy or back up existing datasets before editing: changes are automatically written to disk after a short delay. The saved/error indicator reflects write status. In-memory undo history is per image and resets when navigating or reloading.

MobileSAM refines geometry; it does not infer class names. Choose the class yourself and review each result. If inference fails, the interface reports the failure and retains the rough box for manual adjustment. Smart next is intended for nearby sequential frames, preserves existing target boxes, and requires explicit acceptance of low-confidence candidates. An accepted proposal is not verified ground truth.

This application serves one shared dataset session to a single local user. Keep one active editing tab. The server listens on `127.0.0.1`, rejects foreign origins/hosts, and serves only bundled frontend assets. It does not upload images, call hosted models, or provide collaboration/accounts. Do not publish its port through a tunnel or deploy it as a public service.

## Troubleshooting

- **Python missing:** install Python, reopen the terminal, and rerun setup. On macOS/Linux, `PYTHON_BIN=python3.12 ./setup_web.sh` selects an interpreter explicitly.
- **Scripts cannot execute:** run `bash setup_web.sh` and `bash run_web.sh`. On Windows use the included `.bat` launchers if PowerShell policy blocks scripts.
- **Port in use:** choose another port as shown above.
- **MobileSAM unavailable:** install AI dependencies in the same `.venv-web`, retain `models/mobile_sam.pt`, and read the displayed error. Manual mode remains available.
- **Save failed:** check folder permissions and available space. Stay on the image and save again; failed saves prevent normal navigation from discarding edits.

## Development and validation

```bash
.venv-web/bin/python -m pip install -r requirements-web-dev.txt
.venv-web/bin/python -m pytest -q tests/test_web_service.py tests/test_web_launcher.py tests/test_web_static.py tests/test_annotation_io.py tests/test_ai_backend.py tests/test_propagation.py tests/test_local_web_package.py
node --test tests/frontend/workflow.test.cjs
```

Node 20+ is needed only for frontend development tests. Runtime has no Node or frontend build requirement. Legacy desktop tests additionally require PySide6 and are outside the web package.

The browser workflow was checked on macOS: manual drawing, real MobileSAM refinement, YOLO/VOC saving, persistence after reload, navigation, copying previous boxes, undo/redo, and smart propagation. Automated checks cover annotation I/O, session changes, transactional saves, path boundaries, foreign origins, and mixed propagation results. Windows launch scripts are provided but have not been executed on Windows. Synthetic demo scenes illustrate usage, not accuracy or speed benchmarks.
