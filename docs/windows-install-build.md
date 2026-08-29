# Windows 开发、运行与打包

适用于 Windows 10/11 x64。先安装：

- [Python 3.11 x64](https://www.python.org/downloads/windows/)，安装时勾选 `Add Python to PATH`
- [Git for Windows](https://git-scm.com/download/win)

将项目源码解压或克隆到本地后，在项目根目录打开 PowerShell，依次使用以下四条命令：

```powershell
.\setup.ps1
.\run.ps1
.\.venv\Scripts\python.exe -m pytest -q
.\build_app.ps1
```

- `setup.ps1` 创建 `.venv`，并安装运行、MobileSAM 和开发依赖。
- `run.ps1` 从源码启动应用。
- 测试命令运行完整测试集。修改代码后建议重新执行。
- `build_app.ps1` 安装打包依赖、运行 PyInstaller，并生成发布 ZIP。Windows 可执行文件必须在 Windows 上构建。

主要代码位于 `smart_labelimg\`，测试位于 `tests\`。智能标注所需模型必须保留在 `models\mobile_sam.pt`。

## 构建产物

- EXE：`dist\Smart LabelImg\Smart LabelImg.exe`
- x64 发布包：`release\Smart-LabelImg-MobileSAM-Windows-x64.zip`

发布 ZIP 已包含 `models\mobile_sam.pt`。解压后运行 `Smart LabelImg\Smart LabelImg.exe` 即可。

## PowerShell 阻止脚本时

只为当前 PowerShell 会话放开限制，然后重新执行命令：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

不需要修改系统级执行策略。

## 可选参数

```powershell
.\setup.ps1 -SkipAi
.\build_app.ps1 -SkipInstall
.\build_app.ps1 -NoZip
```

`-SkipAi` 仅安装界面依赖，不能使用智能标注；`-SkipInstall` 复用现有 `.venv`；`-NoZip` 只生成 EXE 目录。
