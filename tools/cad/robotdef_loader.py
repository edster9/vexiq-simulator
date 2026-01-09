#!/usr/bin/env python3
"""
Robot Definition File Loader
=============================

Parses .robotdef YAML files and provides access to robot configuration data
for the simulator including drivetrain, kinematics, and code bindings.

Usage:
    from robotdef_loader import load_robotdef, RobotDef

    robotdef = load_robotdef('models/ClawbotIQ.robotdef')
    print(robotdef.drivetrain.rotation_center)
"""

import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any


@dataclass
class DrivetrainConfig:
    """Drivetrain configuration from .robotdef file."""
    type: str = 'unknown'  # tank, mecanum, omni, ackermann
    left_drive: Optional[str] = None
    right_drive: Optional[str] = None
    rotation_center: Tuple[float, float, float] = (0, 0, 0)  # LDU coordinates
    track_width: float = 0  # LDU
    wheel_diameter: float = 44  # mm


@dataclass
class KinematicsConfig:
    """Kinematics configuration for an articulated submodel."""
    rotation_axis: Tuple[float, float, float] = (1, 0, 0)
    rotation_origin: Tuple[float, float, float] = (0, 0, 0)
    rotation_limits: Tuple[float, float] = (-180, 180)  # degrees


@dataclass
class SubmodelConfig:
    """Configuration for a submodel."""
    name: str
    position: Tuple[float, float, float] = (0, 0, 0)
    parent: Optional[str] = None
    children: List[str] = field(default_factory=list)
    kinematics: Optional[KinematicsConfig] = None
    special_parts: List[Dict] = field(default_factory=list)


@dataclass
class CodeBinding:
    """Binding between code variable and robot submodel."""
    name: str  # Variable name from code (e.g., 'Arm_180')
    type: str  # motor, motor_group, pneumatic
    ports: List[int] = field(default_factory=list)
    submodel: Optional[str] = None
    children: List[str] = field(default_factory=list)
    role: Optional[str] = None  # left_drive, right_drive, arm, etc.
    action: Optional[str] = None  # For pneumatics: open_close, extend_retract


@dataclass
class RobotDef:
    """Complete robot definition loaded from .robotdef file."""
    source_file: str = ''
    main_model: str = ''

    # Drivetrain
    drivetrain: DrivetrainConfig = field(default_factory=DrivetrainConfig)

    # Submodel configurations (keyed by submodel name)
    submodels: Dict[str, SubmodelConfig] = field(default_factory=dict)

    # Code bindings (keyed by variable name)
    code_bindings: Dict[str, CodeBinding] = field(default_factory=dict)

    # Summary stats
    total_wheels: int = 0
    total_motors: int = 0
    total_sensors: int = 0
    has_brain: bool = False

    def get_wheel_part_numbers(self) -> set:
        """
        Get all wheel/tire part numbers from the robot definition.

        Scans special_parts in all submodels for parts with type starting with 'wheel:'.

        Returns:
            Set of part numbers (e.g., {'228-2500-208', '228-2500-209'})
        """
        wheel_parts = set()
        for submodel in self.submodels.values():
            for part in submodel.special_parts:
                part_type = part.get('type', '')
                if part_type.startswith('wheel:'):
                    part_num = part.get('part', '')
                    if part_num:
                        wheel_parts.add(part_num)
        return wheel_parts

    def get_wheel_part_numbers_for_submodel(self, submodel_name: str) -> set:
        """
        Get wheel/tire part numbers for a specific submodel.

        Args:
            submodel_name: Name of the submodel (e.g., 'LeftSideDrive.ldr')

        Returns:
            Set of part numbers for wheels in that submodel
        """
        wheel_parts = set()
        submodel = self.submodels.get(submodel_name)
        if submodel:
            for part in submodel.special_parts:
                part_type = part.get('type', '')
                if part_type.startswith('wheel:'):
                    part_num = part.get('part', '')
                    if part_num:
                        wheel_parts.add(part_num)
        return wheel_parts


def _parse_list_as_tuple(data: Any, default: tuple = (0, 0, 0)) -> tuple:
    """Convert a list from YAML to a tuple."""
    if data is None:
        return default
    if isinstance(data, (list, tuple)):
        return tuple(data)
    return default


