"""
VEX IQ Control Panel
====================
Bottom panel UI showing gamepad visualization and port status.
Replicates the pygame virtual controller visual style.

Layout:
- Left side: Gamepad with animated joysticks and buttons
- Right side: 12 port indicators for motors/pneumatics
"""

from ursina import *


# UI Colors (use built-in colors - color.rgb() doesn't work in Ursina)
UI_BLACK = color.black
UI_DARK_GRAY = color.dark_gray
UI_MID_GRAY = color.gray
UI_LIGHT_GRAY = color.light_gray
UI_WHITE = color.white
UI_BLUE = color.azure
UI_LIGHT_BLUE = color.cyan
UI_GREEN = color.lime
UI_RED = color.red
UI_ORANGE = color.orange
UI_YELLOW = color.yellow


class PortIndicator:
    """Individual port indicator with device type and state display."""

    def __init__(self, port_num: int, x: float, y: float, size: float = 0.038):
        self.port_num = port_num
        self.x = x
        self.y = y
        self.size = size
        self.device_type = None  # 'motor', 'pneumatic', or None
        self.device_name = ""

        # Port outer ring (border)
        self.outer_ring = Entity(
            parent=camera.ui,
            model='circle',
            color=UI_MID_GRAY,
            scale=size,
            position=(x, y, -0.1)
        )

        # Port background circle (changes color based on state)
        self.bg = Entity(
            parent=camera.ui,
            model='circle',
            color=UI_DARK_GRAY,
            scale=size * 0.9,
            position=(x, y, -0.2)
        )

        # Port label (P1, P2, etc.) - larger and bolder
        self.label = Text(
            text=f'P{port_num}',
            parent=camera.ui,
            scale=0.7,
            position=(x, y + 0.014, -0.3),
            origin=(0, 0),
            color=UI_WHITE
        )

        # Value/state text (velocity or EXT/RET) - larger for readability
        self.value_text = Text(
            text='0%',
            parent=camera.ui,
            scale=0.55,
            position=(x, y - 0.012, -0.3),
            origin=(0, 0),
            color=UI_LIGHT_GRAY
        )

        # Device name below (Motor/Pneu) - larger
        self.name_text = Text(
            text='',
            parent=camera.ui,
            scale=0.45,
            position=(x, y - size * 0.9, -0.3),
            origin=(0, 0),
            color=UI_LIGHT_GRAY
        )

    def set_device(self, device_type: str, name: str = ""):
        """Set the device type for this port."""
        self.device_type = device_type
        self.device_name = name

        if device_type == 'motor':
            self.name_text.text = name if name else 'Motor'
            self.outer_ring.color = UI_GREEN
        elif device_type == 'pneumatic':
            self.name_text.text = name if name else 'Pneu'
            self.outer_ring.color = UI_BLUE
        else:
            self.name_text.text = ''
            self.outer_ring.color = UI_MID_GRAY

    def update_motor(self, velocity: float, spinning: bool):
        """Update motor state display."""
        if velocity > 0:
            self.bg.color = UI_GREEN
            # Dark text on bright green background for contrast
            self.label.color = UI_BLACK
            self.value_text.color = UI_BLACK
        elif velocity < 0:
            self.bg.color = UI_RED
            # Dark text on bright red background for contrast
            self.label.color = UI_BLACK
            self.value_text.color = UI_BLACK
        else:
            self.bg.color = UI_DARK_GRAY
            # Light text on dark background
            self.label.color = UI_WHITE
            self.value_text.color = UI_LIGHT_GRAY

        if spinning:
            self.value_text.text = f'{int(velocity)}%'
        else:
            self.value_text.text = '0%'

    def update_pneumatic(self, extended: bool):
        """Update pneumatic state display."""
        if extended:
            self.bg.color = UI_BLUE
            # Dark text on bright blue background for contrast
            self.label.color = UI_BLACK
            self.value_text.color = UI_BLACK
            self.value_text.text = 'EXT'
        else:
            self.bg.color = UI_DARK_GRAY
            # Light text on dark background
            self.label.color = UI_WHITE
            self.value_text.color = UI_LIGHT_GRAY
            self.value_text.text = 'RET'


