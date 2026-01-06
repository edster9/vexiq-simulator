#!/usr/bin/env python3
"""
FreeCAD STEP to OBJ Converter
=============================
Converts VEX IQ STEP files to OBJ format using FreeCAD.

Usage:
    python3 freecad_convert_step.py input.step output.obj
    python3 freecad_convert_step.py /path/to/parts/ /path/to/output/
"""

import sys
import os

# Add FreeCAD library path
FREECAD_LIB_PATHS = [
    '/usr/lib/freecad/lib',
    '/usr/lib/freecad-python3/lib',
    '/usr/share/freecad/lib',
]

for path in FREECAD_LIB_PATHS:
    if os.path.exists(path) and path not in sys.path:
        sys.path.insert(0, path)

# FreeCAD imports
try:
    import FreeCAD
    import Part
    import Mesh
    import MeshPart
except ImportError as e:
    print(f"Error: FreeCAD modules not available: {e}")
    print("Install FreeCAD: sudo apt-get install freecad-python3")
    sys.exit(1)


def convert_step_to_obj(input_path: str, output_path: str, mesh_quality: float = 0.1) -> bool:
    """Convert a STEP file to OBJ format.

    Args:
        input_path: Path to input STEP file
        output_path: Path for output OBJ file
        mesh_quality: Mesh tessellation quality (lower = finer mesh)

    Returns:
        True if conversion succeeded
    """
    try:
        print(f"Loading: {input_path}")

        # Load the STEP file
        shape = Part.Shape()
        shape.read(input_path)

        if shape.isNull():
            print(f"  Error: Failed to load shape from {input_path}")
            return False

        print(f"  Shape loaded: {shape.ShapeType}")
        print(f"  Bounding box: {shape.BoundBox}")

        # Create mesh from shape
        print(f"  Tessellating with quality={mesh_quality}...")
        mesh = MeshPart.meshFromShape(
            Shape=shape,
            LinearDeflection=mesh_quality,
            AngularDeflection=0.5,
            Relative=False
        )

        print(f"  Mesh created: {mesh.CountPoints} vertices, {mesh.CountFacets} faces")

        # Export to OBJ
        mesh.write(output_path)

        # Verify output
        if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
            print(f"  Saved: {output_path} ({os.path.getsize(output_path)} bytes)")
            return True
        else:
            print(f"  Error: Output file invalid or too small")
            return False

    except Exception as e:
        print(f"  Error converting {input_path}: {e}")
        return False


def convert_step_to_stl(input_path: str, output_path: str, mesh_quality: float = 0.1) -> bool:
    """Convert a STEP file to STL format.

    Args:
        input_path: Path to input STEP file
        output_path: Path for output STL file
        mesh_quality: Mesh tessellation quality (lower = finer mesh)

    Returns:
        True if conversion succeeded
    """
    try:
        print(f"Loading: {input_path}")

        # Load the STEP file
        shape = Part.Shape()
        shape.read(input_path)

        if shape.isNull():
            print(f"  Error: Failed to load shape from {input_path}")
            return False

        print(f"  Shape loaded: {shape.ShapeType}")

        # Create mesh from shape
        print(f"  Tessellating...")
        mesh = MeshPart.meshFromShape(
            Shape=shape,
            LinearDeflection=mesh_quality,
            AngularDeflection=0.5,
            Relative=False
        )

        print(f"  Mesh created: {mesh.CountPoints} vertices, {mesh.CountFacets} faces")

        # Export to STL
        mesh.write(output_path)

        if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
            print(f"  Saved: {output_path} ({os.path.getsize(output_path)} bytes)")
            return True
        else:
            print(f"  Error: Output file invalid")
            return False

    except Exception as e:
        print(f"  Error converting {input_path}: {e}")
        return False


def batch_convert(input_dir: str, output_dir: str, format: str = "obj"):
    """Convert all STEP files in a directory.

    Args:
        input_dir: Directory containing STEP files
        output_dir: Directory for output files
        format: Output format ("obj" or "stl")
    """
    os.makedirs(output_dir, exist_ok=True)

    step_files = [f for f in os.listdir(input_dir) if f.lower().endswith(('.step', '.stp'))]
    print(f"Found {len(step_files)} STEP files in {input_dir}")

    success = 0
    failed = 0

    for filename in step_files:
        input_path = os.path.join(input_dir, filename)
        base_name = os.path.splitext(filename)[0]
        output_path = os.path.join(output_dir, f"{base_name}.{format}")

        if format == "stl":
            result = convert_step_to_stl(input_path, output_path)
        else:
            result = convert_step_to_obj(input_path, output_path)

        if result:
            success += 1
        else:
            failed += 1

    print(f"\nConversion complete: {success} succeeded, {failed} failed")


def main():
    # Parse arguments - skip script name
    args = sys.argv[1:]

    if len(args) < 2:
        print("Usage: python3 freecad_convert_step.py input.step output.obj")
        print("       python3 freecad_convert_step.py input_dir/ output_dir/")
        print("\nArguments:")
        print("  input.step   - Input STEP file or directory")
        print("  output.obj   - Output OBJ file or directory")
        sys.exit(1)

    input_path = args[0]
    output_path = args[1]

    # Check if batch mode (directories)
    if os.path.isdir(input_path):
        # Determine format from output path
        fmt = "obj"
        if output_path.endswith("stl") or output_path.endswith("stl/"):
            fmt = "stl"
        batch_convert(input_path, output_path, fmt)
    else:
        # Single file conversion
        if output_path.lower().endswith('.stl'):
            convert_step_to_stl(input_path, output_path)
        else:
            convert_step_to_obj(input_path, output_path)


if __name__ == '__main__':
    main()
