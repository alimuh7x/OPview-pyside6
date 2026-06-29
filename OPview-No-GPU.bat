@echo off
setlocal enabledelayedexpansion
title OPview - No GPU / Software Rendering
cd /d "%~dp0"

echo ================================================
echo   OPview - No GPU / Software Rendering
echo ================================================
echo.
echo [DEBUG] OPview-No-GPU.bat started
echo [DEBUG] Working directory: %CD%

rem --- Optional project path argument ---
set PROJECT_PATH=%~1
if defined PROJECT_PATH (
    echo [DEBUG] Project path argument: "%PROJECT_PATH%"
    if not exist "%PROJECT_PATH%\" (
        echo [ERROR] Project path does not exist or is not a directory: "%PROJECT_PATH%"
        pause & exit /b 1
    )
) else (
    echo [DEBUG] No project path argument provided; OPView will scan the launcher directory.
)

rem --- Force software rendering before Python, Qt, and QtWebEngine start ---
set QT_OPENGL=software
echo [DEBUG] QT_OPENGL=%QT_OPENGL%

set QT_QUICK_BACKEND=software
echo [DEBUG] QT_QUICK_BACKEND=%QT_QUICK_BACKEND%

set QTWEBENGINE_DISABLE_GPU=1
echo [DEBUG] QTWEBENGINE_DISABLE_GPU=%QTWEBENGINE_DISABLE_GPU%

set QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu --disable-gpu-compositing --disable-accelerated-2d-canvas --disable-accelerated-video-decode --disable-webgl --disable-3d-apis --disable-software-rasterizer=false --disable-features=VizDisplayCompositor --ignore-gpu-blocklist
echo [DEBUG] QTWEBENGINE_CHROMIUM_FLAGS=%QTWEBENGINE_CHROMIUM_FLAGS%

rem --- Locate Python ---
echo [DEBUG] Locating Python
set PYTHON=
for %%P in (python python3) do (
    if not defined PYTHON (
        where %%P >nul 2>&1 && set PYTHON=%%P
    )
)

if not defined PYTHON (
    echo [ERROR] Python not found.
    echo.
    echo  Please install Python 3.8 - 3.13 from:
    echo    https://www.python.org/downloads/
    echo.
    echo  IMPORTANT: Check "Add python.exe to PATH" during install.
    echo.
    pause
    start https://www.python.org/downloads/
    exit /b 1
)
echo [DEBUG] Python command: %PYTHON%

rem --- Check Python version (VTK requires < 3.14) ---
echo [DEBUG] Checking Python version
for /f "tokens=2 delims= " %%V in ('"%PYTHON%" --version 2^>^&1') do set PY_VER=%%V
echo [OK] Python %PY_VER% found

for /f "tokens=1,2 delims=." %%A in ("%PY_VER%") do (
    set PY_MAJOR=%%A
    set PY_MINOR=%%B
)
echo [DEBUG] Python major=%PY_MAJOR%
echo [DEBUG] Python minor=%PY_MINOR%

if %PY_MAJOR% LSS 3 (
    echo [ERROR] Python 3.8+ required.
    pause & exit /b 1
)
if %PY_MINOR% GTR 13 (
    echo [ERROR] Python 3.14+ is NOT compatible with VTK.
    echo  Please install Python 3.11 or 3.12 instead.
    pause & exit /b 1
)

rem --- Create venv if missing ---
echo [DEBUG] Checking virtual environment
set VENV_DIR=%~dp0venv-windows
echo [DEBUG] VENV_DIR=%VENV_DIR%

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [..] Creating virtual environment...
    "%PYTHON%" -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause & exit /b 1
    )
    echo [OK] Virtual environment created.
) else (
    echo [OK] Virtual environment already exists.
    echo [DEBUG] Checking existing virtual environment Python...
    "%VENV_DIR%\Scripts\python.exe" --version >nul 2>&1
    if errorlevel 1 (
        echo [WARN] Existing virtual environment is broken or was created on another system.
        echo [DEBUG] Removing broken virtual environment: "%VENV_DIR%"
        rmdir /s /q "%VENV_DIR%"
        if errorlevel 1 (
            echo [ERROR] Failed to remove broken virtual environment.
            pause & exit /b 1
        )
        echo [..] Recreating virtual environment with Windows Python...
        "%PYTHON%" -m venv "%VENV_DIR%"
        if errorlevel 1 (
            echo [ERROR] Failed to recreate virtual environment.
            pause & exit /b 1
        )
        echo [OK] Virtual environment recreated.
    ) else (
        echo [OK] Existing virtual environment Python works.
    )
)

set VENV_PYTHON=%VENV_DIR%\Scripts\python.exe
echo [DEBUG] VENV_PYTHON=%VENV_PYTHON%

set VENV_PIP=%VENV_DIR%\Scripts\pip.exe
echo [DEBUG] VENV_PIP=%VENV_PIP%

rem --- Upgrade pip ---
echo [..] Upgrading pip...
"%VENV_PYTHON%" -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo [ERROR] pip upgrade failed.
    pause & exit /b 1
)
echo [OK] pip up to date.

rem --- Install dependencies ---
echo [..] Installing dependencies (PySide6, VTK, NumPy, Matplotlib, PyVista, SciPy)...
echo     First run may take several minutes.
"%VENV_PIP%" install -r "%~dp0requirements.txt" --quiet
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    echo  Try running again or check your internet connection.
    pause & exit /b 1
)
echo [OK] Dependencies installed.

rem --- Launch app ---
echo.
echo [>>] Launching OPview in no-GPU software rendering mode...
echo [DEBUG] main.py path: %~dp0main.py
if defined PROJECT_PATH (
    echo [DEBUG] Running: "%VENV_PYTHON%" "%~dp0main.py" "%PROJECT_PATH%"
    "%VENV_PYTHON%" "%~dp0main.py" "%PROJECT_PATH%"
) else (
    echo [DEBUG] Running: "%VENV_PYTHON%" "%~dp0main.py"
    "%VENV_PYTHON%" "%~dp0main.py"
)

if errorlevel 1 (
    echo.
    echo [ERROR] Application exited with an error.
    pause
)
