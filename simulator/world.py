"""
VEX IQ 3D World
===============
Ursina-based 3D world with VEX IQ field grid.
"""

import os
from pathlib import Path
from ursina import *

# Project root for model files
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Import LDraw renderer (adds tools/cad to path)
import sys
sys.path.insert(0, str(PROJECT_ROOT / 'tools' / 'cad'))
from ldraw_parser import parse_mpd
from ldraw_renderer import LDrawModelRenderer, GLB_PATH_COLORED


class OrbitCamera:
    """Orbit camera controller with zoom, rotate, and pan.

    Controls:
    - Scroll wheel: Zoom in/out
    - Middle mouse + drag: Orbit/rotate around target
    - Right mouse + drag: Pan
    """

    def __init__(self):
        # Camera distance from target (zoom level)
        self.distance = 10
        self.min_distance = 3
        self.max_distance = 25

        # Orbit angles
        self.rotation_x = 50  # Pitch (up/down)
        self.rotation_y = 0   # Yaw (left/right)
        self.min_pitch = 10
        self.max_pitch = 90

        # Target point to orbit around
        self.target = Vec3(0, 0, 0)

        # Sensitivity
        self.zoom_speed = 1.5
        self.rotate_speed = 100
        self.pan_speed = 0.01

        # Mouse tracking
        self._prev_mouse_pos = None

        # Apply initial position
        self.update_camera()

    def update_camera(self):
        """Update camera position based on orbit parameters."""
        # Calculate position from spherical coordinates
        rad_x = math.radians(self.rotation_x)
        rad_y = math.radians(self.rotation_y)

        # Position relative to target
        x = self.distance * math.sin(rad_y) * math.cos(rad_x)
        y = self.distance * math.sin(rad_x)
        z = -self.distance * math.cos(rad_y) * math.cos(rad_x)

        camera.position = self.target + Vec3(x, y, z)

        # Look at target, then reset rotation_z to prevent roll/tilt
        camera.look_at(self.target)
        camera.rotation_z = 0  # Lock roll axis to keep horizon level

    def handle_input(self, key):
        """Handle keyboard input."""
        # Scroll wheel zoom
        if key == 'scroll up':
            self.distance = max(self.min_distance, self.distance - self.zoom_speed)
            self.update_camera()
        elif key == 'scroll down':
            self.distance = min(self.max_distance, self.distance + self.zoom_speed)
            self.update_camera()

    def update(self):
        """Update camera each frame for mouse drag operations."""
        # Get mouse delta
        if self._prev_mouse_pos is None:
            self._prev_mouse_pos = mouse.position
            return

        delta = mouse.position - self._prev_mouse_pos
        self._prev_mouse_pos = mouse.position

        # Middle mouse: Orbit/rotate
        if mouse.middle:
            self.rotation_y += delta.x * self.rotate_speed
            self.rotation_x -= delta.y * self.rotate_speed
            # Clamp pitch
            self.rotation_x = max(self.min_pitch, min(self.max_pitch, self.rotation_x))
            self.update_camera()

        # Right mouse: Pan
        elif mouse.right:
            # Calculate pan direction based on camera orientation
            right = Vec3(
                math.cos(math.radians(self.rotation_y)),
                0,
                math.sin(math.radians(self.rotation_y))
            )
            forward = Vec3(
                -math.sin(math.radians(self.rotation_y)),
                0,
                math.cos(math.radians(self.rotation_y))
            )

            pan_amount = self.distance * self.pan_speed
            self.target -= right * delta.x * pan_amount * 50
            self.target -= forward * delta.y * pan_amount * 50

            # Clamp target to reasonable bounds
            self.target.x = max(-5, min(5, self.target.x))
            self.target.z = max(-5, min(5, self.target.z))
            self.target.y = 0  # Keep target on ground plane

            self.update_camera()

    def reset(self):
        """Reset camera to default view."""
        self.distance = 10
        self.rotation_x = 50
        self.rotation_y = 0
        self.target = Vec3(0, 0, 0)
        self.update_camera()


