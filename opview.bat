@echo off
setlocal enabledelayedexpansion
title OPview - PySide6 VTK Viewer
cd /d "%~dp0"

echo ================================================
echo   OPview - PySide6 VTK Viewer
echo ================================================
echo.

rem --- Locate Python ---
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

rem --- Check Python version (VTK requires < 3.14) ---
for /f "tokens=2 delims= " %%V in ('"%PYTHON%" --version 2^>^&1') do set PY_VER=%%V
echo [OK] Python %PY_VER% found

for /f "tokens=1,2 delims=." %%A in ("%PY_VER%") do (
    set PY_MAJOR=%%A
    set PY_MINOR=%%B
)
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
set VENV_DIR=%~dp0venv
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
)

set VENV_PYTHON=%VENV_DIR%\Scripts\python.exe
set VENV_PIP=%VENV_DIR%\Scripts\pip.exe

rem --- Upgrade pip ---
echo [..] Upgrading pip...
"%VENV_PYTHON%" -m pip install --upgrade pip --quiet
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
echo [>>] Launching OPview...
echo.
"%VENV_PYTHON%" "%~dp0main.py"

if errorlevel 1 (
    echo.
    echo [ERROR] Application exited with an error.
    pause
)
