#!/bin/bash
# Convert VEX IQ STEP files to GLB format for use in the simulator
#
# Usage:
#   ./tools/convert_vex_parts.sh                    # Convert key parts
#   ./tools/convert_vex_parts.sh --all              # Convert all parts
#   ./tools/convert_vex_parts.sh "wheel"            # Convert parts matching filter
#   ./tools/convert_vex_parts.sh single input.step output.glb

# Blender path (Windows via WSL)
BLENDER="/mnt/c/Program Files/Blender Foundation/Blender 5.0/blender.exe"

# Alternative paths to try
if [ ! -f "$BLENDER" ]; then
    BLENDER="/mnt/c/Program Files/Blender Foundation/Blender 4.2/blender.exe"
fi
if [ ! -f "$BLENDER" ]; then
    BLENDER="/mnt/c/Program Files/Blender Foundation/Blender/blender.exe"
fi
if [ ! -f "$BLENDER" ]; then
    # Try Linux blender
    BLENDER=$(which blender 2>/dev/null)
fi

if [ -z "$BLENDER" ] || [ ! -f "$BLENDER" ]; then
    echo "ERROR: Blender not found!"
    echo "Please install Blender or update the path in this script."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Input and output directories
STEP_DIR="/tmp/vex-parts"
OUTPUT_DIR="$PROJECT_ROOT/simulator/models/parts"

# Convert paths for Windows Blender
SCRIPT_WIN=$(wslpath -w "$SCRIPT_DIR/convert_step_to_glb.py" 2>/dev/null || echo "$SCRIPT_DIR/convert_step_to_glb.py")

echo "=== VEX IQ Parts Converter ==="
echo "Blender: $BLENDER"
echo "Script:  $SCRIPT_DIR/convert_step_to_glb.py"
echo ""

# Key parts we want for the simulator
KEY_PARTS=(
    "Tire (200 mm Travel)"
    "Tire (100 mm Travel)"
    "Tire (160 mm Travel)"
    "Large Wheel Hub (64 mm)"
    "Small Wheel Hub (44 mm)"
    "1x4 Beam"
    "1x6 Beam"
    "1x8 Beam"
    "2x Wide, 1x1 Corner Connector"
    "Hex Cup Half"
)

convert_single() {
    local input="$1"
    local output="$2"

    # Convert paths for Windows
    local input_win=$(wslpath -w "$input" 2>/dev/null || echo "$input")
    local output_win=$(wslpath -w "$output" 2>/dev/null || echo "$output")

    echo "Converting: $(basename "$input")"
    "$BLENDER" --background --python "$SCRIPT_WIN" -- "$input_win" "$output_win" 2>&1 | grep -E "^(  |Converting|SUCCESS|ERROR)"
}

convert_batch() {
    local filter="$1"

    local input_win=$(wslpath -w "$STEP_DIR" 2>/dev/null || echo "$STEP_DIR")
    local output_win=$(wslpath -w "$OUTPUT_DIR" 2>/dev/null || echo "$OUTPUT_DIR")

    echo "Batch converting from: $STEP_DIR"
    echo "                   to: $OUTPUT_DIR"
    if [ -n "$filter" ]; then
        echo "               filter: $filter"
    fi
    echo ""

    "$BLENDER" --background --python "$SCRIPT_WIN" -- --batch "$input_win" "$output_win" "$filter"
}

convert_key_parts() {
    echo "Converting key parts for simulator..."
    mkdir -p "$OUTPUT_DIR"

    for part_name in "${KEY_PARTS[@]}"; do
        # Find the STEP file
        local step_file=$(find "$STEP_DIR" -maxdepth 1 -name "*${part_name}*.step" -o -name "*${part_name}*.STEP" 2>/dev/null | head -1)

        if [ -n "$step_file" ] && [ -f "$step_file" ]; then
            # Create output filename
            local base_name=$(basename "$step_file" .step)
            base_name=$(basename "$base_name" .STEP)
            # Sanitize: remove part numbers, spaces
            local clean_name=$(echo "$base_name" | sed 's/ (228-[0-9-]*)//' | tr ' ' '_' | tr '-' '_')
            local output_file="$OUTPUT_DIR/${clean_name}.glb"

            convert_single "$step_file" "$output_file"
        else
            echo "WARNING: Part not found: $part_name"
        fi
    done
}

# Main
case "${1:-key}" in
    --all)
        convert_batch ""
        ;;
    --key|key)
        convert_key_parts
        ;;
    single)
        if [ -n "$2" ] && [ -n "$3" ]; then
            convert_single "$2" "$3"
        else
            echo "Usage: $0 single input.step output.glb"
            exit 1
        fi
        ;;
    *)
        # Treat as filter
        convert_batch "$1"
        ;;
esac

echo ""
echo "Done! Output files in: $OUTPUT_DIR"
