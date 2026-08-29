# Smart LabelImg

Smart LabelImg is a modern LabelImg-style annotation tool with YOLO TXT, Pascal VOC XML,
and local AI-assisted boxes.
The main workflow is MobileSAM-assisted: draw around an object and MobileSAM tightens the box.

## 推荐：本地 Web 版

本地 Web 版不需要安装 `.app` 或 `.exe`。浏览器只负责界面，图片保存与 MobileSAM 推理全部在本机 Python 中完成，数据不会上传互联网。

macOS：

```bash
./setup_web.sh
./run_web.sh
```

Windows：

```powershell
.\setup_web.ps1
.\run_web.ps1
```

浏览器会自动打开 `http://127.0.0.1:7860`。完整说明见
[`docs/local-web.md`](docs/local-web.md)。

## 下载 macOS App

适用于 Apple Silicon Mac：M1 / M2 / M3 / M4。

[⬇️ Download Smart LabelImg for macOS](https://github.com/3513542967-creator/Smart-Label/releases/latest/download/Smart-LabelImg-macOS-Apple-Silicon.zip)

也可以在终端一键下载并打开：

```bash
cd ~/Downloads
curl -L -O https://github.com/3513542967-creator/Smart-Label/releases/latest/download/Smart-LabelImg-macOS-Apple-Silicon.zip
unzip Smart-LabelImg-macOS-Apple-Silicon.zip
open "Smart LabelImg.app"
```

如果 macOS 提示无法打开：

```bash
xattr -dr com.apple.quarantine "Smart LabelImg.app"
open "Smart LabelImg.app"
```

注意：不要下载 GitHub 的 `Source code`，源码包里没有 `.app`。

智能框选由内置 MobileSAM 模型在本地完成。

## Windows 源码开发

Windows 10/11 x64 请安装 Python 3.11 和 Git，在项目根目录打开 PowerShell：

```powershell
.\setup.ps1
.\run.ps1
.\.venv\Scripts\python.exe -m pytest -q
.\build_app.ps1
```

生成的程序位于 `dist\Smart LabelImg\Smart LabelImg.exe`，发布包位于
`release\Smart-LabelImg-MobileSAM-Windows-x64.zip`。完整开发、执行策略与可选参数说明见
[`docs/windows-install-build.md`](docs/windows-install-build.md)。

## 快速使用

1. `Open` 打开图片或图片文件夹。
2. `Save Format` 选择 YOLO TXT 或 Pascal VOC XML。
3. `Save/Target` 选择保存位置。
4. `普通 LabelImg`：手动画矩形框。
5. `智能标注`：粗略画框，MobileSAM 自动微调。
6. 选中类别后继续画框，标注会自动保存。

常用快捷键：

- `W`：手动画框
- `S`：智能标注
- `A` / `D`：上一张 / 下一张
- `Cmd+A` / `Ctrl+A`：全选框
- `Delete`：删除框
- `Cmd+D` / `Ctrl+D`：复制框
- `Cmd+V` / `Ctrl+V`：复制上一张标注
- `Shift+D`：智能下一张
- `Cmd+S` / `Ctrl+S`：保存

## 声明与引用

Smart LabelImg 的交互和数据集保存方式参考了开源标注工具
[LabelImg](https://github.com/HumanSignal/labelImg)。LabelImg 是一个基于 Qt 的图像标注工具，支持 Pascal VOC、YOLO 等格式。

本项目内置并使用
[MobileSAM](https://github.com/ChaoningZhang/MobileSAM)
作为智能框选辅助模型。MobileSAM 是轻量化的 Segment Anything 模型实现，适合本地标注场景中的快速辅助框选。

请在二次分发或修改发布时，同时遵守本项目依赖项、LabelImg 和 MobileSAM 的开源许可证要求。更多依赖说明见
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。
