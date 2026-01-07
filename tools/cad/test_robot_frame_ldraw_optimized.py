#!/usr/bin/env python3
"""Stress test render with multiple robots using OPTIMIZED LDraw-converted GLB parts."""

from ursina import *
from ursina.shaders import lit_with_shadows_shader

app = Ursina()

# Scale factor - LDraw GLB files are very small, need larger scale
SCALE = 0.25

# VEX IQ pitch is 12.7mm
PITCH = 12.7 * 0.01  # = 0.127 units

# Part counter
part_count = 0
total_triangles = 0

# === Part paths (OPTIMIZED LDraw-converted GLB - 50% decimated) ===
# Part number mapping:
#   Beams: 228-2500-001 (1x2) through 228-2500-016 (1x20)
#   2-wide beams: 228-2500-017 (2x2) through 228-2500-030 (2x20)
#   Plates: 228-2500-034 (3x6), 228-2500-040 (4x4), 228-2500-043 (4x8), 228-2500-045 (4x12)
#   Gears: 228-2500-213 (12T), 228-2500-214 (36T)
#   Wheels: 228-2500-208 (44mm), 228-2500-211 (65mm)
#   Electronics: 228-2540 (Brain), 228-2560 (Motor)

beam_1x2 = 'models/ldraw_optimized/228-2500-001.glb'   # 1x2 Beam
beam_1x3 = 'models/ldraw_optimized/228-2500-002.glb'   # 1x3 Beam
beam_1x4 = 'models/ldraw_optimized/228-2500-003.glb'   # 1x4 Beam
beam_1x5 = 'models/ldraw_optimized/228-2500-004.glb'   # 1x5 Beam
beam_1x6 = 'models/ldraw_optimized/228-2500-005.glb'   # 1x6 Beam
beam_1x7 = 'models/ldraw_optimized/228-2500-006.glb'   # 1x7 Beam
beam_1x8 = 'models/ldraw_optimized/228-2500-007.glb'   # 1x8 Beam
beam_1x9 = 'models/ldraw_optimized/228-2500-008.glb'   # 1x9 Beam
beam_1x10 = 'models/ldraw_optimized/228-2500-009.glb'  # 1x10 Beam
beam_1x11 = 'models/ldraw_optimized/228-2500-010.glb'  # 1x11 Beam
beam_1x12 = 'models/ldraw_optimized/228-2500-011.glb'  # 1x12 Beam
beam_1x13 = 'models/ldraw_optimized/228-2500-012.glb'  # 1x13 Beam
beam_1x14 = 'models/ldraw_optimized/228-2500-013.glb'  # 1x14 Beam
beam_1x16 = 'models/ldraw_optimized/228-2500-014.glb'  # 1x16 Beam
beam_1x18 = 'models/ldraw_optimized/228-2500-015.glb'  # 1x18 Beam
beam_1x20 = 'models/ldraw_optimized/228-2500-016.glb'  # 1x20 Beam
beam_2x7 = 'models/ldraw_optimized/228-2500-022.glb'   # 2x7 Beam

plate_3x6 = 'models/ldraw_optimized/228-2500-034.glb'  # 3x6 Plate
plate_4x4 = 'models/ldraw_optimized/228-2500-040.glb'  # 4x4 Plate
plate_4x6 = 'models/ldraw_optimized/228-2500-042.glb'  # 4x6 Plate
plate_4x8 = 'models/ldraw_optimized/228-2500-043.glb'  # 4x8 Plate
plate_4x12 = 'models/ldraw_optimized/228-2500-045.glb' # 4x12 Plate

gear_12 = 'models/ldraw_optimized/228-2500-213.glb'    # 12 Tooth Gear
gear_36 = 'models/ldraw_optimized/228-2500-214.glb'    # 36 Tooth Gear

wheel_44 = 'models/ldraw_optimized/228-2500-208.glb'   # 44mm Wheel Hub
wheel_65 = 'models/ldraw_optimized/228-2500-211.glb'   # 65mm Wheel Hub

brain_model = 'models/ldraw_optimized/228-2540.glb'    # Robot Brain
motor_model = 'models/ldraw_optimized/228-2560.glb'    # Smart Motor

# VEX IQ Colors from LDConfig.ldr (converted to 0-1 range for Ursina)
VEX_BLACK = color.rgba(0.15, 0.16, 0.16, 1)
VEX_RED = color.rgba(0.82, 0.15, 0.19, 1)
VEX_GREEN = color.rgba(0.0, 0.59, 0.22, 1)
VEX_BLUE = color.rgba(0.0, 0.47, 0.78, 1)
VEX_YELLOW = color.rgba(1.0, 0.80, 0.0, 1)
VEX_WHITE = color.rgba(0.85, 0.85, 0.84, 1)
VEX_ORANGE = color.rgba(1.0, 0.40, 0.12, 1)
VEX_PURPLE = color.rgba(0.37, 0.15, 0.62, 1)
VEX_LIGHT_GRAY = color.rgba(0.70, 0.71, 0.70, 1)
VEX_MEDIUM_GRAY = color.rgba(0.54, 0.55, 0.55, 1)
VEX_DARK_GRAY = color.rgba(0.33, 0.35, 0.35, 1)


