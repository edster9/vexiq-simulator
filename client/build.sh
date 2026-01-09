#!/bin/bash
# Build VEX IQ Simulator client
# OS-aware: handles WSL2, Linux, and MINGW64
# Uses separate build folders so builds don't overwrite each other

set -e

cd "$(dirname "$0")"

case "$(uname -s)" in
    MINGW*|MSYS*)
        # Windows/MINGW64 - use build-windows folder
        BUILD_DIR="build-windows"
        mkdir -p "$BUILD_DIR"
        cd "$BUILD_DIR"
        echo "Building for Windows (MINGW64) in $BUILD_DIR..."
        cmake -G "MinGW Makefiles" ..
        mingw32-make -j$(nproc)
        echo "Build complete: $BUILD_DIR/vexiq_sim.exe"
        ;;
    Linux|*)
        # Linux / WSL2 - use build-linux folder
        BUILD_DIR="build-linux"
        mkdir -p "$BUILD_DIR"
        cd "$BUILD_DIR"
        echo "Building for Linux in $BUILD_DIR..."
        cmake ..
        make -j$(nproc)
        echo "Build complete: $BUILD_DIR/vexiq_sim"
        ;;
esac