class VexField(Entity):
    """VEX IQ competition field - rectangular playing surface.

    Official VEX IQ competition field specifications:
    - Size: 8' x 6' (2.44m x 1.83m) as viewed from above
    - Tiles: 1 foot (305mm) square each, very light grey plastic
    - Grid: 8 tiles wide x 6 tiles deep = 48 tiles
    - Perimeter wall: 2.5" (64mm) high
    - Tiles have continuous dark grid lines forming tile boundaries
    """

    # Official VEX IQ competition field: 8' wide x 6' deep
    # Oriented so 8' is horizontal (X axis) and 6' is depth (Z axis)
    FIELD_WIDTH = 8   # feet (X axis) - horizontal
    FIELD_LENGTH = 6  # feet (Z axis) - depth
    TILE_SIZE = 1     # 1 foot per tile

    # VEX IQ field colors
    # Real tiles are "Very Light Grey" plastic with black lines
    TILE_COLOR = color.rgb(200, 200, 200)  # Light grey tiles
    LINE_COLOR = color.rgb(40, 40, 40)     # Dark grey/black lines
    BORDER_COLOR = color.rgb(60, 60, 60)   # Dark border walls
    # Alliance and zone colors (Rapid Relay 2024-2025 season)
    # Using Ursina's color.hsv(h, s, v) where h=0-360, s=0-1, v=0-1
    ORANGE_COLOR = color.hsv(30, 1, 0.9)     # Orange hue, full saturation, bright
    BLUE_COLOR = color.hsv(220, 0.8, 0.6)    # Blue hue, high sat, medium bright
    RED_COLOR = color.hsv(0, 0.8, 0.7)       # Red hue, high sat, medium bright

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.create_field()

    def create_field(self):
        """Create the field floor and grid lines."""
        # Field floor with tiled texture
        # Texture is in project's textures/ folder (Ursina's default location)
        # VEX IQ field: 8 tiles wide x 6 tiles deep
        # Tiling pattern: half-tile on edges (0.5 + 7 + 0.5 = 8, 0.5 + 5 + 0.5 = 6)

        self.floor = Entity(
            parent=self,
            model='quad',
            scale=(self.FIELD_WIDTH, self.FIELD_LENGTH),
            position=(0, 0, 0),
            rotation_x=90,  # Rotate to lie flat
            texture='vex-tile',  # Ursina looks in textures/ folder
            texture_scale=(self.FIELD_WIDTH, self.FIELD_LENGTH),  # Tile 8x6 times
            texture_offset=(0.5, 0.5),  # Half-tile offset for edge alignment
            collider='box'
        )
        print(f"Floor texture: {self.floor.texture}")

        # Field border (perimeter walls)
        self.create_border()

    def create_zones(self):
        """Create alliance zones and center platform.

        Based on VEX IQ Rapid Relay 2024-2025 field layout:
        - Orange center platform (2x2 tiles in the center)
        - Blue alliance corner (bottom-left, 2x2 tiles)
        - Red alliance corner (top-right, 2x2 tiles)
        """
        zone_height = 0.003  # Slightly raised for visibility

        # Orange center platform (2x2 tiles)
        # Center of 6x8 field is at (0, 0)
        Entity(
            parent=self,
            model='cube',
            scale=(2, zone_height, 2),
            position=(0, zone_height / 2, 0),
            color=self.ORANGE_COLOR
        )

        # Blue alliance corner (bottom-left of field)
        # Position: corner at (-3, -4), so center of 2x2 is at (-2, -3)
        half_width = self.FIELD_WIDTH / 2
        half_length = self.FIELD_LENGTH / 2
        Entity(
            parent=self,
            model='cube',
            scale=(2, zone_height, 2),
            position=(-half_width + 1, zone_height / 2, -half_length + 1),
            color=self.BLUE_COLOR
        )

        # Red alliance corner (top-right of field)
        # Position: corner at (3, 4), so center of 2x2 is at (2, 3)
        Entity(
            parent=self,
            model='cube',
            scale=(2, zone_height, 2),
            position=(half_width - 1, zone_height / 2, half_length - 1),
            color=self.RED_COLOR
        )

    def create_grid_lines(self):
        """Create visible grid lines on the field.

        VEX IQ tiles have black "+" markings at intersections, not continuous
        grid lines. Each "+" is about 4 inches (0.33 feet) in each direction.
        """
        half_width = self.FIELD_WIDTH / 2
        half_length = self.FIELD_LENGTH / 2
        line_width = 0.025  # ~1 inch lines
        cross_length = 0.33  # ~4 inches for each arm of the "+"

        # Create "+" crosses at each tile intersection
        for i in range(self.FIELD_LENGTH + 1):
            for j in range(self.FIELD_WIDTH + 1):
                x_pos = -half_width + j * self.TILE_SIZE
                z_pos = -half_length + i * self.TILE_SIZE

                # Horizontal bar of "+"
                Entity(
                    parent=self,
                    model='cube',
                    scale=(cross_length, 0.008, line_width),
                    position=(x_pos, 0.005, z_pos),
                    color=self.LINE_COLOR
                )
                # Vertical bar of "+"
                Entity(
                    parent=self,
                    model='cube',
                    scale=(line_width, 0.008, cross_length),
                    position=(x_pos, 0.005, z_pos),
                    color=self.LINE_COLOR
                )

    def create_border(self):
        """Create field border walls.

        User requested 4 inch high walls with light grey color.
        """
        wall_height = 4 / 12  # 4 inches in feet (simulator units)
        wall_thickness = 0.08
        wall_color = color.light_gray  # Light grey as requested
        half_width = self.FIELD_WIDTH / 2
        half_length = self.FIELD_LENGTH / 2

        # Border walls (4 sides)
        walls = [
            # Front and back walls (along X axis)
            ((0, wall_height/2, half_length + wall_thickness/2),
             (self.FIELD_WIDTH + wall_thickness*2, wall_height, wall_thickness)),
            ((0, wall_height/2, -half_length - wall_thickness/2),
             (self.FIELD_WIDTH + wall_thickness*2, wall_height, wall_thickness)),
            # Side walls (along Z axis)
            ((half_width + wall_thickness/2, wall_height/2, 0),
             (wall_thickness, wall_height, self.FIELD_LENGTH)),
            ((-half_width - wall_thickness/2, wall_height/2, 0),
             (wall_thickness, wall_height, self.FIELD_LENGTH)),
        ]

        for pos, scale in walls:
            Entity(
                parent=self,
                model='cube',
                position=pos,
                scale=scale,
                color=wall_color
            )


