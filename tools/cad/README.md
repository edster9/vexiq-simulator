# CAD Conversion Tools

This directory contains Blender scripts for converting LDraw VEX IQ parts to GLB format for use in the Ursina 3D engine.

## Prerequisites

1. **Blender** (tested with 4.x)
2. **ExportLDraw Blender Addon**: https://github.com/cuddlyogre/ExportLDraw
3. **VEX IQ LDraw Parts Library**: Download from LDraw.org or VEX forums

## Scripts

### blender_ldraw_to_glb.py

Batch converts all LDraw .dat part files to GLB format.

```bash
blender --background --python blender_ldraw_to_glb.py
```

**Configuration** (edit variables at top of script):
- `LDRAW_LIBRARY`: Path to VEX IQ LDraw library (contains `parts/`, `p/` folders)
- `INPUT_DIR`: Path to parts folder (usually `LDRAW_LIBRARY/parts`)
- `OUTPUT_DIR`: Destination for GLB files

### blender_ldraw_to_glb_optimized.py

Same as above but applies mesh optimization:
- **Decimate modifier** (50% face reduction by default)
- **Weighted Normal modifier** for improved shading

Produces smaller files at the cost of some detail. Adjust `DECIMATE_RATIO` (0.0-1.0) to control quality vs size.

### blender_ldraw_test_single.py

Interactive test script for importing a single LDraw part. Useful for:
- Testing the ExportLDraw addon setup
- Experimenting with import settings
- Manual export with custom settings

```bash
blender --python blender_ldraw_test_single.py
```

## Test Scripts (Ursina)

### test_robot_frame_ldraw.py

Renders a sample robot using original (non-decimated) GLB parts in Ursina. Demonstrates:
- Loading GLB parts with correct scale (SCALE=0.25)
- VEX IQ pitch calculations (12.7mm = 0.127 units)
- VEX IQ color palette from LDConfig.ldr
- Multiple robot instances with different team colors

### test_robot_frame_ldraw_optimized.py

Same as above but uses decimated parts from `models/ldraw_optimized/`.

## VEX IQ Color Palette

Colors from LDConfig.ldr (normalized to 0-1 for Ursina):

```python
VEX_BLACK = color.rgba(0.15, 0.16, 0.16, 1)
VEX_RED = color.rgba(0.82, 0.15, 0.19, 1)
VEX_GREEN = color.rgba(0.0, 0.59, 0.22, 1)
VEX_BLUE = color.rgba(0.0, 0.47, 0.78, 1)
VEX_YELLOW = color.rgba(1.0, 0.80, 0.0, 1)
VEX_WHITE = color.rgba(0.85, 0.85, 0.84, 1)
VEX_ORANGE = color.rgba(1.0, 0.40, 0.12, 1)
VEX_PURPLE = color.rgba(0.37, 0.15, 0.62, 1)
VEX_LIGHT_GRAY = color.rgba(0.70, 0.71, 0.70, 1)
VEX_MEDIUM_GRAY = color.rgba(0.54, 0.55, 0.55, 1)
VEX_DARK_GRAY = color.rgba(0.33, 0.35, 0.35, 1)
```

## Part Number Reference

VEX IQ parts follow this naming convention:

| Part Number | Description |
|-------------|-------------|
| 228-2500-001 to 016 | 1-wide Beams (1x2 to 1x20) |
| 228-2500-017 to 030 | 2-wide Beams (2x2 to 2x20) |
| 228-2500-034 to 045 | Plates (various sizes) |
| 228-2500-208 | 44mm Wheel Hub |
| 228-2500-211 | 65mm Wheel Hub |
| 228-2500-213 | 12 Tooth Gear |
| 228-2500-214 | 36 Tooth Gear |
| 228-2540 | Robot Brain |
| 228-2560 | Smart Motor |

## Notes

- LDraw units (LDU): 1 LDU = 0.4mm
- VEX IQ pitch: 12.7mm (0.5 inches) between holes
- GLB scale factor: 0.25 works well in Ursina
- Materials are stripped during conversion; colors applied at runtime