def load_robotdef(path: str) -> RobotDef:
    """
    Load a .robotdef YAML file and return a RobotDef object.

    Args:
        path: Path to .robotdef file

    Returns:
        RobotDef object with parsed configuration
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Robot definition file not found: {path}")

    with open(path, 'r') as f:
        data = yaml.safe_load(f)

    if data is None:
        raise ValueError(f"Empty or invalid YAML in: {path}")

    robotdef = RobotDef()

    # Basic info
    robotdef.source_file = data.get('source_file', '')
    robotdef.main_model = data.get('main_model', '')

    # Summary
    summary = data.get('summary', {})
    robotdef.total_wheels = summary.get('total_wheels', 0)
    robotdef.total_motors = summary.get('total_motors', 0)
    robotdef.total_sensors = summary.get('total_sensors', 0)
    robotdef.has_brain = summary.get('has_brain', False)

    # Drivetrain
    dt_data = data.get('drivetrain', {})
    robotdef.drivetrain = DrivetrainConfig(
        type=dt_data.get('type', 'unknown'),
        left_drive=dt_data.get('left_drive'),
        right_drive=dt_data.get('right_drive'),
        rotation_center=_parse_list_as_tuple(dt_data.get('rotation_center'), (0, 0, 0)),
        track_width=dt_data.get('track_width', 0),
        wheel_diameter=dt_data.get('wheel_diameter', 44),
    )

    # Submodels
    submodels_data = data.get('submodels', {})
    for name, sm_data in submodels_data.items():
        if sm_data is None:
            sm_data = {}

        # Parse kinematics if present
        kinematics = None
        kin_data = sm_data.get('kinematics')
        if kin_data and isinstance(kin_data, dict):
            kinematics = KinematicsConfig(
                rotation_axis=_parse_list_as_tuple(kin_data.get('rotation_axis'), (1, 0, 0)),
                rotation_origin=_parse_list_as_tuple(kin_data.get('rotation_origin'), (0, 0, 0)),
                rotation_limits=_parse_list_as_tuple(kin_data.get('rotation_limits'), (-180, 180)),
            )

        robotdef.submodels[name] = SubmodelConfig(
            name=name,
            position=_parse_list_as_tuple(sm_data.get('position'), (0, 0, 0)),
            parent=sm_data.get('parent'),
            children=sm_data.get('children', []),
            kinematics=kinematics,
            special_parts=sm_data.get('special_parts', []),
        )

    # Code bindings
    bindings_data = data.get('code_bindings', {})
    if bindings_data:
        for name, bind_data in bindings_data.items():
            if bind_data is None or not isinstance(bind_data, dict):
                continue

            ports = bind_data.get('ports', [])
            if bind_data.get('port'):
                ports = [bind_data['port']]

            robotdef.code_bindings[name] = CodeBinding(
                name=name,
                type=bind_data.get('type', 'motor'),
                ports=ports if isinstance(ports, list) else [ports],
                submodel=bind_data.get('submodel'),
                children=bind_data.get('children', []),
                role=bind_data.get('role'),
                action=bind_data.get('action'),
            )

    return robotdef


def find_robotdef_for_model(model_path: str) -> Optional[str]:
    """
    Find the .robotdef file for a given model file.

    Looks for a file with the same name but .robotdef extension.

    Args:
        model_path: Path to .mpd or .ldr file

    Returns:
        Path to .robotdef file if found, None otherwise
    """
    model_path = Path(model_path)
    robotdef_path = model_path.with_suffix('.robotdef')

    if robotdef_path.exists():
        return str(robotdef_path)

    return None


# Convenience function for getting rotation center in Ursina coordinates
POSITION_SCALE = 0.02  # From ldraw_renderer.py

def get_rotation_center_ursina(robotdef: RobotDef) -> Tuple[float, float, float]:
    """
    Get the drivetrain rotation center in Ursina coordinates.

    Converts from LDU (LDraw Units) to Ursina world units,
    applying the coordinate transform (Y is negated).

    Args:
        robotdef: Loaded RobotDef object

    Returns:
        (x, y, z) tuple in Ursina coordinates
    """
    ldu = robotdef.drivetrain.rotation_center
    return (
        ldu[0] * POSITION_SCALE,
        -ldu[1] * POSITION_SCALE,  # Y is negated for LDraw -> Ursina
        ldu[2] * POSITION_SCALE
    )


if __name__ == '__main__':
    # Test loading
    import sys

    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = 'models/ClawbotIQ.robotdef'

    try:
        robotdef = load_robotdef(path)
        print(f"Loaded: {robotdef.source_file}")
        print(f"Main model: {robotdef.main_model}")
        print(f"Drivetrain type: {robotdef.drivetrain.type}")
        print(f"Rotation center (LDU): {robotdef.drivetrain.rotation_center}")
        print(f"Rotation center (Ursina): {get_rotation_center_ursina(robotdef)}")
        print(f"Track width: {robotdef.drivetrain.track_width} LDU")
        print(f"Submodels: {len(robotdef.submodels)}")
        print(f"Code bindings: {len(robotdef.code_bindings)}")
    except Exception as e:
        print(f"Error: {e}")
