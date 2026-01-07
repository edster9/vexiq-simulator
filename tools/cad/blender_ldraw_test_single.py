"""
Test importing a single LDraw .dat file to verify ExportLDraw addon works.
Run with: blender --background --python blender_ldraw_test_single.py

This will help identify the correct import operator and parameters.
"""

import bpy
import os
import addon_utils

# Settings
LDRAW_LIBRARY = r"C:\Apps\VEXIQ_2018-01-19"
TEST_FILE = os.path.join(LDRAW_LIBRARY, "parts", "228-2500-014.dat")  # 1x16 Beam
OUTPUT_FILE = r"C:\Users\edste\vexiq-test\test_ldraw_beam.glb"


def enable_ldraw_addon():
    """Try to enable the LDraw addon."""
    print("\n=== Checking for LDraw Addons ===")

    # List ALL addons first to see what's available
    print("  Searching for LDraw-related addons...")
    addon_names = []
    all_addons = list(addon_utils.modules())
    print(f"  Total addons found: {len(all_addons)}")

    for mod in all_addons:
        name = mod.__name__
        name_lower = name.lower()
        # Check for ldraw in name or in module file path
        mod_file = getattr(mod, '__file__', '') or ''
        if 'ldraw' in name_lower or 'ldraw' in mod_file.lower():
            addon_names.append(name)
            # Check if enabled
            is_enabled, is_loaded = addon_utils.check(name)
            status = "ENABLED" if is_enabled else "disabled"
            print(f"    {name} [{status}] - {mod_file}")

    if not addon_names:
        print("  No LDraw addons found!")
        print("  Please install ExportLDraw addon:")
        print("    1. Download from: https://github.com/cuddlyogre/ExportLDraw")
        print("    2. In Blender: Edit > Preferences > Add-ons > Install")
        print("    3. Enable the addon and restart Blender")

    # Try to enable common LDraw addon names
    possible_names = [
        'ExportLDraw',
        'io_scene_ldraw',
        'ImportLDraw',
        'importldraw',
        'export_ldraw',
    ]

    for name in possible_names + addon_names:
        try:
            # Check if already enabled
            is_enabled = addon_utils.check(name)[0]
            if is_enabled:
                print(f"  Addon '{name}' is already enabled")
                return name

            # Try to enable it
            bpy.ops.preferences.addon_enable(module=name)
            print(f"  Enabled addon: {name}")
            return name
        except Exception as e:
            pass

    print("  No LDraw addon found to enable")
    return None


def clear_scene():
    """Remove all objects from scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


def list_available_ldraw_operators():
    """List all available LDraw-related operators."""
    print("\n=== Searching for LDraw Operators ===")

    # Search all operator categories
    found_any = False
    for category in dir(bpy.ops):
        if category.startswith('_'):
            continue
        try:
            op_cat = getattr(bpy.ops, category)
            for op_name in dir(op_cat):
                if op_name.startswith('_'):
                    continue
                full_name = f"{category}.{op_name}"
                if 'ldraw' in full_name.lower():
                    print(f"  bpy.ops.{full_name}")
                    found_any = True
        except:
            pass

    if not found_any:
        print("  No LDraw operators found!")

    # Also check import_scene specifically
    print("\n=== import_scene operators ===")
    for attr in dir(bpy.ops.import_scene):
        if not attr.startswith('_'):
            print(f"  bpy.ops.import_scene.{attr}")


def try_import():
    """Try various import methods."""
    clear_scene()

    print(f"\n=== Testing LDraw Import ===")
    print(f"File: {TEST_FILE}")
    print(f"Library: {LDRAW_LIBRARY}")

    # Try to enable the addon first
    addon_name = enable_ldraw_addon()

    # List available operators
    list_available_ldraw_operators()

    # Try different possible operator names
    # Found: bpy.ops.ldraw_exporter.import_operator
    import_methods = [
        ('ldraw_exporter.import_operator', {
            'filepath': TEST_FILE,
            'ldraw_path': LDRAW_LIBRARY,
        }),
        ('ldraw_exporter.import_operator', {
            'filepath': TEST_FILE,
        }),
    ]

    for op_name, params in import_methods:
        print(f"\n--- Trying: bpy.ops.{op_name} ---")
        try:
            parts = op_name.split('.')
            op = bpy.ops
            for part in parts:
                op = getattr(op, part)

            # Get operator properties
            print("  Parameters available:")
            try:
                # This might not work in background mode but worth a try
                rna = op.get_rna_type()
                for prop in rna.properties:
                    if not prop.identifier.startswith('_'):
                        print(f"    {prop.identifier}: {prop.type}")
            except:
                print("    (couldn't list parameters)")

            # Try the import
            result = op(**params)
            print(f"  Result: {result}")

            # Check what was imported
            objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
            print(f"  Imported {len(objects)} mesh objects")

            if objects:
                total_faces = sum(len(o.data.polygons) for o in objects)
                print(f"  Total faces: {total_faces}")

                # Export to GLB
                print(f"\n  Exporting to: {OUTPUT_FILE}")
                bpy.ops.object.select_all(action='SELECT')
                bpy.ops.export_scene.gltf(
                    filepath=OUTPUT_FILE,
                    export_format='GLB',
                    use_selection=True,
                )
                print("  Export successful!")

            return True

        except AttributeError as e:
            print(f"  Not found: {e}")
        except Exception as e:
            print(f"  Error: {e}")

    print("\n=== No working import method found ===")
    print("Make sure ExportLDraw addon is installed and enabled in Blender.")
    return False


if __name__ == '__main__':
    try_import()
