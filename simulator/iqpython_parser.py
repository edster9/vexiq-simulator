"""
IQPython Parser
===============
Parses .iqpython files to extract robot configuration and code.
"""

import json
from dataclasses import dataclass
from typing import Optional
from pathlib import Path


@dataclass
class MotorConfig:
    """Configuration for a motor."""
    port: int
    name: str
    reversed: bool = False
    gear_ratio: float = 1.0


@dataclass
class DrivetrainConfig:
    """Configuration for a drivetrain."""
    left_ports: list[int]
    right_ports: list[int]
    name: str
    wheel_size: float = 200  # mm
    track_width: float = 173  # mm
    wheelbase: float = 76  # mm
    gear_ratio: float = 1.0
    drive_type: str = "2-motor"  # "2-motor" or "4-motor"


@dataclass
class ControllerConfig:
    """Configuration for a controller."""
    name: str
    drive_mode: str = "split"  # "split", "left", "right", "tank"


@dataclass
class MotorGroupConfig:
    """Configuration for a motor group."""
    ports: list[int]
    name: str
    motor_b_reversed: bool = False


@dataclass
class PneumaticConfig:
    """Configuration for a pneumatic cylinder."""
    port: int
    name: str


@dataclass
class RobotConfig:
    """Complete robot configuration."""
    motors: list[MotorConfig]
    drivetrain: Optional[DrivetrainConfig]
    controller: Optional[ControllerConfig]
    motor_groups: list[MotorGroupConfig] = None
    pneumatics: list[PneumaticConfig] = None
    brain_gen: str = "Second"
    python_code: str = ""
    project_name: str = "VEXcode Project"

    def __post_init__(self):
        if self.motor_groups is None:
            self.motor_groups = []
        if self.pneumatics is None:
            self.pneumatics = []


def parse_iqpython(file_path: str | Path) -> RobotConfig:
    """
    Parse an .iqpython file and extract robot configuration.

    Args:
        file_path: Path to the .iqpython file

    Returns:
        RobotConfig with all extracted configuration
    """
    file_path = Path(file_path)

    with open(file_path, 'r') as f:
        data = json.load(f)

    # Extract basic info
    python_code = data.get("textContent", "")
    brain_gen = data.get("targetBrainGen", "Second")
    robot_config = data.get("robotConfig", [])

    # Parse devices
    motors: list[MotorConfig] = []
    drivetrain: Optional[DrivetrainConfig] = None
    controller: Optional[ControllerConfig] = None
    motor_groups: list[MotorGroupConfig] = []
    pneumatics: list[PneumaticConfig] = []

    for device in robot_config:
        device_type = device.get("deviceType", "")
        device_name = device.get("name", "unknown")
        ports = device.get("port", [])
        settings = device.get("setting", {})

        if device_type == "Motor":
            # Individual motor
            if ports:
                motors.append(MotorConfig(
                    port=ports[0],
                    name=device_name,
                    reversed=settings.get("reversed", "false") == "true"
                ))

        elif device_type == "Drivetrain":
            # Drivetrain (includes motors)
            # Ports format: [left_port, right_port, gyro_port] for 2-motor
            # or [left1, left2, right1, right2, gyro_port] for 4-motor
            drive_type = settings.get("type", "2-motor")

            if drive_type == "2-motor" and len(ports) >= 2:
                left_ports = [ports[0]]
                right_ports = [ports[1]]
            elif drive_type == "4-motor" and len(ports) >= 4:
                left_ports = [ports[0], ports[1]]
                right_ports = [ports[2], ports[3]]
            else:
                left_ports = [ports[0]] if ports else [1]
                right_ports = [ports[1]] if len(ports) > 1 else [2]

            # Parse wheel size (e.g., "200mm" -> 200)
            wheel_size_str = settings.get("wheelSize", "200mm")
            wheel_size = float(''.join(c for c in wheel_size_str if c.isdigit() or c == '.') or "200")

            # Parse gear ratio (e.g., "1:1" -> 1.0, "2:1" -> 2.0)
            gear_ratio_str = settings.get("gearRatio", "1:1")
            if ":" in gear_ratio_str:
                parts = gear_ratio_str.split(":")
                try:
                    gear_ratio = float(parts[0]) / float(parts[1])
                except:
                    gear_ratio = 1.0
            else:
                gear_ratio = 1.0

            drivetrain = DrivetrainConfig(
                left_ports=left_ports,
                right_ports=right_ports,
                name=device_name,
                wheel_size=wheel_size,
                track_width=float(settings.get("width", 173)),
                wheelbase=float(settings.get("wheelbase", 76)),
                gear_ratio=gear_ratio,
                drive_type=drive_type
            )

        elif device_type == "Controller":
            controller = ControllerConfig(
                name=device_name,
                drive_mode=settings.get("drive", "split")
            )

        elif device_type == "MotorGroup":
            # Motor group - multiple motors working together
            motor_groups.append(MotorGroupConfig(
                ports=ports,
                name=device_name,
                motor_b_reversed=settings.get("motor_b_reversed", "false") == "true"
            ))

        elif device_type == "Pneumatic":
            # Pneumatic cylinder
            if ports:
                pneumatics.append(PneumaticConfig(
                    port=ports[0],
                    name=device_name
                ))

    # Extract project name from code comments if present
    project_name = "VEXcode Project"
    for line in python_code.split("\n"):
        if "Project:" in line:
            project_name = line.split("Project:")[-1].strip()
            break

    return RobotConfig(
        motors=motors,
        drivetrain=drivetrain,
        controller=controller,
        motor_groups=motor_groups,
        pneumatics=pneumatics,
        brain_gen=brain_gen,
        python_code=python_code,
        project_name=project_name
    )


