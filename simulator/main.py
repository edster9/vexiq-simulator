"""
VEX IQ Simulator - Main Entry Point
====================================
Ursina-based 3D simulator for VEX IQ robots.

Usage:
    python -m simulator.main <path_to_iqpython_file>
    python -m simulator.main mode1.iqpython
"""

import sys
import os
import threading
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ursina import *

# Import simulator modules
from simulator.world import VexField, RobotPlaceholder, VexWorld
from simulator.control_panel import ControlPanel
from simulator.gamepad import GamepadManager
from simulator import vex_stub


class RobotInstance:
    """Represents a single robot in the simulation.

    Designed to support multiple robots in the future.
    Each robot has its own:
    - 3D entity (visual representation)
    - vex_stub state (motors, controller, etc.)
    - Code execution thread
    """

    def __init__(self, robot_id: int, name: str = "Robot"):
        self.robot_id = robot_id
        self.name = name
        self.entity: RobotPlaceholder = None
        self.code_thread: threading.Thread = None
        self.running = False

        # Position on field
        self.start_position = (0, 0.15, 0)
        self.start_rotation = 0

    def spawn(self, parent=None):
        """Create the robot entity in the 3D world."""
        self.entity = RobotPlaceholder()
        self.entity.position = self.start_position
        self.entity.rotation_y = self.start_rotation
        return self.entity

    def load_code(self, code: str) -> bool:
        """Load and execute robot code."""
        self.running = True

        def run_code():
            try:
                # Make vex_stub available as 'vex' module for import statements
                import sys
                sys.modules['vex'] = vex_stub

                # Make urandom available (MicroPython compatibility)
                # Create a simple module-like object for urandom
                import types
                urandom_module = types.ModuleType('urandom')
                urandom_module.seed = vex_stub.urandom.seed
                urandom_module.random = vex_stub.urandom.random
                urandom_module.randint = vex_stub.urandom.randint
                urandom_module.choice = vex_stub.urandom.choice
                sys.modules['urandom'] = urandom_module

                # Create namespace with vex_stub exports
                robot_globals = {
                    '__name__': '__main__',
                    '__builtins__': __builtins__,
                    'vex': vex_stub,  # Also add as global
                }

                # Import all vex_stub items into namespace
                for name in dir(vex_stub):
                    if not name.startswith('_'):
                        robot_globals[name] = getattr(vex_stub, name)

                # Pre-create controller so GUI can connect
                controller = vex_stub.Controller()

                print(f"[{self.name}] Executing robot code...")
                exec(code, robot_globals)

            except Exception as e:
                print(f"[{self.name}] Error: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self.running = False

        self.code_thread = threading.Thread(target=run_code, daemon=True)
        self.code_thread.start()
        return True

    def stop(self):
        """Stop the robot code execution."""
        self.running = False
        # Note: Thread will stop on its own since it's a daemon


class VexSimulator:
    """Main simulator application."""

    def __init__(self):
        self.app: Ursina = None
        self.world: VexWorld = None
        self.control_panel: ControlPanel = None
        self.gamepad: GamepadManager = None

        # Robot instances (supports multiple in future)
        self.robots: dict[int, RobotInstance] = {}
        self.next_robot_id = 0

        # Update tracking
        self.last_update = time.time()

    def init(self, debug_gamepad: bool = False):
        """Initialize the Ursina application."""
        self._debug_gamepad = debug_gamepad

        # Performance optimizations
        from panda3d.core import loadPrcFileData, ClockObject
        loadPrcFileData('', 'show-frame-rate-meter 0')
        loadPrcFileData('', 'texture-minfilter linear')
        loadPrcFileData('', 'texture-magfilter linear')
        loadPrcFileData('', 'gl-check-errors #f')  # Disable GL error checking
        loadPrcFileData('', 'notify-level-display error')  # Reduce logging

        self.app = Ursina(
            title='VEX IQ Simulator',
            borderless=False,
            fullscreen=False,
            size=(1280, 900),  # Taller to accommodate bottom panel
            development_mode=False,
            vsync=False
        )

        # Limit frame rate to 60 FPS to reduce CPU usage
        from panda3d.core import ClockObject
        globalClock = ClockObject.getGlobalClock()
        globalClock.setMode(ClockObject.MLimited)
        globalClock.setFrameRate(60)

        # Set dark background color for the window
        window.color = color.dark_gray

        # Set up 3D world
        self.world = VexWorld()
        self.world.setup()

        # Set up control panel (bottom 25% of screen)
        self.control_panel = ControlPanel()

        # Set up gamepad input
        self.gamepad = GamepadManager(debug=self._debug_gamepad)

        # Update gamepad connection status
        if self.gamepad.connected:
            joystick = self.gamepad.joystick
            name = joystick.get_name() if joystick else 'Unknown'
            self.control_panel.set_gamepad_connected(True, name)
        else:
            self.control_panel.set_gamepad_connected(False)

        # Register callbacks for vex_stub updates
        self.register_callbacks()

        # Set up keyboard shortcuts
        self.setup_input()

        # Adjust camera for bottom panel (3D view is in top 75%)
        self.adjust_camera_for_panel()

        print("Simulator initialized")

    def adjust_camera_for_panel(self):
        """Adjust camera to account for bottom panel taking 25% of screen."""
        # The bottom panel takes 25% of the screen
        # We need to shift the camera's render target up slightly
        # and adjust the field of view to fit the 3D view in top 75%

        # Shift camera view up to center the 3D view in the top portion
        # This is done by adjusting the camera's y position and look angle
        camera.position = (0, 9, -6)
        camera.rotation_x = 50
        camera.rotation_y = 0

        # Set a slightly higher FOV to show more of the field
        camera.fov = 60

    def register_callbacks(self):
        """Register callbacks to receive vex_stub state updates.

        Note: We no longer use callbacks for UI updates as the main loop
        handles all rendering. This avoids thread contention and duplicate
        updates (robot code thread was updating UI every 20ms, main loop
        also updates every frame).
        """
        # Callbacks removed - main loop handles all UI updates
        pass

    def sync_devices_to_panel(self):
        """Scan vex_stub for registered devices and sync to control panel."""
        # Register motors
        for port, motor in vex_stub.Motor.get_all_instances().items():
            self.control_panel.register_motor(port)

        # Register pneumatics
        for port, pneumatic in vex_stub.Pneumatic.get_all_instances().items():
            self.control_panel.register_pneumatic(port)

    def update_robot_movement(self):
        """Update robot movement based on motor states."""
        if len(self.robots) == 0:
            return

        # Get first robot (for now)
        robot = list(self.robots.values())[0]
        if not robot.entity:
            return

        # Try DriveTrain first
        drivetrain = vex_stub.DriveTrain.get_instance()
        if drivetrain:
            # Use wheel_velocity for logical wheel direction (ignores motor mounting)
            left_power = drivetrain.left_motor.wheel_velocity
            right_power = drivetrain.right_motor.wheel_velocity
            robot.entity.set_drive(left_power, right_power)
            return

        # Fallback: check for individual motors on ports 1 and 6
        # (common VEX IQ tank drive configuration)
        motors = vex_stub.Motor.get_all_instances()
        left_motor = motors.get(1)
        right_motor = motors.get(6)

        if left_motor and right_motor:
            # Use wheel_velocity for logical wheel direction
            left_power = left_motor.wheel_velocity
            right_power = right_motor.wheel_velocity
            robot.entity.set_drive(left_power, right_power)

    def setup_input(self):
        """Set up keyboard and mouse input handlers."""

        def input(key):
            if key == 'escape':
                self.app.quit()
            elif key == 'r':
                # Reset robot position
                for robot in self.robots.values():
                    if robot.entity:
                        robot.entity.position = robot.start_position
                        robot.entity.rotation_y = robot.start_rotation
            elif key == 'c':
                # Toggle camera view
                self.toggle_camera()

        # Make input function global for Ursina
        globals()['input'] = input

    def toggle_camera(self):
        """Toggle between different camera views."""
        # Simple toggle between overhead and angled
        if camera.rotation_x < 80:
            # Go to overhead
            camera.position = (0, 12, 0)
            camera.rotation_x = 90
            camera.fov = 50
        else:
            # Go to angled (default view)
            camera.position = (0, 9, -6)
            camera.rotation_x = 50
            camera.fov = 60

    def add_robot(self, name: str = None) -> RobotInstance:
        """Add a new robot to the simulation."""
        robot_id = self.next_robot_id
        self.next_robot_id += 1

        if name is None:
            name = f"Robot_{robot_id}"

        robot = RobotInstance(robot_id, name)
        robot.spawn()
        self.robots[robot_id] = robot

        print(f"Added robot: {name} (ID: {robot_id})")
        return robot

    def load_iqpython(self, filepath: str) -> bool:
        """Load an .iqpython file and execute it."""
        try:
            filepath = Path(filepath)
            if not filepath.exists():
                print(f"Error: File not found: {filepath}")
                return False

            # Reset vex_stub state
            vex_stub.reset_all()

            # Read and parse the file
            content = filepath.read_text()

            # Extract Python code (skip VEXcode IQ JSON header if present)
            python_code = self.extract_python_code(content)
            if not python_code:
                print("Error: No Python code found in file")
                return False

            # Create robot and load code
            robot = self.add_robot(filepath.stem)
            robot.load_code(python_code)

            self.control_panel.set_status(f"Running: {filepath.name}")
            return True

        except Exception as e:
            print(f"Error loading file: {e}")
            import traceback
            traceback.print_exc()
            return False

    def extract_python_code(self, content: str) -> str:
        """Extract Python code from .iqpython file content.

        .iqpython files are JSON with Python code in the 'textContent' field.
        Format: {"mode":"Text", "textContent":"...python code...", ...}
        """
        import json

        content = content.strip()

        # Check if it's JSON format (VEXcode IQ format)
        if content.startswith('{'):
            try:
                data = json.loads(content)
                if 'textContent' in data:
                    # The Python code is in textContent, with escaped newlines
                    python_code = data['textContent']
                    return python_code
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse JSON: {e}")
                # Fall through to legacy parsing

        # Legacy format: plain Python or with #region markers
        lines = content.split('\n')

        # Find the start of Python code
        code_start = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('#region') or line.strip().startswith('# region'):
                code_start = i
                break
            elif line.strip().startswith('import ') or line.strip().startswith('from '):
                code_start = i
                break

        return '\n'.join(lines[code_start:])

    def update(self):
        """Main update loop - called every frame by Ursina."""
        dt = time.time() - self.last_update
        self.last_update = time.time()

        # Update FPS display
        self.control_panel.update_fps(dt)

        # Sync devices to control panel periodically (not every frame)
        # Only check every 60 frames (~1 second) for new devices
        if not hasattr(self, '_sync_counter'):
            self._sync_counter = 0
            self._last_motor_count = 0
            self._last_pneumatic_count = 0

        self._sync_counter += 1
        if self._sync_counter >= 60:
            self._sync_counter = 0
            motor_count = len(vex_stub.Motor.get_all_instances())
            pneumatic_count = len(vex_stub.Pneumatic.get_all_instances())
            if motor_count != self._last_motor_count or pneumatic_count != self._last_pneumatic_count:
                self.sync_devices_to_panel()
                self._last_motor_count = motor_count
                self._last_pneumatic_count = pneumatic_count

        # Update gamepad
        self.gamepad.update()

        # Get controller and update its state from gamepad
        controller = vex_stub.Controller.get_instance()
        if controller and self.gamepad.connected:
            # Update axes
            axes = self.gamepad.get_axes()
            controller.axisA.set_position(axes.get('A', 0))
            controller.axisB.set_position(axes.get('B', 0))
            controller.axisC.set_position(axes.get('C', 0))
            controller.axisD.set_position(axes.get('D', 0))

            # Update joystick display (with change detection)
            if not hasattr(self, '_last_axes'):
                self._last_axes = {}
            left_axes = (axes.get('B', 0), axes.get('A', 0))
            right_axes = (axes.get('C', 0), axes.get('D', 0))
            if self._last_axes.get('left') != left_axes:
                self.control_panel.update_joystick('left', left_axes[0], left_axes[1])
                self._last_axes['left'] = left_axes
            if self._last_axes.get('right') != right_axes:
                self.control_panel.update_joystick('right', right_axes[0], right_axes[1])
                self._last_axes['right'] = right_axes

            # Update buttons (with change detection)
            if not hasattr(self, '_last_buttons'):
                self._last_buttons = {}
            buttons = self.gamepad.get_buttons()
            for btn_name, pressed in buttons.items():
                btn = getattr(controller, f'button{btn_name.replace("-", "")}', None)
                if btn:
                    btn.set_pressed(pressed)
                if self._last_buttons.get(btn_name) != pressed:
                    self.control_panel.update_button(btn_name, pressed)
                    self._last_buttons[btn_name] = pressed

        # Update motor displays (with change detection)
        if not hasattr(self, '_last_motor_states'):
            self._last_motor_states = {}
        for port, motor in vex_stub.Motor.get_all_instances().items():
            vel = motor.actual_velocity
            spinning = motor.is_spinning()
            state = (vel, spinning)
            if self._last_motor_states.get(port) != state:
                self.control_panel.update_motor(port, vel, spinning)
                self._last_motor_states[port] = state

        # Update pneumatic displays (with change detection)
        if not hasattr(self, '_last_pneumatic_states'):
            self._last_pneumatic_states = {}
        for port, pneumatic in vex_stub.Pneumatic.get_all_instances().items():
            extended = pneumatic.is_extended()
            if self._last_pneumatic_states.get(port) != extended:
                self.control_panel.update_pneumatic(port, extended)
                self._last_pneumatic_states[port] = extended

        # Update robot movement from motor states
        self.update_robot_movement()

        # Update robot physics
        for robot in self.robots.values():
            if robot.entity:
                robot.entity.move(dt)

    def run(self):
        """Start the simulator main loop."""

        # Create Ursina update function
        def update():
            self.update()

        # Make update global for Ursina
        globals()['update'] = update

        print("\nControls:")
        print("  ESC - Quit")
        print("  R   - Reset robot position")
        print("  C   - Toggle camera view")
        if self._debug_gamepad:
            print("\n[Debug mode: Raw gamepad values will print to console]")
        print("")

        self.app.run()


def main():
    """Main entry point."""
    # Parse command line args
    iqpython_file = None
    debug_gamepad = False

    for arg in sys.argv[1:]:
        if arg == '--debug-gamepad':
            debug_gamepad = True
        elif not arg.startswith('-'):
            iqpython_file = arg

    # Create and initialize simulator
    sim = VexSimulator()
    sim.init(debug_gamepad=debug_gamepad)

    # Load robot code if provided
    if iqpython_file:
        sim.load_iqpython(iqpython_file)
    else:
        # No file - just show empty world with placeholder robot
        sim.add_robot("TestBot")
        sim.control_panel.set_status("No .iqpython file loaded")
        print("\nUsage: python -m simulator.main [--debug-gamepad] <path_to_iqpython_file>")
        print("Running in demo mode with placeholder robot\n")

    # Run the simulator
    sim.run()


if __name__ == '__main__':
    main()
