#!/usr/bin/env python3
"""
Render an LDraw MPD/LDR model using Ursina and pre-converted GLB parts.

Usage (from project root):
    python tools/cad/render_ldraw_model.py <model.mpd>
    python tools/cad/render_ldraw_model.py models/test1.mpd

Works on both Windows and WSL2 when cd'd into the project directory.
"""

import sys
import os
import math
from pathlib import Path

# Determine project root (works whether run from project root or tools/cad/)
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

# Add paths for imports
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

from ursina import *
from normal_lighting_shader import normal_lighting_shader
from ldraw_parser import parse_mpd, LDrawDocument, LDRAW_COLORS


# ============================================================================
# Configuration
# ============================================================================

# LDraw to Ursina scale conversion
# GLB files from Blender ExportLDraw have an internal scale from the import
# We need different scales for positions vs models to make parts fit
#
# The ExportLDraw addon imports at default scale (1 LDU = 0.02 Blender units)
# So we DON'T scale the models, just the positions to match
MODEL_SCALE = 1.0  # Don't scale GLB models - use their native size
POSITION_SCALE = 0.02  # Scale positions to match GLB native scale

# Path to GLB parts - use relative path for Ursina compatibility
# (Ursina/Panda3D can't load from UNC paths like \\wsl$\...)
GLB_PATH_COLORED = 'models/ldraw_colored'  # Vertex colors baked in
GLB_PATH_PLAIN = 'models/ldraw/glb'        # No colors (smaller files)


# ============================================================================
# Rendering
# ============================================================================

