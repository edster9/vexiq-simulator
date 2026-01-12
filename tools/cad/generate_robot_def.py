#!/usr/bin/env python3
"""
Generate Robot Definition File from LDraw MPD/LDR
=================================================

Analyzes an LDraw model file and generates a companion .robotdef YAML file
that describes the robot's structure, hierarchy, and special components.

Uses parts_catalog.yaml for part classification (motors, sensors, wheels, etc.)

Usage:
    python tools/cad/generate_robot_def.py models/ClawbotIQ.mpd
    python tools/cad/generate_robot_def.py models/ClawbotIQ.mpd -o custom_output.robotdef
"""

import sys
import os
import re
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict

# Add parent for imports
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from ldraw_parser import parse_mpd, LDrawDocument

# =============================================================================
# Parts Catalog Loading
# =============================================================================

def load_parts_catalog() -> Dict[str, Any]:
    """Load the parts catalog from YAML file."""
    catalog_path = SCRIPT_DIR.parent.parent / 'models' / 'parts_catalog.yaml'

    if not catalog_path.exists():
        print(f"Warning: Parts catalog not found at {catalog_path}")
        return {'parts': {}, 'wheel_assemblies': {}}

    # Simple YAML parsing (avoid external dependency)
    catalog = {
        'parts': {},
        'wheel_assemblies': {},
    }

    with open(catalog_path, 'r') as f:
        content = f.read()

    # Parse wheel_assemblies section
    wheel_match = re.search(r'wheel_assemblies:\n((?:  .+\n)*)', content)
    if wheel_match:
        catalog['wheel_assemblies'] = parse_yaml_section(wheel_match.group(1), indent=2)

    # Parse parts section - extract category -> part_number -> info
    parts_match = re.search(r'^parts:\n([\s\S]*?)(?=\n[a-z]|\Z)', content, re.MULTILINE)
    if parts_match:
        parts_content = parts_match.group(1)

        # Find each category (comment line with category name, then entries)
        # Pattern: "  # CATEGORY_NAME (N parts)" followed by "  category_name:"
        category_pattern = r'^  # [A-Z_ ]+ \(\d+ parts\)\n  ([a-z_]+):\n((?:    .+\n)*)'
        for cat_match in re.finditer(category_pattern, parts_content, re.MULTILINE):
            category = cat_match.group(1)
            category_content = cat_match.group(2)

            # Find each part in category
            part_pattern = r'^    "([^"]+)":\n((?:      .+\n)*)'
            for part_match in re.finditer(part_pattern, category_content, re.MULTILINE):
                part_number = part_match.group(1)
                part_info = parse_part_info(part_match.group(2))
                part_info['category'] = category
                catalog['parts'][part_number] = part_info

    return catalog


def parse_yaml_section(content: str, indent: int = 2) -> Dict:
    """Parse a simple YAML section into a dict."""
    result = {}
    current_key = None
    current_dict = None

    for line in content.split('\n'):
        if not line.strip() or line.strip().startswith('#'):
            continue

        # Count leading spaces
        spaces = len(line) - len(line.lstrip())
        stripped = line.strip()

        if spaces == indent and stripped.endswith(':'):
            # New top-level key
            current_key = stripped[:-1]
            current_dict = {}
            result[current_key] = current_dict
        elif spaces == indent + 2 and current_dict is not None:
            # Key-value pair
            if ':' in stripped:
                k, v = stripped.split(':', 1)
                v = v.strip().strip('"')
                if v == 'null':
                    v = None
                elif v.lstrip('-').replace('.', '').isdigit() and '-' not in v[1:]:
                    # Only convert if it's actually a number (not a part number with hyphens)
                    v = float(v) if '.' in v else int(v)
                current_dict[k] = v

    return result


