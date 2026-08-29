# Windows Development Transfer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a clean source archive that can be copied to a Windows 10/11 x64 computer, developed there, and packaged into a Windows executable with bundled MobileSAM.

**Architecture:** Keep the existing cross-platform Python/PySide6 application unchanged. Tighten the Windows bootstrap and build scripts, document one simple workflow, and create a source-only transfer ZIP from tracked files plus the required model checkpoint while excluding macOS and generated build artifacts.

**Tech Stack:** Python 3.11, PowerShell, PySide6, PyTorch, MobileSAM, PyInstaller, ZIP.

## Global Constraints

- Target Windows 10/11 x64 with Python 3.11.
- Keep `models/mobile_sam.pt` in the transfer archive and Windows build.
- Do not include `.git`, `.worktrees`, `.venv`, `build`, `dist`, `release`, caches, or macOS `.app` artifacts.
- Build Windows `.exe` on Windows, never on macOS.
- Keep the end-user workflow limited to setup, run, test, and build commands.

---

### Task 1: Windows scripts and dependency checks

**Files:**
- Modify: `setup.ps1`
- Modify: `run.ps1`
- Modify: `build_app.ps1`
- Modify: `smart-labelimg.spec`
- Test: `tests/test_packaging_config.py`

**Interfaces:**
- Consumes: Python 3.11 and Git for Windows.
- Produces: `.venv`, source launch, `dist\Smart LabelImg\Smart LabelImg.exe`, and the Windows release ZIP.

- [ ] Add failing packaging tests for Windows-safe PyInstaller configuration and required MobileSAM inclusion.
- [ ] Run `pytest tests/test_packaging_config.py -q` and confirm the new assertions fail for the expected configuration gap.
- [ ] Make the smallest script/spec changes needed for clean Windows setup and packaging.
- [ ] Run `pytest tests/test_packaging_config.py -q` and confirm it passes.

### Task 2: Concise Windows development guide

**Files:**
- Modify: `docs/windows-install-build.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: scripts from Task 1.
- Produces: exact Windows setup, run, test, edit, and build instructions.

- [ ] Rewrite the Windows guide around Python 3.11, Git, PowerShell, and four copyable commands.
- [ ] Document the generated EXE/ZIP locations and common PowerShell execution-policy recovery.
- [ ] Remove obsolete claims and verify every documented filename exists.

### Task 3: Transfer archive generator and archive

**Files:**
- Create: `scripts/create_windows_dev_package.sh`
- Create: `tests/test_windows_dev_package.py`
- Generate: `release/Smart-Label-Windows-Development-Source.zip`

**Interfaces:**
- Consumes: repository tracked source files and `models/mobile_sam.pt`.
- Produces: a deterministic Windows development source archive with a single `Smart-Label/` root folder.

- [ ] Write a failing test that requires the archive to include Windows scripts, source, docs, icon, and MobileSAM while excluding generated/macOS-only artifacts.
- [ ] Run the focused test and confirm failure because the package generator is missing.
- [ ] Implement the archive generator using a temporary staging directory and `ditto`/`zip` without changing source files.
- [ ] Run the focused test, the complete pytest suite, generate the ZIP, extract it into a temporary directory, and validate its contents.
