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


# LDraw Color codes from LDConfig.ldr
# Format: color_code -> (r, g, b, name)
LDRAW_COLORS = {
    # Standard LDraw colors
    0: (0.13, 0.13, 0.13, "Black"),
    1: (0.00, 0.20, 0.70, "Blue"),
    2: (0.00, 0.55, 0.08, "Green"),
    3: (0.00, 0.60, 0.62, "Dark Turquoise"),
    4: (0.77, 0.00, 0.15, "Red"),
    5: (0.87, 0.40, 0.58, "Dark Pink"),
    6: (0.36, 0.13, 0.00, "Brown"),
    7: (0.76, 0.76, 0.76, "Light Gray"),
    8: (0.39, 0.37, 0.32, "Dark Gray"),
    9: (0.42, 0.67, 0.86, "Light Blue"),
    10: (0.47, 0.93, 0.46, "Bright Green"),
    11: (0.33, 0.65, 0.69, "Light Turquoise"),
    12: (0.99, 0.50, 0.45, "Salmon"),
    13: (0.98, 0.64, 0.78, "Pink"),
    14: (1.00, 0.86, 0.00, "Yellow"),
    15: (1.00, 1.00, 1.00, "White"),
    17: (0.73, 1.00, 0.81, "Light Green"),
    18: (0.99, 0.91, 0.59, "Light Yellow"),
    19: (0.91, 0.81, 0.63, "Tan"),
    20: (0.84, 0.77, 0.90, "Light Violet"),
    22: (0.51, 0.00, 0.48, "Purple"),
    25: (1.00, 0.52, 0.00, "Orange"),
    26: (0.84, 0.00, 0.56, "Magenta"),
    27: (0.85, 0.94, 0.16, "Lime"),
    28: (0.77, 0.59, 0.31, "Dark Tan"),
    29: (0.90, 0.76, 0.87, "Bright Pink"),
    # Special colors
    16: (1.00, 1.00, 1.00, "Main Color"),      # Inherits from parent (render as white)
    24: (0.50, 0.50, 0.50, "Edge Color"),      # Edge/line color
    # VEX IQ specific colors
    70: (0.15, 0.16, 0.16, "VEX Black"),       # #272929
    71: (0.70, 0.71, 0.70, "VEX Light Gray"),  # #B3B5B3
    72: (0.33, 0.35, 0.35, "VEX Dark Gray"),   # #545858
    73: (0.54, 0.55, 0.55, "VEX Medium Gray"), # #8A8C8C
    320: (0.82, 0.15, 0.19, "VEX Red"),        # #D22630
    321: (0.00, 0.59, 0.22, "VEX Green"),      # #009639
    322: (0.00, 0.47, 0.78, "VEX Blue"),       # #0078C8
    323: (1.00, 0.80, 0.00, "VEX Yellow"),     # #FFCC00
    324: (0.85, 0.85, 0.84, "VEX White"),      # #D9D9D6
    325: (1.00, 0.40, 0.12, "VEX Orange"),     # #FF661F
    326: (0.37, 0.15, 0.62, "VEX Purple"),     # #5E269E
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
