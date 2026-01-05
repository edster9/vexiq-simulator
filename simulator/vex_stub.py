"""
VEX IQ Stub Library
===================
Mock implementation of the VEX library for local testing.
This allows robot code to run unchanged outside of VEXcode IQ.
"""

import threading
import time
from typing import Callable, Optional
from dataclasses import dataclass, field
from enum import Enum, auto

# ============================================================
# CONSTANTS - Match VEX library constants
# ============================================================

# Directions
FORWARD = "forward"
REVERSE = "reverse"
LEFT = "left"
RIGHT = "right"

# Units
PERCENT = "percent"
MM = "mm"
INCHES = "inches"
DEGREES = "degrees"
TURNS = "turns"
SECONDS = "seconds"
MSEC = "msec"

# Axes
XAXIS = "xaxis"
YAXIS = "yaxis"
ZAXIS = "zaxis"

# Brake modes
COAST = "coast"
BRAKE = "brake"
HOLD = "hold"


# ============================================================
# PORTS - Enum for port numbers
# ============================================================

class Ports:
    PORT1 = 1
    PORT2 = 2
    PORT3 = 3
    PORT4 = 4
    PORT5 = 5
    PORT6 = 6
    PORT7 = 7
    PORT8 = 8
    PORT9 = 9
    PORT10 = 10
    PORT11 = 11
    PORT12 = 12


# ============================================================
# CALLBACK REGISTRY - For GUI updates
# ============================================================

class CallbackRegistry:
    """Central registry for callbacks that notify the GUI of state changes."""
    _motor_callbacks: list[Callable] = []
    _brain_callbacks: list[Callable] = []

    @classmethod
    def register_motor_callback(cls, callback: Callable):
        cls._motor_callbacks.append(callback)

    @classmethod
    def register_brain_callback(cls, callback: Callable):
        cls._brain_callbacks.append(callback)

    @classmethod
    def notify_motor_update(cls, motor: 'Motor'):
        for cb in cls._motor_callbacks:
            cb(motor)

    @classmethod
    def notify_brain_update(cls, brain: 'Brain', message: str):
        for cb in cls._brain_callbacks:
            cb(brain, message)


# ============================================================
# MOTOR CLASS
# ============================================================

class Motor:
    """Mock Motor class that tracks state."""

    _instances: dict[int, 'Motor'] = {}

    def __init__(self, port: int, gear_ratio: float = 1.0, reversed: bool = False):
        self.port = port
        self.gear_ratio = gear_ratio
        self.reversed = reversed
        self._velocity = 0
        self._target_velocity = 0
        self._spinning = False
        self._direction = FORWARD
        self._position = 0.0  # degrees
        self._brake_mode = COAST

        # Register this motor instance
        Motor._instances[port] = self

    @classmethod
    def get_instance(cls, port: int) -> Optional['Motor']:
        return cls._instances.get(port)

    @classmethod
    def get_all_instances(cls) -> dict[int, 'Motor']:
        return cls._instances.copy()

    def set_velocity(self, velocity: float, unit=PERCENT):
        """Set the motor velocity."""
        self._target_velocity = velocity
        if self._spinning:
            self._velocity = velocity
            CallbackRegistry.notify_motor_update(self)

    def spin(self, direction=FORWARD):
        """Start spinning the motor."""
        self._direction = direction
        self._spinning = True
        self._velocity = self._target_velocity

        # Apply reversal
        actual_velocity = self._velocity
        if self.reversed:
            actual_velocity = -actual_velocity
        if direction == REVERSE:
            actual_velocity = -actual_velocity

        CallbackRegistry.notify_motor_update(self)

    def spin_for(self, direction, amount: float, unit=DEGREES, wait_for: bool = True):
        """Spin for a specific amount."""
        self._direction = direction
        self._spinning = True
        self._velocity = self._target_velocity
        CallbackRegistry.notify_motor_update(self)

        # Calculate duration based on unit
        if unit == SECONDS:
            duration = amount
        elif unit == MSEC:
            duration = amount / 1000
        elif unit == DEGREES:
            # Approximate: assume 100% velocity = 200 deg/sec
            speed = abs(self._velocity) if self._velocity != 0 else 50
            duration = amount / (speed * 2)
        elif unit == TURNS:
            speed = abs(self._velocity) if self._velocity != 0 else 50
            duration = (amount * 360) / (speed * 2)
        else:
            duration = 1

        if wait_for:
            time.sleep(duration)
            self.stop()

    def stop(self, brake_mode=None):
        """Stop the motor."""
        self._spinning = False
        self._velocity = 0
        if brake_mode:
            self._brake_mode = brake_mode
        CallbackRegistry.notify_motor_update(self)

    def set_stopping(self, mode):
        """Set the brake mode."""
        self._brake_mode = mode

    def velocity(self, unit=PERCENT) -> float:
        """Get current velocity."""
        return self._velocity

    def position(self, unit=DEGREES) -> float:
        """Get current position."""
        return self._position

    def is_spinning(self) -> bool:
        """Check if motor is spinning."""
        return self._spinning

    @property
    def actual_velocity(self) -> float:
        """Get velocity accounting for direction and reversal."""
        vel = self._velocity
        if self.reversed:
            vel = -vel
        if self._direction == REVERSE:
            vel = -vel
        return vel

    @property
    def wheel_velocity(self) -> float:
        """Get logical wheel velocity for 3D simulation.

        This returns what the wheel is doing from the robot's perspective,
        not the physical motor shaft direction. The 'reversed' flag only
        compensates for motor mounting and shouldn't affect the wheel direction.
        """
        vel = self._velocity
        if self._direction == REVERSE:
            vel = -vel
        return vel