def parse_part_info(content: str) -> Dict:
    """Parse part info from YAML content."""
    info = {}
    for line in content.split('\n'):
        if ':' in line:
            k, v = line.strip().split(':', 1)
            v = v.strip().strip('"')
            # Only convert to number if it's actually numeric (not part numbers with hyphens)
            if v.lstrip('-').replace('.', '').isdigit() and '-' not in v[1:]:
                v = float(v) if '.' in v else int(v)
            info[k] = v
    return info


# =============================================================================
# Part Classification
# =============================================================================

# Categories that matter for simulation (filter out structural parts)
SIMULATION_CATEGORIES = {'motor', 'sensor', 'brain', 'controller', 'wheel'}

# Global catalog (loaded once)
_CATALOG: Optional[Dict] = None


def get_catalog() -> Dict:
    """Get the parts catalog, loading if necessary."""
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = load_parts_catalog()
    return _CATALOG


def classify_part(part_number: str) -> Optional[Tuple[str, Dict]]:
    """
    Classify a part number using the parts catalog.

    Returns:
        Tuple of (category, part_info) or None if not found
    """
    catalog = get_catalog()

    # Normalize: remove .dat extension, handle variants
    base = part_number.replace('.dat', '').replace('.DAT', '')
    base = re.sub(r'-v\d+$', '', base)  # Remove version suffix (-v2)
    base = re.sub(r'c\d+$', '', base)   # Remove LDraw composite suffix (c01, c02)

    if base in catalog['parts']:
        info = catalog['parts'][base]
        return (info['category'], info)

    return None


def get_part_type_string(category: str, info: Dict) -> str:
    """
    Generate a type string for a part based on its category and info.

    Format: category:subtype (e.g., "wheel:hub", "sensor:color_sensor")
    """
    # For wheels, include the wheel_type if available
    if category == 'wheel' and 'wheel_type' in info:
        return f"{category}:{info['wheel_type']}"

    # For sensors/motors/brain, use the name to derive subtype
    if category in ('sensor', 'motor', 'brain', 'controller'):
        name = info.get('name', '')
        # Convert "Color Sensor" -> "color_sensor"
        subtype = name.lower().replace(' ', '_').replace('(', '').replace(')', '')
        # Simplify common patterns
        subtype = subtype.replace('robot_brain_with_battery', 'brain_with_battery')
        subtype = subtype.replace('robot_brain', 'brain')
        return f"{category}:{subtype}"

    # Default: just category
    return category


@dataclass
class PartInfo:
    """Information about a single part reference."""
    part_number: str
    color: int
    position: Tuple[float, float, float]
    rotation_matrix: Tuple[float, ...]
    category: Optional[str] = None
    catalog_info: Optional[Dict] = None

    @property
    def type_string(self) -> Optional[str]:
        """Get the type string for this part."""
        if self.category and self.catalog_info:
            return get_part_type_string(self.category, self.catalog_info)
        return None


@dataclass
class SubmodelInfo:
    """Information about a submodel in the hierarchy."""
    name: str
    parent: Optional[str] = None
    children: List[str] = field(default_factory=list)
    parts: List[PartInfo] = field(default_factory=list)
    position: Tuple[float, float, float] = (0, 0, 0)
    rotation_matrix: Tuple[float, ...] = (1, 0, 0, 0, 1, 0, 0, 0, 1)

    # Category counts
    category_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    @property
    def wheel_count(self) -> int:
        return self.category_counts.get('wheel', 0)

    @property
    def motor_count(self) -> int:
        return self.category_counts.get('motor', 0)

    @property
    def sensor_count(self) -> int:
        return self.category_counts.get('sensor', 0)

    @property
    def has_brain(self) -> bool:
        return self.category_counts.get('brain', 0) > 0


