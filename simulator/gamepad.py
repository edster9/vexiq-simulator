"""
Gamepad Manager
===============
Handles gamepad/joystick input using pygame.
Maps physical controller to VEX IQ Controller axes and buttons.

Supports multiple gamepads for local multiplayer (up to 4 controllers).
Automatically detects platform (Windows/Linux) and uses appropriate mappings.
"""

import platform
from typing import Optional

# Detect platform
IS_WINDOWS = platform.system() == 'Windows'

# Try to import pygame, but make it optional
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("Warning: pygame not available - gamepad support disabled")


class GamepadState:
    """State for a single gamepad."""

    def __init__(self, gamepad_id: int):
        self.gamepad_id = gamepad_id
        self.robot_id: Optional[int] = None  # Which robot this controls

        # Axis values (-100 to 100)
        self.axes = {
            'A': 0,  # Left Y
            'B': 0,  # Left X
            'C': 0,  # Right X
            'D': 0,  # Right Y
        }

        # Button states
        self.buttons = {
            'LUp': False,
            'LDown': False,
            'RUp': False,
            'RDown': False,
            'EUp': False,
            'EDown': False,
            'FUp': False,
            'FDown': False,
        }

    def get_axes(self) -> dict:
        return self.axes.copy()

    def get_buttons(self) -> dict:
        return {
            'L-Up': self.buttons['LUp'],
            'L-Down': self.buttons['LDown'],
            'R-Up': self.buttons['RUp'],
            'R-Down': self.buttons['RDown'],
            'E-Up': self.buttons['EUp'],
            'E-Down': self.buttons['EDown'],
            'F-Up': self.buttons['FUp'],
            'F-Down': self.buttons['FDown'],
        }


