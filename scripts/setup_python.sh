#!/bin/bash
# Download portable Python bundles for VEX IQ Simulator
# Uses python-build-standalone for consistent cross-platform builds
# https://github.com/indygreg/python-build-standalone

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

PYTHON_VERSION="3.11.9"
RELEASE_DATE="20240814"
RELEASE_TAG="${RELEASE_DATE}"

# Download URLs from python-build-standalone
BASE_URL="https://github.com/indygreg/python-build-standalone/releases/download/${RELEASE_TAG}"

LINUX_FILE="cpython-${PYTHON_VERSION}+${RELEASE_TAG}-x86_64-unknown-linux-gnu-install_only.tar.gz"
WINDOWS_FILE="cpython-${PYTHON_VERSION}+${RELEASE_TAG}-x86_64-pc-windows-msvc-shared-install_only.tar.gz"

LINUX_URL="${BASE_URL}/${LINUX_FILE}"
WINDOWS_URL="${BASE_URL}/${WINDOWS_FILE}"

download_and_extract() {
    local url="$1"
    local output_dir="$2"
    local filename="$3"

    echo "Downloading ${filename}..."

    if [ -d "$output_dir" ]; then
        echo "  Directory $output_dir already exists, skipping..."
        return
    fi

    mkdir -p "$output_dir"
    cd "$output_dir"

    # Download
    curl -L -o "${filename}" "${url}"

    # Extract
    echo "Extracting..."
    tar -xzf "${filename}"

    # Move contents from python/ subdirectory to current dir
    if [ -d "python" ]; then
        mv python/* .
        rmdir python
    fi

    # Cleanup
    rm "${filename}"

    echo "  Done: $output_dir"
}

echo "Setting up portable Python for VEX IQ Simulator"
echo "================================================"
echo ""

# Determine which platform to download
case "$1" in
    linux)
        download_and_extract "$LINUX_URL" "$PROJECT_ROOT/python-linux" "$LINUX_FILE"
        ;;
    windows)
        download_and_extract "$WINDOWS_URL" "$PROJECT_ROOT/python-win" "$WINDOWS_FILE"
        ;;
    all|"")
        download_and_extract "$LINUX_URL" "$PROJECT_ROOT/python-linux" "$LINUX_FILE"
        download_and_extract "$WINDOWS_URL" "$PROJECT_ROOT/python-win" "$WINDOWS_FILE"
        ;;
    *)
        echo "Usage: $0 [linux|windows|all]"
        exit 1
        ;;
esac

echo ""
echo "Python bundles ready!"
echo "  Linux:   $PROJECT_ROOT/python-linux/bin/python3"
echo "  Windows: $PROJECT_ROOT/python-win/python.exe"
