# What to put in the depend folder

This folder is intended for the "portable / no-install" setup. Once the dependencies are placed here, the entire software directory can be copied to any computer and used by double-clicking `启动start.bat`, without changing system environment variables.

## 1. Directory structure

```text
DJI_Color_Space\
├─ 启动start.bat
├─ app.py
├─ web\
└─ depend\
   ├─ readme_depend.md        ← This file
   ├─ python\
   │  └─ python.exe           ← Put Python here
   └─ ffmpeg.exe              ← Put ffmpeg here (or in depend\bin\ffmpeg.exe)
```

## 2. Where to put Python

### 1. Necessity

- For **scanning, recognition, and renaming** only: Python 3 is all you need; ffmpeg and Pillow are not required.
- To use **frame saturation/contrast analysis**: Pillow and ffmpeg are also needed.

### 2. Recommended placement

Install Python 3.12 or higher anywhere, then copy the installation directory to:

```text
depend\python\
```

Make sure this file exists:

```text
depend\python\python.exe
```

`启动start.bat` will look for it first.

### 3. Official download

Python official website: <https://www.python.org/downloads/windows/>

Download **Windows installer (64-bit)**. It is recommended to check **Add Python to PATH** during installation; even if you don't, as long as you place it in `depend\python\` as described above, the startup script will still find it.

## 3. Where to put Pillow (only needed for frame analysis)

Pillow is a Python library, not an exe. Install it into the Python at `depend\python\`:

```bat
depend\python\python.exe -m pip install pillow
```

Verify:

```bat
depend\python\python.exe -c "import PIL; print('Pillow OK')"
```

Seeing `Pillow OK` means it worked.

## 4. Where to put ffmpeg (only needed for frame analysis)

### 1. Official download

- Recommended: <https://www.gyan.dev/ffmpeg/builds/>, download `ffmpeg-release-essentials.zip`
- Alternative: <https://ffmpeg.org/download.html>

### 2. Placement

Extract the downloaded package, find `bin\ffmpeg.exe` inside it, and copy it to any of the following locations:

```text
depend\ffmpeg.exe
depend\bin\ffmpeg.exe
```

The program searches in this order: `DJI_FFMPEG` environment variable → PATH → imageio-ffmpeg → `bin/` → `depend/` → `depend/bin/` → WorkBuddy venv.

Verify:

```bat
depend\ffmpeg.exe -version
```

Being able to print the version number means it worked.

## 5. Launch and verification

Double-click `启动start.bat`. The first line in the console shows the actual Python path being used, for example:

```text
正在使用 Python 解释器：G:\...\DJI_Color_Space\depend\python\python.exe
Python interpreter: G:\...\DJI_Color_Space\depend\python\python.exe
```

If Pillow or ffmpeg is not installed properly, a warning will appear; scanning and renaming will still work, only frame analysis will be unavailable.

## 6. FAQ

| Issue | Solution |
|---|---|
| Closes immediately after double-clicking | Open via a mapped drive letter, for example `W:\...\启动start.bat`, not through a UNC path |
| Reports no Python | Confirm that `depend\python\python.exe` exists, or install Python 3.12+ and check Add Python to PATH |
| Reports missing ffmpeg | Put `ffmpeg.exe` in `depend\` or `depend\bin\` |
| Reports missing Pillow | Run `depend\python\python.exe -m pip install pillow` |
| Switching computers | Just copy the entire software directory along with `depend\` |
