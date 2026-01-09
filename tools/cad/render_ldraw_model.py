#!/usr/bin/env python3
"""
Render an LDraw MPD/LDR model using Ursina and pre-converted GLB parts.

Usage (from project root):
    python tools/cad/render_ldraw_model.py <model.mpd>
    python tools/cad/render_ldraw_model.py models/ClawbotIQ.mpd

Works on both Windows and WSL2 when cd'd into the project directory.
"""

import sys
import os
from pathlib import Path

# Determine project root (works whether run from project root or tools/cad/)
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

# Add paths for imports
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

# Debug: print paths before anything else
print(f"Script dir: {SCRIPT_DIR}")
print(f"Project root: {PROJECT_ROOT}")
print(f"CWD before chdir: {os.getcwd()}")

# Change to project root BEFORE importing Ursina
try:
    os.chdir(str(PROJECT_ROOT))
    print(f"CWD after chdir: {os.getcwd()}")
except Exception as e:
    print(f"Warning: Could not change to project root: {e}")

from ldraw_parser import parse_mpd
from ldraw_renderer import LDrawModelRenderer, GLB_PATH


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Render an LDraw MPD/LDR model using Ursina and pre-converted GLB parts.'
    )
    parser.add_argument('model', help='Path to LDraw model file (.mpd or .ldr)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Print verbose debug output')
    parser.add_argument('--no-shader', action='store_true',
                        help='Disable custom shader (debug rendering issues)')
    parser.add_argument('--no-rotation', action='store_true',
                        help='Disable rotation matrix (debug rendering issues)')

    args = parser.parse_args()

    print(f"Using parts from: {GLB_PATH}")

    model_path = Path(args.model)

    # Try to find the model file
    if not model_path.exists():
        alt_path = PROJECT_ROOT / model_path
        if alt_path.exists():
            model_path = alt_path
        else:
            print(f"Error: File not found: {args.model}")
            print(f"  Tried: {model_path}")
            print(f"  Tried: {alt_path}")
            sys.exit(1)

    model_path = str(model_path)

    # Parse the LDraw file
    print(f"Parsing: {model_path}")
    doc = parse_mpd(model_path)

    # Initialize Ursina AFTER setting cwd
    from ursina import Ursina, Entity, Text, color, EditorCamera, camera
    app = Ursina(vsync=False)

    # Limit frame rate to 30 FPS to reduce CPU/GPU usage
    from panda3d.core import ClockObject
    globalClock = ClockObject.getGlobalClock()
    globalClock.setMode(ClockObject.MLimited)
    globalClock.setFrameRate(30)

    # Set asset folder to project root so relative model paths work
    # Do this IMMEDIATELY after Ursina init
    from ursina import application
    from panda3d.core import getModelPath

    # Convert to string for Panda3D compatibility
    project_root_str = str(PROJECT_ROOT)
    application.asset_folder = Path(project_root_str)
    getModelPath().prependDirectory(project_root_str)

    print(f"\nPath configuration:")
    print(f"  application.asset_folder: {application.asset_folder}")
    print(f"  CWD: {os.getcwd()}")
    print(f"  Model search paths: {getModelPath()}")

    # Create renderer and render
    print(f"\n{'='*60}")
    print("Rendering LDraw Document")
    print(f"{'='*60}")

    renderer = LDrawModelRenderer(
        doc,
        glb_path=GLB_PATH,
        project_root=PROJECT_ROOT,
        use_shader=not args.no_shader,
        skip_rotation=args.no_rotation,
        verbose=args.verbose
    )
    renderer.render()

    print(f"\n{'='*60}")
    print(f"Rendering Complete")
    print(f"  Total parts: {renderer.part_count}")
    print(f"  Total triangles: {renderer.triangle_count:,}")
    print(f"  Shader: {'enabled' if not args.no_shader else 'DISABLED'}")
    print(f"  Rotation: {'enabled' if not args.no_rotation else 'DISABLED'}")
    if renderer.missing_parts:
        print(f"  Missing parts: {len(renderer.missing_parts)}")
    print(f"{'='*60}\n")

    # Debug: print entity positions
    if args.verbose and renderer.entities:
        print("Entity positions (first 5):")
        for i, ent in enumerate(renderer.entities[:5]):
            print(f"  [{i}] pos={ent.position}, scale={ent.scale}, visible={ent.visible}")

        # Calculate bounds
        if renderer.entities:
            xs = [e.position.x for e in renderer.entities]
            ys = [e.position.y for e in renderer.entities]
            zs = [e.position.z for e in renderer.entities]
            print(f"\nModel bounds:")
            print(f"  X: {min(xs):.2f} to {max(xs):.2f}")
            print(f"  Y: {min(ys):.2f} to {max(ys):.2f}")
            print(f"  Z: {min(zs):.2f} to {max(zs):.2f}")
            center = ((min(xs)+max(xs))/2, (min(ys)+max(ys))/2, (min(zs)+max(zs))/2)
            print(f"  Center: ({center[0]:.2f}, {center[1]:.2f}, {center[2]:.2f})")

    # Blue background
    from panda3d.core import VBase4
    base.setBackgroundColor(VBase4(70/255, 130/255, 180/255, 1))  # Steel blue

    # Add small axes at origin for reference
    axis_len = 1
    Entity(model='cube', scale=(axis_len, 0.01, 0.01), color=color.red, x=axis_len/2)
    Entity(model='cube', scale=(0.01, axis_len, 0.01), color=color.green, y=axis_len/2)
    Entity(model='cube', scale=(0.01, 0.01, axis_len), color=color.blue, z=axis_len/2)

    # Add a test cube at model center to verify rendering works
    if renderer.entities:
        xs = [e.position.x for e in renderer.entities]
        ys = [e.position.y for e in renderer.entities]
        zs = [e.position.z for e in renderer.entities]
        center = ((min(xs)+max(xs))/2, (min(ys)+max(ys))/2, (min(zs)+max(zs))/2)
        # Bright magenta test cube at model center
        test_cube = Entity(
            model='cube',
            scale=0.5,
            position=center,
            color=color.magenta
        )
        print(f"Test cube placed at: {center}")

    # Add orbit camera
    EditorCamera()
    camera.position = (0, 10, -25)
    camera.rotation_x = 20

    if args.verbose:
        print(f"\nCamera setup:")
        print(f"  Position: {camera.position}")
        print(f"  Rotation: ({camera.rotation_x}, {camera.rotation_y}, {camera.rotation_z})")

    # Info text
    Text(
        text=f"Parts: {renderer.part_count} | Triangles: {renderer.triangle_count:,}",
        position=(0, 0.45),
        origin=(0, 0),
        scale=1.5
    )

    # Controls
    Text(
        text="Controls: Mouse drag to orbit, scroll to zoom, WASD to move",
        position=(0, -0.45),
        origin=(0, 0),
        scale=1.2
    )

    app.run()


if __name__ == "__main__":
    main()