class ControlPanel:
    """Main control panel managing the bottom panel UI.

    Layout (bottom 25% of screen):
    ┌──────────────────────────────────────────────────────────┐
    │ CONTROLLER (gamepad)      │  PORTS (12 indicators)       │
    │ [Joysticks] [Buttons]     │  [P1][P2]...[P12]            │
    └──────────────────────────────────────────────────────────┘
    """

    PANEL_HEIGHT = 0.25
    PANEL_Y = -0.375  # Center of bottom panel

    def __init__(self):
        # Panel background (z=0, furthest back)
        self.panel_bg = Entity(
            parent=camera.ui,
            model='quad',
            color=UI_BLACK,
            scale=(2, self.PANEL_HEIGHT),
            position=(0, self.PANEL_Y, 0)
        )

        # Divider line at top (z=-0.1 to be in front of background)
        self.divider_top = Entity(
            parent=camera.ui,
            model='quad',
            color=UI_MID_GRAY,
            scale=(2, 0.003),
            position=(0, -0.25, -0.1)
        )

        # Vertical divider between controller and ports
        self.divider_mid = Entity(
            parent=camera.ui,
            model='quad',
            color=UI_MID_GRAY,
            scale=(0.003, self.PANEL_HEIGHT - 0.02),
            position=(0.05, self.PANEL_Y, -0.1)
        )

        # Section titles (z=-0.2 to be in front)
        # Controller area: left edge to divider - shift left for proper visual centering
        self.ctrl_title = Text(
            text='CONTROLLER',
            parent=camera.ui,
            scale=0.9,
            position=(-0.32, -0.265, -0.2),
            origin=(0, 0),  # Centered
            color=UI_WHITE
        )

        # Ports area: divider to right edge - shift right for proper visual centering
        self.ports_title = Text(
            text='PORTS',
            parent=camera.ui,
            scale=0.9,
            position=(0.38, -0.265, -0.2),
            origin=(0, 0),  # Centered
            color=UI_WHITE
        )

        # Create joystick displays
        self._create_joysticks()

        # Create button displays
        self._create_buttons()

        # Create port indicators
        self._create_ports()

        # Status text (top center, above 3D view)
        self.status_text = Text(
            text='Ready',
            parent=camera.ui,
            scale=0.7,
            position=(0, 0.47, -0.2),
            origin=(0, 0.5),  # Anchor to top
            color=UI_YELLOW
        )

        # Gamepad status (centered in controller pane bottom)
        self.gamepad_status = Text(
            text='No gamepad',
            parent=camera.ui,
            scale=0.5,
            position=(-0.32, -0.485, -0.2),
            origin=(0, 0),  # Centered
            color=UI_ORANGE
        )

        # Mode indicator (below controller title)
        self.mode_text = Text(
            text='',
            parent=camera.ui,
            scale=0.5,
            position=(-0.32, -0.285, -0.2),
            origin=(0, 0),
            color=UI_YELLOW
        )

        # FPS indicator (top right corner)
        self.fps_text = Text(
            text='FPS: --',
            parent=camera.ui,
            scale=0.6,
            position=(0.47, 0.47, -0.2),
            origin=(0.5, 0.5),
            color=UI_LIGHT_GRAY
        )
        self._fps_update_timer = 0
        self._frame_count = 0
        self._last_fps = 0

    def _create_joysticks(self):
        """Create joystick visualizations - larger like pygame version."""
        # Joystick positions - shifted further left to center in controller pane
        js_size = 0.09  # Larger joysticks
        left_x = -0.46   # Further left for proper visual centering
        right_x = -0.30  # Further left for proper visual centering
        js_y = -0.37

        # Store joystick size for movement calculations
        self._js_size = js_size
        self._js_max_offset = js_size * 0.28  # How far stick can move (in parent-relative units)

        # === LEFT JOYSTICK ===
        # Container entity for left joystick (all parts will be children)
        self.left_js_container = Entity(
            parent=camera.ui,
            position=(left_x, js_y, 0)
        )

        # Background circle (outer ring)
        self.left_js_outer = Entity(
            parent=self.left_js_container,
            model='circle',
            color=UI_MID_GRAY,
            scale=js_size,
            z=-0.1
        )

        # Inner dark circle
        self.left_js_bg = Entity(
            parent=self.left_js_container,
            model='circle',
            color=UI_DARK_GRAY,
            scale=js_size * 0.92,
            z=-0.2
        )

        # Crosshairs (horizontal)
        Entity(
            parent=self.left_js_container,
            model='quad',
            color=UI_MID_GRAY,
            scale=(js_size * 0.8, 0.002),
            z=-0.3
        )
        # Crosshairs (vertical)
        Entity(
            parent=self.left_js_container,
            model='quad',
            color=UI_MID_GRAY,
            scale=(0.002, js_size * 0.8),
            z=-0.3
        )

        # Stick highlight ring (behind stick)
        self.left_js_ring = Entity(
            parent=self.left_js_container,
            model='circle',
            color=UI_WHITE,
            scale=js_size * 0.38,
            z=-0.35
        )

        # Joystick stick (the movable part)
        self.left_js_stick = Entity(
            parent=self.left_js_container,
            model='circle',
            color=UI_BLUE,
            scale=js_size * 0.35,
            z=-0.4
        )

        # Label above joystick
        self.left_js_label = Text(
            text='LEFT',
            parent=camera.ui,
            scale=0.5,
            position=(left_x, js_y + js_size * 0.65, -0.2),
            origin=(0, 0),
            color=UI_LIGHT_GRAY
        )

        # Values below joystick
        self.left_js_values = Text(
            text='A:  0  B:  0',
            parent=camera.ui,
            scale=0.45,
            position=(left_x, js_y - js_size * 0.65, -0.2),
            origin=(0, 0),
            color=UI_LIGHT_GRAY
        )

        # === RIGHT JOYSTICK ===
        # Container entity for right joystick
        self.right_js_container = Entity(
            parent=camera.ui,
            position=(right_x, js_y, 0)
        )

        # Background circle (outer ring)
        self.right_js_outer = Entity(
            parent=self.right_js_container,
            model='circle',
            color=UI_MID_GRAY,
            scale=js_size,
            z=-0.1
        )

        # Inner dark circle
        self.right_js_bg = Entity(
            parent=self.right_js_container,
            model='circle',
            color=UI_DARK_GRAY,
            scale=js_size * 0.92,
            z=-0.2
        )

        # Crosshairs
        Entity(
            parent=self.right_js_container,
            model='quad',
            color=UI_MID_GRAY,
            scale=(js_size * 0.8, 0.002),
            z=-0.3
        )
        Entity(
            parent=self.right_js_container,
            model='quad',
            color=UI_MID_GRAY,
            scale=(0.002, js_size * 0.8),
            z=-0.3
        )

        # Stick highlight ring (behind stick)
        self.right_js_ring = Entity(
            parent=self.right_js_container,
            model='circle',
            color=UI_WHITE,
            scale=js_size * 0.38,
            z=-0.35
        )

        # Joystick stick
        self.right_js_stick = Entity(
            parent=self.right_js_container,
            model='circle',
            color=UI_BLUE,
            scale=js_size * 0.35,
            z=-0.4
        )

        # Label above joystick
        self.right_js_label = Text(
            text='RIGHT',
            parent=camera.ui,
            scale=0.5,
            position=(right_x, js_y + js_size * 0.65, -0.2),
            origin=(0, 0),
            color=UI_LIGHT_GRAY
        )

        # Values below joystick
        self.right_js_values = Text(
            text='C:  0  D:  0',
            parent=camera.ui,
            scale=0.45,
            position=(right_x, js_y - js_size * 0.65, -0.2),
            origin=(0, 0),
            color=UI_LIGHT_GRAY
        )

    def _create_buttons(self):
        """Create button indicators like pygame version."""
        self.button_entities = {}
        self.button_labels = {}

        # Button layout - 2 columns of 4 buttons each
        # Shifted left to center in controller pane
        # Left column: L-Up, L-Dn, E-Up, E-Dn
        # Right column: R-Up, R-Dn, F-Up, F-Dn
        button_config = [
            ('L-Up', -0.17, -0.30),
            ('L-Dn', -0.17, -0.34),
            ('E-Up', -0.17, -0.40),
            ('E-Dn', -0.17, -0.44),
            ('R-Up', -0.10, -0.30),
            ('R-Dn', -0.10, -0.34),
            ('F-Up', -0.10, -0.40),
            ('F-Dn', -0.10, -0.44),
        ]

        btn_width = 0.055
        btn_height = 0.028

        for name, x, y in button_config:
            # Button border (behind)
            Entity(
                parent=camera.ui,
                model='quad',
                color=UI_MID_GRAY,
                scale=(btn_width + 0.003, btn_height + 0.003),
                position=(x, y, -0.15)
            )

            # Button background
            bg = Entity(
                parent=camera.ui,
                model='quad',
                color=UI_DARK_GRAY,
                scale=(btn_width, btn_height),
                position=(x, y, -0.2)
            )

            # Button label
            label = Text(
                text=name,
                parent=camera.ui,
                scale=0.4,
                position=(x, y + 0.002, -0.3),
                origin=(0, 0),
                color=UI_WHITE
            )

            self.button_entities[name] = bg
            self.button_labels[name] = label

    def _create_ports(self):
        """Create port indicators using PortIndicator class."""
        self.port_indicators: dict[int, PortIndicator] = {}

        # Larger ports, centered in the ports area (shifted right for visual centering)
        port_size = 0.062  # Bigger ports for better readability
        spacing_x = 0.070  # Spacing between port centers
        # Total width = 5 * spacing = 0.35
        # Visually centered around 0.38, so start at 0.38 - 0.175 = 0.205
        start_x = 0.205
        row1_y = -0.325
        row2_y = -0.435

        for i in range(1, 13):
            col = (i - 1) % 6
            row = (i - 1) // 6
            x = start_x + col * spacing_x
            y = row1_y if row == 0 else row2_y

            indicator = PortIndicator(i, x, y, port_size)
            self.port_indicators[i] = indicator

    def register_motor(self, port: int, name: str = ""):
        """Register a motor on a port."""
        if port in self.port_indicators:
            self.port_indicators[port].set_device('motor', name)

    def register_pneumatic(self, port: int, name: str = ""):
        """Register a pneumatic on a port."""
        if port in self.port_indicators:
            self.port_indicators[port].set_device('pneumatic', name)

    def update_joystick(self, side: str, x: int, y: int):
        """Update joystick position (-100 to 100 for each axis)."""
        # Positions are relative to container center (0, 0)
        offset_x = (x / 100) * self._js_max_offset
        offset_y = (y / 100) * self._js_max_offset

        if side == 'left':
            # Move both the stick and its ring (relative to container)
            self.left_js_stick.x = offset_x
            self.left_js_stick.y = offset_y
            self.left_js_ring.x = offset_x
            self.left_js_ring.y = offset_y

            # Update values text (A=vertical, B=horizontal for left stick)
            self.left_js_values.text = f'A:{y:4d}  B:{x:4d}'

            # Change color when active
            if abs(x) > 5 or abs(y) > 5:
                self.left_js_stick.color = UI_LIGHT_BLUE
            else:
                self.left_js_stick.color = UI_BLUE

        elif side == 'right':
            # Move both the stick and its ring (relative to container)
            self.right_js_stick.x = offset_x
            self.right_js_stick.y = offset_y
            self.right_js_ring.x = offset_x
            self.right_js_ring.y = offset_y

            # Update values text (C=horizontal, D=vertical for right stick)
            self.right_js_values.text = f'C:{x:4d}  D:{y:4d}'

            if abs(x) > 5 or abs(y) > 5:
                self.right_js_stick.color = UI_LIGHT_BLUE
            else:
                self.right_js_stick.color = UI_BLUE

    def update_button(self, name: str, pressed: bool):
        """Update button state."""
        # Map full names to short names used in UI
        name_map = {
            'L-Up': 'L-Up', 'L-Down': 'L-Dn',
            'R-Up': 'R-Up', 'R-Down': 'R-Dn',
            'E-Up': 'E-Up', 'E-Down': 'E-Dn',
            'F-Up': 'F-Up', 'F-Down': 'F-Dn'
        }
        short_name = name_map.get(name, name)

        if short_name in self.button_entities:
            if pressed:
                self.button_entities[short_name].color = UI_BLUE
            else:
                self.button_entities[short_name].color = UI_DARK_GRAY

    def update_motor(self, port: int, velocity: float, spinning: bool = True):
        """Update motor display for a port."""
        if port in self.port_indicators:
            self.port_indicators[port].update_motor(velocity, spinning)

    def update_pneumatic(self, port: int, extended: bool):
        """Update pneumatic display for a port."""
        if port in self.port_indicators:
            self.port_indicators[port].update_pneumatic(extended)

    def set_status(self, text: str):
        """Update status text."""
        self.status_text.text = text

    def set_mode(self, mode_name: str):
        """Update mode display."""
        self.mode_text.text = f'[{mode_name}]' if mode_name else ''

    def set_gamepad_connected(self, connected: bool, name: str = ''):
        """Update gamepad connection status."""
        if connected:
            short_name = name[:25] if len(name) > 25 else name
            self.gamepad_status.text = f'Gamepad: {short_name}'
            self.gamepad_status.color = UI_GREEN
        else:
            self.gamepad_status.text = 'No gamepad (mouse: drag joysticks)'
            self.gamepad_status.color = UI_ORANGE

    def update_fps(self, dt: float):
        """Update FPS display - call each frame with delta time."""
        self._frame_count += 1
        self._fps_update_timer += dt

        # Update display every 0.5 seconds
        if self._fps_update_timer >= 0.5:
            fps = self._frame_count / self._fps_update_timer
            self._last_fps = fps
            self.fps_text.text = f'FPS: {int(fps)}'
            self._frame_count = 0
            self._fps_update_timer = 0