class GamepadManager:
    """Manages multiple gamepad inputs and maps to VEX IQ controllers.

    Supports up to MAX_GAMEPADS controllers for local multiplayer.

    VEX IQ Controller Mapping:
    - Axis A: Left stick Y (forward/back)
    - Axis B: Left stick X (left/right)
    - Axis C: Right stick X (left/right)
    - Axis D: Right stick Y (forward/back)

    Buttons:
    - L-Up, L-Down: Left shoulder buttons
    - R-Up, R-Down: Right shoulder buttons
    - E-Up, E-Down: Additional buttons (mapped to face buttons)
    - F-Up, F-Down: Additional buttons (mapped to face buttons)
    """

    # Maximum number of supported gamepads
    MAX_GAMEPADS = 4

    # Deadzone for analog sticks
    DEADZONE = 0.1

    def __init__(self, debug: bool = False):
        # Debug mode to print raw gamepad values
        self.debug = debug
        self._debug_counter = 0

        # Multiple gamepad support
        self.joysticks: dict = {}
        self.gamepad_states: dict[int, GamepadState] = {}

        # Legacy single-gamepad interface (for backwards compatibility)
        self.joystick = None
        self.connected = False
        self.axes = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
        self.buttons = {
            'LUp': False, 'LDown': False,
            'RUp': False, 'RDown': False,
            'EUp': False, 'EDown': False,
            'FUp': False, 'FDown': False,
        }

        # Only initialize pygame if available
        if not PYGAME_AVAILABLE:
            print("Gamepad manager: pygame not available, gamepad disabled")
            return

        # Initialize pygame joystick subsystem
        pygame.init()
        pygame.joystick.init()

        print(f"Gamepad manager initialized (Platform: {platform.system()})")

        # Scan for connected gamepads
        self.scan_gamepads()

    def scan_gamepads(self):
        """Scan for all connected gamepads."""
        if not PYGAME_AVAILABLE:
            return

        pygame.joystick.quit()
        pygame.joystick.init()

        count = pygame.joystick.get_count()
        print(f"Found {count} gamepad(s)")

        for i in range(min(count, self.MAX_GAMEPADS)):
            self.connect_gamepad(i)

        # Set legacy interface to first gamepad
        if count > 0 and 0 in self.joysticks:
            self.joystick = self.joysticks[0]
            self.connected = True

    def connect_gamepad(self, index: int) -> bool:
        """Connect to a specific gamepad by index."""
        try:
            joystick = pygame.joystick.Joystick(index)
            joystick.init()

            self.joysticks[index] = joystick
            self.gamepad_states[index] = GamepadState(index)

            print(f"Gamepad {index} connected: {joystick.get_name()}")
            print(f"  Axes: {joystick.get_numaxes()}, Buttons: {joystick.get_numbuttons()}")
            return True

        except pygame.error as e:
            print(f"Failed to connect gamepad {index}: {e}")
            return False

    def get_gamepad_count(self) -> int:
        """Get number of connected gamepads."""
        return len(self.joysticks)

    def get_gamepad(self, index: int) -> Optional[GamepadState]:
        """Get state for a specific gamepad."""
        return self.gamepad_states.get(index)

    def assign_gamepad_to_robot(self, gamepad_index: int, robot_id: int):
        """Assign a gamepad to control a specific robot."""
        if gamepad_index in self.gamepad_states:
            self.gamepad_states[gamepad_index].robot_id = robot_id
            print(f"Gamepad {gamepad_index} assigned to Robot {robot_id}")

    def get_gamepad_for_robot(self, robot_id: int) -> Optional[GamepadState]:
        """Get the gamepad state controlling a specific robot."""
        for state in self.gamepad_states.values():
            if state.robot_id == robot_id:
                return state
        return None

    def apply_deadzone(self, value: float) -> float:
        """Apply deadzone to analog value."""
        if abs(value) < self.DEADZONE:
            return 0.0
        # Scale remaining range
        sign = 1 if value > 0 else -1
        return sign * (abs(value) - self.DEADZONE) / (1 - self.DEADZONE)

    def update(self):
        """Update all gamepad states - call each frame."""
        if not PYGAME_AVAILABLE:
            return

        # Process pygame events
        pygame.event.pump()

        # Check for new gamepads
        current_count = pygame.joystick.get_count()
        if current_count != len(self.joysticks):
            self.scan_gamepads()

        # Update each connected gamepad
        for idx, joystick in list(self.joysticks.items()):
            state = self.gamepad_states.get(idx)
            if not state:
                continue

            try:
                self._update_single_gamepad(joystick, state)
            except pygame.error:
                # Gamepad disconnected
                print(f"Gamepad {idx} disconnected")
                del self.joysticks[idx]
                del self.gamepad_states[idx]

        # Update legacy single-gamepad interface from first gamepad
        if 0 in self.gamepad_states:
            state = self.gamepad_states[0]
            self.axes = state.axes.copy()
            self.buttons = state.buttons.copy()
            self.connected = True
        else:
            self.connected = False

    def _update_single_gamepad(self, joystick, state: GamepadState):
        """Update state for a single gamepad."""
        num_axes = joystick.get_numaxes()
        num_buttons = joystick.get_numbuttons()

        # Debug output - print raw values periodically
        if self.debug:
            self._debug_counter += 1
            if self._debug_counter >= 60:  # Every ~1 second at 60fps
                self._debug_counter = 0
                axes_str = ', '.join([f'{i}:{joystick.get_axis(i):.2f}' for i in range(num_axes)])
                btns_str = ', '.join([f'{i}:{joystick.get_button(i)}' for i in range(num_buttons)])
                print(f"[Gamepad Debug] Axes: [{axes_str}]")
                print(f"[Gamepad Debug] Buttons: [{btns_str}]")

        # Platform-specific axis mapping
        if IS_WINDOWS:
            # Windows (DirectInput/XInput via pygame)
            # Typical Xbox controller on Windows:
            # Axis 0: Left X
            # Axis 1: Left Y (inverted)
            # Axis 2: Right X
            # Axis 3: Right Y (inverted)
            # Axis 4: Left/Right Triggers combined or separate
            if num_axes >= 2:
                left_x = self.apply_deadzone(joystick.get_axis(0))
                left_y = self.apply_deadzone(-joystick.get_axis(1))
                state.axes['B'] = int(left_x * 100)
                state.axes['A'] = int(left_y * 100)

            if num_axes >= 4:
                right_x = self.apply_deadzone(joystick.get_axis(2))
                right_y = self.apply_deadzone(-joystick.get_axis(3))
                state.axes['C'] = int(right_x * 100)
                state.axes['D'] = int(right_y * 100)

            # Windows trigger handling
            # Xbox controller on Windows via pygame:
            # - Axis 4: Left Trigger, rests at -1, goes to 1 when pressed
            # - Axis 5: Right Trigger, rests at -1, goes to 1 when pressed
            if num_axes >= 6:
                left_trigger = joystick.get_axis(4)
                right_trigger = joystick.get_axis(5)
                # Pressed when > 0 (halfway point between -1 and 1)
                state.buttons['LDown'] = left_trigger > 0.0
                state.buttons['RDown'] = right_trigger > 0.0
        else:
            # Linux (SDL/evdev)
            # Xbox controller on Linux:
            # Axis 0: Left X
            # Axis 1: Left Y (inverted)
            # Axis 2: Left Trigger (0 to 1)
            # Axis 3: Right X
            # Axis 4: Right Y (inverted)
            # Axis 5: Right Trigger (0 to 1)
            if num_axes >= 2:
                left_x = self.apply_deadzone(joystick.get_axis(0))
                left_y = self.apply_deadzone(-joystick.get_axis(1))
                state.axes['B'] = int(left_x * 100)
                state.axes['A'] = int(left_y * 100)

            if num_axes >= 5:
                right_x = self.apply_deadzone(joystick.get_axis(3))
                right_y = self.apply_deadzone(-joystick.get_axis(4))
                state.axes['C'] = int(right_x * 100)
                state.axes['D'] = int(right_y * 100)

            # Linux trigger handling - separate axes
            if num_axes >= 6:
                left_trigger = joystick.get_axis(2)
                right_trigger = joystick.get_axis(5)
                state.buttons['LDown'] = left_trigger > 0.5
                state.buttons['RDown'] = right_trigger > 0.5

        # Button mapping (same for both platforms - standard Xbox layout)
        # 0: A, 1: B, 2: X, 3: Y
        # 4: LB (Left Bumper), 5: RB (Right Bumper)
        # 6: Back/Select, 7: Start
        if num_buttons >= 6:
            state.buttons['LUp'] = joystick.get_button(4)    # LB → L-Up
            state.buttons['RUp'] = joystick.get_button(5)    # RB → R-Up
            state.buttons['EUp'] = joystick.get_button(3)    # Y → E-Up
            state.buttons['EDown'] = joystick.get_button(2)  # X → E-Down
            state.buttons['FUp'] = joystick.get_button(1)    # B → F-Up
            state.buttons['FDown'] = joystick.get_button(0)  # A → F-Down

        # Handle D-pad (hat) if available
        num_hats = joystick.get_numhats()
        if num_hats > 0:
            hat = joystick.get_hat(0)
            # Could use D-pad for additional controls
            # hat is (x, y) where each is -1, 0, or 1

    def get_axes(self) -> dict:
        """Get current axis values."""
        return self.axes.copy()

    def get_buttons(self) -> dict:
        """Get current button states with VEX naming."""
        return {
            'L-Up': self.buttons['LUp'],
            'L-Down': self.buttons['LDown'],
            'R-Up': self.buttons['RUp'],
            'R-Down': self.buttons['RDown'],
            'E-Up': self.buttons['EUp'],
            'E-Down': self.buttons['EDown'],
            'F-Up': self.buttons['FUp'],
            'F-Down': self.buttons['FDown'],
        }

    def get_button(self, name: str) -> bool:
        """Get specific button state."""
        clean_name = name.replace('-', '').replace('_', '')
        return self.buttons.get(clean_name, False)

    def close(self):
        """Clean up pygame resources."""
        if PYGAME_AVAILABLE:
            pygame.joystick.quit()


