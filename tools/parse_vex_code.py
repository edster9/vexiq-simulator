#!/usr/bin/env python3
"""
Parse VEXcode IQ Python files to extract device bindings.

Extracts Motor, Sensor, and other device declarations with their ports
and variable names for use in robotdef code_bindings section.

Usage:
    python tools/parse_vex_code.py code/myrobot.py
    python tools/parse_vex_code.py code/myrobot.py --update models/robots/MyRobot.robotdef
"""

import re
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class DeviceBinding:
    """Represents a device binding from VEX code."""
    variable_name: str
    device_type: str  # Motor, Inertial, ColorSensor, etc.
    port: Optional[int]  # 1-12 or None for Brain/Inertial
    direction: Optional[bool] = None  # For motors: False=forward, True=reverse
    gear_ratio: Optional[str] = None  # For motors: RATIO_18_1, RATIO_36_1, etc.
    extra_args: Optional[Dict] = None


# Device type mappings to robotdef categories
DEVICE_TYPE_MAP = {
    'Motor': 'motor',
    'MotorGroup': 'motor_group',
    'Inertial': 'sensor',
    'Gyro': 'sensor',
    'ColorSensor': 'sensor',
    'DistanceSensor': 'sensor',
    'BumperSwitch': 'sensor',
    'TouchLed': 'sensor',
    'Drivetrain': 'drivetrain',
    'SmartDrive': 'drivetrain',
    'Controller': 'controller',
    'Brain': 'brain',
}


def parse_port(port_str: str) -> Optional[int]:
    """Extract port number from various formats."""
    # Match: Ports.PORT1, PORT1, 1
    match = re.search(r'PORT(\d+)', port_str, re.IGNORECASE)
    if match:
        return int(match.group(1))

    # Direct number
    if port_str.isdigit():
        return int(port_str)

    return None


def parse_motor_declaration(line: str, var_name: str) -> Optional[DeviceBinding]:
    """Parse a Motor declaration line."""
    # Pattern: Motor(Ports.PORT1, GearSetting.RATIO_18_1, False)
    # Or: Motor(Ports.PORT1, True)  # reversed
    # Or: Motor(Ports.PORT1)

    match = re.search(r'Motor\s*\(\s*([^,\)]+)(?:\s*,\s*([^,\)]+))?(?:\s*,\s*([^,\)]+))?\s*\)', line)
    if not match:
        return None

    port_str = match.group(1).strip()
    arg2 = match.group(2).strip() if match.group(2) else None
    arg3 = match.group(3).strip() if match.group(3) else None

    port = parse_port(port_str)
    gear_ratio = None
    direction = None

    # Parse gear ratio and direction
    if arg2:
        if 'RATIO' in arg2.upper():
            gear_ratio = arg2.split('.')[-1] if '.' in arg2 else arg2
        elif arg2.lower() in ('true', 'false'):
            direction = arg2.lower() == 'true'

    if arg3:
        if arg3.lower() in ('true', 'false'):
            direction = arg3.lower() == 'true'

    return DeviceBinding(
        variable_name=var_name,
        device_type='Motor',
        port=port,
        direction=direction,
        gear_ratio=gear_ratio
    )


def parse_sensor_declaration(line: str, var_name: str, sensor_type: str) -> Optional[DeviceBinding]:
    """Parse a sensor declaration line."""
    # Pattern: ColorSensor(Ports.PORT1) or Inertial() or Gyro(Ports.PORT1)

    # Inertial doesn't require a port (uses built-in)
    if sensor_type == 'Inertial':
        return DeviceBinding(
            variable_name=var_name,
            device_type=sensor_type,
            port=None
        )

    # Other sensors require a port
    match = re.search(rf'{sensor_type}\s*\(\s*([^,\)]+)', line)
    if match:
        port = parse_port(match.group(1).strip())
        return DeviceBinding(
            variable_name=var_name,
            device_type=sensor_type,
            port=port
        )

    return None


def parse_motor_group_declaration(line: str, var_name: str) -> Optional[DeviceBinding]:
    """Parse a MotorGroup declaration line."""
    # Pattern: MotorGroup(motor1, motor2, ...)

    match = re.search(r'MotorGroup\s*\(\s*([^)]+)\s*\)', line)
    if match:
        motor_refs = [m.strip() for m in match.group(1).split(',')]
        return DeviceBinding(
            variable_name=var_name,
            device_type='MotorGroup',
            port=None,
            extra_args={'motors': motor_refs}
        )

    return None


def parse_drivetrain_declaration(line: str, var_name: str) -> Optional[DeviceBinding]:
    """Parse a Drivetrain or SmartDrive declaration."""
    # Drivetrain(left_motor, right_motor, wheel_travel, track_width, wheelbase, units, ratio)
    # SmartDrive(left_motor, right_motor, inertial, wheel_travel, track_width, wheelbase, units, ratio)

    for dt_type in ['SmartDrive', 'Drivetrain']:
        match = re.search(rf'{dt_type}\s*\(\s*([^)]+)\s*\)', line)
        if match:
            args = [a.strip() for a in match.group(1).split(',')]
            return DeviceBinding(
                variable_name=var_name,
                device_type=dt_type,
                port=None,
                extra_args={'args': args}
            )

    return None


