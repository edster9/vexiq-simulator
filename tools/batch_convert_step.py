#!/usr/bin/env python3
"""
Batch STEP to OBJ Converter
===========================
Converts all STEP files to high-quality OBJ using FreeCAD.

Usage:
    python3 batch_convert_step.py
"""

import sys
import os
from pathlib import Path

# Add FreeCAD library path
FREECAD_LIB_PATHS = [
    '/usr/lib/freecad/lib',
    '/usr/lib/freecad-python3/lib',
    '/usr/share/freecad/lib',
]

for path in FREECAD_LIB_PATHS:
    if os.path.exists(path) and path not in sys.path:
        sys.path.insert(0, path)

try:
    import FreeCAD
    import Part
    import MeshPart
except ImportError as e:
    print(f"Error: FreeCAD modules not available: {e}")
    sys.exit(1)


def convert_step_to_obj(input_path: str, output_path: str, quality: float = 0.01) -> bool:
    """Convert STEP to OBJ with high quality tessellation."""
    try:
        shape = Part.Shape()
        shape.read(input_path)

        mesh = MeshPart.meshFromShape(
            Shape=shape,
            LinearDeflection=quality,
            AngularDeflection=0.5,
            Relative=False
        )

        mesh.write(output_path)
        return True, mesh.CountFacets
    except Exception as e:
        return False, str(e)


def batch_convert(step_dir: str, obj_dir: str):
    """Convert all STEP files in a directory to OBJ."""
    step_path = Path(step_dir)
    obj_path = Path(obj_dir)
    obj_path.mkdir(parents=True, exist_ok=True)

    step_files = list(step_path.glob('*.STEP')) + list(step_path.glob('*.step')) + list(step_path.glob('*.stp'))

    print(f"Found {len(step_files)} STEP files in {step_dir}")

    success = 0
    failed = 0

    for i, step_file in enumerate(step_files):
        obj_file = obj_path / (step_file.stem + '.obj')

        # Skip if already converted
        if obj_file.exists():
            print(f"[{i+1}/{len(step_files)}] Skipping (exists): {step_file.name}")
            success += 1
            continue

        print(f"[{i+1}/{len(step_files)}] Converting: {step_file.name}...", end=' ', flush=True)

        result, info = convert_step_to_obj(str(step_file), str(obj_file))

        if result:
            print(f"OK ({info} faces)")
            success += 1
        else:
            print(f"FAILED: {info}")
            failed += 1

    return success, failed


def main():
    base_dir = Path(__file__).parent.parent / 'models'

    # Convert electronics
    print("\n=== Converting Electronics ===")
    e_success, e_failed = batch_convert(
        base_dir / 'electronics' / 'step',
        base_dir / 'electronics' / 'obj'
    )

    # Convert parts
    print("\n=== Converting Parts ===")
    p_success, p_failed = batch_convert(
        base_dir / 'parts' / 'step',
        base_dir / 'parts' / 'obj'
    )

    print("\n=== Summary ===")
    print(f"Electronics: {e_success} success, {e_failed} failed")
    print(f"Parts: {p_success} success, {p_failed} failed")
    print(f"Total: {e_success + p_success} success, {e_failed + p_failed} failed")


if __name__ == '__main__':
    main()