def get_triangle_count(entity):
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
        pass
    return 0


def load_part(path, pos=(0,0,0), rot=(0,0,0), col=color.gray):
    """Load a GLB part with shader and color."""
    global part_count, total_triangles
    try:
        e = Entity(
            model=path,
            scale=SCALE,
            position=pos,
            rotation=rot,
        )
        e.shader = lit_with_shadows_shader
        e.color = col
        part_count += 1
        total_triangles += get_triangle_count(e)
        return e
    except Exception as ex:
        print(f"Failed to load {path}: {ex}")
        return None


def build_robot(offset_x=0, offset_z=0, team_color=None):
    """Build a complete robot at the given position."""
    # Default team color (red)
    if team_color is None:
        team_color = VEX_RED

    # Part colors
    FRAME = team_color
    BRAIN = VEX_DARK_GRAY
    WHEEL = VEX_BLACK
    PLATE = VEX_BLUE
    BEAM = VEX_LIGHT_GRAY
    GEAR = VEX_GREEN
    CONN = VEX_ORANGE
    MOTOR = VEX_DARK_GRAY

    def p(x, y, z):
        """Helper to add offset to position."""
        return (x + offset_x, y, z + offset_z)

    # Chassis frame (4 long beams)
    load_part(beam_1x16, pos=p(0, 0, 8*PITCH), col=FRAME)
    load_part(beam_1x16, pos=p(0, 0, -8*PITCH), col=FRAME)
    load_part(beam_1x16, pos=p(-8*PITCH, 0, 0), rot=(0, 90, 0), col=FRAME)
    load_part(beam_1x16, pos=p(8*PITCH, 0, 0), rot=(0, 90, 0), col=FRAME)

    # Cross beams
    load_part(beam_1x12, pos=p(0, 0, 4*PITCH), col=BEAM)
    load_part(beam_1x12, pos=p(0, 0, -4*PITCH), col=BEAM)
    load_part(beam_1x12, pos=p(0, 0, 0), col=BEAM)

    # Side cross supports
    load_part(beam_1x8, pos=p(-4*PITCH, 0, 4*PITCH), rot=(0, 90, 0), col=BEAM)
    load_part(beam_1x8, pos=p(4*PITCH, 0, 4*PITCH), rot=(0, 90, 0), col=BEAM)
    load_part(beam_1x8, pos=p(-4*PITCH, 0, -4*PITCH), rot=(0, 90, 0), col=BEAM)
    load_part(beam_1x8, pos=p(4*PITCH, 0, -4*PITCH), rot=(0, 90, 0), col=BEAM)

    # Vertical tower beams
    load_part(beam_1x6, pos=p(-6*PITCH, 3*PITCH, 6*PITCH), rot=(0, 0, 90), col=BEAM)
    load_part(beam_1x6, pos=p(6*PITCH, 3*PITCH, 6*PITCH), rot=(0, 0, 90), col=BEAM)
    load_part(beam_1x6, pos=p(-6*PITCH, 3*PITCH, -6*PITCH), rot=(0, 0, 90), col=BEAM)
    load_part(beam_1x6, pos=p(6*PITCH, 3*PITCH, -6*PITCH), rot=(0, 0, 90), col=BEAM)

    # Top frame
    load_part(beam_1x12, pos=p(0, 6*PITCH, 6*PITCH), col=FRAME)
    load_part(beam_1x12, pos=p(0, 6*PITCH, -6*PITCH), col=FRAME)
    load_part(beam_1x12, pos=p(-6*PITCH, 6*PITCH, 0), rot=(0, 90, 0), col=FRAME)
    load_part(beam_1x12, pos=p(6*PITCH, 6*PITCH, 0), rot=(0, 90, 0), col=FRAME)

    # Plates
    load_part(plate_4x12, pos=p(0, -0.5*PITCH, 2*PITCH), col=PLATE)
    load_part(plate_4x12, pos=p(0, -0.5*PITCH, -2*PITCH), col=PLATE)
    load_part(plate_4x8, pos=p(-6*PITCH, 3*PITCH, 0), rot=(0, 0, 90), col=PLATE)
    load_part(plate_4x8, pos=p(6*PITCH, 3*PITCH, 0), rot=(0, 0, -90), col=PLATE)
    load_part(plate_3x6, pos=p(0, 6*PITCH, 0), col=PLATE)
    load_part(plate_4x4, pos=p(-3*PITCH, 6*PITCH, 0), col=PLATE)
    load_part(plate_4x4, pos=p(3*PITCH, 6*PITCH, 0), col=PLATE)
    load_part(plate_4x4, pos=p(-5*PITCH, 0, 5*PITCH), col=PLATE)
    load_part(plate_4x4, pos=p(5*PITCH, 0, 5*PITCH), col=PLATE)
    load_part(plate_4x4, pos=p(-5*PITCH, 0, -5*PITCH), col=PLATE)
    load_part(plate_4x4, pos=p(5*PITCH, 0, -5*PITCH), col=PLATE)

    # Brain
    load_part(brain_model, pos=p(0, 2*PITCH, 0), col=BRAIN)

    # Motors (4 corners)
    load_part(motor_model, pos=p(-6*PITCH, -PITCH, 6*PITCH), rot=(0, 0, 90), col=MOTOR)
    load_part(motor_model, pos=p(6*PITCH, -PITCH, 6*PITCH), rot=(0, 0, -90), col=MOTOR)
    load_part(motor_model, pos=p(-6*PITCH, -PITCH, -6*PITCH), rot=(0, 0, 90), col=MOTOR)
    load_part(motor_model, pos=p(6*PITCH, -PITCH, -6*PITCH), rot=(0, 0, -90), col=MOTOR)

    # Wheels (44mm hubs)
    load_part(wheel_44, pos=p(-7*PITCH, -PITCH, 7*PITCH), rot=(0, 0, 90), col=WHEEL)
    load_part(wheel_44, pos=p(7*PITCH, -PITCH, 7*PITCH), rot=(0, 0, -90), col=WHEEL)
    load_part(wheel_44, pos=p(-7*PITCH, -PITCH, -7*PITCH), rot=(0, 0, 90), col=WHEEL)
    load_part(wheel_44, pos=p(7*PITCH, -PITCH, -7*PITCH), rot=(0, 0, -90), col=WHEEL)

    # Gears
    load_part(gear_36, pos=p(-5*PITCH, -PITCH, 7*PITCH), rot=(0, 0, 90), col=GEAR)
    load_part(gear_36, pos=p(5*PITCH, -PITCH, 7*PITCH), rot=(0, 0, 90), col=GEAR)
    load_part(gear_36, pos=p(-5*PITCH, -PITCH, -7*PITCH), rot=(0, 0, 90), col=GEAR)
    load_part(gear_36, pos=p(5*PITCH, -PITCH, -7*PITCH), rot=(0, 0, 90), col=GEAR)
    load_part(gear_12, pos=p(-3*PITCH, -PITCH, 7*PITCH), rot=(0, 0, 90), col=GEAR)
    load_part(gear_12, pos=p(3*PITCH, -PITCH, 7*PITCH), rot=(0, 0, 90), col=GEAR)
    load_part(gear_12, pos=p(-3*PITCH, -PITCH, -7*PITCH), rot=(0, 0, 90), col=GEAR)
    load_part(gear_12, pos=p(3*PITCH, -PITCH, -7*PITCH), rot=(0, 0, 90), col=GEAR)

    # Connector beams
    for i in range(-2, 3):
        load_part(beam_1x4, pos=p(i*3*PITCH, 0.5*PITCH, 6*PITCH), col=CONN)
        load_part(beam_1x4, pos=p(i*3*PITCH, 0.5*PITCH, -6*PITCH), col=CONN)

    # Angled supports
    load_part(beam_2x7, pos=p(-4*PITCH, 2*PITCH, 4*PITCH), rot=(45, 0, 0), col=BEAM)
    load_part(beam_2x7, pos=p(4*PITCH, 2*PITCH, 4*PITCH), rot=(45, 0, 0), col=BEAM)
    load_part(beam_2x7, pos=p(-4*PITCH, 2*PITCH, -4*PITCH), rot=(-45, 0, 0), col=BEAM)
    load_part(beam_2x7, pos=p(4*PITCH, 2*PITCH, -4*PITCH), rot=(-45, 0, 0), col=BEAM)


# === Build multiple robots ===
# Robot 1 - Red team (center)
build_robot(0, 0, VEX_RED)

# Robot 2 - Blue team (right)
build_robot(4, 0, VEX_BLUE)

# Robot 3 - Green team (left)
build_robot(-4, 0, VEX_GREEN)


# === Lighting ===
sun = DirectionalLight()
sun.look_at(Vec3(1, -1, 1))
AmbientLight(color=color.rgba(0.4, 0.4, 0.4, 1))

# === Camera ===
EditorCamera()

print(f"Loaded {part_count} parts, {total_triangles:,} triangles")
print("Using OPTIMIZED LDraw-converted GLB parts (50% decimated)")
print("Use mouse to rotate, scroll to zoom, WASD to move")

app.run()
