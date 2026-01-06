# SnapCAD to Ursina Render Pipeline

This document outlines the pathways to convert SnapCAD/LDraw robot models into formats renderable by Ursina (Panda3D).

## Overview

SnapCAD uses the **LDraw** file format, an open standard originally created for LEGO CAD software. VEX IQ parts have been modeled in this format, making SnapCAD files compatible with various LDraw tools.

### File Formats

| Extension | Description |
|-----------|-------------|
| `.ldr` | LDraw model file (single model) |
| `.mpd` | Multi-Part Document (assembly with submodels) |
| `.dat` | LDraw part definition file |

### Why SnapCAD/LDraw?

| Advantage | Description |
|-----------|-------------|
| **Colors included** | Parts have color definitions (unlike STEP) |
| **Complete assemblies** | Full robots, not individual parts |
| **Submodels** | Articulated parts defined as subassemblies |
| **Community models** | SnapCAD Repository has downloadable robots |
| **Open format** | Well-documented, many tools available |

---

## Pipeline Options

### Option 1: Blender Pipeline (Recommended)

```
SnapCAD (.ldr/.mpd) → Blender → glTF (.glb) → Ursina
```

**Tools Required:**
- Blender 2.82+ (Windows version available at `/mnt/c/Program Files/Blender Foundation/Blender 5.0/`)
- [ImportLDraw/ExportLDraw](https://github.com/cuddlyogre/ExportLDraw) Blender addon
- LDraw parts library (included with SnapCAD)

**Process:**
1. Install ImportLDraw addon in Blender
2. Import .ldr/.mpd file (File → Import → LDraw)
3. Run material fix script (see below)
4. Export to glTF 2.0 (.glb format)
5. Load in Ursina

**Material Fix Script (Blender Python):**
```python
import bpy

for mat in bpy.data.materials:
    if mat.node_tree:
        try:
            output = mat.node_tree.nodes["Material Output"]
            group = mat.node_tree.nodes["Group"]
            group2 = mat.node_tree.nodes["Group.001"]
            r,g,b,a = group.inputs['Color'].default_value
            bsdf = mat.node_tree.nodes.new(type="ShaderNodeBsdfPrincipled")
            bsdf.inputs["Base Color"].default_value = (r,g,b,a)
            mat.node_tree.links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
            mat.node_tree.nodes.remove(group)
            mat.node_tree.nodes.remove(group2)
        except:
            pass
```

**Ursina Loading:**
```python
from ursina import *

app = Ursina()

# Requires panda3d-gltf: pip install panda3d-gltf
robot = Entity(model='robot.glb', scale=0.01)

app.run()
```

**Pros:**
- Full color/material preservation
- Can decimate in Blender before export
- Manual control over optimization
- Blender's powerful editing tools available

**Cons:**
- Manual process (unless scripted)
- Requires Blender installation
- Complex material nodes need fixing

---

### Option 2: Online Converters

```
SnapCAD (.ldr/.mpd) → Online Service → OBJ/glTF → Ursina
```

**Services:**

#### MakerBrane
- **URL:** https://beta.makerbrane.com/tools/ldraw-viewer/
- **Features:** View LDraw files online, export to STL/glTF/OBJ
- **Limitation:** May require account for exports

#### 3DPEA
- **URL:** https://www.3dpea.com/en/convert/LDraw-to-OBJ
- **Formats:** LDraw → GLB, GLTF 1.0, GLTF 2.0, OBJ
- **Limitation:** File size limits, no batch processing

#### FabConvert
- **URL:** https://fabconvert.com/convert/ldraw/to/obj
- **Features:** Free online conversion

**Pros:**
- No software installation needed
- Quick for single files

**Cons:**
- Manual upload/download
- Potential file size limits
- No batch automation
- Quality may vary

---

### Option 3: LDView Export

```
SnapCAD (.ldr/.mpd) → LDView → POV-Ray/3DS/STL → (further conversion) → Ursina
```

**Tool:** [LDView](https://tcobbs.github.io/ldview/)

**Export Formats:**
- POV-Ray (ray tracing)
- 3DS (3D Studio)
- STL (mesh)

**Pros:**
- Native LDraw viewer
- Good rendering quality

**Cons:**
- Limited export formats (no glTF/OBJ direct)
- Additional conversion step needed

---

### Option 4: Python Direct Parsing

```
SnapCAD (.ldr/.mpd) → Python (pyldraw) → Custom mesh generation → Ursina
```

**Libraries:**

#### pyldraw (Recommended)
- **GitHub:** https://github.com/michaelgale/pyldraw
- **Install:** `pip install pyldraw` or clone from GitHub
- **Features:** Parse LDraw files, access part geometry, colors, transformations

#### python-ldraw
- **GitHub:** https://github.com/rienafairefr/python-ldraw
- **PyPI:** `pip install python-ldraw`
- **Features:** Create and read LDraw files, library access

#### LDRParser
- **GitHub:** https://github.com/JoshTheDerf/LDRParser
- **Features:** Recursive parser, outputs Python dict or JSON

**Example (pyldraw):**
```python
from pyldraw import LDRFile

# Parse LDraw file
model = LDRFile.from_file("robot.ldr")

# Access parts
for part in model.parts:
    print(f"Part: {part.name}, Color: {part.color}, Position: {part.position}")
```

**Pros:**
- Full programmatic control
- Can integrate directly into our pipeline
- Batch processing
- Custom optimization possible

**Cons:**
- Need to generate mesh geometry ourselves
- More development work
- Need LDraw parts library for geometry data

---

### Option 5: Automated Blender Script

```
SnapCAD (.ldr/.mpd) → Blender (headless) → glTF → Ursina
```

**Concept:** Create a Python script that runs Blender in background mode to automate conversion.

**Script Structure:**
```python
#!/usr/bin/env python3
"""
LDraw to glTF Converter using Blender
"""

import subprocess
import sys

BLENDER = "/mnt/c/Program Files/Blender Foundation/Blender 5.0/blender.exe"

def convert_ldraw_to_gltf(input_ldr, output_glb):
    """Convert LDraw file to glTF using Blender."""

    blender_script = f'''
import bpy

# Clear scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# Import LDraw
bpy.ops.import_scene.importldraw(filepath="{input_ldr}")

# Fix materials
for mat in bpy.data.materials:
    if mat.node_tree:
        try:
            output = mat.node_tree.nodes["Material Output"]
            group = mat.node_tree.nodes["Group"]
            r,g,b,a = group.inputs['Color'].default_value
            bsdf = mat.node_tree.nodes.new(type="ShaderNodeBsdfPrincipled")
            bsdf.inputs["Base Color"].default_value = (r,g,b,a)
            mat.node_tree.links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
        except:
            pass

# Export glTF
bpy.ops.export_scene.gltf(filepath="{output_glb}", export_format='GLB')
'''

    # Run Blender in background
    subprocess.run([
        BLENDER, "--background", "--python-expr", blender_script
    ])

if __name__ == "__main__":
    convert_ldraw_to_gltf(sys.argv[1], sys.argv[2])
```

**Pros:**
- Automated batch processing
- Consistent output quality
- Uses proven Blender pipeline

**Cons:**
- Requires Blender + ImportLDraw addon
- Slower than native parsing
- Windows/WSL path handling needed

---

## Comparison Matrix

| Option | Colors | Automation | Quality | Setup Complexity | Speed |
|--------|--------|------------|---------|------------------|-------|
| **Blender Pipeline** | ✅ Yes | ⚠️ Manual/Scriptable | ✅ High | Medium | Medium |
| **Online Converters** | ⚠️ Varies | ❌ Manual | ⚠️ Varies | Low | Fast |
| **LDView** | ✅ Yes | ❌ Manual | ✅ High | Low | Fast |
| **Python Direct** | ✅ Yes | ✅ Full | ⚠️ Custom | High | Fast |
| **Blender Script** | ✅ Yes | ✅ Full | ✅ High | Medium | Medium |

---

## Recommended Approach

### For Development/Testing
**Option 1 (Manual Blender)** - Quick to test, verify quality

### For Production Pipeline
**Option 5 (Automated Blender Script)** - Best balance of quality and automation

### For Advanced Integration
**Option 4 (Python Direct)** - Full control, but more work

---

## Implementation Steps

### Phase 1: Proof of Concept
1. Download sample robot from SnapCAD Repository
2. Install ImportLDraw in Blender
3. Manually convert to glTF
4. Test loading in Ursina
5. Verify colors and geometry

### Phase 2: Automation
1. Create Blender conversion script
2. Handle WSL/Windows path conversion
3. Add decimation step for optimization
4. Test batch conversion

### Phase 3: Integration
1. Add conversion tool to `tools/` directory
2. Create robot model loader for Ursina
3. Handle articulation (separate meshes for moving parts)
4. Implement color mapping

---

## Resources

### SnapCAD Repository
- **URL:** https://www.vexrobotics.com/iq/downloads/cad-snapcad/snapcad-repository
- **Content:** Community-designed robots with build instructions

### LDraw Parts Library
- **URL:** https://www.ldraw.org/parts/latest-parts.html
- **Note:** VEX IQ parts included with SnapCAD installation

### Tools
- [ImportLDraw Blender Addon](https://github.com/cuddlyogre/ExportLDraw)
- [LDView](https://tcobbs.github.io/ldview/)
- [pyldraw](https://github.com/michaelgale/pyldraw)
- [MakerBrane](https://beta.makerbrane.com/tools/ldraw-viewer/)

### Tutorials
- [Panda3D LDraw to glTF Tutorial](https://discourse.panda3d.org/t/tutorial-how-to-import-virtual-lego-models-in-panda3d-ldraw-to-gltf/29470)

---

*Document created: January 2025*