class RobotPlaceholder(Entity):
    """Simple box placeholder for robot - will be replaced with actual robot model."""

    def __init__(self, **kwargs):
        super().__init__(
            model='cube',
            scale=(0.5, 0.3, 0.5),  # Roughly 6 inches cube
            position=(0, 0.15, 0),
            color=color.red,  # Use built-in color (color.rgb() doesn't work in Ursina)
            **kwargs
        )

        # Add a direction indicator (small cube at front)
        self.front_indicator = Entity(
            parent=self,
            model='cube',
            scale=(0.3, 0.1, 0.1),
            position=(0, 0.2, 0.3),
            color=color.lime  # Use built-in color (color.rgb() doesn't work in Ursina)
        )

        # Movement state
        self.velocity = Vec3(0, 0, 0)
        self.angular_velocity = 0

    def update(self):
        """Update robot position based on motor states."""
        # This will be driven by motor values from vex_stub
        pass

    def set_drive(self, left_power: float, right_power: float):
        """Set drive motor powers (-100 to 100)."""
        # Convert motor powers to movement
        # Average for forward speed, difference for turning
        forward = (left_power + right_power) / 200  # Normalize to -1 to 1
        # Tank drive: left faster = turn right, right faster = turn left
        # In Ursina, positive rotation_y = clockwise = turn right
        turn = (left_power - right_power) / 200

        # Apply movement (scaled for reasonable speed)
        speed = 2.0  # units per second at full power
        turn_speed = 90  # degrees per second at full power

        self.velocity = Vec3(0, 0, forward * speed)
        self.angular_velocity = turn * turn_speed

    def move(self, dt):
        """Move robot based on current velocity."""
        if self.velocity.length() > 0.001 or abs(self.angular_velocity) > 0.001:
            # Rotate velocity by current heading
            rad = math.radians(self.rotation_y)
            world_vel = Vec3(
                self.velocity.z * math.sin(rad),
                0,
                self.velocity.z * math.cos(rad)
            )

            self.position += world_vel * dt
            self.rotation_y += self.angular_velocity * dt

            # Keep robot on field (8' wide x 6' deep)
            # Half dimensions minus robot size buffer
            bound_x = 3.8  # ~8/2 - 0.2 buffer
            bound_z = 2.8  # ~6/2 - 0.2 buffer
            self.x = max(-bound_x, min(bound_x, self.x))
            self.z = max(-bound_z, min(bound_z, self.z))


