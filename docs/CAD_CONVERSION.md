# CAD Conversion Guide

This document describes how to convert VEX IQ CAD files (STEP format) to 3D models (OBJ format) for use in the simulator.

## Overview

VEX provides official CAD files for all VEX IQ parts in STEP format. These need to be converted to OBJ format for use with the Ursina 3D engine.

**Pipeline:** STEP (CAD) → OBJ (Mesh) → Ursina rendering

## Prerequisites

### 1. Install FreeCAD (STEP file support)

FreeCAD is used to read STEP files and convert them to mesh format.

```bash
# Add FreeCAD PPA (Ubuntu 24.04)
sudo add-apt-repository -y ppa:freecad-maintainers/freecad-stable

# Update and install
sudo apt-get update
sudo apt-get install -y freecad-python3
```

Verify installation:
```bash
python3 -c "import sys; sys.path.insert(0, '/usr/lib/freecad/lib'); import FreeCAD; print('FreeCAD OK')"
```

### 2. Download VEX IQ CAD Files

#### VEX IQ Parts Pack
Download the official VEX IQ parts pack from:
- **Official VEX CAD Page:** https://www.vexrobotics.com/iq/downloads/cad-snapcad

The parts pack contains ~470 STEP files for all VEX IQ structural parts.

#### Rapid Relay Field CAD (2024-2025 Season)
Download the competition field CAD from:
- **VEX Competition Page:** https://www.vexrobotics.com/iq/competition/viqc-current-game

This includes the field elements and game pieces (6" padded balls).

## Conversion Process

### Using the Conversion Script

The conversion script is located at `tools/freecad_convert_step.py`.

#### Convert a Single File

```bash
python3 tools/freecad_convert_step.py input.step output.obj
```

Example:
```bash
python3 tools/freecad_convert_step.py \
    "/tmp/vex-parts/Tire (200 mm Travel) (228-2500-209).step" \
    simulator/models/parts/tire_200mm.obj
```

#### Batch Convert a Directory

```bash
python3 tools/freecad_convert_step.py /path/to/step/files/ /path/to/output/
```

### Output Format

The script produces OBJ files with:
- Tessellated mesh geometry
- Automatic vertex and face optimization
- Units preserved from STEP file (typically millimeters for VEX parts)

### Quality Settings

The default mesh quality is `0.1` (LinearDeflection). Lower values produce finer meshes but larger files:

| Quality | Use Case | Typical File Size |
|---------|----------|-------------------|
| 0.5 | Preview, low-poly | ~100KB |
| 0.1 | Standard (default) | ~500KB |
| 0.01 | High detail | ~2MB+ |

## Using Models in Ursina

### Loading OBJ Files

```python
from ursina import *

# VEX parts are in millimeters, scale down for Ursina (feet)
# 1 foot = 304.8mm, so scale = 1/304.8 ≈ 0.00328
MM_TO_FEET = 1 / 304.8

tire = Entity(
    model='simulator/models/parts/tire_200mm.obj',
    scale=MM_TO_FEET,
    position=(0, 0.5, 0),
    color=color.gray
)
```

### Model Caching

Ursina automatically caches OBJ files as `.bam` (Panda3D binary) format in `models_compressed/` for faster subsequent loads.

## Directory Structure

```
simulator/
├── models/
│   └── parts/           # Converted OBJ files
│       ├── tire_200mm.obj
│       ├── tire_100mm.obj
│       ├── hub_32mm.obj
│       ├── beam_1x4.obj
│       └── beam_1x10.obj
tools/
├── freecad_convert_step.py   # Main conversion script
└── convert_vex_parts.sh      # Batch conversion helper (optional)
```

## Key VEX IQ Parts

### Commonly Needed Parts

| Part Name | File Pattern | Description |
|-----------|--------------|-------------|
| 200mm Tire | `Tire (200 mm Travel)*.step` | Large travel wheel tire |
| 100mm Tire | `Tire (100 mm Travel)*.step` | Medium travel wheel tire |
| 32mm Hub | `*32.2mm Diameter Hub*.step` | Wheel hub |
| 1x4 Beam | `1x4 Beam*.step` | Basic structural beam |
| 1x10 Beam | `1x10 Beam*.step` | Longer structural beam |

### Finding Parts

List available STEP files:
```bash
ls /path/to/vex-parts/*.step | grep -i "tire\|wheel\|beam\|motor"
```

## Troubleshooting

### Import Error: FreeCAD modules not available

Ensure the FreeCAD library path is in your Python path:
```python
import sys
sys.path.insert(0, '/usr/lib/freecad/lib')
import FreeCAD
```

### Empty or Invalid Output

- Check that the STEP file exists and is readable
- Verify FreeCAD can load the file: `freecad input.step`
- Some complex assemblies may need to be simplified

### WSL2 Display Issues

When running in WSL2, you may see X11 warnings. These don't affect conversion:
```
Xlib: extension "XFree86-DGA" missing on display ":0"
```

## References

- **VEX IQ CAD Resources:** https://kb.vex.com/hc/en-us/articles/360044338912-CAD-Resources-for-VEX-IQ
- **FreeCAD Documentation:** https://wiki.freecad.org/
- **Ursina Engine:** https://www.ursinaengine.org/
- **STEP File Format:** ISO 10303-21 (STEP-File)