class LDrawRenderer:
    """Renders an LDraw document in Ursina."""

    def __init__(self, doc: LDrawDocument, glb_path: str = GLB_PATH_COLORED):
        self.doc = doc
        self.glb_path = glb_path
        self.entities = []
        self.part_count = 0
        self.triangle_count = 0
        self.missing_parts = set()

    def rotation_matrix_to_hpr(self, matrix: tuple) -> tuple:
        """
        Convert LDraw rotation matrix to Euler angles for Ursina.

        LDraw matrix is row-major:
        | a b c |   | m[0] m[1] m[2] |
        | d e f | = | m[3] m[4] m[5] |
        | g h i |   | m[6] m[7] m[8] |

        LDraw: X=right, Y=down, Z=toward viewer
        Ursina: X=right, Y=up, Z=forward

        To convert: negate Y and Z axes
        """
        a, b, c, d, e, f, g, h, i = matrix

        # Try simpler approach: extract Euler directly from raw matrix
        # then adjust for coordinate system

        import math

        # Extract Euler angles assuming the matrix is for LDraw's coordinate system
        # We'll adjust the final angles for Ursina's system

        # For rotation matrix, extract using standard formulas
        # Assuming rotation order is important...

        # Check for gimbal lock
        if abs(d) >= 0.999:
            # Gimbal lock case
            heading = 0
            if d < 0:
                pitch = math.pi / 2
                roll = math.atan2(-c, a)
            else:
                pitch = -math.pi / 2
                roll = math.atan2(c, a)
        else:
            pitch = math.asin(-d)
            roll = math.atan2(g, a)
            heading = math.atan2(e, f) if abs(f) > 0.001 else 0

        # Convert to degrees and adjust for coordinate system difference
        # LDraw Y is down, Ursina Y is up -> negate pitch
        # LDraw Z is toward viewer, Ursina Z is forward -> negate heading
        return (
            -math.degrees(pitch),   # rotation_x (negated for Y flip)
            -math.degrees(heading), # rotation_y (negated for Z flip)
            math.degrees(roll)      # rotation_z
        )

    def get_triangle_count(self, entity: Entity) -> int:
        """Get triangle count from entity's Panda3D geometry."""
        try:
            total = 0
            for node in entity.model.findAllMatches('**/+GeomNode'):
                geom_node = node.node()
                for i in range(geom_node.getNumGeoms()):
                    geom = geom_node.getGeom(i)
                    for j in range(geom.getNumPrimitives()):
                        prim = geom.getPrimitive(j)
                        total += prim.getNumFaces()
            return total
        except:
            return 0

    def render_model(self, model_name: str = None, parent_color: int = 71,
                     offset: tuple = (0, 0, 0), parent_rotation: tuple = None):
        """Render a model and all its parts."""
        if model_name is None:
            model_name = self.doc.main_model

        if model_name not in self.doc.models:
            print(f"Warning: Model '{model_name}' not found")
            return

        model = self.doc.models[model_name]
        print(f"\nRendering model: {model_name}")
        print(f"  Parts: {len(model.parts)}")

        for part in model.parts:
            self.render_part(part, parent_color, offset)

        # Render submodels recursively
        for submodel_name, placement in model.submodel_refs:
            # Apply transformation and render submodel
            sub_offset = (
                offset[0] + placement.x * POSITION_SCALE,
                offset[1] + placement.y * POSITION_SCALE,
                offset[2] + placement.z * POSITION_SCALE,
            )
            sub_color = placement.color if placement.color != 16 else parent_color
            self.render_model(submodel_name, sub_color, sub_offset)

    def render_part(self, part, parent_color: int = 71,
                    offset: tuple = (0, 0, 0)):
        """Render a single part."""
        glb_name = part.glb_name
        # Relative path for Ursina (works with UNC paths on Windows)
        glb_file_relative = f"{self.glb_path}/{glb_name}"
        # Absolute path for file existence check
        glb_file_absolute = str(PROJECT_ROOT / self.glb_path / glb_name)

        # Check if GLB exists using absolute path
        if not os.path.exists(glb_file_absolute):
            if glb_name not in self.missing_parts:
                self.missing_parts.add(glb_name)
                print(f"  Warning: Missing part: {glb_name}")
                print(f"    Checked path: {glb_file_absolute}")
            return

        # Convert position from LDU to Ursina units
        # LDraw coordinate system: X=right, Y=down, Z=back (toward viewer)
        # Ursina/Panda3D: X=right, Y=up, Z=forward
        # So we need to: negate Y, negate Z
        pos_x = offset[0] + part.x * POSITION_SCALE
        pos_y = offset[1] - part.y * POSITION_SCALE  # Negate Y
        pos_z = offset[2] - part.z * POSITION_SCALE  # Negate Z

        # Get rotation using Panda3D's matrix utilities
        euler = self.rotation_matrix_to_hpr(part.rotation_matrix)

        # Debug output
        print(f"    Part: {glb_name}")
        print(f"      LDraw pos: ({part.x}, {part.y}, {part.z})")
        print(f"      Ursina pos: ({pos_x:.3f}, {pos_y:.3f}, {pos_z:.3f})")
        print(f"      Rotation matrix: {part.rotation_matrix}")
        print(f"      Euler angles: {euler}")

        try:
            from panda3d.core import LMatrix4f

            # Use relative path for model loading (project root added to model path)
            entity = Entity(
                model=glb_file_relative,
                position=(pos_x, pos_y, pos_z),
                scale=MODEL_SCALE,
            )

            # Set rotation matrix directly instead of using Euler angles
            # LDraw matrix is row-major: a,b,c / d,e,f / g,h,i
            # We need to transform for coordinate system change (Y and Z flipped)
            a, b, c, d, e, f, g, h, i = part.rotation_matrix

            # Apply coordinate change: C * M * C where C = diag(1, -1, -1)
            # This transforms the rotation for the coordinate flip
            # New matrix after transformation:
            a2, b2, c2 = a, -b, -c
            d2, e2, f2 = -d, e, f
            g2, h2, i2 = -g, h, i

            # Create Panda3D rotation matrix (column-major, so transpose)
            mat = LMatrix4f(
                a2, d2, g2, 0,
                b2, e2, h2, 0,
                c2, f2, i2, 0,
                0, 0, 0, 1
            )

            # Apply the rotation matrix to the entity's underlying node
            entity.setMat(mat)
            # Re-apply position and scale since setMat overwrites them
            entity.position = (pos_x, pos_y, pos_z)
            entity.scale = MODEL_SCALE

            # Use custom normal-based shader - built-in lighting + vertex colors
            entity.shader = normal_lighting_shader

            # Apply color from MPD file (color 16 inherits from parent)
            # For colored GLBs: multiplies with vertex colors (white->color, black->black)
            # For plain GLBs: applies as solid color to entire part
            color_code = part.color if part.color != 16 else parent_color
            if color_code in LDRAW_COLORS:
                r, g, b, color_name = LDRAW_COLORS[color_code]
                entity.color = color.rgba(r, g, b, 1)
                print(f"      Color: {color_name} (code {color_code})")
            self.entities.append(entity)
            self.part_count += 1
            self.triangle_count += self.get_triangle_count(entity)
        except Exception as e:
            print(f"  Error loading {glb_name}: {e}")

    def render_all(self, render_all_models: bool = False):
        """Render the entire document starting from main model."""
        print(f"\n{'='*60}")
        print("Rendering LDraw Document")
        print(f"{'='*60}")

        if render_all_models:
            # Render all models (including unreferenced submodels)
            for model_name in self.doc.models:
                self.render_model(model_name)
        else:
            # Only render the main model (and its referenced submodels)
            self.render_model(self.doc.main_model)

        print(f"\n{'='*60}")
        print(f"Rendering Complete")
        print(f"  Total parts: {self.part_count}")
        print(f"  Total triangles: {self.triangle_count:,}")
        if self.missing_parts:
            print(f"  Missing parts: {len(self.missing_parts)}")
        print(f"{'='*60}\n")


