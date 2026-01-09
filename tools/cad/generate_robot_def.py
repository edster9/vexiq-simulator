#!/usr/bin/env python3
"""
Generate Robot Definition File from LDraw MPD/LDR
=================================================

Analyzes an LDraw model file and generates a companion .robotdef YAML file
that describes the robot's structure, hierarchy, and special components.

This definition file can then be extended with:
- Rotation axis points for articulated parts
- Movement limits (min/max angles)
- Wheel/drivetrain configuration
- Sensor mappings

Usage:
    python tools/cad/generate_robot_def.py models/ClawbotIQ.mpd
    python tools/cad/generate_robot_def.py models/ClawbotIQ.mpd -o custom_output.robotdef
"""

import sys
import os
import re
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict

# Add parent for imports
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from ldraw_parser import parse_mpd, LDrawDocument

# =============================================================================
# Known VEX IQ Part Classifications
# =============================================================================

# Part numbers that are wheels/hubs
WHEEL_PARTS = {
    '228-2500-208': 'wheel_hub_44mm',
    '228-2500-209': 'tire_44mm',
    '228-2500-210': 'wheel_hub_60mm',
    '228-2500-211': 'tire_60mm',
    '228-2500-212': 'wheel_hub_200mm',
    '228-2500-231': 'tread_link',  # Tank tread
}

# Part numbers that are motors
MOTOR_PARTS = {
    '228-2560': 'smart_motor',
}

# Part numbers that are the brain
BRAIN_PARTS = {
    '228-2540': 'robot_brain',
    '228-2540c02': 'robot_brain_with_battery',
}

# Part numbers that are sensors
SENSOR_PARTS = {
    '228-3010': 'touch_led',
    '228-3011': 'bumper_switch',
    '228-3012': 'color_sensor',
    '228-3014': 'gyro_sensor',
    '228-3015': 'distance_sensor',
    '228-3388-901': 'optical_sensor',
    '228-3388-912': 'optical_shaft_encoder',
}

# Part numbers that are pneumatics
PNEUMATIC_PARTS = {
    '228-6300': 'pneumatic_cylinder',
}


@dataclass
class PartInfo:
    """Information about a single part reference."""
    part_number: str
    color: int
    position: Tuple[float, float, float]
    rotation_matrix: Tuple[float, ...]
    classification: Optional[str] = None  # wheel, motor, brain, sensor, etc.


@dataclass
class SubmodelInfo:
    """Information about a submodel in the hierarchy."""
    name: str
    parent: Optional[str] = None
    children: List[str] = field(default_factory=list)
    parts: List[PartInfo] = field(default_factory=list)
    position: Tuple[float, float, float] = (0, 0, 0)
    rotation_matrix: Tuple[float, ...] = (1, 0, 0, 0, 1, 0, 0, 0, 1)

    # Counts of special parts
    wheel_count: int = 0
    motor_count: int = 0
    sensor_count: int = 0
    has_brain: bool = False


def classify_part(part_number: str) -> Optional[str]:
    """Classify a part number into a category."""
    # Normalize: remove .dat extension, handle -v2 variants
    base = part_number.replace('.dat', '').replace('.DAT', '')
    base = re.sub(r'-v\d+$', '', base)  # Remove version suffix

    if base in WHEEL_PARTS:
        return f"wheel:{WHEEL_PARTS[base]}"
    if base in MOTOR_PARTS:
        return f"motor:{MOTOR_PARTS[base]}"
    if base in BRAIN_PARTS:
        return f"brain:{BRAIN_PARTS[base]}"
    if base in SENSOR_PARTS:
        return f"sensor:{SENSOR_PARTS[base]}"
    if base in PNEUMATIC_PARTS:
        return f"pneumatic:{PNEUMATIC_PARTS[base]}"

    return None


def analyze_model(doc: LDrawDocument) -> Dict[str, SubmodelInfo]:
    """Analyze the LDraw document and extract hierarchy information."""
    submodels: Dict[str, SubmodelInfo] = {}

    # First pass: create SubmodelInfo for each model
    for name, model in doc.models.items():
        submodels[name] = SubmodelInfo(name=name)

    # Second pass: analyze parts and build hierarchy
    for name, model in doc.models.items():
        info = submodels[name]

        # Process direct parts
        for part in model.parts:
            classification = classify_part(part.part_name)
            part_info = PartInfo(
                part_number=part.part_name.replace('.dat', '').replace('.DAT', ''),
                color=part.color,
                position=(part.x, part.y, part.z),
                rotation_matrix=part.rotation_matrix,
                classification=classification
            )
            info.parts.append(part_info)

            # Count special parts
            if classification:
                if classification.startswith('wheel:'):
                    info.wheel_count += 1
                elif classification.startswith('motor:'):
                    info.motor_count += 1
                elif classification.startswith('sensor:'):
                    info.sensor_count += 1
                elif classification.startswith('brain:'):
                    info.has_brain = True

        # Process submodel references
        for submodel_name, placement in model.submodel_refs:
            if submodel_name in submodels:
                child_info = submodels[submodel_name]
                child_info.parent = name
                child_info.position = (placement.x, placement.y, placement.z)
                child_info.rotation_matrix = placement.rotation_matrix
                info.children.append(submodel_name)

    return submodels


