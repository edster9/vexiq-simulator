"""
Batch convert LDraw .dat files to GLB with VERTEX COLORS as a COLOR MASK.
Run with: blender --background --python blender_ldraw_to_glb_vertex_colors.py

This version bakes vertex colors as a MASK:
- BLACK (0,0,0) for rubber/black areas -> stays black regardless of MPD color
- WHITE (1,1,1) for everything else -> takes the MPD color directly

This matches how LDCad works: rubber parts stay black, other parts take color.

Requires: ExportLDraw addon installed in Blender
          https://github.com/cuddlyogre/ExportLDraw

Source: C:/Apps/VEXIQ_2018-01-19/parts/*.dat
Output: WSL path models/ldraw_colored/
"""

import bpy
import os
from pathlib import Path

# Settings
LDRAW_LIBRARY = r"C:\Apps\VEXIQ_2018-01-19"
INPUT_DIR = os.path.join(LDRAW_LIBRARY, "parts")
OUTPUT_DIR = r"\\wsl$\Ubuntu-24.04\home\edster\projects\esahakian\vexiq\models\ldraw_colored"

# No skip patterns - convert all parts including v2 variants
SKIP_PATTERNS = []

# Colors that should stay BLACK (rubber, black plastic)
# These will NOT take the MPD entity color
RUBBER_BLACK_CODES = {
    0,      # Black
    256,    # Rubber_Black
    375,    # Rubber_Grey (still dark rubber)
    70,     # VEX Black
}

# Mask colors
BLACK_MASK = (0.0, 0.0, 0.0, 1.0)  # Stays black, ignores entity color
WHITE_MASK = (1.0, 1.0, 1.0, 1.0)  # Takes full entity color from MPD


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
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)


def get_mask_color_from_name(mat_name):
    """
    Extract LDraw color code from material name and return mask color.

    Returns BLACK for rubber/black parts, WHITE for everything else.
    This creates a color mask that works with MPD entity colors.
    """
    if not mat_name:
        return WHITE_MASK  # Default: take entity color

    try:
        if mat_name.startswith("("):
            parts = mat_name.strip("()").split(",")
            code_str = parts[0].strip().strip("'\"")
            code = int(code_str)
            # Return black for rubber/black, white for everything else
            if code in RUBBER_BLACK_CODES:
                return BLACK_MASK
            return WHITE_MASK
    except (ValueError, IndexError):
        pass

    return WHITE_MASK  # Default: take entity color


def bake_vertex_colors(obj):
    """Bake color mask into vertex colors (black=rubber, white=colorable)."""
    mesh = obj.data

    # Create vertex color layer (Blender 4.0+ uses color attributes)
    if hasattr(mesh, 'color_attributes'):
        if 'Col' not in mesh.color_attributes:
            mesh.color_attributes.new(name='Col', type='FLOAT_COLOR', domain='CORNER')
        color_attr = mesh.color_attributes['Col']
    else:
        if not mesh.vertex_colors:
            mesh.vertex_colors.new(name='Col')
        color_attr = mesh.vertex_colors.active

    # Get mask color for each material (black or white)
    mat_colors = {}
    for i, mat in enumerate(mesh.materials):
        mat_name = mat.name if mat else None
        mat_colors[i] = get_mask_color_from_name(mat_name)

    # Apply mask colors to each face based on material index
    for poly in mesh.polygons:
        mat_idx = poly.material_index
        col = mat_colors.get(mat_idx, WHITE_MASK)
        for loop_idx in poly.loop_indices:
            color_attr.data[loop_idx].color = col


def process_ldraw(input_path, output_path):
    """Process single LDraw .dat file to GLB with vertex colors."""
    clear_scene()

    try:
        bpy.ops.ldraw_exporter.import_operator(
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

    mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    if not mesh_objects:
        return False, "No mesh imported"

    total_faces = sum(len(obj.data.polygons) for obj in mesh_objects)

    # Bake vertex colors for each object BEFORE joining
    for obj in mesh_objects:
        bake_vertex_colors(obj)

    # Join all objects
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

    # Clear materials (vertex colors will provide the color)
    obj.data.materials.clear()

    # Select for export
    bpy.ops.object.select_all(action='DESELECT')
    if obj:
        obj.select_set(True)

    # Export GLB
    bpy.ops.export_scene.gltf(
        filepath=output_path,
        export_format='GLB',
        use_selection=True,
        export_apply=True,
        export_materials='NONE',
    )

    return True, f"{total_faces} faces"


def main():
    print("\n" + "=" * 60)
    print("Blender LDraw to GLB Batch Converter (COLOR MASK)")
    print("  Black = rubber (stays black)")
    print("  White = colorable (takes MPD color)")
    print("=" * 60)
    print(f"Input:  {INPUT_DIR}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"LDraw Library: {LDRAW_LIBRARY}")
    print("=" * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

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
    total_faces = 0

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
                try:
                    faces = int(info.split()[0])
                    total_faces += faces
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
    print(f"  Total faces: {total_faces:,}")
    print("=" * 60)


if __name__ == '__main__':
    main()