# ============================================================
# CONTROLLER CLASS
# ============================================================

class ControllerAxis:
    """Represents a controller joystick axis."""

    def __init__(self, name: str):
        self.name = name
        self._position = 0

    def position(self) -> int:
        """Get axis position (-100 to 100)."""
        return self._position

    def set_position(self, value: int):
        """Set axis position (called by GUI)."""
        self._position = max(-100, min(100, value))


class ControllerButton:
    """Represents a controller button."""

    def __init__(self, name: str):
        self.name = name
        self._pressed = False
        self._just_pressed = False
        self._just_released = False
        self._press_callbacks: list[Callable] = []
        self._release_callbacks: list[Callable] = []

    def pressing(self) -> bool:
        """Check if button is currently pressed."""
        return self._pressed

    def pressed(self, callback: Callable):
        """Register callback for button press."""
        self._press_callbacks.append(callback)

    def released(self, callback: Callable):
        """Register callback for button release."""
        self._release_callbacks.append(callback)

    def set_pressed(self, value: bool):
        """Set button state (called by GUI)."""
        was_pressed = self._pressed
        self._pressed = value

        if value and not was_pressed:
            # Just pressed
            for cb in self._press_callbacks:
                cb()
        elif not value and was_pressed:
            # Just released
            for cb in self._release_callbacks:
                cb()


class Controller:
    """Mock Controller class - singleton pattern."""

    _instance: Optional['Controller'] = None

    def __new__(cls):
        """Return existing instance if one exists (singleton)."""
        if cls._instance is not None:
            return cls._instance
        return super().__new__(cls)

    def __init__(self):
        # Skip re-initialization if already set up
        if Controller._instance is not None:
            return

        # Axes
        self.axisA = ControllerAxis("A")  # Left stick Y
        self.axisB = ControllerAxis("B")  # Left stick X
        self.axisC = ControllerAxis("C")  # Right stick X
        self.axisD = ControllerAxis("D")  # Right stick Y

        # Buttons
        self.buttonLUp = ControllerButton("L-Up")
        self.buttonLDown = ControllerButton("L-Down")
        self.buttonRUp = ControllerButton("R-Up")
        self.buttonRDown = ControllerButton("R-Down")
        self.buttonEUp = ControllerButton("E-Up")
        self.buttonEDown = ControllerButton("E-Down")
        self.buttonFUp = ControllerButton("F-Up")
        self.buttonFDown = ControllerButton("F-Down")

        Controller._instance = self

    @classmethod
    def get_instance(cls) -> Optional['Controller']:
        return cls._instance


# ============================================================
# DRIVETRAIN CLASS
# ============================================================

