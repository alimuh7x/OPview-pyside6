#!/bin/bash
set -e

echo "[DEBUG] OPview Linux launcher started"
echo "[DEBUG] Working directory: $(pwd)"

if [ -n "${OPVIEW_NO_GPU:-}" ]; then
    echo "[DEBUG] OPVIEW_NO_GPU enabled; forcing Qt WebEngine software rendering"
    export QT_OPENGL=software
    echo "[DEBUG] QT_OPENGL=$QT_OPENGL"
    export QT_QUICK_BACKEND=software
    echo "[DEBUG] QT_QUICK_BACKEND=$QT_QUICK_BACKEND"
    export QTWEBENGINE_DISABLE_GPU=1
    echo "[DEBUG] QTWEBENGINE_DISABLE_GPU=$QTWEBENGINE_DISABLE_GPU"
    export QTWEBENGINE_CHROMIUM_FLAGS="${QTWEBENGINE_CHROMIUM_FLAGS:-} --disable-gpu --disable-gpu-compositing --disable-accelerated-2d-canvas --disable-accelerated-video-decode --disable-webgl --disable-3d-apis --disable-software-rasterizer=false --disable-features=VizDisplayCompositor --ignore-gpu-blocklist"
    echo "[DEBUG] QTWEBENGINE_CHROMIUM_FLAGS=$QTWEBENGINE_CHROMIUM_FLAGS"
else
    echo "[DEBUG] OPVIEW_NO_GPU not set; using default Qt WebEngine rendering"
fi

PROJECT_PATH="${1:-}"
if [ -n "$PROJECT_PATH" ]; then
    echo "[DEBUG] Project path argument: $PROJECT_PATH"
    if [ ! -d "$PROJECT_PATH" ]; then
        echo "[ERROR] Project path does not exist or is not a directory: $PROJECT_PATH"
        exit 1
    fi
else
    echo "[DEBUG] No project path argument provided; OPView will scan the current working directory."
fi

echo "[DEBUG] Checking Python version"
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "[OK] Python $python_version found"

echo "[DEBUG] Checking virtual environment"
if [ ! -x "venv/bin/python" ]; then
    echo "[..] Creating virtual environment..."
    python3 -m venv venv
    echo "[OK] Virtual environment created."
else
    echo "[OK] Virtual environment already exists."
fi

echo "[DEBUG] Activating virtual environment"
source venv/bin/activate
echo "[DEBUG] VIRTUAL_ENV=$VIRTUAL_ENV"

echo "[..] Upgrading pip..."
python -m pip install --upgrade pip --quiet
echo "[OK] pip up to date."

echo "[..] Installing dependencies..."
echo "    First run may take several minutes."
pip install -r requirements.txt --quiet
echo "[OK] Dependencies installed."

echo "[>>] Launching OPView..."
if [ -n "$PROJECT_PATH" ]; then
    echo "[DEBUG] Running: python main.py $PROJECT_PATH"
    python main.py "$PROJECT_PATH"
else
    echo "[DEBUG] Running: python main.py"
    python main.py
fi
