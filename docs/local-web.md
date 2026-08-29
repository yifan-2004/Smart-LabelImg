# Smart Label 本地 Web 版

本地 Web 版使用浏览器作为界面，Python 在本机完成 MobileSAM 推理和 YOLO/VOC 文件读写。图片、模型和标注不会上传到互联网，服务只监听 `127.0.0.1`。

## macOS

安装 Python 3.11 和 Git，然后在项目目录运行：

```bash
./setup_web.sh
./run_web.sh
```

直接打开某个数据集：

```bash
./run_web.sh "/Users/your-name/datasets/vehicles"
```

## Windows 10/11

安装 Python 3.11 x64 和 Git for Windows。在项目目录打开 PowerShell：

```powershell
.\setup_web.ps1
.\run_web.ps1
```

直接打开某个数据集：

```powershell
.\run_web.ps1 -Dataset "D:\datasets\vehicles"
```

如果 PowerShell 阻止脚本，可直接使用：

```bat
setup_web.bat
run_web.bat
```

启动后浏览器会自动打开 `http://127.0.0.1:7860`。关闭运行脚本的终端即可停止服务。

## 数据集和保存

- 数据集目录中放置 JPG、JPEG、PNG、BMP、WEBP 或 TIFF 图片。
- YOLO 模式在图片旁保存同名 `.txt`，并维护 `classes.txt`。
- Pascal VOC 模式在图片旁保存同名 `.xml`。
- 每次保存都由本机 Python 直接写入数据集目录，规则与桌面版保持一致。
- `models/mobile_sam.pt` 必须保留；智能框选第一次使用时会加载模型。

## 开发

后端入口为 `smart_labelimg/web_service.py`，浏览器界面位于 `smart_labelimg/web/static/`。运行测试：

```bash
.venv-web/bin/python -m pytest -q
```

Windows：

```powershell
.\.venv-web\Scripts\python.exe -m pytest -q
```