# ============================================================================
# Main
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Render an LDraw MPD/LDR model using Ursina and pre-converted GLB parts.'
    )
    parser.add_argument('model', help='Path to LDraw model file (.mpd or .ldr)')
    parser.add_argument('--plain', action='store_true',
                        help='Use plain/uncolored GLB models (smaller files)')

    args = parser.parse_args()

    # Select GLB path based on flag
    glb_path = GLB_PATH_PLAIN if args.plain else GLB_PATH_COLORED
    print(f"Using {'plain' if args.plain else 'colored'} models from: {glb_path}")

    model_path = Path(args.model)

    # Try to find the model file
    # 1. As given (absolute or relative to cwd)
    # 2. Relative to project root
    if not model_path.exists():
        alt_path = PROJECT_ROOT / model_path
        if alt_path.exists():
            model_path = alt_path
        else:
            print(f"Error: File not found: {sys.argv[1]}")
            print(f"  Tried: {model_path}")
            print(f"  Tried: {alt_path}")
            sys.exit(1)

    model_path = str(model_path)

    # Change to project root so Ursina's asset_folder is correct
    os.chdir(str(PROJECT_ROOT))

    # Parse the LDraw file
    print(f"Parsing: {model_path}")
    doc = parse_mpd(model_path)

    # Initialize Ursina
    app = Ursina()

    # Set asset folder to project root so relative model paths work
    # Ursina defaults to __main__.__file__ directory, which is tools/cad/
    from ursina import application
    from panda3d.core import getModelPath
    application.asset_folder = PROJECT_ROOT
    getModelPath().prependDirectory(str(PROJECT_ROOT))

    # Create renderer and render
    renderer = LDrawRenderer(doc, glb_path=glb_path)
    renderer.render_all()

    # No scene lights needed - shader has built-in normal-based lighting

    # Blue background
    from panda3d.core import VBase4
    base.setBackgroundColor(VBase4(70/255, 130/255, 180/255, 1))  # Steel blue

    # Add small axes at origin for reference (scaled to match scene)
    axis_len = 1  # 1 Ursina unit = 100 LDU
    Entity(model='cube', scale=(axis_len, 0.01, 0.01), color=color.red, x=axis_len/2)    # X axis
    Entity(model='cube', scale=(0.01, axis_len, 0.01), color=color.green, y=axis_len/2)  # Y axis
    Entity(model='cube', scale=(0.01, 0.01, axis_len), color=color.blue, z=axis_len/2)   # Z axis

    # Add orbit camera - position based on scene scale
    # With POSITION_SCALE=0.025, a 400 LDU frame is ~10 Ursina units
    EditorCamera()
    camera.position = (0, 10, -25)
    camera.rotation_x = 20

    # Info text (centered at top)
    info = Text(
        text=f"Parts: {renderer.part_count} | Triangles: {renderer.triangle_count:,}",
        position=(0, 0.45),
        origin=(0, 0),
        scale=1.5
    )

    # Controls (centered at bottom)
    controls = Text(
        text="Controls: Mouse drag to orbit, scroll to zoom, WASD to move",
        position=(0, -0.45),
        origin=(0, 0),
        scale=1.2
    )

    app.run()


if __name__ == "__main__":
    main()
