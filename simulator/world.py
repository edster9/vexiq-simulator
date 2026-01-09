"""
VEX IQ 3D World
===============
Ursina-based 3D world with VEX IQ field grid.
"""

import math
import os
from pathlib import Path
from ursina import *

# Project root for model files
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Import LDraw renderer and robotdef loader (adds tools/cad to path)
import sys
sys.path.insert(0, str(PROJECT_ROOT / 'tools' / 'cad'))
from ldraw_parser import parse_mpd
from ldraw_renderer import LDrawModelRenderer, GLB_PATH, POSITION_SCALE
from robotdef_loader import load_robotdef, find_robotdef_for_model, RobotDef


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

        # Robot definition (loaded from .robotdef file)
        self.robotdef: RobotDef = None

        # Drivetrain rotation center offset (in robot's local scaled coordinates)
        # This is where the robot pivots when turning
        self._rotation_center_offset = Vec3(0, 0, 0)

        # Wheel rotation tracking for animation
        self._left_wheel_rotation = 0.0  # degrees
        self._right_wheel_rotation = 0.0  # degrees
        self._left_wheel_speed = 0.0  # degrees per second
        self._right_wheel_speed = 0.0  # degrees per second
        self._wheel_entities_left = []
        self._wheel_entities_right = []
        self._wheel_original_mats = {}  # Original transformation matrices for wheels

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

        # Load robot definition file if it exists
        robotdef_path = find_robotdef_for_model(model_path)
        if robotdef_path:
            try:
                self.robotdef = load_robotdef(robotdef_path)
                print(f"Loaded robot definition: {robotdef_path}")
                print(f"  Drivetrain type: {self.robotdef.drivetrain.type}")
                print(f"  Rotation center (LDU): {self.robotdef.drivetrain.rotation_center}")
            except Exception as e:
                print(f"Warning: Could not load robot definition: {e}")
                self.robotdef = None
        else:
            print(f"No robot definition found for {model_path}")

        # Calculate y_offset based on wheel radius from robotdef
        # This positions the robot so wheels touch the ground
        y_offset = self._calculate_ground_offset()
        print(f"  Ground offset from wheel radius: {y_offset}")

        # Render with the calculated y_offset
        self.renderer = LDrawModelRenderer(
            doc,
            glb_path=GLB_PATH,
            project_root=PROJECT_ROOT,
            parent=self,
            use_shader=True,
            y_offset=y_offset,
            verbose=False
        )
        self.renderer.render()

        # Find actual min Y after rendering and adjust all entities directly
        # (self.y adjustment doesn't work - must move each entity individually)
        min_y_with_bounds = float('inf')
        for entity in self.renderer.entities:
            try:
                if hasattr(entity, 'model') and entity.model:
                    bounds = entity.model.getTightBounds()
                    if bounds:
                        model_min_y = bounds[0].y * entity.scale_y
                        world_min_y = entity.y + model_min_y
                        min_y_with_bounds = min(min_y_with_bounds, world_min_y)
            except:
                pass

        # Adjust all entity positions to place robot on ground (Y=0)
        if min_y_with_bounds != float('inf'):
            adjustment = -min_y_with_bounds
            for entity in self.renderer.entities:
                entity.y += adjustment
            print(f"  Ground adjustment: +{adjustment:.3f} (lowest point was at {min_y_with_bounds:.3f})")

            # Verify: re-check min Y after adjustment
            new_min_y = float('inf')
            for entity in self.renderer.entities:
                try:
                    if hasattr(entity, 'model') and entity.model:
                        bounds = entity.model.getTightBounds()
                        if bounds:
                            model_min_y = bounds[0].y * entity.scale_y
                            local_min_y = entity.y + model_min_y
                            new_min_y = min(new_min_y, local_min_y)
                except:
                    pass
            print(f"  After adjustment: lowest point local Y = {new_min_y:.3f}")

        # Calculate rotation center offset from robotdef
        self._calculate_rotation_center()

        print(f"Loaded {self.renderer.part_count} parts "
              f"({len(self.renderer.missing_parts)} missing)")
        if self.renderer.entities_by_submodel:
            print(f"  Submodels: {list(self.renderer.entities_by_submodel.keys())}")

        # Find wheel entities for animation
        self._find_wheel_entities()

    def _calculate_ground_offset(self) -> float:
        """Calculate y_offset to position robot on the ground based on wheel radius.

        Uses wheel_diameter from robotdef, or defaults to 44mm (VEX IQ standard).
        The drivetrain rotation center Y coordinate tells us where the axle is,
        and we offset by wheel radius to place wheels on ground.

        Returns:
            Y offset in renderer coordinate space (POSITION_SCALE units)
        """
        # Get wheel diameter (mm) - default to 44mm VEX IQ wheel
        wheel_diameter_mm = 44.0
        if self.robotdef:
            wheel_diameter_mm = self.robotdef.drivetrain.wheel_diameter or 44.0

        # Calculate wheel radius in LDU (1 LDU = 0.4mm)
        wheel_radius_ldu = (wheel_diameter_mm / 2.0) / 0.4

        # Get drivetrain Y position in LDU (where the axle is)
        axle_y_ldu = 0
        if self.robotdef:
            axle_y_ldu = self.robotdef.drivetrain.rotation_center[1]

        # In LDraw: Y is down, so higher Y values are lower in space
        # The wheel bottom is at axle_y + radius (further "down" in LDraw)
        # We want this point to be at Y=0 in Ursina (on the ground)
        #
        # After Y-flip: ursina_y = -ldraw_y * POSITION_SCALE + y_offset
        # For wheel bottom (ldraw_y = axle_y + radius), we want ursina_y = 0
        # 0 = -(axle_y + radius) * POSITION_SCALE + y_offset
        # y_offset = (axle_y + radius) * POSITION_SCALE

        y_offset = (axle_y_ldu + wheel_radius_ldu) * POSITION_SCALE

        print(f"  Wheel diameter: {wheel_diameter_mm}mm, radius: {wheel_radius_ldu} LDU")
        print(f"  Axle Y (LDU): {axle_y_ldu}")

        return y_offset

    def _calculate_rotation_center(self):
        """Calculate the drivetrain rotation center offset in local robot coordinates."""
        if not self.robotdef:
            self._rotation_center_offset = Vec3(0, 0, 0)
            return

        # Get rotation center in LDU from robotdef
        ldu = self.robotdef.drivetrain.rotation_center

        # Convert to Ursina coordinates (apply POSITION_SCALE, negate Y)
        # Then apply y_offset used during rendering
        y_offset = self.renderer.y_offset if self.renderer else 0
        self._rotation_center_offset = Vec3(
            ldu[0] * POSITION_SCALE,
            -ldu[1] * POSITION_SCALE + y_offset,
            ldu[2] * POSITION_SCALE
        )
        print(f"  Rotation center offset: {self._rotation_center_offset}")

    def _find_wheel_entities(self):
        """Find wheel entities from left and right drive submodels for animation."""
        self._wheel_entities_left = []
        self._wheel_entities_right = []
        self._wheel_original_mats = {}  # Store original transformation matrices

        if not self.renderer or not self.robotdef:
            print("  WARNING: No renderer or robotdef for wheel detection")
            return

        # Get drive submodel names from robotdef
        left_name = self.robotdef.drivetrain.left_drive
        right_name = self.robotdef.drivetrain.right_drive
        print(f"  Drive submodels: left={left_name}, right={right_name}")

        # Debug: Check what submodels have special_parts
        for sm_name, sm_config in self.robotdef.submodels.items():
            if sm_config.special_parts:
                print(f"    Submodel {sm_name} has {len(sm_config.special_parts)} special_parts")

        # Get wheel part numbers from robotdef (extracted from special_parts)
        left_wheel_parts = self.robotdef.get_wheel_part_numbers_for_submodel(left_name) if left_name else set()
        right_wheel_parts = self.robotdef.get_wheel_part_numbers_for_submodel(right_name) if right_name else set()
        print(f"  Wheel part numbers: left={left_wheel_parts}, right={right_wheel_parts}")

        if left_name and left_name in self.renderer.entities_by_submodel:
            all_entities = self.renderer.entities_by_submodel[left_name]
            # Debug: show part numbers of entities
            entity_parts = [e.part_number for e in all_entities if hasattr(e, 'part_number')]
            print(f"  Left submodel entity part numbers: {entity_parts}")

            self._wheel_entities_left = [
                e for e in all_entities
                if hasattr(e, 'part_number') and e.part_number in left_wheel_parts
            ]
            print(f"  Left wheel entities: {len(self._wheel_entities_left)} (of {len(all_entities)} in submodel)")

            # Store original transformation matrices
            for entity in self._wheel_entities_left:
                self._wheel_original_mats[id(entity)] = entity.getMat()
        else:
            print(f"  WARNING: Left drive '{left_name}' not in entities_by_submodel")
            print(f"    Available submodels: {list(self.renderer.entities_by_submodel.keys())}")

        if right_name and right_name in self.renderer.entities_by_submodel:
            all_entities = self.renderer.entities_by_submodel[right_name]
            # Debug: show part numbers of entities
            entity_parts = [e.part_number for e in all_entities if hasattr(e, 'part_number')]
            print(f"  Right submodel entity part numbers: {entity_parts}")

            self._wheel_entities_right = [
                e for e in all_entities
                if hasattr(e, 'part_number') and e.part_number in right_wheel_parts
            ]
            print(f"  Right wheel entities: {len(self._wheel_entities_right)} (of {len(all_entities)} in submodel)")

            # Store original transformation matrices
            for entity in self._wheel_entities_right:
                self._wheel_original_mats[id(entity)] = entity.getMat()
        else:
            print(f"  WARNING: Right drive '{right_name}' not in entities_by_submodel")
            print(f"    Available submodels: {list(self.renderer.entities_by_submodel.keys())}")

    def _position_on_ground(self):
        """Position robot so wheels sit on ground (Y=0)."""
        if not self.renderer or not self.renderer.entities:
            return

        # Find lowest world Y position among all entities
        min_world_y = float('inf')
        for entity in self.renderer.entities:
            try:
                if hasattr(entity, 'model') and entity.model:
                    bounds = entity.model.getTightBounds()
                    if bounds:
                        # Get entity's world position and add model bounds
                        model_min_y = bounds[0].y * entity.world_scale_y
                        world_min_y = entity.world_y + model_min_y
                        min_world_y = min(min_world_y, world_min_y)
            except:
                pass

        print(f"  World min Y after scaling: {min_world_y:.4f}")

        # Move robot up so lowest point is at Y=0
        if min_world_y != float('inf') and abs(min_world_y) > 0.001:
            self.y -= min_world_y
            print(f"  Adjusted robot.y by {-min_world_y:.4f} to {self.y:.4f}")

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

        # Store individual wheel speeds for animation
        # Left wheel rotates based on left_power, right based on right_power
        self._left_wheel_speed = left_power / 100.0 * 360  # degrees per second at full power
        self._right_wheel_speed = right_power / 100.0 * 360

    def move(self, dt):
        """Move robot based on current velocity.

        The robot rotates around its drivetrain center (defined in .robotdef)
        rather than the entity origin. This makes turning more realistic.
        """
        if self.velocity.length() > 0.001 or abs(self.angular_velocity) > 0.001:
            # Get current heading in radians
            rad = math.radians(self.rotation_y)
            cos_r, sin_r = math.cos(rad), math.sin(rad)

            # Calculate rotation center offset in world space (rotated by current heading)
            # Scale offset by entity scale since it's in local coordinates
            offset = self._rotation_center_offset * self.scale
            offset_world_x = offset.x * cos_r - offset.z * sin_r
            offset_world_z = offset.x * sin_r + offset.z * cos_r

            # World position of the drivetrain rotation center
            pivot_world_x = self.x + offset_world_x
            pivot_world_z = self.z + offset_world_z

            # Calculate forward velocity in world space
            forward_world_x = self.velocity.z * sin_r
            forward_world_z = self.velocity.z * cos_r

            # Move the pivot point forward
            pivot_world_x += forward_world_x * dt
            pivot_world_z += forward_world_z * dt

            # Apply rotation
            old_rotation = self.rotation_y
            self.rotation_y += self.angular_velocity * dt

            # Calculate new offset in world space with new heading
            rad_new = math.radians(self.rotation_y)
            cos_new, sin_new = math.cos(rad_new), math.sin(rad_new)
            new_offset_world_x = offset.x * cos_new - offset.z * sin_new
            new_offset_world_z = offset.x * sin_new + offset.z * cos_new

            # Set entity position so rotation center stays at pivot point
            self.x = pivot_world_x - new_offset_world_x
            self.z = pivot_world_z - new_offset_world_z

            # Keep robot on field
            bound_x = 3.8
            bound_z = 2.8
            self.x = max(-bound_x, min(bound_x, self.x))
            self.z = max(-bound_z, min(bound_z, self.z))

        # TODO: Wheel animation disabled - needs better approach (possibly Bullet physics)
        # self._animate_wheels(dt)

    def _animate_wheels(self, dt):
        """Animate wheel rotation based on motor speeds.

        Wheels rotate around their local Y axis (the axle in the wheel's model space).
        We compose a spin rotation with the original LDraw transformation matrix.
        """
        from panda3d.core import LMatrix4f

        # Update rotation accumulators
        self._left_wheel_rotation += self._left_wheel_speed * dt
        self._right_wheel_rotation += self._right_wheel_speed * dt

        # Keep rotation in reasonable range
        self._left_wheel_rotation %= 360
        self._right_wheel_rotation %= 360

        def apply_wheel_spin(entity, spin_degrees):
            """Apply spin rotation to a wheel entity."""
            orig_mat = self._wheel_original_mats.get(id(entity))
            if orig_mat is None:
                return

            # Create a rotation matrix around the Y axis (wheel's local axle)
            # VEX IQ wheels are modeled with axle along Y
            spin_rad = math.radians(spin_degrees)
            cos_s, sin_s = math.cos(spin_rad), math.sin(spin_rad)

            # Rotation around Y axis
            spin_mat = LMatrix4f(
                cos_s, 0, -sin_s, 0,
                0, 1, 0, 0,
                sin_s, 0, cos_s, 0,
                0, 0, 0, 1
            )

            # Compose: apply spin first (in model space), then original transform
            combined = spin_mat * orig_mat
            entity.setMat(combined)

        # Apply rotation to wheel entities
        for entity in self._wheel_entities_left:
            # Left wheels spin forward when power is positive
            apply_wheel_spin(entity, self._left_wheel_rotation)

        for entity in self._wheel_entities_right:
            # Right wheels spin in the opposite direction (mirrored)
            apply_wheel_spin(entity, -self._right_wheel_rotation)


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
