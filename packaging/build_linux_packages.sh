#!/bin/bash
# Build the Linux .deb and AppImage inside Ubuntu 22.04 — the oldest supported
# target — so the PyInstaller bundle carries no newer-glibc requirements.
#
# Usage (from the repo root):
#   docker run --rm -v "$PWD:/src" -w /src ubuntu:22.04 bash packaging/build_linux_packages.sh [build_dir] [version]
#
# Artifacts land in <build_dir>/packages/ (default build-linux/). The
# optional version arg overrides OPVIEW_VERSION (default 2.1.0, see
# CMakeLists.txt); leave empty to keep the default.
set -e
export DEBIAN_FRONTEND=noninteractive

BUILD_DIR=${1:-build-linux}
VERSION=${2:-}

echo "=== Installing build prerequisites ==="
apt-get update -q
apt-get install -y -q python3 python3-venv python3-pip binutils ca-certificates file >/dev/null
# System libs that must be present BEFORE freezing: PyInstaller bundles the
# dependency closure of the Qt/VTK libraries from this environment (e.g.
# libglib-2.0, libxkbfile, the GTK theme + audio stacks) and deliberately
# excludes the rest (glibc, libGL, xcb, NSS, wayland, ...), which the
# frozen-app smoke test below still needs to import Qt. Missing bundleable
# libs surface only at runtime on machines that lack them — keep this list
# in sync with what the desktop dev machines have.
apt-get install -y -q libglib2.0-0 \
    libgl1 libegl1 libopengl0 libfontconfig1 libdbus-1-3 \
    libnss3 libnspr4 libasound2 libxkbcommon0 libxkbcommon-x11-0 \
    libx11-xcb1 libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
    libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-xkb1 \
    libxcomposite1 libxdamage1 libxrandr2 libxtst6 libsm6 libice6 \
    libdrm2 libgbm1 libcups2 \
    libxkbfile1 libxcursor1 libxi6 libxinerama1 libxres1 \
    libgtk-3-0 liblcms2-2 \
    libpulse0 libsndfile1 libflac8 libopus0 libvorbisenc2 libogg0 \
    libmpg123-0 libmp3lame0 \
    libseccomp2 libunistring2 libatomic1 libapparmor1 >/dev/null
# Ubuntu 22.04's apt cmake is 3.22 which works, but pip provides a current one
python3 -m pip install --quiet "cmake>=3.22"

echo "=== Configure + freeze ==="
cmake -S . -B "$BUILD_DIR" -DOPVIEW_VERSION="$VERSION"
cmake --build "$BUILD_DIR"

echo "=== Smoke test ==="
ctest --test-dir "$BUILD_DIR" -R opview_frozen_version --output-on-failure

echo "=== .deb ==="
cpack --config "$BUILD_DIR/CPackConfig.cmake" -B "$(pwd)/$BUILD_DIR/packages"

echo "=== AppImage ==="
cmake --build "$BUILD_DIR" --target opview_appimage

# When run via docker as root on a mounted checkout, hand the build tree back
# to the host user
chown -R "$(stat -c %u:%g .)" "$BUILD_DIR" || true

ls -lh "$BUILD_DIR/packages/"