def parse_vex_python(content: str) -> List[DeviceBinding]:
    """Parse VEXcode Python content and extract device bindings."""
    bindings = []

    # Device types to look for
    sensor_types = ['ColorSensor', 'DistanceSensor', 'BumperSwitch', 'TouchLed', 'Inertial', 'Gyro']

    for line in content.split('\n'):
        line = line.strip()

        # Skip comments and empty lines
        if not line or line.startswith('#'):
            continue

        # Look for assignment patterns: variable = DeviceType(...)
        assignment_match = re.match(r'(\w+)\s*=\s*(\w+)\s*\(', line)
        if not assignment_match:
            continue

        var_name = assignment_match.group(1)
        device_type = assignment_match.group(2)

        # Parse based on device type
        if device_type == 'Motor':
            binding = parse_motor_declaration(line, var_name)
            if binding:
                bindings.append(binding)

        elif device_type == 'MotorGroup':
            binding = parse_motor_group_declaration(line, var_name)
            if binding:
                bindings.append(binding)

        elif device_type in sensor_types:
            binding = parse_sensor_declaration(line, var_name, device_type)
            if binding:
                bindings.append(binding)

        elif device_type in ['Drivetrain', 'SmartDrive']:
            binding = parse_drivetrain_declaration(line, var_name)
            if binding:
                bindings.append(binding)

    return bindings


def generate_code_bindings_yaml(bindings: List[DeviceBinding]) -> str:
    """Generate YAML code_bindings section from device bindings."""
    lines = ["code_bindings:"]

    if not bindings:
        lines.append("  {}  # No device bindings found")
        return '\n'.join(lines)

    for binding in bindings:
        lines.append(f"  {binding.variable_name}:")
        lines.append(f"    type: {DEVICE_TYPE_MAP.get(binding.device_type, binding.device_type.lower())}")
        lines.append(f"    device: {binding.device_type}")

        if binding.port is not None:
            lines.append(f"    port: {binding.port}")

        if binding.direction is not None:
            direction_str = 'reverse' if binding.direction else 'forward'
            lines.append(f"    direction: {direction_str}")

        if binding.gear_ratio:
            lines.append(f"    gear_ratio: {binding.gear_ratio}")

        if binding.extra_args:
            if 'motors' in binding.extra_args:
                motors = ', '.join(binding.extra_args['motors'])
                lines.append(f"    motors: [{motors}]")
            elif 'args' in binding.extra_args:
                args = ', '.join(binding.extra_args['args'])
                lines.append(f"    args: [{args}]")

        # Placeholder for submodel mapping (user fills in)
        lines.append("    submodel: null  # Map to robotdef submodel")

    return '\n'.join(lines)


def parse_robotdef_devices(content: str) -> Dict[str, Dict]:
    """
    Parse robotdef content to extract motor/sensor port mappings.

    Returns dict mapping port numbers to submodel info.
    """
    devices = {}

    # Parse motors section - extract each motor block
    motors_match = re.search(r'^motors:\n((?:  - .+\n(?:    .+\n)*)*)', content, re.MULTILINE)
    if motors_match:
        motors_content = motors_match.group(1)
        # Split into individual motor entries
        motor_blocks = re.split(r'^  - ', motors_content, flags=re.MULTILINE)[1:]  # Skip first empty

        for block in motor_blocks:
            lines = block.strip().split('\n')
            submodel = None
            port = None

            for line in lines:
                line = line.strip()
                if line.startswith('submodel:'):
                    submodel = line.split(':', 1)[1].strip()
                elif line.startswith('port:'):
                    port_str = line.split(':', 1)[1].strip()
                    if port_str != 'null' and port_str.isdigit():
                        port = int(port_str)

            if submodel and port is not None:
                devices[('motor', port)] = {'submodel': submodel, 'type': 'motor'}

    # Parse sensors section
    sensors_match = re.search(r'^sensors:\n((?:  - .+\n(?:    .+\n)*)*)', content, re.MULTILINE)
    if sensors_match:
        sensors_content = sensors_match.group(1)
        # Split into individual sensor entries
        sensor_blocks = re.split(r'^  - ', sensors_content, flags=re.MULTILINE)[1:]

        for block in sensor_blocks:
            lines = block.strip().split('\n')
            sensor_type = None
            submodel = None
            port = None

            for line in lines:
                line = line.strip()
                if line.startswith('type:'):
                    sensor_type = line.split(':', 1)[1].strip()
                elif line.startswith('submodel:'):
                    submodel = line.split(':', 1)[1].strip()
                elif line.startswith('port:'):
                    port_str = line.split(':', 1)[1].strip().split()[0]  # Handle "port: 1  # comment"
                    if port_str != 'null' and port_str.isdigit():
                        port = int(port_str)

            if submodel and port is not None:
                devices[('sensor', port)] = {'submodel': submodel, 'type': sensor_type or 'sensor'}

    return devices


