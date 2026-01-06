# VEX IQ CAD to GLB Conversion Pipeline

This document describes the complete pipeline for converting VEX IQ STEP CAD files to optimized GLB models for use in the Ursina-based simulator.

## Overview

```
STEP (VEX CAD) → FreeCAD (tessellation) → OBJ → Blender (decimate + smooth) → GLB → Ursina
```

### Why This Pipeline?

| Step | Tool | Reason |
|------|------|--------|
| STEP → OBJ | FreeCAD | Better tessellation than Blender's STEP importer |
| OBJ → GLB | Blender | Decimation + weighted normal for smooth low-poly |
| GLB → Render | Ursina | Fast loading, runtime color control |

## Prerequisites

### WSL2 (Ubuntu)
```bash
# FreeCAD for STEP conversion
sudo add-apt-repository ppa:freecad-maintainers/freecad-stable
sudo apt update
sudo apt install freecad

# Python dependencies
pip install trimesh
```

### Windows
- **Blender 5.0+**: https://www.blender.org/download/
- **Python 3.12+** with `panda3d-gltf`:
  ```powershell
  pip install panda3d-gltf
  ```

## Directory Structure

```
models/
├── electronics/
│   ├── step/      # Original STEP files (11 files)
│   ├── obj/       # FreeCAD tessellated OBJ (11 files)
│   └── glb/       # Final GLB for Ursina (11 files)
└── parts/
    ├── step/      # Original STEP files (441 files)
    ├── obj/       # FreeCAD tessellated OBJ (441 files)
    └── glb/       # Final GLB for Ursina (441 files)
```

## Step 1: STEP to OBJ (FreeCAD)

FreeCAD provides superior CAD tessellation compared to Blender's STEP importer.

### Single File Conversion
```bash
source venv/bin/activate
python3 tools/freecad_convert_step.py input.step output.obj
```

### Batch Conversion (All Files)
```bash
source venv/bin/activate
python3 tools/batch_convert_step.py
```

This converts all STEP files in `models/*/step/` to OBJ in `models/*/obj/`.

### Quality Settings

The FreeCAD converter uses `LinearDeflection=0.01` for high-quality tessellation:
- Lower values = more polygons, finer detail
- Higher values = fewer polygons, faster conversion

## Step 2: OBJ to GLB (Blender)

Blender applies decimation and smoothing to create game-ready models.

### Single File Test (Windows PowerShell)
```powershell
cd C:\Users\edste\vexiq-test
& "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" --background --python blender_test_single.py
```

### Batch Conversion (All Files)
```powershell
cd C:\Users\edste\vexiq-test
& "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" --background --python blender_batch_all.py
```

### Blender Processing Steps

1. **Import OBJ** - Load the FreeCAD-tessellated mesh
2. **Decimate Modifier** - Reduce polygon count (ratio: 0.19 = ~80% reduction)
3. **Shade Smooth** - Smooth vertex normals
4. **Weighted Normal Modifier** - Better normal distribution for smooth surfaces
5. **Export GLB** - Binary glTF format for fast loading

### Decimation Guidelines

| Part Type | Visibility | Decimate Ratio | Target Faces |
|-----------|------------|----------------|--------------|
| Brain/Controller | Hidden | 0.15-0.20 | 5-8K |
| Motors | Hidden | 0.15-0.20 | 3-5K |
| Beams/Plates | Visible | 0.20-0.30 | 500-2K |
| Wheels | Very visible | 0.15-0.20 | 2-5K |
| Gears | Sometimes visible | 0.20-0.25 | 1-3K |
| Small connectors | Barely visible | 0.25-0.35 | 200-500 |

## Step 3: Loading in Ursina

### Basic Usage
```python
from ursina import *
from ursina.shaders import lit_with_shadows_shader

app = Ursina()

# Load GLB model
part = Entity(
    model='models/parts/glb/1x6 Beam (228-2500-005).glb',
    scale=0.01,  # STEP files are in mm
    color=color.red,  # Apply color at runtime
)

# Required for proper material rendering
part.shader = lit_with_shadows_shader

# Lighting
sun = DirectionalLight()
sun.look_at(Vec3(1, -1, 1))

EditorCamera()
app.run()
```

### Runtime Color Control

GLB files have no embedded material - colors are applied in code:

```python
# Team colors
TEAM_RED = color.rgb(200, 50, 50)
TEAM_BLUE = color.rgb(50, 50, 200)

# Part type colors
COLORS = {
    'beam': color.rgb(180, 180, 180),    # Light grey
    'plate': color.rgb(160, 160, 160),   # Medium grey
    'motor': color.rgb(50, 50, 55),      # Dark grey
    'tire': color.rgb(30, 30, 30),       # Black
    'gear': color.rgb(140, 140, 140),    # Grey
}

# Apply to parts
chassis.color = TEAM_RED
motor.color = COLORS['motor']
```

## Performance Budget

| Scene Component | Faces | Notes |
|-----------------|-------|-------|
| Single robot | ~50K | 30-50 parts |
| 3 robots | ~150K | Competition scene |
| Field | ~5K | Simple geometry |
| **Total** | ~155K | Well under 500K limit |

Modern PCs handle 500K-1M faces easily at 60fps.

## Troubleshooting

### Model appears white in Ursina
- Ensure shader is applied: `entity.shader = lit_with_shadows_shader`
- Ensure DirectionalLight exists in scene
- Apply color explicitly: `entity.color = color.gray`

### Model has artifacts after decimation
- Increase decimate ratio (e.g., 0.19 → 0.25)
- Ensure Weighted Normal modifier is applied after Decimate
- Check that Shade Smooth is applied

### Blender can't find WSL files
- Use full UNC path: `\\wsl$\Ubuntu-24.04\home\...`
- Ensure WSL is running

### FreeCAD import fails
- Check FreeCAD is installed: `freecad --version`
- Verify library path in script matches installation

## File Sizes (After Conversion)

| Category | Files | OBJ Size | GLB Size | Reduction |
|----------|-------|----------|----------|-----------|
| Electronics | 11 | ~50 MB | 5.2 MB | 90% |
| Parts | 441 | ~400 MB | 44 MB | 89% |

## Tools Reference

| Script | Location | Purpose |
|--------|----------|---------|
| `batch_convert_step.py` | `tools/` | FreeCAD STEP → OBJ batch |
| `blender_batch_all.py` | Windows test dir | Blender OBJ → GLB batch |
| `blender_test_single.py` | Windows test dir | Single file Blender test |
| `test_glb.py` | Windows test dir | Ursina GLB viewer |

## Manual Blender Workflow

For fine-tuning individual parts:

1. **File → Import → Wavefront (.obj)**
2. Select object, **Add Modifier → Decimate**
   - Mode: Collapse
   - Ratio: 0.19 (adjust as needed)
3. **Apply** the modifier
4. **Right-click → Shade Smooth**
5. **Add Modifier → Weighted Normal**
   - Weight: 50
   - Keep Sharp: ✓
6. **Apply** the modifier
7. **File → Export → glTF 2.0 (.glb)**
   - Format: glTF Binary (.glb)