class LDrawRobot(Entity):
    """Robot loaded from LDraw MPD/LDR file.

    Uses the shared LDrawModelRenderer for rendering, with the same
    movement interface as RobotPlaceholder for simulation control.
    """

    # Scale factor to convert LDraw/Blender units to field units (feet)
    # 1 LDU = 0.4mm, 1 foot = 304.8mm, POSITION_SCALE = 0.02
    # So: 1 foot = 762 LDU = 15.24 Ursina units at POSITION_SCALE
    # We want 1 foot = 1 Ursina unit, so scale by 1/15.24
    ROBOT_SCALE = 1.0 / 15.24  # ≈ 0.066

    # Y offset to place robot on ground (adjusted for LDraw origin)
    ROBOT_Y_OFFSET = 0.05  # feet above ground

    def __init__(self, model_path: str = None, **kwargs):
        super().__init__(**kwargs)

        # Use default model if none specified
        if model_path is None:
            model_path = str(PROJECT_ROOT / 'models' / 'ClawbotIQ.mpd')

        # Movement state (same as RobotPlaceholder)
        self.velocity = Vec3(0, 0, 0)
        self.angular_velocity = 0

        # Renderer reference for stats
        self.renderer = None

        # Load the LDraw model using shared renderer
        self.load_model(model_path)

        # Scale robot to match field units (feet)
        self.scale = self.ROBOT_SCALE

        # Auto-position robot on ground based on bounding box
        self._position_on_ground()

    def load_model(self, model_path: str):
        """Load and render an LDraw MPD/LDR file."""
        if not os.path.exists(model_path):
            print(f"Warning: Model not found: {model_path}")
            return

        print(f"Loading LDraw model: {model_path}")
        doc = parse_mpd(model_path)

        if not doc.main_model:
            print("Warning: No main model found in document")
            return

        # First pass: render with no offset to calculate bounding box
        self.renderer = LDrawModelRenderer(
            doc,
            glb_path=GLB_PATH_COLORED,
            project_root=PROJECT_ROOT,
            parent=self,
            use_shader=True,
            y_offset=0,
            verbose=False
        )
        self.renderer.render()

        # Calculate min_y from rendered entities to position robot on ground
        min_y = self._calculate_min_y()

        # Apply offset to bring bottom to Y=0
        if min_y != 0:
            # Clear first render and re-render with ground offset
            for entity in self.renderer.entities:
                entity.enabled = False
                destroy(entity)
            self.renderer.entities.clear()
            self.renderer.part_count = 0

            self.renderer.y_offset = min_y  # Shift to place bottom at Y=0
            self.renderer.render()

        print(f"Loaded {self.renderer.part_count} parts "
              f"({len(self.renderer.missing_parts)} missing)")

    def _calculate_min_y(self):
        """Calculate the minimum Y position of all parts."""
        if not self.renderer or not self.renderer.entities:
            return 0

        min_y = float('inf')
        for entity in self.renderer.entities:
            # Get entity position (in renderer's local space)
            local_y = entity.y

            # Try to get model bounds
            if hasattr(entity, 'model') and entity.model:
                try:
                    bounds = entity.model.getTightBounds()
                    if bounds:
                        # Add model's local min to entity position
                        min_y = min(min_y, local_y + bounds[0].y)
                        continue
                except:
                    pass

            min_y = min(min_y, local_y)

        return min_y if min_y != float('inf') else 0

    def _position_on_ground(self):
        """Position robot so wheels sit on ground (Y=0)."""
        # Position is now handled by y_offset in renderer
        pass

    @property
    def part_count(self) -> int:
        """Get number of loaded parts."""
        return self.renderer.part_count if self.renderer else 0

    @property
    def missing_parts(self) -> set:
        """Get set of missing part names."""
        return self.renderer.missing_parts if self.renderer else set()

    def set_drive(self, left_power: float, right_power: float):
        """Set drive motor powers (-100 to 100)."""
        forward = (left_power + right_power) / 200
        turn = (left_power - right_power) / 200

        speed = 2.0
        turn_speed = 90

        # Negate forward to match LDraw model orientation
        self.velocity = Vec3(0, 0, -forward * speed)
        self.angular_velocity = turn * turn_speed

    def move(self, dt):
        """Move robot based on current velocity."""
        if self.velocity.length() > 0.001 or abs(self.angular_velocity) > 0.001:
            rad = math.radians(self.rotation_y)
            world_vel = Vec3(
                self.velocity.z * math.sin(rad),
                0,
                self.velocity.z * math.cos(rad)
            )

            self.position += world_vel * dt
            self.rotation_y += self.angular_velocity * dt

            # Keep robot on field
            bound_x = 3.8
            bound_z = 2.8
            self.x = max(-bound_x, min(bound_x, self.x))
            self.z = max(-bound_z, min(bound_z, self.z))


class VexWorld:
    """Main VEX IQ 3D world manager."""

    def __init__(self):
        self.field = None
        self.robot = None

    def setup(self):
        """Set up the 3D world."""
        # Create field
        self.field = VexField()

        # Note: Robot placeholder is created by VexSimulator when adding robots

        # Lighting
        self.setup_lighting()

        # Note: Camera is set up by VexSimulator.adjust_camera_for_panel()

    def setup_lighting(self):
        """Set up scene lighting."""
        # Ambient light (brighter for better visibility)
        ambient = AmbientLight()
        ambient.color = color.light_gray

        # Directional light (sun-like)
        # Note: shadows=False for better performance, especially in WSL2/fullscreen
        DirectionalLight(
            shadows=False,
            rotation=(45, -45, 0)
        )
