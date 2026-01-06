"""
Batch convert all OBJ files to GLB using Blender.
Run with: blender --background --python blender_batch_all.py

Processes both parts and electronics from WSL filesystem.
"""

import bpy
import os
from pathlib import Path

# Settings
WSL_BASE = r"\\wsl$\Ubuntu-24.04\home\edster\projects\esahakian\vexiq\models"

# Parts that get lower decimation (round objects don't need as many polys)
LOW_POLY_KEYWORDS = ['wheel', 'tire', 'hub', 'tread']

# Directories to process with different decimation ratios
DIRS = [
    {
        "input": os.path.join(WSL_BASE, "electronics", "obj"),
        "output": os.path.join(WSL_BASE, "electronics", "glb"),
        "decimate": 0.2,  # Electronics - usually hidden
        "decimate_low": 0.2,  # Same for electronics
    },
    {
        "input": os.path.join(WSL_BASE, "parts", "obj"),
        "output": os.path.join(WSL_BASE, "parts", "glb"),
        "decimate": 0.3,  # Parts - more visible, need more detail
        "decimate_low": 0.05,  # Wheels/tires - round, can go very low
    },
]


def get_decimate_ratio(filename, default_ratio, low_ratio):
    """Get decimation ratio based on filename."""
    name_lower = filename.lower()
    for keyword in LOW_POLY_KEYWORDS:
        if keyword in name_lower:
            return low_ratio
    return default_ratio


def clear_scene():
    """Remove all objects from scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


def process_obj(input_path, output_path, decimate_ratio=0.19):
    """Process single OBJ file."""
    clear_scene()

    # Import OBJ
    bpy.ops.wm.obj_import(filepath=input_path)

    if not bpy.context.selected_objects:
        return False, "Import failed"

    obj = bpy.context.selected_objects[0]
    original_faces = len(obj.data.polygons)

    # Select and make active
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # Apply Decimate modifier
    mod = obj.modifiers.new(name='Decimate', type='DECIMATE')
    mod.ratio = decimate_ratio
    bpy.ops.object.modifier_apply(modifier='Decimate')
    final_faces = len(obj.data.polygons)

    # Apply smooth shading
    bpy.ops.object.shade_smooth()

    # Apply Weighted Normal modifier
    mod = obj.modifiers.new(name='WeightedNormal', type='WEIGHTED_NORMAL')
    mod.weight = 50
    mod.keep_sharp = True
    bpy.ops.object.modifier_apply(modifier='WeightedNormal')

    # Select for export
    obj.select_set(True)

    # Export GLB
    bpy.ops.export_scene.gltf(
        filepath=output_path,
        export_format='GLB',
        use_selection=True,
        export_apply=True
    )

    return True, f"{original_faces} -> {final_faces}"


def main():
    print("\n" + "=" * 50)
    print("Blender Batch OBJ to GLB Converter")
    print("=" * 50)

    total_success = 0
    total_failed = 0
    total_skipped = 0

    for dir_config in DIRS:
        input_dir = dir_config["input"]
        output_dir = dir_config["output"]
        default_ratio = dir_config.get("decimate", 0.2)
        low_ratio = dir_config.get("decimate_low", 0.15)

        print(f"\n--- Processing: {input_dir} ---")
        print(f"Default decimate: {default_ratio}, Low-poly (wheels/tires): {low_ratio}")

        # Create output dir if needed
        os.makedirs(output_dir, exist_ok=True)

        # Find all OBJ files
        try:
            obj_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.obj')]
        except Exception as e:
            print(f"Error reading directory: {e}")
            continue

        print(f"Found {len(obj_files)} OBJ files")

        for i, obj_file in enumerate(obj_files):
            input_path = os.path.join(input_dir, obj_file)
            output_file = obj_file.rsplit('.', 1)[0] + '.glb'
            output_path = os.path.join(output_dir, output_file)

            # Skip if already exists
            if os.path.exists(output_path):
                print(f"[{i+1}/{len(obj_files)}] Skipping (exists): {obj_file}")
                total_skipped += 1
                continue

            # Get ratio based on filename
            decimate_ratio = get_decimate_ratio(obj_file, default_ratio, low_ratio)
            print(f"[{i+1}/{len(obj_files)}] Converting: {obj_file} (ratio={decimate_ratio})...", end=' ', flush=True)

            try:
                result, info = process_obj(input_path, output_path, decimate_ratio)
                if result:
                    print(f"OK ({info})")
                    total_success += 1
                else:
                    print(f"FAILED: {info}")
                    total_failed += 1
            except Exception as e:
                print(f"ERROR: {e}")
                total_failed += 1

    print("\n" + "=" * 50)
    print(f"COMPLETE: {total_success} converted, {total_skipped} skipped, {total_failed} failed")
    print("=" * 50)


if __name__ == '__main__':
    main()