def describe_robot(config: RobotConfig) -> str:
    """
    Generate a human-readable description of the robot configuration.

    Args:
        config: Parsed robot configuration

    Returns:
        Multi-line string describing the robot
    """
    lines = [
        f"Robot: {config.project_name}",
        f"Brain Generation: {config.brain_gen}",
        ""
    ]

    if config.drivetrain:
        dt = config.drivetrain
        lines.append("Drivetrain:")
        lines.append(f"  Type: {dt.drive_type}")
        lines.append(f"  Left motor(s): Port {', '.join(map(str, dt.left_ports))}")
        lines.append(f"  Right motor(s): Port {', '.join(map(str, dt.right_ports))}")
        lines.append(f"  Wheel size: {dt.wheel_size}mm")
        lines.append(f"  Track width: {dt.track_width}mm")
        lines.append(f"  Gear ratio: {dt.gear_ratio}:1")
        lines.append("")

    if config.controller:
        ctrl = config.controller
        lines.append("Controller:")
        lines.append(f"  Drive mode: {ctrl.drive_mode}")

        if ctrl.drive_mode == "split":
            lines.append("  Left stick (A): Forward/Back")
            lines.append("  Right stick (C): Turn Left/Right")
        elif ctrl.drive_mode == "left":
            lines.append("  Left stick: Arcade (A=turn, B=drive)")
        elif ctrl.drive_mode == "right":
            lines.append("  Right stick: Arcade (C=turn, D=drive)")
        elif ctrl.drive_mode == "tank":
            lines.append("  Left stick (B): Left motors")
            lines.append("  Right stick (D): Right motors")
        lines.append("")

    if config.motors:
        lines.append("Additional Motors:")
        for motor in config.motors:
            rev = " (reversed)" if motor.reversed else ""
            lines.append(f"  {motor.name}: Port {motor.port}{rev}")
        lines.append("")

    if config.motor_groups:
        lines.append("Motor Groups:")
        for mg in config.motor_groups:
            ports_str = ", ".join(f"P{p}" for p in mg.ports)
            rev = " (B reversed)" if mg.motor_b_reversed else ""
            lines.append(f"  {mg.name}: {ports_str}{rev}")
        lines.append("")

    if config.pneumatics:
        lines.append("Pneumatics:")
        for pn in config.pneumatics:
            lines.append(f"  {pn.name}: Port {pn.port}")

    return "\n".join(lines)


# Test if run directly
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        config = parse_iqpython(sys.argv[1])
        print(describe_robot(config))
    else:
        print("Usage: python iqpython_parser.py <file.iqpython>")
