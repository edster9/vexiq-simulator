"""
Batch convert LDraw .dat files to optimized GLB using Blender with ExportLDraw addon.
Run with: blender --background --python blender_ldraw_to_glb_optimized.py

Adds decimation (50%) and weighted normals for smaller file size while keeping quality.

Requires: ExportLDraw addon installed in Blender
          https://github.com/cuddlyogre/ExportLDraw

Source: C:/Apps/VEXIQ_2018-01-19/parts/*.dat
Output: WSL path models/ldraw/glb_optimized/
"""

import bpy
import os
from pathlib import Path

# Settings
LDRAW_LIBRARY = r"C:\Apps\VEXIQ_2018-01-19"
INPUT_DIR = os.path.join(LDRAW_LIBRARY, "parts")
OUTPUT_DIR = r"\\wsl$\Ubuntu-24.04\home\edster\projects\esahakian\vexiq\models\ldraw\glb_optimized"

# Optimization settings
DECIMATE_RATIO = 0.5  # Keep 50% of faces

# Skip v2 variants and subpart files (we want main parts only)
SKIP_PATTERNS = ['-v2', 's01', 's02', 's03', 's04', 's05']


def should_skip(filename):
    """Check if file should be skipped (variants, subparts)."""
    name_lower = filename.lower()
    for pattern in SKIP_PATTERNS:
        if pattern in name_lower:
            return True
    return False


def clear_scene():
    """Remove all objects from scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    # Clear orphan data
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)


def process_ldraw(input_path, output_path):
    """Process single LDraw .dat file to optimized GLB."""
    clear_scene()

    # Import using ExportLDraw addon
    try:
        result = bpy.ops.ldraw_exporter.import_operator(
            filepath=input_path,
            ldraw_path=LDRAW_LIBRARY,
            resolution='Standard',
            shade_smooth=True,
            remove_doubles=True,
            merge_distance=0.05,
            meta_bfc=True,
            import_edges=False,
            use_freestyle_edges=False,
            parent_to_empty=False,
            display_logo=False,
            no_studs=False,
        )
    except Exception as e:
        return False, f"Import error: {e}"

    # Get imported mesh objects
    mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']

    if not mesh_objects:
        return False, "No mesh imported"

    original_faces = sum(len(obj.data.polygons) for obj in mesh_objects)

    # Join all objects if multiple
    if len(mesh_objects) > 1:
        bpy.ops.object.select_all(action='DESELECT')
        for obj in mesh_objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = mesh_objects[0]
        bpy.ops.object.join()
        obj = bpy.context.active_object
    else:
        obj = mesh_objects[0]
        bpy.context.view_layer.objects.active = obj

    # Select the object
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)

    # Apply Decimate modifier (50% reduction)
    mod = obj.modifiers.new(name='Decimate', type='DECIMATE')
    mod.ratio = DECIMATE_RATIO
    bpy.ops.object.modifier_apply(modifier='Decimate')

    # Apply smooth shading
    bpy.ops.object.shade_smooth()

    # Apply Weighted Normal modifier for better shading
    mod = obj.modifiers.new(name='WeightedNormal', type='WEIGHTED_NORMAL')
    mod.weight = 50
    mod.keep_sharp = True
    bpy.ops.object.modifier_apply(modifier='WeightedNormal')

    final_faces = len(obj.data.polygons)

    # Clear materials (we apply colors at runtime in Ursina)
    if obj and obj.data:
        obj.data.materials.clear()

    # Select for export
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)

    # Export GLB
    bpy.ops.export_scene.gltf(
        filepath=output_path,
        export_format='GLB',
        use_selection=True,
        export_apply=True,
        export_materials='NONE',
    )

    return True, f"{original_faces} -> {final_faces} faces"


def main():
    print("\n" + "=" * 60)
    print("Blender LDraw to OPTIMIZED GLB Batch Converter")
    print("=" * 60)
    print(f"Input:  {INPUT_DIR}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"LDraw Library: {LDRAW_LIBRARY}")
    print(f"Decimate Ratio: {DECIMATE_RATIO} (keep {int(DECIMATE_RATIO*100)}%)")
    print("=" * 60)

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Find all .dat files (skip subparts in 's' folder)
    try:
        dat_files = [f for f in os.listdir(INPUT_DIR)
                     if f.lower().endswith('.dat') and not should_skip(f)]
    except Exception as e:
        print(f"Error reading directory: {e}")
        return

    print(f"Found {len(dat_files)} .dat files to convert")
    print("-" * 60)

    total_success = 0
    total_failed = 0
    total_skipped = 0
    total_original = 0
    total_final = 0

    for i, dat_file in enumerate(sorted(dat_files)):
        input_path = os.path.join(INPUT_DIR, dat_file)
        output_file = dat_file.rsplit('.', 1)[0] + '.glb'
        output_path = os.path.join(OUTPUT_DIR, output_file)

        # Skip if already exists
        if os.path.exists(output_path):
            print(f"[{i+1}/{len(dat_files)}] Skipping (exists): {dat_file}")
            total_skipped += 1
            continue

        print(f"[{i+1}/{len(dat_files)}] Converting: {dat_file}...", end=' ', flush=True)

        try:
            result, info = process_ldraw(input_path, output_path)
            if result:
                print(f"OK ({info})")
                total_success += 1
                # Extract face counts from info
                try:
                    parts = info.split(' -> ')
                    total_original += int(parts[0])
                    total_final += int(parts[1].split()[0])
                except:
                    pass
            else:
                print(f"FAILED: {info}")
                total_failed += 1
        except Exception as e:
            print(f"ERROR: {e}")
            total_failed += 1

    print("\n" + "=" * 60)
    print(f"COMPLETE!")
    print(f"  Converted: {total_success}")
    print(f"  Skipped:   {total_skipped}")
    print(f"  Failed:    {total_failed}")
    print(f"  Original faces: {total_original:,}")
    print(f"  Final faces:    {total_final:,}")
    if total_original > 0:
        reduction = (1 - total_final / total_original) * 100
        print(f"  Reduction: {reduction:.1f}%")
    print("=" * 60)


if __name__ == '__main__':
    main()
