#!/usr/bin/env python3
"""
Build VEX IQ Parts Catalog from STEP file names.

Parses part names and numbers from VEX official STEP archives and creates
a comprehensive YAML catalog for use by the robotdef generator.
"""

import re
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

# Category detection patterns (order matters - first match wins)
CATEGORY_PATTERNS = [
    # Wheels and Tires (critical for simulation)
    (r'wheel|tire|traction|omni|mecanum|rover wheel', 'wheel'),
    (r'hub.*wheel|wheel.*hub', 'wheel_hub'),

    # Gears
    (r'gear(?!.*rack)', 'gear'),
    (r'rack gear|gear rack', 'rack_gear'),
    (r'worm gear', 'worm_gear'),
    (r'crown gear', 'crown_gear'),

    # Sprockets and Chain
    (r'sprocket', 'sprocket'),
    (r'chain link|tank tread', 'chain'),

    # Pulleys and Belts
    (r'pulley', 'pulley'),
    (r'belt(?! \()', 'belt'),  # Belt but not Belt (Mechanical)

    # Structural - Beams
    (r'\dx\d+.*beam|beam.*\dx\d+|\d+x\d+ beam|^1x\d+ beam', 'beam'),
    (r'beam', 'beam'),

    # Structural - Plates
    (r'plate|panel|smooth panel', 'plate'),

    # Connectors and Pins
    (r'connector pin|idler pin|sheet pin|snap pin', 'pin'),
    (r'corner connector|chassis connector', 'connector'),
    (r'connector', 'connector'),

    # Shafts and Axles
    (r'shaft|axle', 'shaft'),
    (r'standoff', 'standoff'),
    (r'spacer', 'spacer'),

    # Motion components
    (r'linear motion|slide|slider', 'linear_motion'),
    (r'bearing|bushing', 'bearing'),
    (r'lock|latch', 'lock'),

    # Decorative/Aesthetic
    (r'eye|nose|mouth|ear|hair|face|head|body|arm(?!.*crank)|leg|hand|foot|wing|tail|feather|antenna', 'decorative'),
    (r'propeller|blade', 'decorative'),
    (r'satellite|dish|monitor|screen', 'decorative'),
    (r'hook|crane|bucket|scoop|claw(?!.*bot)', 'manipulator'),

    # Hardware
    (r'rubber band|silicone|band #', 'rubber_band'),
    (r'washer|collar|sleeve', 'hardware'),
    (r'spool', 'spool'),

    # Special mechanisms
    (r'crank|linkage|ball socket|differential', 'mechanism'),
    (r'turntable|swivel', 'turntable'),
    (r'shock|suspension|spring', 'suspension'),

    # Default
    (r'.*', 'other'),
]

# Additional attributes to extract
WHEEL_DIAMETER_PATTERN = r'(\d+(?:\.\d+)?)\s*(?:mm|inch|")\s*(?:diameter)?'
WHEEL_WIDTH_PATTERN = r'(\d+(?:\.\d+)?)\s*(?:mm|inch|")?\s*wide'

# Control parts (from the control STEP archive)
CONTROL_PARTS = {
    '228-2560': {'name': 'Smart Motor', 'category': 'motor'},
    '228-2530': {'name': 'Controller', 'category': 'controller'},
    '228-2540': {'name': 'Robot Brain', 'category': 'brain'},
    '228-2540c02': {'name': 'Robot Brain with Battery', 'category': 'brain'},  # LDraw variant
    '228-2604': {'name': 'Robot Battery', 'category': 'battery'},
    '228-2621': {'name': '900 MHz Radio', 'category': 'radio'},
    '228-2677': {'name': 'Bumper Switch (Gen 1)', 'category': 'sensor'},
    '228-2780': {'name': 'Cable', 'category': 'cable'},
    '228-3010': {'name': 'Touch LED', 'category': 'sensor'},
    '228-3011': {'name': 'Distance Sensor / Bumper Switch', 'category': 'sensor'},  # Note: name conflict in VEX docs
    '228-3012': {'name': 'Color Sensor', 'category': 'sensor'},
    '228-3014': {'name': 'Gyro Sensor', 'category': 'sensor'},
}

