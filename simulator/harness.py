"""
VEX IQ Simulator Harness
========================
Main entry point that loads robot code and runs it with the virtual controller.
"""

import sys
import os
import threading
import time
from pathlib import Path

# Add simulator directory to path
sys.path.insert(0, str(Path(__file__).parent))

from iqpython_parser import parse_iqpython, describe_robot, RobotConfig
from virtual_controller import VirtualControllerGUI
import vex_stub


class SimulatorHarness:
    """Main harness that runs robot code with virtual controller."""

    def __init__(self, iqpython_path: str):
        self.iqpython_path = Path(iqpython_path)
        self.config: RobotConfig = None
        self.gui: VirtualControllerGUI = None
        self._running = False
        self._robot_thread = None

    def load(self):
        """Load and parse the .iqpython file."""
        print(f"Loading: {self.iqpython_path}")

        self.config = parse_iqpython(self.iqpython_path)
        print("\n" + describe_robot(self.config))
        print("-" * 50)

    def setup_gui(self):
        """Initialize the GUI with motor indicators based on config."""
        self.gui = VirtualControllerGUI(
            title=f"VEX IQ Simulator - {self.config.project_name}"
        )

        # Add motor indicators based on drivetrain config
        if self.config.drivetrain:
            dt = self.config.drivetrain
            for i, port in enumerate(dt.left_ports):
                self.gui.add_motor_indicator(port, f"Left {i+1}")
            for i, port in enumerate(dt.right_ports):
                self.gui.add_motor_indicator(port, f"Right {i+1}")

        # Add any standalone motors
        for motor in self.config.motors:
            self.gui.add_motor_indicator(motor.port, motor.name)

        # Add motors from motor groups
        for mg in self.config.motor_groups:
            for i, port in enumerate(mg.ports):
                suffix = chr(ord('A') + i)  # A, B, C, etc.
                self.gui.add_motor_indicator(port, f"{mg.name} {suffix}")

        # Add pneumatic indicators
        for pneu in self.config.pneumatics:
            self.gui.add_pneumatic_indicator(pneu.port, pneu.name)

    def _motor_update_callback(self, motor: vex_stub.Motor):
        """Callback when a motor's state changes."""
        # Just update the motor - GUI will read it on next frame
        pass

    def _update_motors_from_stubs(self):
        """Update GUI motor indicators from stub motor states."""
        for port, motor in vex_stub.Motor.get_all_instances().items():
            self.gui.update_motor(port, motor.actual_velocity, motor._spinning)

    def _update_pneumatics_from_stubs(self):
        """Update GUI pneumatic indicators from stub pneumatic states."""
        for port, pneu in vex_stub.Pneumatic.get_all_instances().items():
            self.gui.update_pneumatic(port, pneu._extended, pneu._pump_on)

    def execute_robot_code(self):
        """Execute the robot code from the .iqpython file."""
        # Reset all stub state
        vex_stub.reset_all()

        # Register motor callback
        vex_stub.CallbackRegistry.register_motor_callback(self._motor_update_callback)

        # Create a namespace for the robot code
        robot_globals = {
            '__name__': '__main__',
            '__file__': str(self.iqpython_path),
        }

        # Inject vex stub module as 'vex'
        sys.modules['vex'] = vex_stub

        # Inject urandom as a module (MicroPython compatibility)
        sys.modules['urandom'] = vex_stub.urandom

        try:
            # Pre-create the controller so we can connect it to GUI before exec
            # (exec may block forever if robot code has a while True loop)
            controller = vex_stub.Controller()
            if self.gui:
                self.gui.set_controller(controller)
                self.gui.set_status("Robot code running")

            print("\nRobot code started successfully!")
            print("Use mouse to drag joysticks, or connect a USB gamepad.")
            print("Close window to exit.\n")

            # Execute the robot code (may block forever with while True loop)
            exec(self.config.python_code, robot_globals)

        except Exception as e:
            print(f"\nError executing robot code: {e}")
            import traceback
            traceback.print_exc()
            if self.gui:
                self.gui.set_status(f"Error: {e}")

    def run(self):
        """Main run loop."""
        self.load()
        self.setup_gui()

        # Start robot code in a separate thread
        self._running = True
        self._robot_thread = threading.Thread(target=self.execute_robot_code, daemon=True)
        self._robot_thread.start()

        # Give robot code a moment to initialize
        time.sleep(0.5)

        # Main loop - GUI and motor/pneumatic updates
        while self.gui.running:
            self.gui.update()
            self._update_motors_from_stubs()
            self._update_pneumatics_from_stubs()

        # Cleanup
        self._running = False
        print("\nSimulator closed.")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        # Try to find an .iqpython file in common locations
        search_paths = [
            Path(__file__).parent.parent,  # vexiq folder
            Path(__file__).parent.parent / "robot",
            Path.cwd(),
        ]

        iqpython_file = None
        for search_path in search_paths:
            if search_path.exists():
                files = list(search_path.glob("*.iqpython"))
                if files:
                    iqpython_file = files[0]
                    break

        if iqpython_file:
            print(f"Auto-detected: {iqpython_file}")
        else:
            print("Usage: python harness.py <file.iqpython>")
            print("\nNo .iqpython file specified or found.")
            sys.exit(1)
    else:
        iqpython_file = Path(sys.argv[1])

    if not iqpython_file.exists():
        print(f"Error: File not found: {iqpython_file}")
        sys.exit(1)

    harness = SimulatorHarness(str(iqpython_file))
    harness.run()


if __name__ == "__main__":
    main()