def auto_match_bindings(bindings: List[DeviceBinding], robotdef_content: str) -> Dict[str, str]:
    """
    Auto-match code bindings to robotdef submodels by port number.

    Returns dict mapping variable names to submodel names.
    """
    matches = {}
    devices = parse_robotdef_devices(robotdef_content)

    for binding in bindings:
        if binding.port is None:
            continue

        # Check for motor match
        if binding.device_type == 'Motor':
            key = ('motor', binding.port)
            if key in devices:
                matches[binding.variable_name] = devices[key]['submodel']

        # Check for sensor match
        elif binding.device_type in ('ColorSensor', 'DistanceSensor', 'BumperSwitch', 'TouchLed', 'Gyro'):
            key = ('sensor', binding.port)
            if key in devices:
                matches[binding.variable_name] = devices[key]['submodel']

    return matches


def generate_code_bindings_yaml(bindings: List[DeviceBinding], submodel_matches: Dict[str, str] = None) -> str:
    """Generate YAML code_bindings section from device bindings."""
    lines = ["code_bindings:"]
    submodel_matches = submodel_matches or {}

    if not bindings:
        lines.append("  {}  # No device bindings found")
        return '\n'.join(lines)

    for binding in bindings:
        lines.append(f"  {binding.variable_name}:")
        lines.append(f"    type: {DEVICE_TYPE_MAP.get(binding.device_type, binding.device_type.lower())}")
        lines.append(f"    device: {binding.device_type}")

        if binding.port is not None:
            lines.append(f"    port: {binding.port}")

        if binding.direction is not None:
            direction_str = 'reverse' if binding.direction else 'forward'
            lines.append(f"    direction: {direction_str}")

        if binding.gear_ratio:
            lines.append(f"    gear_ratio: {binding.gear_ratio}")

        if binding.extra_args:
            if 'motors' in binding.extra_args:
                motors = ', '.join(binding.extra_args['motors'])
                lines.append(f"    motors: [{motors}]")
            elif 'args' in binding.extra_args:
                args = ', '.join(binding.extra_args['args'])
                lines.append(f"    args: [{args}]")

        # Use matched submodel or placeholder
        if binding.variable_name in submodel_matches:
            lines.append(f"    submodel: {submodel_matches[binding.variable_name]}")
        else:
            lines.append("    submodel: null  # Map to robotdef submodel")

    return '\n'.join(lines)


def update_robotdef(robotdef_path: str, bindings: List[DeviceBinding]) -> bool:
    """Update a robotdef file with code bindings."""
    path = Path(robotdef_path)
    if not path.exists():
        print(f"Error: robotdef not found: {path}")
        return False

    content = path.read_text()

    # Try to auto-match bindings to submodels by port
    matches = auto_match_bindings(bindings, content)
    if matches:
        print(f"Auto-matched {len(matches)} bindings by port:")
        for var, submodel in matches.items():
            print(f"  {var} -> {submodel}")

    # Generate new code_bindings section with matches
    new_bindings = generate_code_bindings_yaml(bindings, matches)

    # Find and replace existing code_bindings section
    # Pattern matches from "code_bindings:" to end of section (next top-level key or EOF)
    pattern = r'(code_bindings:.*?)(?=\n[a-z_]+:|\Z)'

    if re.search(pattern, content, re.DOTALL):
        new_content = re.sub(pattern, new_bindings, content, flags=re.DOTALL)
    else:
        # Append if not found
        new_content = content.rstrip() + '\n\n' + new_bindings + '\n'

    path.write_text(new_content)
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Parse VEXcode IQ Python files to extract device bindings.'
    )
    parser.add_argument('code_file', help='Path to VEXcode Python file')
    parser.add_argument('--update', '-u', metavar='ROBOTDEF',
                       help='Update this robotdef file with extracted bindings')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Print verbose output')

    args = parser.parse_args()

    code_path = Path(args.code_file)
    if not code_path.exists():
        print(f"Error: File not found: {code_path}")
        sys.exit(1)

    print(f"Parsing: {code_path}")
    content = code_path.read_text()

    bindings = parse_vex_python(content)

    print(f"Found {len(bindings)} device bindings:")
    for binding in bindings:
        port_str = f"PORT{binding.port}" if binding.port else "N/A"
        print(f"  {binding.variable_name}: {binding.device_type} ({port_str})")
        if args.verbose:
            if binding.direction is not None:
                print(f"    direction: {'reverse' if binding.direction else 'forward'}")
            if binding.gear_ratio:
                print(f"    gear_ratio: {binding.gear_ratio}")
            if binding.extra_args:
                print(f"    extra: {binding.extra_args}")

    if args.update:
        print(f"\nUpdating: {args.update}")
        if update_robotdef(args.update, bindings):
            print("Done!")
        else:
            sys.exit(1)
    else:
        print("\n" + generate_code_bindings_yaml(bindings))


if __name__ == '__main__':
    main()
