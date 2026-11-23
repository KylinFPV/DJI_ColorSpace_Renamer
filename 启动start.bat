@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
setlocal EnableDelayedExpansion
rem Portable launcher - no machine-specific absolute paths.
rem Override with: set DJI_PYTHON=C:\full\path\to\python.exe
rem Candidates: DJI_PYTHON > project-local depend\python > WorkBuddy default venv
rem             > project-local .venv/venv > PATH python > py launcher.
rem Round 1 prefers a Python with Pillow + imageio-ffmpeg (/api/analyze).
rem Round 2 accepts any working Python (core scan/rename needs stdlib only).
set "PY="
set "PARGS="
set "FULLDEPS=1"

if defined DJI_PYTHON if exist "!DJI_PYTHON!" set "PY=!DJI_PYTHON!"
if defined PY goto run

call :pick "%~dp0depend\python\python.exe"
if not defined PY call :pick "%~dp0depend\python\Scripts\python.exe"
if not defined PY call :pick "!USERPROFILE!\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
if not defined PY call :pick "%~dp0.venv\Scripts\python.exe"
if not defined PY call :pick "%~dp0venv\Scripts\python.exe"
if not defined PY call :pick "python"
if not defined PY call :pick "py" -3

if not defined PY set "FULLDEPS=0"
if not defined PY call :pick "%~dp0depend\python\python.exe"
if not defined PY call :pick "%~dp0depend\python\Scripts\python.exe"
if not defined PY call :pick "!USERPROFILE!\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
if not defined PY call :pick "%~dp0.venv\Scripts\python.exe"
if not defined PY call :pick "%~dp0venv\Scripts\python.exe"
if not defined PY call :pick "python"
if not defined PY call :pick "py" -3
if not defined PY goto noPython

:run
rem Final dependency check on the actually selected interpreter. This also covers
rem an explicit DJI_PYTHON override, which skips the two probe rounds above.
"!PY!" !PARGS! -c "import PIL, imageio_ffmpeg" >nul 2>&1
if errorlevel 1 set "FULLDEPS=0"
echo 正在使用 Python 解释器：!PY! !PARGS!
echo Python interpreter: !PY! !PARGS!
if "!FULLDEPS!"=="0" (
  echo 提示：未找到同时具备 Pillow + imageio-ffmpeg 的解释器，已用备选 Python；改名不受影响。
  echo Tip: No interpreter with both Pillow + imageio-ffmpeg; using a fallback Python; renaming is unaffected.
  echo       画面分析仍可用：Pillow 就绪且 ffmpeg 在 PATH、depend\ 或 bin\ 中即可。
  echo       Analysis still works when Pillow is present and ffmpeg is on PATH or in depend\ / bin\.
  echo       如需消警：python -m pip install imageio-ffmpeg；若 Pillow 也缺，再装 pillow。
  echo       To silence: python -m pip install imageio-ffmpeg; add pillow if it is also missing.
)
echo 正在启动本地页面；关闭此窗口即可退出程序。
echo Starting local page; close this window to stop.
"!PY!" !PARGS! app.py
set "RC=!ERRORLEVEL!"
echo 程序已退出。按任意键关闭窗口。
echo Exited. Press any key to close this window.
pause
exit /b !RC!

:pick
set "C=%~1"
set "A=%~2"
if /i not "!C!"=="python" if /i not "!C!"=="py" if not exist "!C!" exit /b 1
if "!FULLDEPS!"=="1" (
  "!C!" !A! -c "import PIL, imageio_ffmpeg" >nul 2>&1
) else (
  "!C!" !A! -c "pass" >nul 2>&1
)
if errorlevel 1 exit /b 1
set "PY=!C!"
set "PARGS=!A!"
exit /b 0

:noPython
echo [错误] 没有找到可用的 Python。
echo [ERROR] No usable Python found.
echo         可把 python.exe 放到 depend\python\，或安装 Python 3.12+ 并勾选 Add Python to PATH，也可设置 DJI_PYTHON。
echo         Put python.exe in depend\python\, install Python 3.12+ with Add Python to PATH, or set DJI_PYTHON.
pause
exit /b 1
