"""
Batch convert LDraw .dat files to GLB with VERTEX COLORS preserving part colors.
Run with: blender --background --python blender_ldraw_to_glb_vertex_colors.py

This version bakes vertex colors with the following logic:
- Color 16 (Main Color / inherit) -> WHITE (1,1,1) -> takes MPD entity color
- All other colors -> actual LDraw color -> preserved regardless of MPD color

This matches how LDCad works: only "main color" areas change when you set
the part color; other colored sections (buttons, labels, etc.) stay fixed.

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

# LDraw color lookup table (from LDConfig.ldr)
# Format: color_code -> (R, G, B, A) in 0-1 range
LDRAW_COLORS = {
    0: (0.13, 0.13, 0.13, 1.0),      # Black
    1: (0.0, 0.20, 0.70, 1.0),       # Blue
    2: (0.0, 0.55, 0.08, 1.0),       # Green
    4: (0.77, 0.0, 0.15, 1.0),       # Red
    7: (0.60, 0.60, 0.60, 1.0),      # Light Gray
    8: (0.40, 0.40, 0.40, 1.0),      # Dark Gray
    14: (1.0, 0.84, 0.0, 1.0),       # Yellow
    15: (1.0, 1.0, 1.0, 1.0),        # White
    16: (1.0, 1.0, 1.0, 1.0),        # Main Color (inherit) -> WHITE = colorable
    24: (0.50, 0.50, 0.50, 1.0),     # Edge Color
    70: (0.15, 0.16, 0.16, 1.0),     # VEX Black
    71: (0.70, 0.71, 0.70, 1.0),     # VEX Light Gray
    72: (0.33, 0.35, 0.35, 1.0),     # VEX Dark Gray
    73: (0.82, 0.15, 0.19, 1.0),     # VEX Red
    74: (0.00, 0.59, 0.22, 1.0),     # VEX Green
    75: (0.00, 0.47, 0.78, 1.0),     # VEX Blue
    76: (1.00, 0.80, 0.00, 1.0),     # VEX Yellow
    77: (0.85, 0.85, 0.84, 1.0),     # VEX White
    78: (1.00, 0.40, 0.12, 1.0),     # VEX Orange
    79: (0.37, 0.15, 0.62, 1.0),     # VEX Purple
    80: (0.54, 0.55, 0.55, 1.0),     # VEX Medium Gray
    256: (0.13, 0.13, 0.13, 1.0),    # Rubber_Black
    375: (0.40, 0.40, 0.40, 1.0),    # Rubber_Grey
    494: (0.70, 0.55, 0.35, 1.0),    # Electric_Contact_Copper
}

# White marker for colorable areas (color 16)
WHITE_MASK = (1.0, 1.0, 1.0, 1.0)
# Default for unknown colors
DEFAULT_COLOR = (0.5, 0.5, 0.5, 1.0)


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


def get_vertex_color_from_name(mat_name):
    """
    Extract LDraw color code from material name and return vertex color.

    - Color 16 (Main Color) -> WHITE (1,1,1) -> will take entity color in shader
    - All other colors -> actual LDraw color -> preserved as-is

    This matches LDCad behavior: only "main color" areas are colorable.
    """
    if not mat_name:
        return WHITE_MASK  # Default: colorable

    try:
        if mat_name.startswith("("):
            parts = mat_name.strip("()").split(",")
            code_str = parts[0].strip().strip("'\"")
            code = int(code_str)
            # Color 16 = Main Color = colorable = WHITE
            if code == 16:
                return WHITE_MASK
            # All other colors: return the actual LDraw color
            return LDRAW_COLORS.get(code, DEFAULT_COLOR)
    except (ValueError, IndexError):
        pass

    return WHITE_MASK  # Default: colorable


def bake_vertex_colors(obj):
    """Bake LDraw colors into vertex colors.

    - White (1,1,1) for color 16 areas = colorable via entity color
    - Actual colors for everything else = preserved as-is
    """
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

    # Get vertex color for each material
    mat_colors = {}
    for i, mat in enumerate(mesh.materials):
        mat_name = mat.name if mat else None
        mat_colors[i] = get_vertex_color_from_name(mat_name)

    # Apply colors to each face based on material index
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
    print("Blender LDraw to GLB Batch Converter (PRESERVE COLORS)")
    print("  Color 16 (Main Color) = WHITE = colorable via MPD")
    print("  All other colors = preserved as-is")
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
