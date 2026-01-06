#!/usr/bin/env python3
"""
Blender Python script to convert STEP files to GLB (glTF binary) format.

VEX IQ parts come as STEP files, but Ursina/Panda3D needs GLB/OBJ format.
This script batch converts STEP files to GLB for use in the simulator.

Requirements:
  - Blender 4.0+ with CAD add-on enabled (Edit > Preferences > Add-ons > "Import: CAD formats")
  - Or FreeCAD for STEP import if Blender add-on not available

Usage:
  blender --background --python convert_step_to_glb.py -- input.step output.glb

  Or batch convert:
  blender --background --python convert_step_to_glb.py -- --batch input_dir/ output_dir/
"""

import bpy
import sys
import os
from pathlib import Path


def clear_scene():
    """Remove all objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    # Also clear orphan data
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)


def import_step(filepath):
    """Import a STEP file into Blender.

    Requires the CAD formats add-on to be enabled.
    """
    # Try the built-in STEP importer (Blender 4.0+ with add-on)
    try:
        bpy.ops.wm.stl_import(filepath=filepath)
        print(f"  Imported via STL importer (fallback)")
        return True
    except:
        pass

    # Try CAD formats add-on
    try:
        bpy.ops.import_scene.step(filepath=filepath)
        print(f"  Imported via STEP importer")
        return True
    except AttributeError:
        pass

    # Try alternative add-on names
    try:
        bpy.ops.import_mesh.step(filepath=filepath)
        print(f"  Imported via mesh STEP importer")
        return True
    except AttributeError:
        pass

    print(f"  ERROR: No STEP importer available!")
    print(f"  Please enable: Edit > Preferences > Add-ons > 'Import: CAD formats'")
    print(f"  Or install 'CAD Sketcher' or 'Import AutoCAD DXF/STEP' add-on")
    return False


def apply_vex_material(obj):
    """Apply a VEX IQ-style grey material to the object."""
    mat = bpy.data.materials.new(name="VEX_Grey")
    mat.use_nodes = True

    # Get the principled BSDF node
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        # VEX IQ parts are typically light grey plastic
        bsdf.inputs["Base Color"].default_value = (0.7, 0.7, 0.7, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.4
        bsdf.inputs["Specular IOR Level"].default_value = 0.3

    # Assign material to object
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


def center_and_normalize(obj, target_size=None):
    """Center object at origin and optionally scale to target size."""
    # Move origin to geometry center
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

    # Move to world origin
    obj.location = (0, 0, 0)

    # Apply transforms
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    if target_size:
        # Scale to target size (based on largest dimension)
        dims = obj.dimensions
        max_dim = max(dims)
        if max_dim > 0:
            scale_factor = target_size / max_dim
            obj.scale = (scale_factor, scale_factor, scale_factor)
            bpy.ops.object.transform_apply(scale=True)


def export_glb(filepath):
    """Export all mesh objects to GLB format."""
    # Select all mesh objects
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            obj.select_set(True)

    # Export
    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format='GLB',
        use_selection=True,
        export_apply=True,
        export_yup=True  # Y-up for Panda3D/Ursina
    )


def export_obj(filepath):
    """Export all mesh objects to OBJ format (fallback)."""
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            obj.select_set(True)

    bpy.ops.wm.obj_export(
        filepath=filepath,
        export_selected_objects=True,
        export_materials=True,
        export_uv=True,
        export_normals=True,
        forward_axis='NEGATIVE_Z',
        up_axis='Y'
    )


def convert_step_to_glb(input_path, output_path, apply_material=True):
    """Convert a single STEP file to GLB."""
    print(f"\nConverting: {input_path}")
    print(f"       To: {output_path}")

    clear_scene()

    if not import_step(input_path):
        return False

    # Get imported objects
    mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']

    if not mesh_objects:
        print(f"  ERROR: No mesh objects imported!")
        return False

    print(f"  Imported {len(mesh_objects)} mesh object(s)")

    # Join all objects into one if multiple
    if len(mesh_objects) > 1:
        bpy.ops.object.select_all(action='DESELECT')
        for obj in mesh_objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = mesh_objects[0]
        bpy.ops.object.join()
        mesh_objects = [bpy.context.active_object]

    # Process the mesh
    obj = mesh_objects[0]
    center_and_normalize(obj)

    if apply_material:
        apply_vex_material(obj)

    # Create output directory if needed
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Export
    if output_path.endswith('.glb') or output_path.endswith('.gltf'):
        export_glb(output_path)
    else:
        export_obj(output_path)

    print(f"  SUCCESS: Exported to {output_path}")
    return True


def batch_convert(input_dir, output_dir, file_filter=None):
    """Batch convert all STEP files in a directory."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    # Find all STEP files
    step_files = list(input_path.glob("*.step")) + list(input_path.glob("*.STEP"))

    if file_filter:
        # Filter by name pattern
        step_files = [f for f in step_files if file_filter.lower() in f.name.lower()]

    print(f"\n=== Batch Conversion ===")
    print(f"Input:  {input_dir}")
    print(f"Output: {output_dir}")
    print(f"Files:  {len(step_files)}")

    output_path.mkdir(parents=True, exist_ok=True)

    success = 0
    failed = 0

    for step_file in step_files:
        # Create output filename (sanitize name)
        name = step_file.stem
        # Remove part numbers in parentheses for cleaner names
        if '(' in name:
            name = name[:name.rfind('(')].strip()
        # Replace spaces and special chars
        name = name.replace(' ', '_').replace(',', '').replace('-', '_')

        output_file = output_path / f"{name}.glb"

        if convert_step_to_glb(str(step_file), str(output_file)):
            success += 1
        else:
            failed += 1

    print(f"\n=== Results ===")
    print(f"Success: {success}")
    print(f"Failed:  {failed}")

    return success, failed


def main():
    """Parse command line args and run conversion."""
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        print("Usage:")
        print("  Single file: blender --background --python convert_step_to_glb.py -- input.step output.glb")
        print("  Batch:       blender --background --python convert_step_to_glb.py -- --batch input_dir/ output_dir/ [filter]")
        sys.exit(1)

    if len(argv) >= 2 and argv[0] == "--batch":
        # Batch mode
        input_dir = argv[1]
        output_dir = argv[2] if len(argv) > 2 else "output/"
        file_filter = argv[3] if len(argv) > 3 else None
        batch_convert(input_dir, output_dir, file_filter)
    elif len(argv) >= 2:
        # Single file mode
        input_path = argv[0]
        output_path = argv[1]
        convert_step_to_glb(input_path, output_path)
    else:
        print("ERROR: Not enough arguments")
        sys.exit(1)


if __name__ == "__main__":
    main()