# Known wheel assemblies (wheel + tire pairs that should rotate together)
# Note: VEX uses "Travel" (circumference) not diameter for tires
# Outer diameter = Travel / pi
WHEEL_ASSEMBLIES = {
    # 44mm hub with 200mm travel tire
    # Hub inner: 44mm, Tire outer: ~64mm (200/pi)
    '44mm_hub': {
        'hub': '228-2500-208',
        'tire': '228-2500-209',
        'hub_diameter_mm': 44,
        'outer_diameter_mm': 63.7,  # 200mm travel / pi
        'travel_mm': 200,
    },
    # 64mm hub with 250mm travel tire
    # Hub inner: 64mm, Tire outer: ~80mm (250/pi)
    '64mm_hub': {
        'hub': '228-2500-211',
        'tire': '228-2500-212',
        'hub_diameter_mm': 64,
        'outer_diameter_mm': 79.6,  # 250mm travel / pi
        'travel_mm': 250,
    },
    # Smaller assemblies
    '44mm_hub_small_tire': {
        'hub': '228-2500-208',
        'tire': '228-2500-207',
        'hub_diameter_mm': 44,
        'outer_diameter_mm': 31.8,  # 100mm travel / pi
        'travel_mm': 100,
    },
    '64mm_hub_medium_tire': {
        'hub': '228-2500-211',
        'tire': '228-2500-210',
        'hub_diameter_mm': 64,
        'outer_diameter_mm': 50.9,  # 160mm travel / pi
        'travel_mm': 160,
    },
    # New gen2 wheels with different hub sizes
    '32mm_hub': {
        'hub': '228-2500-1950',  # 2x Wide, 32.2mm Diameter Hub
        'tire': None,  # Multiple tire options
        'hub_diameter_mm': 32.2,
    },
    '48mm_hub': {
        'hub': '228-2500-1953',  # 2x Wide, 48.5mm Diameter Hub
        'tire': None,  # Multiple tire options
        'hub_diameter_mm': 48.5,
    },
}


def parse_part_line(line: str) -> Optional[Tuple[str, str]]:
    """Parse a line like 'Part Name (228-2500-XXX).step' into (name, part_number)."""
    # Match: Name (228-XXXX-XXX).step or Name (228-XXXX-XXX).STEP
    match = re.match(r'^(.+?)\s*\((228-\d+-\d+(?:-\d+)?)\)\.[sS][tT][eE][pP]$', line.strip())
    if match:
        return match.group(1).strip(), match.group(2)
    return None


def categorize_part(name: str) -> str:
    """Determine category based on part name."""
    name_lower = name.lower()
    for pattern, category in CATEGORY_PATTERNS:
        if re.search(pattern, name_lower):
            return category
    return 'other'


def extract_wheel_info(name: str) -> Dict:
    """Extract wheel-specific info like diameter."""
    info = {}
    name_lower = name.lower()

    # Try to extract diameter
    # Common patterns: "44mm", "2.75" Diameter", "200 mm"
    diameter_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:mm|inch|")\s*(?:diameter)?', name_lower)
    if diameter_match:
        val = float(diameter_match.group(1))
        # Assume mm if value > 10, otherwise inches
        if val > 10:
            info['diameter_mm'] = val
        else:
            info['diameter_mm'] = val * 25.4  # Convert to mm

    # Check for pitch diameter (used in VEX naming)
    pitch_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:x\s*)?pitch\s*diameter', name_lower)
    if pitch_match:
        # VEX pitch is 0.5 inches = 12.7mm
        pitches = float(pitch_match.group(1))
        info['diameter_mm'] = pitches * 12.7

    # Check if it's a tire vs hub vs wheel assembly
    if 'tire' in name_lower or 'traction' in name_lower:
        info['wheel_type'] = 'tire'
    elif 'hub' in name_lower:
        info['wheel_type'] = 'hub'
    elif 'omni' in name_lower:
        info['wheel_type'] = 'omni'
    elif 'mecanum' in name_lower:
        info['wheel_type'] = 'mecanum'
    else:
        info['wheel_type'] = 'wheel'

    return info


def build_catalog(parts_file: str) -> Dict:
    """Build the parts catalog from parsed file names."""
    catalog = {
        'version': 1,
        'source': 'VEX-IQ-All-Parts-2024-11-08.zip',
        'categories': defaultdict(dict),
        'wheel_assemblies': WHEEL_ASSEMBLIES,
    }

    # Read and parse parts
    with open(parts_file, 'r') as f:
        for line in f:
            result = parse_part_line(line)
            if not result:
                continue
            name, part_num = result

            category = categorize_part(name)

            part_info = {
                'name': name,
                'category': category,
            }

            # Add wheel-specific info
            if category in ('wheel', 'wheel_hub'):
                wheel_info = extract_wheel_info(name)
                part_info.update(wheel_info)

            # Use short part number (without 228-2500- prefix for storage)
            catalog['categories'][category][part_num] = part_info

    # Add control parts
    for part_num, info in CONTROL_PARTS.items():
        catalog['categories'][info['category']][part_num] = {
            'name': info['name'],
            'category': info['category'],
        }

    return catalog