def generate_yaml(doc: LDrawDocument, submodels: Dict[str, SubmodelInfo]) -> str:
    """Generate YAML definition file content."""
    lines = []

    # Header
    lines.append("# Robot Definition File")
    lines.append("# Generated from: " + (doc.filename or "unknown"))
    lines.append("# ")
    lines.append("# This file describes the robot's structure and can be extended with:")
    lines.append("#   - rotation_axis: Define pivot points for articulated parts")
    lines.append("#   - rotation_limits: min/max angles for joints")
    lines.append("#   - wheel_config: drivetrain setup (left/right, diameter, etc.)")
    lines.append("#   - sensor_ports: Map sensors to VEX IQ ports")
    lines.append("")
    lines.append("version: 1")
    lines.append(f"source_file: {doc.filename or 'unknown'}")
    lines.append(f"main_model: {doc.main_model}")
    lines.append("")

    # Summary
    total_wheels = sum(s.wheel_count for s in submodels.values())
    total_motors = sum(s.motor_count for s in submodels.values())
    total_sensors = sum(s.sensor_count for s in submodels.values())
    has_brain = any(s.has_brain for s in submodels.values())

    lines.append("# Summary")
    lines.append("summary:")
    lines.append(f"  total_submodels: {len(submodels)}")
    lines.append(f"  total_wheels: {total_wheels}")
    lines.append(f"  total_motors: {total_motors}")
    lines.append(f"  total_sensors: {total_sensors}")
    lines.append(f"  has_brain: {str(has_brain).lower()}")
    lines.append("")

    # Hierarchy section
    lines.append("# Submodel Hierarchy")
    lines.append("hierarchy:")

    # Find root models (no parent)
    roots = [name for name, info in submodels.items() if info.parent is None]

    def write_hierarchy(name: str, indent: int = 2):
        info = submodels[name]
        prefix = " " * indent
        lines.append(f"{prefix}{name}:")
        if info.children:
            lines.append(f"{prefix}  children:")
            for child in info.children:
                lines.append(f"{prefix}    - {child}")
                # Recursively add children's children as nested comments

        # Add summary of special parts in this submodel
        specials = []
        if info.wheel_count > 0:
            specials.append(f"{info.wheel_count} wheels")
        if info.motor_count > 0:
            specials.append(f"{info.motor_count} motors")
        if info.sensor_count > 0:
            specials.append(f"{info.sensor_count} sensors")
        if info.has_brain:
            specials.append("brain")
        if specials:
            lines.append(f"{prefix}  contains: [{', '.join(specials)}]")

    for root in roots:
        write_hierarchy(root)

    lines.append("")

    # Detailed submodels section
    lines.append("# Detailed Submodel Definitions")
    lines.append("# Add rotation_axis, rotation_limits, etc. to articulated parts")
    lines.append("submodels:")

    for name, info in submodels.items():
        lines.append(f"  {name}:")
        lines.append(f"    position: [{info.position[0]}, {info.position[1]}, {info.position[2]}]")

        if info.parent:
            lines.append(f"    parent: {info.parent}")

        # Placeholder for kinematics (to be filled in manually)
        lines.append("    # Kinematics (fill in for articulated parts):")
        lines.append("    # rotation_axis: [x, y, z]  # Local axis of rotation")
        lines.append("    # rotation_origin: [x, y, z]  # Pivot point in local coords")
        lines.append("    # rotation_limits: [min_deg, max_deg]")
        lines.append("    kinematics: null")

        # List special parts
        special_parts = [p for p in info.parts if p.classification]
        if special_parts:
            lines.append("    special_parts:")
            for part in special_parts:
                lines.append(f"      - part: {part.part_number}")
                lines.append(f"        type: {part.classification}")
                lines.append(f"        position: [{part.position[0]}, {part.position[1]}, {part.position[2]}]")

        lines.append("")

    # Drivetrain section - calculate rotation center from wheel positions
    lines.append("# Drivetrain Configuration")
    lines.append("# Defines the robot's rotation center and drive geometry")
    lines.append("drivetrain:")

    wheel_submodels = [(name, info) for name, info in submodels.items() if info.wheel_count > 0]

    if len(wheel_submodels) >= 2:
        # Try to identify left/right by name or X position
        left_drive = None
        right_drive = None

        for name, info in wheel_submodels:
            name_lower = name.lower()
            if 'left' in name_lower:
                left_drive = (name, info)
            elif 'right' in name_lower:
                right_drive = (name, info)

        # Fallback: use X position to determine left/right
        if not left_drive or not right_drive:
            sorted_by_x = sorted(wheel_submodels, key=lambda x: x[1].position[0])
            if len(sorted_by_x) >= 2:
                left_drive = sorted_by_x[0]  # Smaller X = left
                right_drive = sorted_by_x[-1]  # Larger X = right

        if left_drive and right_drive:
            left_pos = left_drive[1].position
            right_pos = right_drive[1].position

            # Calculate center point (rotation axis)
            center_x = (left_pos[0] + right_pos[0]) / 2
            center_y = (left_pos[1] + right_pos[1]) / 2
            center_z = (left_pos[2] + right_pos[2]) / 2

            # Track width = distance between left and right wheels (X axis)
            track_width = abs(right_pos[0] - left_pos[0])

            lines.append(f"  type: tank  # tank (skid-steer) | mecanum | omni | ackermann")
            lines.append(f"  left_drive: {left_drive[0]}")
            lines.append(f"  right_drive: {right_drive[0]}")
            lines.append(f"  # Rotation center (midpoint between drive assemblies)")
            lines.append(f"  rotation_center: [{center_x}, {center_y}, {center_z}]")
            lines.append(f"  track_width: {track_width}  # Distance between left and right wheels (LDU)")
            lines.append(f"  # wheel_diameter: 44  # mm - set based on wheel type used")
        else:
            lines.append("  type: unknown")
            lines.append("  # Could not auto-detect left/right drives")
            lines.append("  rotation_center: [0, 0, 0]  # Fill in manually")
    else:
        lines.append("  type: unknown")
        lines.append("  # Less than 2 wheel submodels detected")
        lines.append("  rotation_center: [0, 0, 0]  # Fill in manually")

    lines.append("")

    # Wheels section - specific identification for drivetrain
    lines.append("# Wheel Configuration")
    lines.append("# Identify which submodels contain drive wheels")
    lines.append("wheels:")

    wheel_submodels = [(name, info) for name, info in submodels.items() if info.wheel_count > 0]
    if wheel_submodels:
        for name, info in wheel_submodels:
            lines.append(f"  - submodel: {name}")
            lines.append(f"    count: {info.wheel_count}")
            lines.append("    # Configure drivetrain role:")
            lines.append("    # role: left_drive | right_drive | caster | manipulator")
            lines.append("    # diameter_mm: 44  # or 60, 200")
            lines.append("    role: null")
    else:
        lines.append("  # No wheel parts detected")

    lines.append("")

    # Motors section
    lines.append("# Motor Configuration")
    lines.append("motors:")

    motor_submodels = [(name, info) for name, info in submodels.items() if info.motor_count > 0]
    if motor_submodels:
        for name, info in motor_submodels:
            lines.append(f"  - submodel: {name}")
            lines.append(f"    count: {info.motor_count}")
            lines.append("    # port: 1-12  # VEX IQ port number")
            lines.append("    # purpose: drive | arm | intake | etc")
            lines.append("    port: null")
    else:
        lines.append("  # No motor parts detected")

    lines.append("")

    # Sensors section
    lines.append("# Sensor Configuration")
    lines.append("sensors:")

    for name, info in submodels.items():
        sensor_parts = [p for p in info.parts if p.classification and p.classification.startswith('sensor:')]
        for part in sensor_parts:
            sensor_type = part.classification.split(':')[1]
            lines.append(f"  - type: {sensor_type}")
            lines.append(f"    submodel: {name}")
            lines.append(f"    part: {part.part_number}")
            lines.append("    # port: 1-12  # VEX IQ port number")
            lines.append("    port: null")

    if not any(info.sensor_count > 0 for info in submodels.values()):
        lines.append("  # No sensor parts detected")

    lines.append("")

    # Code bindings section - maps code labels to physical parts
    lines.append("# Code Bindings")
    lines.append("# Maps variable names from VEX Python code to robot submodels")
    lines.append("# This enables the simulator to animate the correct parts when code runs")
    lines.append("code_bindings:")
    lines.append("  # Example bindings (fill in based on your robot code):")
    lines.append("  # ")
    lines.append("  # Arm_180:                    # Variable name from code")
    lines.append("  #   type: motor_group         # motor | motor_group | pneumatic")
    lines.append("  #   ports: [2, 5]             # VEX IQ port numbers")
    lines.append("  #   submodel: Arm.ldr         # Which submodel to animate")
    lines.append("  #   children: [FingerA.ldr, FingerB.ldr]  # Child parts that move with it")
    lines.append("  # ")
    lines.append("  # A180_Claws:")
    lines.append("  #   type: pneumatic")
    lines.append("  #   port: 9")
    lines.append("  #   submodels: [FingerA.ldr, FingerB.ldr]  # Parts actuated by pneumatic")
    lines.append("  #   action: open_close        # open_close | extend_retract")
    lines.append("  # ")
    lines.append("  # left_drive_smart:")
    lines.append("  #   type: motor")
    lines.append("  #   port: 1")
    lines.append("  #   submodel: LeftSideDrive.ldr")
    lines.append("  #   role: left_drive")

    # Generate placeholder bindings for detected motor submodels
    arm_submodels = [name for name, info in submodels.items()
                    if info.motor_count > 0 and 'arm' in name.lower()]
    drive_submodels = [name for name, info in submodels.items()
                      if info.motor_count > 0 and 'drive' in name.lower()]

    if arm_submodels or drive_submodels:
        lines.append("  ")
        lines.append("  # Auto-detected candidates (uncomment and configure):")

    for name in arm_submodels:
        var_name = name.replace('.ldr', '').replace('.', '_')
        lines.append(f"  # {var_name}:")
        lines.append(f"  #   type: motor_group")
        lines.append(f"  #   ports: []  # Fill in port numbers")
        lines.append(f"  #   submodel: {name}")

    for name in drive_submodels:
        var_name = name.replace('.ldr', '').replace('.', '_')
        role = 'left_drive' if 'left' in name.lower() else 'right_drive' if 'right' in name.lower() else 'drive'
        lines.append(f"  # {var_name}:")
        lines.append(f"  #   type: motor")
        lines.append(f"  #   port: null  # Fill in port number")
        lines.append(f"  #   submodel: {name}")
        lines.append(f"  #   role: {role}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Generate robot definition file from LDraw MPD/LDR model.'
    )
    parser.add_argument('model', help='Path to LDraw model file (.mpd or .ldr)')
    parser.add_argument('-o', '--output', help='Output file path (default: same name with .robotdef)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Print verbose output')

    args = parser.parse_args()

    model_path = Path(args.model)
    if not model_path.exists():
        print(f"Error: File not found: {model_path}")
        sys.exit(1)

    # Parse the LDraw file
    print(f"Parsing: {model_path}")
    doc = parse_mpd(str(model_path))
    doc.filename = model_path.name

    if not doc.main_model:
        print("Error: No main model found in document")
        sys.exit(1)

    print(f"Main model: {doc.main_model}")
    print(f"Submodels found: {len(doc.models)}")

    # Analyze the model
    submodels = analyze_model(doc)

    if args.verbose:
        print("\nHierarchy:")
        for name, info in submodels.items():
            parent = info.parent or "(root)"
            print(f"  {name} <- {parent}")
            if info.wheel_count or info.motor_count or info.sensor_count or info.has_brain:
                parts = []
                if info.wheel_count:
                    parts.append(f"{info.wheel_count} wheels")
                if info.motor_count:
                    parts.append(f"{info.motor_count} motors")
                if info.sensor_count:
                    parts.append(f"{info.sensor_count} sensors")
                if info.has_brain:
                    parts.append("brain")
                print(f"    Contains: {', '.join(parts)}")

    # Generate YAML
    yaml_content = generate_yaml(doc, submodels)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = model_path.with_suffix('.robotdef')

    # Write output
    output_path.write_text(yaml_content)
    print(f"\nGenerated: {output_path}")

    # Summary
    total_wheels = sum(s.wheel_count for s in submodels.values())
    total_motors = sum(s.motor_count for s in submodels.values())
    total_sensors = sum(s.sensor_count for s in submodels.values())

    print(f"\nSummary:")
    print(f"  Submodels: {len(submodels)}")
    print(f"  Wheels: {total_wheels}")
    print(f"  Motors: {total_motors}")
    print(f"  Sensors: {total_sensors}")


if __name__ == '__main__':
    main()