def analyze_model(doc: LDrawDocument) -> Dict[str, SubmodelInfo]:
    """Analyze the LDraw document and extract hierarchy information."""
    submodels: Dict[str, SubmodelInfo] = {}

    # First pass: create SubmodelInfo for each model
    for name, model in doc.models.items():
        info = SubmodelInfo(name=name)
        submodels[name] = info

    # Second pass: analyze parts and build hierarchy
    for name, model in doc.models.items():
        info = submodels[name]

        # Process direct parts
        for part in model.parts:
            part_num = part.part_name.replace('.dat', '').replace('.DAT', '')

            # Classify using catalog
            classification = classify_part(part_num)

            part_info = PartInfo(
                part_number=part_num,
                color=part.color,
                position=(part.x, part.y, part.z),
                rotation_matrix=part.rotation_matrix,
                category=classification[0] if classification else None,
                catalog_info=classification[1] if classification else None
            )
            info.parts.append(part_info)

            # Count by category
            if classification:
                category = classification[0]
                info.category_counts[category] += 1

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
    lines.append(f"# Generated from: {doc.filename or 'unknown'}")
    lines.append("# ")
    lines.append("# This file describes the robot's structure for simulation.")
    lines.append("# Extend with kinematics, port mappings, and code bindings.")
    lines.append("")
    lines.append("version: 1")
    lines.append(f"source_file: {doc.filename or 'unknown'}")
    lines.append(f"main_model: {doc.main_model}")
    lines.append("")

    # Summary - collect all categories
    all_categories: Dict[str, int] = defaultdict(int)
    for info in submodels.values():
        for cat, count in info.category_counts.items():
            all_categories[cat] += count

    has_brain = any(s.has_brain for s in submodels.values())

    lines.append("# Summary")
    lines.append("summary:")
    lines.append(f"  total_submodels: {len(submodels)}")
    lines.append(f"  has_brain: {str(has_brain).lower()}")

    # List significant categories
    significant_cats = ['motor', 'sensor', 'wheel', 'gear', 'brain']
    for cat in significant_cats:
        if cat in all_categories:
            lines.append(f"  total_{cat}s: {all_categories[cat]}")

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

        # Add summary of special parts in this submodel
        specials = []
        for cat in ['wheel', 'motor', 'sensor', 'gear', 'brain']:
            count = info.category_counts.get(cat, 0)
            if count > 0:
                if cat == 'brain':
                    specials.append('brain')
                else:
                    specials.append(f"{count} {cat}{'s' if count > 1 else ''}")
        if specials:
            lines.append(f"{prefix}  contains: [{', '.join(specials)}]")

    for root in roots:
        write_hierarchy(root)

    lines.append("")

    # Detailed submodels section
    lines.append("# Detailed Submodel Definitions")
    lines.append("submodels:")

    for name, info in submodels.items():
        lines.append(f"  {name}:")
        lines.append(f"    position: [{info.position[0]}, {info.position[1]}, {info.position[2]}]")

        if info.parent:
            lines.append(f"    parent: {info.parent}")

        # Placeholder for kinematics
        lines.append("    kinematics: null  # rotation_axis, rotation_origin, rotation_limits")

        # List special parts (only simulation-relevant categories)
        special_parts = [p for p in info.parts if p.category in SIMULATION_CATEGORIES]
        if special_parts:
            lines.append("    special_parts:")
            for part in special_parts:
                lines.append(f"      - part: {part.part_number}")
                lines.append(f"        category: {part.category}")
                if part.type_string:
                    lines.append(f"        type: {part.type_string}")
                if part.catalog_info and 'name' in part.catalog_info:
                    lines.append(f"        name: \"{part.catalog_info['name']}\"")
                lines.append(f"        position: [{part.position[0]}, {part.position[1]}, {part.position[2]}]")

        lines.append("")

    # Motors section
    # List each motor individually with a unique name
    lines.append("# Motor Configuration")
    lines.append("# Each motor has a unique name: {SubmodelBaseName}_{N}")
    lines.append("motors:")

    motor_count_by_submodel = {}  # Track count for unique naming
    motor_entries = []

    for name, info in submodels.items():
        motor_parts = [p for p in info.parts if p.category == 'motor']
        if motor_parts:
            # Get base name without .ldr extension for cleaner naming
            base_name = name.replace('.ldr', '').replace('.LDR', '')

            for i, motor_part in enumerate(motor_parts, start=1):
                motor_name = f"{base_name}_{i}" if len(motor_parts) > 1 or info.motor_count > 1 else f"{base_name}_1"
                motor_entries.append({
                    'name': motor_name,
                    'submodel': name,
                    'part': motor_part.part_number,
                    'position': motor_part.position,
                    'type': motor_part.type_string or 'motor:unknown',
                })

    if motor_entries:
        for entry in motor_entries:
            lines.append(f"  - name: {entry['name']}")
            lines.append(f"    submodel: {entry['submodel']}")
            lines.append(f"    part: {entry['part']}")
            lines.append(f"    type: {entry['type']}")
            lines.append(f"    position: [{entry['position'][0]}, {entry['position'][1]}, {entry['position'][2]}]")
            lines.append("    port: null  # 1-12")
            lines.append("    purpose: null  # drive | arm | intake | etc")
            lines.append("")
    else:
        lines.append("  []  # No motor parts detected")

    lines.append("")

    # ==========================================================================
    # Wheel Assemblies - group parts at same position that spin together
    # ==========================================================================
    lines.append("# Wheel Assemblies")
    lines.append("# Each assembly groups parts (hub, tire, etc.) that spin together")
    lines.append("# Assemblies are referenced by ID in the drivetrain section")
    lines.append("wheel_assemblies:")

    # Collect all wheel parts with their world positions
    wheel_parts_by_position = {}  # (submodel, pos_key) -> list of parts

    for name, info in submodels.items():
        wheel_parts = [p for p in info.parts if p.category == 'wheel']
        for part in wheel_parts:
            # Round position to group parts at "same" location (within 1 LDU)
            pos_key = (round(part.position[0]), round(part.position[1]), round(part.position[2]))
            key = (name, pos_key)

            if key not in wheel_parts_by_position:
                wheel_parts_by_position[key] = []
            wheel_parts_by_position[key].append(part)

    # Build wheel assemblies
    wheel_assemblies = []
    wheel_id_counter = 0

    for (submodel_name, pos_key), parts in wheel_parts_by_position.items():
        info = submodels[submodel_name]

        # Calculate world position
        world_x = info.position[0] + pos_key[0]
        world_y = info.position[1] + pos_key[1]
        world_z = info.position[2] + pos_key[2]

        # Determine side from submodel name or position
        name_lower = submodel_name.lower()
        if 'left' in name_lower:
            side = 'left'
        elif 'right' in name_lower:
            side = 'right'
        else:
            side = 'left' if world_x < 0 else 'right'

        # Determine front/rear from Z position (lower Z = front in LDraw)
        # We'll refine this after collecting all wheels
        z_pos = world_z

        # Find the outer diameter and wheel type
        # First, check if this is a known hub+tire assembly from catalog
        catalog = get_catalog()
        part_numbers = {p.part_number for p in parts}
        outer_diameter = 0
        wheel_type = 'wheel'

        # Check catalog wheel_assemblies for matching hub+tire pair
        for asm_name, asm_info in catalog.get('wheel_assemblies', {}).items():
            hub = asm_info.get('hub')
            tire = asm_info.get('tire')
            if hub and tire and hub in part_numbers and tire in part_numbers:
                # Found matching assembly - use catalog outer diameter
                outer_diameter = asm_info.get('outer_diameter_mm', 0)
                wheel_type = 'tire'
                break

        # Fallback: determine from individual parts if no catalog match
        if outer_diameter == 0:
            for part in parts:
                if part.catalog_info:
                    wt = part.catalog_info.get('wheel_type', 'wheel')
                    # For omni/mecanum wheels, use diameter directly
                    if wt in ('omni', 'mecanum'):
                        d = part.catalog_info.get('diameter_mm', 0)
                        outer_diameter = d
                        wheel_type = wt
                        break
                    # For tires, the catalog "diameter_mm" is actually travel (circumference)
                    # Convert: outer_diameter = travel / pi
                    elif wt == 'tire':
                        travel = part.catalog_info.get('diameter_mm', 0)
                        if travel > 0:
                            outer_diameter = travel / 3.14159
                            wheel_type = 'tire'
                    # For standalone hubs/wheels
                    elif wt in ('hub', 'wheel') and outer_diameter == 0:
                        outer_diameter = part.catalog_info.get('diameter_mm', 0)
                        wheel_type = wt

        # Check if this submodel has a motor (powered wheel)
        is_powered = info.motor_count > 0

        # Extract spin axis from wheel's rotation matrix
        # The wheel's local Y-axis (axle) transformed to submodel space
        # Column 1 of the rotation matrix = (m[1], m[4], m[7]) = local Y in submodel coords
        first_wheel = parts[0]
        m = first_wheel.rotation_matrix
        spin_axis = (m[1], m[4], m[7])

        # Heuristic: if spin axis is vertical (Y-dominant), it's likely wrong.
        # Tank drive wheels spin around a horizontal axis. Use X-axis based on side.
        abs_x, abs_y, abs_z = abs(spin_axis[0]), abs(spin_axis[1]), abs(spin_axis[2])
        if abs_y > abs_x and abs_y > abs_z:
            # Vertical spin axis detected - use horizontal X-axis instead
            # Left side: +X, Right side: -X (outward-facing axles)
            spin_axis = (1.0, 0.0, 0.0) if side == 'left' else (-1.0, 0.0, 0.0)

        wheel_assemblies.append({
            'id': None,  # Will assign after sorting
            'world_position': (world_x, world_y, world_z),
            'side': side,
            'z_pos': z_pos,
            'outer_diameter_mm': outer_diameter,
            'wheel_type': wheel_type,
            'spin_axis': spin_axis,
            'is_powered': is_powered,  # Used for drivetrain calculation only
            'parts': [
                {
                    'part_number': p.part_number,
                    'type': p.catalog_info.get('wheel_type', 'unknown') if p.catalog_info else 'unknown',
                    'submodel': submodel_name,
                    'local_position': pos_key,
                }
                for p in parts
            ],
        })

    # Sort by side, then by Z position to assign front/rear
    left_wheels = sorted([w for w in wheel_assemblies if w['side'] == 'left'], key=lambda w: w['z_pos'])
    right_wheels = sorted([w for w in wheel_assemblies if w['side'] == 'right'], key=lambda w: w['z_pos'])

    # Assign IDs based on position
    def assign_ids(wheels, side_prefix):
        if len(wheels) == 1:
            wheels[0]['id'] = f"{side_prefix}"
        elif len(wheels) == 2:
            wheels[0]['id'] = f"{side_prefix}_front"
            wheels[1]['id'] = f"{side_prefix}_rear"
        else:
            for i, w in enumerate(wheels):
                w['id'] = f"{side_prefix}_{i}"

    assign_ids(left_wheels, 'left')
    assign_ids(right_wheels, 'right')

    # Combine back and output
    all_wheels = left_wheels + right_wheels

    if all_wheels:
        for w in all_wheels:
            wp = w['world_position']
            sa = w['spin_axis']
            lines.append(f"  {w['id']}:")
            lines.append(f"    world_position: [{wp[0]:.1f}, {wp[1]:.1f}, {wp[2]:.1f}]")
            lines.append(f"    spin_axis: [{sa[0]:.3f}, {sa[1]:.3f}, {sa[2]:.3f}]")
            lines.append(f"    outer_diameter_mm: {w['outer_diameter_mm']}")
            lines.append(f"    wheel_type: {w['wheel_type']}  # tire | omni | mecanum | wheel")
            lines.append(f"    parts:")
            for part in w['parts']:
                lp = part['local_position']
                lines.append(f"      - part: {part['part_number']}")
                lines.append(f"        type: {part['type']}")
                lines.append(f"        submodel: {part['submodel']}")
                lines.append(f"        local_position: [{lp[0]}, {lp[1]}, {lp[2]}]")
    else:
        lines.append("  {}  # No wheel assemblies detected")

    lines.append("")

    # ==========================================================================
    # Drivetrain - references wheel assembly IDs
    # ==========================================================================
    lines.append("# Drivetrain Configuration")
    lines.append("# References wheel assemblies by ID")
    lines.append("drivetrain:")
    lines.append("  type: tank  # tank | mecanum | x_drive | h_drive")

    # Get powered wheels for drivetrain
    powered_wheels = [w for w in all_wheels if w['is_powered']]
    powered_left = [w for w in powered_wheels if w['side'] == 'left']
    powered_right = [w for w in powered_wheels if w['side'] == 'right']

    if powered_wheels:
        # Calculate rotation center from powered wheel positions
        all_positions = [w['world_position'] for w in powered_wheels]
        center_x = sum(p[0] for p in all_positions) / len(all_positions)
        center_y = sum(p[1] for p in all_positions) / len(all_positions)
        center_z = sum(p[2] for p in all_positions) / len(all_positions)

        # Track width
        if powered_left and powered_right:
            left_center_x = sum(w['world_position'][0] for w in powered_left) / len(powered_left)
            right_center_x = sum(w['world_position'][0] for w in powered_right) / len(powered_right)
            track_width = abs(right_center_x - left_center_x)
        else:
            track_width = 0

        # Wheel diameter (assume uniform)
        wheel_diameter = powered_wheels[0]['outer_diameter_mm'] if powered_wheels else 0

        lines.append(f"  rotation_center: [{center_x:.1f}, {center_y:.1f}, {center_z:.1f}]")
        # For tank drive, rotation is around vertical axis (Y-up in OpenGL)
        lines.append("  rotation_axis: [0, 1, 0]")
        lines.append(f"  track_width_mm: {track_width:.1f}")
        lines.append(f"  wheel_diameter_mm: {wheel_diameter}")
        lines.append("")
        lines.append("  left_wheels:")
        for w in powered_left:
            lines.append(f"    - {w['id']}")
        if not powered_left:
            lines.append("    []")
        lines.append("")
        lines.append("  right_wheels:")
        for w in powered_right:
            lines.append(f"    - {w['id']}")
        if not powered_right:
            lines.append("    []")
    else:
        lines.append("  rotation_center: [0, 0, 0]")
        lines.append("  track_width_mm: 0")
        lines.append("  wheel_diameter_mm: 0")
        lines.append("  left_wheels: []")
        lines.append("  right_wheels: []")

    lines.append("")

    # Sensors section
    lines.append("# Sensor Configuration")
    lines.append("sensors:")

    sensor_found = False
    for name, info in submodels.items():
        sensor_parts = [p for p in info.parts if p.category == 'sensor']
        for part in sensor_parts:
            sensor_found = True
            sensor_type = part.type_string or 'unknown'
            lines.append(f"  - type: {sensor_type}")
            lines.append(f"    submodel: {name}")
            lines.append(f"    part: {part.part_number}")
            lines.append("    port: null  # 1-12")

    if not sensor_found:
        lines.append("  []  # No sensor parts detected")

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

    # Load catalog
    catalog = get_catalog()
    print(f"Loaded parts catalog: {len(catalog['parts'])} parts")

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
            if info.category_counts:
                cats = [f"{count} {cat}" for cat, count in info.category_counts.items()]
                print(f"    Contains: {', '.join(cats)}")

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
    all_categories: Dict[str, int] = defaultdict(int)
    for info in submodels.values():
        for cat, count in info.category_counts.items():
            all_categories[cat] += count

    print(f"\nSummary:")
    print(f"  Submodels: {len(submodels)}")
    for cat, count in sorted(all_categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")


if __name__ == '__main__':
    main()