class DriveTrain:
    """Mock DriveTrain class."""

    _instance: Optional['DriveTrain'] = None

    def __init__(self, left_motor: Motor, right_motor: Motor,
                 wheel_size: float = 200, track_width: float = 173,
                 wheelbase: float = 76, unit=MM, gear_ratio: float = 1.0):
        self.left_motor = left_motor
        self.right_motor = right_motor
        self.wheel_size = wheel_size
        self.track_width = track_width
        self.wheelbase = wheelbase
        self.unit = unit
        self.gear_ratio = gear_ratio
        self._velocity = 50
        self._turn_velocity = 50

        DriveTrain._instance = self

    @classmethod
    def get_instance(cls) -> Optional['DriveTrain']:
        return cls._instance

    def set_drive_velocity(self, velocity: float, unit=PERCENT):
        self._velocity = velocity

    def set_turn_velocity(self, velocity: float, unit=PERCENT):
        self._turn_velocity = velocity

    def drive(self, direction=FORWARD):
        """Start driving."""
        vel = self._velocity if direction == FORWARD else -self._velocity
        self.left_motor.set_velocity(vel, PERCENT)
        self.right_motor.set_velocity(vel, PERCENT)
        self.left_motor.spin(FORWARD)
        self.right_motor.spin(FORWARD)

    def drive_for(self, direction, distance: float, unit=MM, wait_for: bool = True):
        """Drive for a specific distance."""
        self.drive(direction)

        # Calculate duration based on distance (approximate)
        if unit == MM:
            duration = distance / 200  # ~200mm/sec at 50% speed
        elif unit == INCHES:
            duration = (distance * 25.4) / 200
        elif unit == SECONDS:
            duration = distance
        else:
            duration = 1

        if wait_for:
            time.sleep(duration)
            self.stop()

    def turn(self, direction=RIGHT):
        """Start turning."""
        vel = self._turn_velocity
        if direction == RIGHT:
            self.left_motor.set_velocity(vel, PERCENT)
            self.right_motor.set_velocity(-vel, PERCENT)
        else:
            self.left_motor.set_velocity(-vel, PERCENT)
            self.right_motor.set_velocity(vel, PERCENT)
        self.left_motor.spin(FORWARD)
        self.right_motor.spin(FORWARD)

    def turn_for(self, direction, angle: float, unit=DEGREES, wait_for: bool = True):
        """Turn for a specific angle."""
        self.turn(direction)

        # Calculate duration (approximate)
        duration = angle / 90  # ~90 deg/sec at 50% speed

        if wait_for:
            time.sleep(duration)
            self.stop()

    def stop(self, brake_mode=None):
        """Stop the drivetrain."""
        self.left_motor.stop(brake_mode)
        self.right_motor.stop(brake_mode)


# ============================================================
# BRAIN CLASS
# ============================================================

class BrainScreen:
    """Mock Brain screen."""

    def __init__(self):
        self._cursor_row = 1
        self._cursor_col = 1
        self._lines: list[str] = [""] * 10

    def print(self, *args):
        """Print to screen."""
        text = " ".join(str(a) for a in args)
        if self._cursor_row <= len(self._lines):
            self._lines[self._cursor_row - 1] = text
        print(f"[BRAIN SCREEN] {text}")

    def clear_screen(self):
        """Clear the screen."""
        self._lines = [""] * 10
        self._cursor_row = 1
        self._cursor_col = 1

    def set_cursor(self, row: int, col: int):
        """Set cursor position."""
        self._cursor_row = row
        self._cursor_col = col

    def next_row(self):
        """Move to next row."""
        self._cursor_row += 1


class BrainTimer:
    """Mock Brain timer."""

    def __init__(self):
        self._start_time = time.time()

    def system(self) -> float:
        """Get system time in ms."""
        return (time.time() - self._start_time) * 1000

    def clear(self):
        """Reset timer."""
        self._start_time = time.time()


class Brain:
    """Mock Brain class."""

    _instance: Optional['Brain'] = None

    def __init__(self):
        self.screen = BrainScreen()
        self.timer = BrainTimer()
        Brain._instance = self

    @classmethod
    def get_instance(cls) -> Optional['Brain']:
        return cls._instance


# ============================================================
# INERTIAL SENSOR CLASS
# ============================================================

class Inertial:
    """Mock Inertial sensor."""

    def __init__(self, port: int = 0):
        self.port = port
        self._heading = 0.0
        self._rotation = 0.0
        self._calibrating = False

    def calibrate(self):
        """Calibrate the sensor."""
        self._calibrating = True
        # Simulate brief calibration
        time.sleep(0.1)
        self._calibrating = False

    def is_calibrating(self) -> bool:
        """Check if sensor is currently calibrating."""
        return self._calibrating

    def heading(self) -> float:
        """Get heading (0-360)."""
        return self._heading

    def rotation(self) -> float:
        """Get rotation (continuous)."""
        return self._rotation

    def acceleration(self, axis) -> float:
        """Get acceleration on axis."""
        # Return small random-ish values for seed generation
        import random
        return random.uniform(-1, 1)


# ============================================================
# SMARTDRIVE CLASS (Drivetrain with inertial)
# ============================================================

class SmartDrive(DriveTrain):
    """Mock SmartDrive class - DriveTrain with integrated inertial sensor."""

    def __init__(self, left_motor: Motor, right_motor: Motor,
                 inertial: Inertial, wheel_size: float = 200,
                 track_width: float = 173, wheelbase: float = 76,
                 unit=MM, gear_ratio: float = 1.0):
        super().__init__(left_motor, right_motor, wheel_size, track_width,
                        wheelbase, unit, gear_ratio)
        self.inertial = inertial

    def turn_to_heading(self, heading: float, unit=DEGREES, wait_for: bool = True):
        """Turn to a specific heading using inertial sensor."""
        current = self.inertial.heading()
        diff = heading - current
        if diff > 180:
            diff -= 360
        elif diff < -180:
            diff += 360

        direction = RIGHT if diff > 0 else LEFT
        self.turn_for(direction, abs(diff), unit, wait_for)


