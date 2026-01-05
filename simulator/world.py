"""
VEX IQ 3D World
===============
Ursina-based 3D world with VEX IQ field grid.
"""

from ursina import *


class VexField(Entity):
    """VEX IQ competition field - flat grid surface.

    VEX IQ fields have a dark gray base with lighter grid lines,
    similar to foam tile competition mats.
    """

    # Standard VEX IQ field is 6x6 feet (1.83m x 1.83m)
    FIELD_SIZE = 6  # feet
    GRID_LINES = 6  # number of grid squares per side

    # VEX IQ field colors (use built-in colors - color.rgb() doesn't work)
    FIELD_COLOR = color.dark_gray
    GRID_COLOR = color.gray
    BORDER_COLOR = color.smoke
    ACCENT_COLOR = color.red

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.create_field()

    def create_field(self):
        """Create the field floor and grid lines."""
        # Field floor - dark gray surface (like foam tiles)
        # Use flat cube instead of plane (plane model ignores color in Ursina)
        self.floor = Entity(
            parent=self,
            model='cube',
            scale=(self.FIELD_SIZE, 0.02, self.FIELD_SIZE),
            position=(0, -0.01, 0),
            color=self.FIELD_COLOR,
            collider='box'
        )

        # Grid lines
        self.create_grid_lines()

        # Field border
        self.create_border()

    def create_grid_lines(self):
        """Create visible grid lines on the field."""
        grid_spacing = self.FIELD_SIZE / self.GRID_LINES
        half_size = self.FIELD_SIZE / 2
        line_width = 0.03  # Wider lines for visibility

        # Create horizontal and vertical lines
        for i in range(self.GRID_LINES + 1):
            offset = -half_size + (i * grid_spacing)

            # Horizontal line (along X)
            Entity(
                parent=self,
                model='cube',
                scale=(self.FIELD_SIZE, 0.01, line_width),
                position=(0, 0.005, offset),
                color=self.GRID_COLOR
            )

            # Vertical line (along Z)
            Entity(
                parent=self,
                model='cube',
                scale=(line_width, 0.01, self.FIELD_SIZE),
                position=(offset, 0.005, 0),
                color=self.GRID_COLOR
            )

        # Center cross (more prominent)
        Entity(
            parent=self,
            model='cube',
            scale=(self.FIELD_SIZE, 0.012, line_width * 1.5),
            position=(0, 0.006, 0),
            color=self.ACCENT_COLOR
        )
        Entity(
            parent=self,
            model='cube',
            scale=(line_width * 1.5, 0.012, self.FIELD_SIZE),
            position=(0, 0.006, 0),
            color=self.ACCENT_COLOR
        )

    def create_border(self):
        """Create field border walls."""
        wall_height = 0.25
        wall_thickness = 0.08
        half_size = self.FIELD_SIZE / 2

        # Border walls (4 sides)
        walls = [
            # (position, scale)
            ((0, wall_height/2, half_size + wall_thickness/2), (self.FIELD_SIZE + wall_thickness*2, wall_height, wall_thickness)),
            ((0, wall_height/2, -half_size - wall_thickness/2), (self.FIELD_SIZE + wall_thickness*2, wall_height, wall_thickness)),
            ((half_size + wall_thickness/2, wall_height/2, 0), (wall_thickness, wall_height, self.FIELD_SIZE)),
            ((-half_size - wall_thickness/2, wall_height/2, 0), (wall_thickness, wall_height, self.FIELD_SIZE)),
        ]

        for pos, scale in walls:
            Entity(
                parent=self,
                model='cube',
                position=pos,
                scale=scale,
                color=self.BORDER_COLOR
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
        turn = (right_power - left_power) / 200

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

            # Keep robot on field (simple bounds)
            bound = 2.8
            self.x = max(-bound, min(bound, self.x))
            self.z = max(-bound, min(bound, self.z))


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