def write_yaml_catalog(catalog: Dict, output_file: str):
    """Write catalog as YAML."""
    with open(output_file, 'w') as f:
        f.write("# VEX IQ Parts Catalog\n")
        f.write("# Auto-generated from official VEX STEP files\n")
        f.write(f"# Source: {catalog['source']}\n")
        f.write(f"# Total parts: {sum(len(v) for v in catalog['categories'].values())}\n")
        f.write("#\n")
        f.write("# Categories:\n")
        for cat, parts in sorted(catalog['categories'].items()):
            f.write(f"#   {cat}: {len(parts)} parts\n")
        f.write("\n")
        f.write(f"version: {catalog['version']}\n\n")

        # Write wheel assemblies first (important for simulation)
        f.write("# Wheel assemblies (hub + tire pairs that rotate together)\n")
        f.write("# VEX tires use 'Travel' = circumference, so outer_diameter = travel / pi\n")
        f.write("wheel_assemblies:\n")
        for name, assembly in catalog['wheel_assemblies'].items():
            f.write(f"  {name}:\n")
            f.write(f"    hub: \"{assembly['hub']}\"\n")
            if assembly.get('tire'):
                f.write(f"    tire: \"{assembly['tire']}\"\n")
            else:
                f.write(f"    tire: null  # Multiple tire options available\n")
            if assembly.get('hub_diameter_mm'):
                f.write(f"    hub_diameter_mm: {assembly['hub_diameter_mm']}\n")
            if assembly.get('outer_diameter_mm'):
                f.write(f"    outer_diameter_mm: {assembly['outer_diameter_mm']}\n")
            if assembly.get('travel_mm'):
                f.write(f"    travel_mm: {assembly['travel_mm']}\n")
        f.write("\n")

        # Write parts by category
        f.write("# Parts by category\n")
        f.write("parts:\n")

        # Order categories: critical ones first
        category_order = [
            'wheel', 'wheel_hub', 'motor', 'sensor', 'brain', 'controller',
            'gear', 'rack_gear', 'worm_gear', 'crown_gear',
            'sprocket', 'chain', 'pulley', 'belt',
            'beam', 'plate', 'connector', 'pin',
            'shaft', 'standoff', 'spacer',
            'linear_motion', 'bearing', 'turntable', 'mechanism',
            'manipulator', 'suspension', 'spool', 'rubber_band', 'hardware',
            'battery', 'radio', 'cable', 'decorative', 'other', 'lock'
        ]

        written_categories = set()
        for category in category_order:
            if category in catalog['categories']:
                write_category(f, category, catalog['categories'][category])
                written_categories.add(category)

        # Write any remaining categories
        for category in sorted(catalog['categories'].keys()):
            if category not in written_categories:
                write_category(f, category, catalog['categories'][category])


def write_category(f, category: str, parts: Dict):
    """Write a category section to the YAML file."""
    f.write(f"\n  # {category.upper().replace('_', ' ')} ({len(parts)} parts)\n")
    f.write(f"  {category}:\n")

    # Sort parts by part number
    for part_num in sorted(parts.keys()):
        info = parts[part_num]
        f.write(f"    \"{part_num}\":\n")
        f.write(f"      name: \"{info['name']}\"\n")

        # Write additional attributes
        for key, val in info.items():
            if key not in ('name', 'category'):
                if isinstance(val, str):
                    f.write(f"      {key}: \"{val}\"\n")
                else:
                    f.write(f"      {key}: {val}\n")


def main():
    if len(sys.argv) < 2:
        # Default paths
        parts_file = '/tmp/vex_parts_names.txt'
        output_file = Path(__file__).parent.parent / 'models' / 'parts_catalog.yaml'
    else:
        parts_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else 'parts_catalog.yaml'

    print(f"Building parts catalog from: {parts_file}")
    catalog = build_catalog(parts_file)

    print(f"Found {sum(len(v) for v in catalog['categories'].values())} parts in {len(catalog['categories'])} categories:")
    for cat, parts in sorted(catalog['categories'].items(), key=lambda x: -len(x[1])):
        print(f"  {cat}: {len(parts)}")

    print(f"\nWriting catalog to: {output_file}")
    write_yaml_catalog(catalog, str(output_file))
    print("Done!")


if __name__ == '__main__':
    main()
