# LDraw CAD Conversion Tools

This directory contains tools for converting VEX IQ LDraw parts to GLB format and rendering LDraw models in Ursina.

## Overview

The pipeline converts LDraw .dat part files to GLB with vertex colors, then renders complete robot assemblies from .mpd/.ldr files.

```
LDraw .dat parts → Blender → GLB with vertex colors → Ursina renderer
                                                           ↑
LDraw .mpd/.ldr models (positions, rotations, colors) ────┘
```

## Prerequisites

1. **Blender 4.x+** with [ExportLDraw addon](https://github.com/cuddlyogre/ExportLDraw)
2. **VEX IQ LDraw Parts Library** (from SnapCAD or Philo's unofficial library)
3. **Python 3.12+** with Ursina and Panda3D

## Files

| File | Purpose |
|------|---------|
| `blender_ldraw_to_glb_vertex_colors.py` | Batch convert .dat parts to GLB with color preservation |
| `render_ldraw_model.py` | Render .mpd/.ldr models in Ursina |
| `ldraw_parser.py` | Parse LDraw file format |
| `ldraw_renderer.py` | Reusable LDraw model renderer for Ursina |
| `normal_lighting_shader.py` | Custom shader for headlight-style lighting |
| `generate_robot_def.py` | Generate robot definition files from MPD models |

## Color Preservation Logic

The conversion preserves LDraw's color system exactly like LDCad:

### In Blender Pipeline (`blender_ldraw_to_glb_vertex_colors.py`)

Vertex colors are baked based on LDraw color codes:

- **Color 16 (Main Color)** → WHITE (1,1,1) → Colorable via MPD file
- **All other colors** → Actual LDraw color → Preserved as-is

This means:
- Black rubber tires stay black regardless of part color
- Motor buttons/labels keep their original colors
- Brain screen areas keep their colors
- Only "main color" areas change when you set part color in MPD

### In Shader (`normal_lighting_shader.py`)

The fragment shader detects white vertex colors:
- White areas (>0.95 on all channels) → Use entity color from MPD
- Non-white areas → Use preserved vertex color

## Usage

### Step 1: Convert LDraw Parts to GLB (Windows)

```powershell
# Delete existing GLBs to force reconversion
Remove-Item models\parts\*.glb

# Run Blender conversion
blender --background --python tools/cad/blender_ldraw_to_glb_vertex_colors.py
```

Configuration (edit at top of script):
- `LDRAW_LIBRARY`: Path to VEX IQ LDraw library
- `INPUT_DIR`: Path to parts folder
- `OUTPUT_DIR`: Destination for GLB files

### Step 2: Render LDraw Models (WSL/Linux)

```bash
python tools/cad/render_ldraw_model.py models/your_robot.mpd
```

Options:
- `-v, --verbose`: Print verbose debug output
- `--no-shader`: Disable custom shader (for debugging)
- `--no-rotation`: Disable rotation matrix (for debugging)

## LDraw Color Codes

From LDConfig.ldr (normalized to 0-1):

| Code | Color | RGB |
|------|-------|-----|
| 0 | Black | 0.13, 0.13, 0.13 |
| 14 | Yellow | 1.0, 0.84, 0.0 |
| 15 | White | 1.0, 1.0, 1.0 |
| 16 | Main Color | (colorable) |
| 70 | VEX Black | 0.15, 0.16, 0.16 |
| 71 | VEX Light Gray | 0.70, 0.71, 0.70 |
| 73 | VEX Red | 0.82, 0.15, 0.19 |
| 74 | VEX Green | 0.00, 0.59, 0.22 |
| 75 | VEX Blue | 0.00, 0.47, 0.78 |
| 76 | VEX Yellow | 1.00, 0.80, 0.00 |
| 256 | Rubber Black | 0.13, 0.13, 0.13 |

## Directory Structure

```
models/
├── parts/             # GLB parts with vertex colors (colorable + preserved)
├── *.mpd              # Robot model files
└── *.ldr              # Robot model files
```

## Part Number Reference

VEX IQ parts follow this naming: `228-XXXX-YYY.dat`

| Part Number | Description |
|-------------|-------------|
| 228-2500-001 to 016 | 1-wide Beams |
| 228-2500-017 to 030 | 2-wide Beams |
| 228-2500-208 | 44mm Wheel Hub |
| 228-2540 | Robot Brain |
| 228-2540c02 | Brain with Battery |

## Shader Details

The custom shader provides:

1. **Headlight-style lighting**: Light comes from camera direction, consistent from any angle
2. **Normal-based shading**: Faces pointing at camera are brighter (0.95), away are darker (0.7)
3. **Color preservation**: Non-white vertex colors are used directly; white areas take entity color

## Generating Robot Definition Files

The `generate_robot_def.py` tool creates a `.robotdef` YAML file that describes a robot's structure:

```bash
python tools/cad/generate_robot_def.py models/ClawbotIQ.mpd
python tools/cad/generate_robot_def.py models/ClawbotIQ.mpd -v  # verbose
python tools/cad/generate_robot_def.py models/ClawbotIQ.mpd -o custom.robotdef
```

### What it generates

The tool parses an LDraw MPD file and produces:

1. **Submodel hierarchy** - Parent/child relationships between parts (e.g., Arm → FingerA, FingerB)
2. **Special part detection** - Automatically identifies:
   - Wheels/tires (228-2500-208, 228-2500-209, etc.)
   - Motors (228-2560)
   - Brain (228-2540, 228-2540c02)
   - Sensors (touch, color, gyro, distance, etc.)
3. **Position data** - Where each submodel is placed
4. **Kinematics placeholders** - Ready for manual configuration

### Extending the definition

After generation, manually fill in kinematics for articulated parts:

```yaml
Arm.ldr:
  position: [80.0, -29.05, 18.242]
  parent: ClawbotIQ.ldr
  kinematics:
    rotation_axis: [1, 0, 0]      # Rotates around X axis
    rotation_origin: [0, 0, 0]    # Pivot point
    rotation_limits: [-45, 90]    # Min/max degrees
```

Configure wheel roles for drivetrain simulation:

```yaml
wheels:
  - submodel: LeftSideDrive.ldr
    role: left_drive
    diameter_mm: 44
  - submodel: RightSideDrive.ldr
    role: right_drive
    diameter_mm: 44
```

## Troubleshooting

### Colors look wrong
- Re-export GLB files with the vertex color script
- Ensure shader is applied: `entity.shader = normal_lighting_shader`

### Part appears all one color
- Check that vertex colors exported correctly
- Verify the part has color 16 areas (check in LDCad)

### Blender can't find WSL files
- Use full UNC path: `\\wsl$\Ubuntu-24.04\home\...`
- Ensure WSL is running