# ============================================================
# MOTORGROUP CLASS
# ============================================================

class MotorGroup:
    """Mock MotorGroup class - multiple motors working as one."""

    _instances: list['MotorGroup'] = []

    def __init__(self, *motors: Motor):
        self.motors = list(motors)
        self._velocity = 50
        self._direction = FORWARD
        self._spinning = False
        MotorGroup._instances.append(self)

    def set_velocity(self, velocity: float, unit=PERCENT):
        """Set velocity for all motors in group."""
        self._velocity = velocity
        for motor in self.motors:
            motor.set_velocity(velocity, unit)

    def spin(self, direction=FORWARD):
        """Spin all motors in group."""
        self._direction = direction
        self._spinning = True
        for motor in self.motors:
            motor.spin(direction)

    def spin_for(self, direction, amount: float, unit=DEGREES, wait_for: bool = True):
        """Spin all motors for a specific amount."""
        self._direction = direction
        self._spinning = True
        # Only wait on the last motor
        for i, motor in enumerate(self.motors):
            wait = wait_for and (i == len(self.motors) - 1)
            motor.spin_for(direction, amount, unit, wait)
        if wait_for:
            self._spinning = False

    def stop(self, brake_mode=None):
        """Stop all motors in group."""
        self._spinning = False
        for motor in self.motors:
            motor.stop(brake_mode)

    def set_stopping(self, mode):
        """Set brake mode for all motors."""
        for motor in self.motors:
            motor.set_stopping(mode)


# ============================================================
# PNEUMATIC CLASS
# ============================================================

class Pneumatic:
    """Mock Pneumatic class for pneumatic cylinders."""

    _instances: dict[int, 'Pneumatic'] = {}

    def __init__(self, port: int):
        self.port = port
        self._extended = False
        self._pump_on = True
        Pneumatic._instances[port] = self

    def extend(self, cylinder: str = "cylinder1"):
        """Extend the pneumatic cylinder."""
        self._extended = True
        print(f"[PNEUMATIC P{self.port}] Extended")

    def retract(self, cylinder: str = "cylinder1"):
        """Retract the pneumatic cylinder."""
        self._extended = False
        print(f"[PNEUMATIC P{self.port}] Retracted")

    def pump_on(self):
        """Turn on the pneumatic pump."""
        self._pump_on = True
        print(f"[PNEUMATIC P{self.port}] Pump ON")

    def pump_off(self):
        """Turn off the pneumatic pump."""
        self._pump_on = False
        print(f"[PNEUMATIC P{self.port}] Pump OFF")

    def is_extended(self) -> bool:
        """Check if cylinder is extended."""
        return self._extended

    @classmethod
    def get_all_instances(cls) -> dict[int, 'Pneumatic']:
        return cls._instances.copy()


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def wait(duration: float, unit=MSEC):
    """Wait for specified duration."""
    if unit == MSEC:
        time.sleep(duration / 1000)
    elif unit == SECONDS:
        time.sleep(duration)


def sleep(duration: float, unit=MSEC):
    """Alias for wait() - MicroPython compatibility."""
    wait(duration, unit)


class Thread:
    """Mock Thread class matching VEX API."""

    def __init__(self, callback: Callable):
        self._callback = callback
        self._thread = threading.Thread(target=callback, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the thread (not directly supported, thread must check a flag)."""
        pass


# ============================================================
# URANDOM MOCK (MicroPython compatibility)
# ============================================================

import random as _random

class urandom:
    """Mock urandom module (MicroPython compatibility)."""

    _seed = 0

    @classmethod
    def seed(cls, value: int):
        cls._seed = value
        _random.seed(value)

    @classmethod
    def random(cls) -> float:
        return _random.random()

    @classmethod
    def randint(cls, a: int, b: int) -> int:
        return _random.randint(a, b)

    @classmethod
    def choice(cls, seq):
        return _random.choice(seq)


# ============================================================
# RESET FUNCTION - Clear all state
# ============================================================

def reset_all():
    """Reset all mock state. Call before loading new robot code."""
    Motor._instances.clear()
    Controller._instance = None
    DriveTrain._instance = None
    Brain._instance = None
    MotorGroup._instances.clear()
    Pneumatic._instances.clear()
    CallbackRegistry._motor_callbacks.clear()
    CallbackRegistry._brain_callbacks.clear()