# Keyboard fallback for testing without gamepad
class KeyboardFallback:
    """Provides keyboard-based controller input for testing."""

    KEY_MAPPING = {
        # WASD for left stick
        'w': ('A', 100),
        's': ('A', -100),
        'a': ('B', -100),
        'd': ('B', 100),
        # Arrow keys for right stick
        'up arrow': ('D', 100),
        'down arrow': ('D', -100),
        'left arrow': ('C', -100),
        'right arrow': ('C', 100),
    }

    BUTTON_MAPPING = {
        'q': 'L-Up',
        'e': 'R-Up',
        'z': 'L-Down',
        'c': 'R-Down',
        '1': 'E-Up',
        '2': 'E-Down',
        '3': 'F-Up',
        '4': 'F-Down',
    }

    def __init__(self):
        self.axes = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
        self.buttons = {k: False for k in ['L-Up', 'L-Down', 'R-Up', 'R-Down',
                                            'E-Up', 'E-Down', 'F-Up', 'F-Down']}
        self.connected = True  # Keyboard is always "connected"

    def update(self):
        """Update from keyboard state - handled by Ursina input system."""
        pass

    def handle_key(self, key: str, pressed: bool):
        """Handle a key press/release."""
        # Axis keys
        if key in self.KEY_MAPPING:
            axis, value = self.KEY_MAPPING[key]
            self.axes[axis] = value if pressed else 0

        # Button keys
        if key in self.BUTTON_MAPPING:
            btn = self.BUTTON_MAPPING[key]
            self.buttons[btn] = pressed

    def get_axes(self) -> dict:
        return self.axes.copy()

    def get_buttons(self) -> dict:
        return self.buttons.copy()