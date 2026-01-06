#!/usr/bin/env python3
"""
Blender Batch Decimate Script
=============================
Run with Blender in background mode to batch convert OBJ to decimated GLB.

Usage (from project root):
    blender --background --python tools/blender_batch_decimate.py -- [options]

Options:
    --input-dir DIR      Input directory with OBJ files
    --output-dir DIR     Output directory for GLB files
    --decimate RATIO     Decimate ratio (default: 0.2)
    --smooth-angle DEG   Auto smooth angle (default: 30)

Example:
    blender --background --python tools/blender_batch_decimate.py -- \
        --input-dir models/parts/obj \
        --output-dir models/parts/glb \
        --decimate 0.2
"""

import bpy
import sys
import os
from pathlib import Path


def clear_scene():
    """Remove all objects from scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


def import_obj(filepath):
    """Import OBJ file."""
    bpy.ops.wm.obj_import(filepath=filepath)
    return bpy.context.selected_objects[0] if bpy.context.selected_objects else None


def apply_decimate(obj, ratio):
    """Apply decimate modifier."""
    mod = obj.modifiers.new(name='Decimate', type='DECIMATE')
    mod.ratio = ratio
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier='Decimate')


def apply_weighted_normal(obj):
    """Apply weighted normal modifier for smooth shading."""
    mod = obj.modifiers.new(name='WeightedNormal', type='WEIGHTED_NORMAL')
    mod.weight = 50
    mod.keep_sharp = True
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier='WeightedNormal')


def apply_smooth_shading(obj, angle=30):
    """Apply smooth shading with auto smooth."""
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()

    # Enable auto smooth (Blender 4.0+ uses different method)
    if hasattr(obj.data, 'use_auto_smooth'):
        obj.data.use_auto_smooth = True
        obj.data.auto_smooth_angle = angle * (3.14159 / 180)


def export_glb(filepath):
    """Export scene as GLB."""
    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format='GLB',
        use_selection=True,
        export_apply=True
    )


def process_obj(input_path, output_path, decimate_ratio=0.2, smooth_angle=30):
    """Process single OBJ file."""
    clear_scene()

    # Import
    obj = import_obj(input_path)
    if not obj:
        return False, "Import failed"

    original_faces = len(obj.data.polygons)

    # Select object
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # Apply decimate
    apply_decimate(obj, decimate_ratio)
    final_faces = len(obj.data.polygons)

    # Apply smooth shading
    apply_smooth_shading(obj, smooth_angle)

    # Apply weighted normal
    apply_weighted_normal(obj)

    # Select for export
    obj.select_set(True)

    # Export
    export_glb(output_path)

    return True, f"{original_faces} -> {final_faces} faces"


def batch_process(input_dir, output_dir, decimate_ratio=0.2, smooth_angle=30):
    """Process all OBJ files in directory."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    obj_files = list(input_path.glob('*.obj'))
    print(f"Found {len(obj_files)} OBJ files")

    success = 0
    failed = 0

    for i, obj_file in enumerate(obj_files):
        glb_file = output_path / (obj_file.stem + '.glb')

        # Skip if already exists
        if glb_file.exists():
            print(f"[{i+1}/{len(obj_files)}] Skipping (exists): {obj_file.name}")
            success += 1
            continue

        print(f"[{i+1}/{len(obj_files)}] Processing: {obj_file.name}...", end=' ', flush=True)

        result, info = process_obj(
            str(obj_file),
            str(glb_file),
            decimate_ratio,
            smooth_angle
        )

        if result:
            print(f"OK ({info})")
            success += 1
        else:
            print(f"FAILED: {info}")
            failed += 1

    return success, failed


def main():
    # Parse arguments after '--'
    argv = sys.argv
    if '--' in argv:
        argv = argv[argv.index('--') + 1:]
    else:
        argv = []

    # Defaults
    input_dir = 'models/parts/obj'
    output_dir = 'models/parts/glb'
    decimate_ratio = 0.2
    smooth_angle = 30

    # Parse args
    i = 0
    while i < len(argv):
        if argv[i] == '--input-dir' and i + 1 < len(argv):
            input_dir = argv[i + 1]
            i += 2
        elif argv[i] == '--output-dir' and i + 1 < len(argv):
            output_dir = argv[i + 1]
            i += 2
        elif argv[i] == '--decimate' and i + 1 < len(argv):
            decimate_ratio = float(argv[i + 1])
            i += 2
        elif argv[i] == '--smooth-angle' and i + 1 < len(argv):
            smooth_angle = float(argv[i + 1])
            i += 2
        else:
            i += 1

    print(f"Input: {input_dir}")
    print(f"Output: {output_dir}")
    print(f"Decimate ratio: {decimate_ratio}")
    print(f"Smooth angle: {smooth_angle}°")
    print()

    success, failed = batch_process(input_dir, output_dir, decimate_ratio, smooth_angle)

    print(f"\nComplete: {success} success, {failed} failed")


if __name__ == '__main__':
    main()
