"""
Single file test for Blender decimation pipeline.
Run with: blender --background --python blender_test_single.py
"""

import bpy
import sys
from pathlib import Path

# Settings
INPUT_FILE = "228-2540.obj"
OUTPUT_FILE = "228-2540-blender.glb"
DECIMATE_RATIO = 0.19


def clear_scene():
    """Remove all objects from scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


def main():
    print(f"\n=== Blender Batch Test ===")
    print(f"Input: {INPUT_FILE}")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Decimate ratio: {DECIMATE_RATIO}")

    # Clear scene
    clear_scene()

    # Import OBJ
    print("Importing OBJ...")
    bpy.ops.wm.obj_import(filepath=INPUT_FILE)

    obj = bpy.context.selected_objects[0]
    print(f"Imported: {obj.name}")
    print(f"Original faces: {len(obj.data.polygons)}")

    # Select and make active
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # Apply Decimate modifier
    print(f"Applying Decimate (ratio={DECIMATE_RATIO})...")
    mod = obj.modifiers.new(name='Decimate', type='DECIMATE')
    mod.ratio = DECIMATE_RATIO
    bpy.ops.object.modifier_apply(modifier='Decimate')
    print(f"After decimate: {len(obj.data.polygons)} faces")

    # Apply smooth shading
    print("Applying smooth shading...")
    bpy.ops.object.shade_smooth()

    # Apply Weighted Normal modifier
    print("Applying Weighted Normal...")
    mod = obj.modifiers.new(name='WeightedNormal', type='WEIGHTED_NORMAL')
    mod.weight = 50
    mod.keep_sharp = True
    bpy.ops.object.modifier_apply(modifier='WeightedNormal')

    # Select for export
    obj.select_set(True)

    # Export GLB
    print(f"Exporting to {OUTPUT_FILE}...")
    bpy.ops.export_scene.gltf(
        filepath=OUTPUT_FILE,
        export_format='GLB',
        use_selection=True,
        export_apply=True
    )

    print("Done!")


if __name__ == '__main__':
    main()
