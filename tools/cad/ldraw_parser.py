"""
LDraw MPD/LDR Parser for VEX IQ

Parses LDraw files and extracts part placements with transformations.

LDraw Line Format:
  0 - Comment or meta-command
  1 - Part reference: 1 <color> <x> <y> <z> <a> <b> <c> <d> <e> <f> <g> <h> <i> <part.dat>
      The 9 values (a-i) form a 3x3 rotation matrix in row-major order:
      | a b c |
      | d e f |
      | g h i |

LDraw Units (LDU): 1 LDU = 0.4mm
VEX IQ Pitch: 12.7mm = 31.75 LDU

Usage (from project root):
    python tools/cad/ldraw_parser.py <file.mpd|file.ldr>

Works on both Windows and WSL2 when cd'd into the project directory.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from pathlib import Path

# Determine project root (works whether run from project root or tools/cad/)
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent


# LDraw Color codes from VEX IQ LDConfig.ldr (by Philo, 2017/05/09)
# Source: C:\Apps\VEXIQ_2018-01-19\LDConfig.ldr
# Format: color_code -> (r, g, b, name)
LDRAW_COLORS = {
    # Special colors
    16: (1.00, 1.00, 1.00, "Main Color"),           # Inherits from parent (render as white)
    24: (0.50, 0.50, 0.50, "Edge Color"),           # Edge/line color

    # VEX IQ Solid Colors (from official LDConfig)
    0: (0.145, 0.157, 0.165, "VEX Black"),          # #25282A
    2: (0.000, 0.588, 0.224, "VEX Green"),          # #009639
    4: (0.824, 0.149, 0.188, "VEX Red"),            # #D22630
    5: (0.898, 0.427, 0.694, "VEX Pink"),           # #E56DB1
    7: (0.698, 0.706, 0.698, "VEX Light Gray"),     # #B2B4B2
    10: (0.263, 0.690, 0.165, "VEX Bright Green"),  # #43B02A
    11: (0.000, 0.698, 0.765, "VEX Teal"),          # #00B2C3
    14: (1.000, 0.804, 0.000, "VEX Yellow"),        # #FFCD00
    15: (1.000, 1.000, 1.000, "VEX Bright White"),  # #FFFFFF
    17: (0.761, 0.855, 0.722, "Light Green"),       # #C2DAB8
    22: (0.373, 0.145, 0.624, "VEX Purple"),        # #5F259F
    25: (1.000, 0.404, 0.122, "VEX Orange"),        # #FF671F
    26: (0.882, 0.000, 0.596, "VEX Magenta"),       # #E10098
    27: (0.710, 0.741, 0.000, "VEX Chartreuse"),    # #B5BD00
    71: (0.537, 0.553, 0.553, "VEX Medium Gray"),   # #898D8D
    72: (0.329, 0.345, 0.353, "VEX Dark Gray"),     # #54585A
    73: (0.000, 0.467, 0.784, "VEX Blue"),          # #0077C8 - pins, gears, connectors
    84: (0.796, 0.376, 0.082, "VEX Burnt Orange"),  # #CB6015
    89: (0.000, 0.200, 0.627, "VEX Navy Blue"),     # #0033A0
    112: (0.420, 0.357, 0.780, "VEX Lavender"),     # #6B5BC7
    115: (0.592, 0.843, 0.000, "VEX Lime Green"),   # #97D700
    150: (0.733, 0.780, 0.839, "VEX Light Slate Gray"),  # #BBC7D6
    151: (0.851, 0.851, 0.839, "VEX White"),        # #D9D9D6
    191: (0.855, 0.667, 0.000, "VEX Gold"),         # #DAAA00
    212: (0.384, 0.710, 0.898, "VEX Sky Blue"),     # #62B5E5
    216: (0.463, 0.137, 0.184, "VEX Maroon"),       # #76232F
    272: (0.000, 0.298, 0.592, "VEX Royal Blue"),   # #004C97
    288: (0.125, 0.361, 0.251, "VEX Dark Green"),   # #205C40
    320: (0.651, 0.098, 0.180, "VEX Crimson Red"),  # #A6192E
    321: (0.196, 0.384, 0.584, "VEX Denim Blue"),   # #326295
    462: (1.000, 0.596, 0.000, "VEX Citrus Orange"),  # #FF9800
    503: (0.780, 0.788, 0.780, "VEX Very Light Gray"),  # #C7C9C7

    # VEX IQ Rubber Colors
    256: (0.129, 0.129, 0.129, "Rubber Black"),     # #212121
    504: (0.537, 0.529, 0.533, "Rubber Gray"),      # #898788

    # VEX IQ Transparent Colors
    33: (0.000, 0.200, 0.627, "VEX Trans Navy Blue"),  # #0033A0
    34: (0.137, 0.471, 0.255, "VEX Trans Green"),   # #237841
    35: (0.263, 0.690, 0.165, "VEX Trans Bright Green"),  # #43B02A
    36: (0.824, 0.149, 0.188, "VEX Trans Red"),     # #D22630
    40: (0.000, 0.000, 0.000, "VEX Trans Black"),   # #000000
    41: (0.000, 0.467, 0.784, "VEX Trans Blue"),    # #0077C8
    42: (0.710, 0.741, 0.000, "VEX Trans Chartreuse"),  # #B5BD00
    43: (0.384, 0.710, 0.898, "VEX Trans Sky Blue"),  # #62B5E5
    45: (0.898, 0.427, 0.694, "VEX Trans Pink"),    # #E56DB1
    46: (0.855, 0.667, 0.000, "VEX Trans Gold"),    # #DAAA00
    47: (0.988, 0.988, 0.988, "VEX Clear"),         # #FCFCFC
    52: (0.373, 0.145, 0.624, "VEX Trans Purple"),  # #5F259F
    54: (1.000, 0.804, 0.000, "VEX Trans Yellow"),  # #FFCD00
    55: (0.537, 0.553, 0.553, "VEX Trans Medium Gray"),  # #898D8D
    56: (0.329, 0.345, 0.353, "VEX Trans Dark Gray"),  # #54585A
    57: (1.000, 0.404, 0.122, "VEX Trans Orange"),  # #FF671F

    # Internal colors
    32: (0.000, 0.000, 0.000, "Trans Black IR Lens"),  # #000000
    80: (0.816, 0.816, 0.816, "Metal"),             # #D0D0D0
    334: (0.882, 0.431, 0.075, "Chrome Gold"),      # #E16E13
}

# Alias for backward compatibility
VEX_COLORS = LDRAW_COLORS


@dataclass
class PartPlacement:
    """Represents a single part placement in the model."""
    part_name: str           # e.g., "228-2500-014.dat"
    color: int               # LDraw color code
    x: float                 # Position X (LDU)
    y: float                 # Position Y (LDU)
    z: float                 # Position Z (LDU)
    rotation_matrix: Tuple[float, ...]  # 9 values (a-i) in row-major order

    @property
    def glb_name(self) -> str:
        """Convert part name to GLB filename."""
        return self.part_name.replace('.dat', '.glb')

    def get_color_rgb(self, parent_color: int = 71) -> Tuple[float, float, float]:
        """Get RGB color (0-1 range). Color 16 inherits from parent."""
        color_code = self.color if self.color != 16 else parent_color
        if color_code in VEX_COLORS:
            r, g, b, _ = VEX_COLORS[color_code]
            return (r, g, b)
        return (0.5, 0.5, 0.5)  # Default gray


@dataclass
class LDrawModel:
    """Represents an LDraw model (can be main or submodel)."""
    name: str
    parts: List[PartPlacement] = field(default_factory=list)
    submodel_refs: List[Tuple[str, PartPlacement]] = field(default_factory=list)


@dataclass
class LDrawDocument:
    """Represents an LDraw MPD document with multiple models."""
    models: Dict[str, LDrawModel] = field(default_factory=dict)
    main_model: Optional[str] = None

    def get_all_parts(self, model_name: Optional[str] = None,
                      parent_color: int = 71) -> List[dict]:
        """
        Recursively get all parts from a model and its submodels.
        Returns list of dicts with position, rotation, color, and part info.
        """
        if model_name is None:
            model_name = self.main_model

        if model_name not in self.models:
            return []

        model = self.models[model_name]
        all_parts = []

        # Add direct parts
        for part in model.parts:
            all_parts.append({
                'part_name': part.part_name,
                'glb_name': part.glb_name,
                'x': part.x,
                'y': part.y,
                'z': part.z,
                'rotation': part.rotation_matrix,
                'color': part.get_color_rgb(parent_color),
                'color_code': part.color,
            })

        # TODO: Handle submodel references with transformations

        return all_parts


def parse_line_type_1(line: str) -> Optional[PartPlacement]:
    """
    Parse an LDraw type 1 line (part reference).
    Format: 1 <color> <x> <y> <z> <a> <b> <c> <d> <e> <f> <g> <h> <i> <part>
    """
    parts = line.strip().split()
    if len(parts) < 15 or parts[0] != '1':
        return None

    try:
        color = int(parts[1])
        x = float(parts[2])
        y = float(parts[3])
        z = float(parts[4])
        rotation = tuple(float(parts[i]) for i in range(5, 14))
        part_name = parts[14]

        # Handle part names with spaces (rare but possible)
        if len(parts) > 15:
            part_name = ' '.join(parts[14:])

        return PartPlacement(
            part_name=part_name,
            color=color,
            x=x, y=y, z=z,
            rotation_matrix=rotation
        )
    except (ValueError, IndexError) as e:
        print(f"Warning: Could not parse line: {line[:50]}... ({e})")
        return None


def parse_mpd(filepath: str) -> LDrawDocument:
    """
    Parse an LDraw MPD (Multi-Part Document) or LDR file.
    """
    doc = LDrawDocument()
    current_model: Optional[LDrawModel] = None

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # Check for new file/model
            if line.startswith('0 FILE '):
                model_name = line[7:].strip()
                current_model = LDrawModel(name=model_name)
                doc.models[model_name] = current_model
                if doc.main_model is None:
                    doc.main_model = model_name

            # Check for name (used for single-file LDR)
            elif line.startswith('0 Name:') and current_model is None:
                model_name = line[7:].strip()
                current_model = LDrawModel(name=model_name)
                doc.models[model_name] = current_model
                doc.main_model = model_name

            # Parse part reference
            elif line.startswith('1 '):
                if current_model is None:
                    current_model = LDrawModel(name="main")
                    doc.models["main"] = current_model
                    doc.main_model = "main"

                placement = parse_line_type_1(line)
                if placement:
                    # Check if it's a submodel reference or external part
                    if placement.part_name.endswith('.ldr'):
                        current_model.submodel_refs.append(
                            (placement.part_name, placement)
                        )
                    else:
                        current_model.parts.append(placement)

    return doc


def print_document_summary(doc: LDrawDocument):
    """Print a summary of the parsed document."""
    print(f"\n{'='*60}")
    print(f"LDraw Document Summary")
    print(f"{'='*60}")
    print(f"Main model: {doc.main_model}")
    print(f"Total models: {len(doc.models)}")

    for name, model in doc.models.items():
        print(f"\n  Model: {name}")
        print(f"    Parts: {len(model.parts)}")
        print(f"    Submodel refs: {len(model.submodel_refs)}")

        # List unique parts
        unique_parts = set(p.part_name for p in model.parts)
        print(f"    Unique part types: {len(unique_parts)}")
        for part in sorted(unique_parts):
            count = sum(1 for p in model.parts if p.part_name == part)
            print(f"      - {part} (x{count})")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ldraw_parser.py <file.mpd|file.ldr>")
        print("\nExample:")
        print("  python tools/cad/ldraw_parser.py models/test1.mpd")
        sys.exit(1)

    filepath = Path(sys.argv[1])

    # Try to find the file
    # 1. As given (absolute or relative to cwd)
    # 2. Relative to project root
    if not filepath.exists():
        alt_path = PROJECT_ROOT / filepath
        if alt_path.exists():
            filepath = alt_path
        else:
            print(f"Error: File not found: {sys.argv[1]}")
            print(f"  Tried: {filepath}")
            print(f"  Tried: {alt_path}")
            sys.exit(1)

    doc = parse_mpd(str(filepath))
    print_document_summary(doc)

    # Print all parts with positions
    print(f"\n{'='*60}")
    print("All Parts (flattened)")
    print(f"{'='*60}")

    all_parts = doc.get_all_parts()
    for i, part in enumerate(all_parts):
        print(f"\n  [{i+1}] {part['part_name']}")
        print(f"      Position: ({part['x']:.1f}, {part['y']:.1f}, {part['z']:.1f}) LDU")
        print(f"      Color: {part['color']} (code {part['color_code']})")
        print(f"      GLB: {part['glb_name']}")
