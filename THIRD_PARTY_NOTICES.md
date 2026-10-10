# Third-party notices

The MIT license covers original Smart LabelImg application code and documentation. It does not replace licenses of dependencies, pretrained models, or third-party images.

- **MobileSAM:** [ChaoningZhang/MobileSAM](https://github.com/ChaoningZhang/MobileSAM), Apache-2.0. The unmodified `models/mobile_sam.pt` checkpoint is included for local inference. A copy of its upstream license is in [licenses/MobileSAM-Apache-2.0.txt](licenses/MobileSAM-Apache-2.0.txt). AI dependencies are installed separately.
- **LabelImg:** [HumanSignal/labelImg](https://github.com/HumanSignal/labelImg), MIT. Its annotation workflow and YOLO/Pascal VOC interoperability inspired this project. The upstream copyright/license notice is preserved in [licenses/LabelImg-MIT.txt](licenses/LabelImg-MIT.txt).
- **Web runtime:** Python, FastAPI, Starlette, Uvicorn, NumPy, Pillow, and OpenCV retain their respective licenses; installed package distributions provide their licensing materials.
- **Optional inference:** PyTorch, torchvision, timm, and MobileSAM retain their upstream licenses.
- **Legacy desktop source:** PySide6/Qt and PyInstaller are used by historical desktop code. They are not dependencies of the web release and their binaries are not bundled in it.
- **Examples:** `examples/web-demo/` and `examples/make_web_demo.py` are original synthetic illustrations covered by this repository's MIT license. Older example photographs retained in source history are not relicensed by this project and are excluded from the web release archive.

The web release is source plus a model checkpoint, not a redistributed Python/Qt runtime. No university, company, or upstream project endorsement is implied.
