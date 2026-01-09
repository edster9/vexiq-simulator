#!/usr/bin/env python3
"""
IPC Bridge for VEX IQ Simulator
================================
Bridges C++ rendering client with Python robot harness via JSON over stdin/stdout.

Protocol:
---------
C++ → Python (stdin):
    {"type":"gamepad","axes":{"A":0,"B":0,"C":0,"D":0},"buttons":{...}}
    {"type":"tick","dt":0.016}
    {"type":"shutdown"}

Python → C++ (stdout):
    {"type":"motors","data":{1:{"speed":100,"spinning":true},...}}
    {"type":"pneumatics","data":{9:{"extended":true,"pump":false},...}}
    {"type":"ready"}
    {"type":"status","message":"Robot running"}

Usage:
    python ipc_bridge.py <file.iqpython>
"""

import sys
import os
import json
import threading
import time
import select
from pathlib import Path

# Add simulator directory to path
sys.path.insert(0, str(Path(__file__).parent))

from iqpython_parser import parse_iqpython, describe_robot, RobotConfig
import vex_stub


class IPCBridge:
    """Bridge between C++ client and Python robot harness."""

    def __init__(self, iqpython_path: str):
        self.iqpython_path = Path(iqpython_path)
        self.config: RobotConfig = None
        self._running = False
        self._robot_thread = None
        self._controller: vex_stub.Controller = None

    def send_message(self, msg: dict):
        """Send a JSON message to C++ via stdout."""
        try:
            json_str = json.dumps(msg, separators=(',', ':'))
            print(json_str, flush=True)
        except Exception as e:
            self.log_error(f"Failed to send message: {e}")

    def log_error(self, msg: str):
        """Log error to stderr (not stdout which is for IPC)."""
        print(f"[IPC ERROR] {msg}", file=sys.stderr, flush=True)

    def log_info(self, msg: str):
        """Log info to stderr."""
        print(f"[IPC] {msg}", file=sys.stderr, flush=True)

    def load(self):
        """Load and parse the .iqpython file."""
        self.log_info(f"Loading: {self.iqpython_path}")

        self.config = parse_iqpython(self.iqpython_path)
        self.log_info(f"Project: {self.config.project_name}")

        # Send ready signal with robot config
        self.send_message({
            "type": "ready",
            "project": self.config.project_name,
            "motors": [{"port": m.port, "name": m.name} for m in self.config.motors],
            "motor_groups": [{"name": mg.name, "ports": mg.ports} for mg in self.config.motor_groups],
            "pneumatics": [{"port": p.port, "name": p.name} for p in self.config.pneumatics],
        })

    def handle_gamepad(self, data: dict):
        """Handle gamepad input from C++."""
        if not self._controller:
            return

        # Update controller axes (A, B, C, D)
        axes = data.get("axes", {})
        self._controller._axis_a = int(axes.get("A", 0))
        self._controller._axis_b = int(axes.get("B", 0))
        self._controller._axis_c = int(axes.get("C", 0))
        self._controller._axis_d = int(axes.get("D", 0))

        # Update controller buttons
        buttons = data.get("buttons", {})
        self._controller._button_l_up = buttons.get("LUp", False)
        self._controller._button_l_down = buttons.get("LDown", False)
        self._controller._button_r_up = buttons.get("RUp", False)
        self._controller._button_r_down = buttons.get("RDown", False)
        self._controller._button_e_up = buttons.get("EUp", False)
        self._controller._button_e_down = buttons.get("EDown", False)
        self._controller._button_f_up = buttons.get("FUp", False)
        self._controller._button_f_down = buttons.get("FDown", False)

    def handle_tick(self, data: dict):
        """Handle tick - send motor/pneumatic state back to C++."""
        # Collect motor states
        motors = {}
        for port, motor in vex_stub.Motor.get_all_instances().items():
            motors[port] = {
                "speed": motor.actual_velocity,
                "spinning": motor._spinning,
                "position": motor._position,
            }

        # Collect pneumatic states
        pneumatics = {}
        for port, pneu in vex_stub.Pneumatic.get_all_instances().items():
            pneumatics[port] = {
                "extended": pneu._extended,
                "pump": pneu._pump_on,
            }

        # Send state update
        self.send_message({
            "type": "state",
            "motors": motors,
            "pneumatics": pneumatics,
        })

    def process_message(self, line: str):
        """Process a JSON message from C++."""
        try:
            msg = json.loads(line)
            msg_type = msg.get("type", "")

            if msg_type == "gamepad":
                self.handle_gamepad(msg)
            elif msg_type == "tick":
                self.handle_tick(msg)
            elif msg_type == "shutdown":
                self._running = False
            else:
                self.log_error(f"Unknown message type: {msg_type}")

        except json.JSONDecodeError as e:
            self.log_error(f"Invalid JSON: {e}")
        except Exception as e:
            self.log_error(f"Error processing message: {e}")

    def execute_robot_code(self):
        """Execute the robot code from the .iqpython file."""
        # Reset all stub state
        vex_stub.reset_all()

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
            # Pre-create the controller
            self._controller = vex_stub.Controller()
            self.send_message({"type": "status", "message": "Robot code starting"})
            self.log_info("Robot code started")

            # Execute the robot code (may block forever with while True loop)
            exec(self.config.python_code, robot_globals)

        except Exception as e:
            self.log_error(f"Robot code error: {e}")
            self.send_message({"type": "error", "message": str(e)})
            import traceback
            traceback.print_exc(file=sys.stderr)

    def run(self):
        """Main run loop."""
        self.load()

        # Start robot code in a separate thread
        self._running = True
        self._robot_thread = threading.Thread(target=self.execute_robot_code, daemon=True)
        self._robot_thread.start()

        # Give robot code a moment to initialize
        time.sleep(0.2)

        # Main loop - read stdin for messages
        while self._running:
            try:
                # Non-blocking read with timeout
                if sys.platform == 'win32':
                    # Windows: use a simple blocking read with timeout via thread
                    line = sys.stdin.readline()
                    if not line:
                        break
                    self.process_message(line.strip())
                else:
                    # Unix: use select for non-blocking
                    ready, _, _ = select.select([sys.stdin], [], [], 0.01)
                    if ready:
                        line = sys.stdin.readline()
                        if not line:
                            break
                        self.process_message(line.strip())

            except KeyboardInterrupt:
                break
            except Exception as e:
                self.log_error(f"Main loop error: {e}")
                break

        self._running = False
        self.send_message({"type": "shutdown"})
        self.log_info("Bridge shutdown")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        # Try to find an .iqpython file
        search_paths = [
            Path(__file__).parent.parent,
            Path.cwd(),
        ]

        iqpython_file = None
        for search_path in search_paths:
            if search_path.exists():
                files = list(search_path.glob("*.iqpython"))
                if files:
                    iqpython_file = files[0]
                    break

        if not iqpython_file:
            print("Usage: python ipc_bridge.py <file.iqpython>", file=sys.stderr)
            sys.exit(1)
    else:
        iqpython_file = Path(sys.argv[1])

    if not iqpython_file.exists():
        print(f"Error: File not found: {iqpython_file}", file=sys.stderr)
        sys.exit(1)

    bridge = IPCBridge(str(iqpython_file))
    bridge.run()


if __name__ == "__main__":
    main()
