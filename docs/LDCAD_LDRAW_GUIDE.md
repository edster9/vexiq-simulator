# LDCad and LDraw for VEX IQ - Complete Guide

This guide provides detailed information about using LDCad for VEX IQ robot design, based on research and the fact that many VEX IQ teams use this workflow.

---

## Why Teams Use LDCad for VEX IQ

LDCad is a popular choice among VEX IQ teams because:

1. **Free and powerful** - No cost, professional-grade features
2. **Parts snapping** - Parts automatically align when moved close enough
3. **Superior rendering** - High-quality images for documentation
4. **Flexible parts tool** - Create rubber bands, cables, and chains
5. **SnapCAD compatibility** - Models work in both programs
6. **Step-by-step instructions** - Export assembly documentation
7. **Community support** - Active VEX IQ community using it

---

## LDraw File Format Fundamentals

LDraw is the underlying file format system that both SnapCAD and LDCad use. Understanding these formats is key to working with VEX IQ CAD files.

### File Extensions

| Extension | Name | Purpose |
|-----------|------|---------|
| **.dat** | Part File | Defines individual parts (beams, plates, gears, etc.) |
| **.ldr** | Model File | Contains a robot built from parts |
| **.mpd** | Multi-Part Document | Combines multiple .ldr files into one archive |

### .DAT Files (Parts)

DAT files define individual VEX IQ parts using primitive geometry and references to sub-parts.

**Structure:**
```
0 Part Name
0 Name: filename.dat
0 Author: Author Name
0 !LDRAW_ORG Part ...

1 <color> <x> <y> <z> <transform matrix> <subpart.dat>
4 <color> <x1 y1 z1> <x2 y2 z2> <x3 y3 z3> <x4 y4 z4>
```

- Line type `0` = Metadata/comments
- Line type `1` = Part reference (with position, rotation, and color)
- Line type `4` = Quadrilateral polygon

**Example:** A beam might reference stud primitives and box primitives to construct the shape.

### .LDR Files (Models)

LDR files contain your robot design - a collection of positioned parts.

**Structure:**
```
0 Robot Name
0 Name: myrobot.ldr
0 Author: Team Name

1 16 0 0 0 1 0 0 0 1 0 0 0 1 228-2500-014.dat
1 16 0 0 50 1 0 0 0 1 0 0 0 1 228-2540.dat
...
```

Each line type `1` places a part at a specific position with a transformation matrix.

**Color Codes:**
- `16` = Main color (inherits from parent or uses default)
- Specific colors: Red=4, Green=2, Blue=1, Yellow=14, etc.

### .MPD Files (Multi-Part Documents)

MPD files combine multiple models/subassemblies into one file. This is the recommended format for sharing complete robots.

**Structure:**
```
0 FILE mainmodel.ldr
0 Robot Main Assembly
1 16 0 0 0 1 0 0 0 1 0 0 0 1 chassis.ldr
1 16 0 100 0 1 0 0 0 1 0 0 0 1 arm.ldr

0 FILE chassis.ldr
0 Chassis Subassembly
1 16 0 0 0 1 0 0 0 1 0 0 0 1 228-2500-014.dat
...

0 FILE arm.ldr
0 Arm Subassembly
...
```

Key points:
- `0 FILE <name>` separates each subfile
- First file is the main model
- Other files are only rendered if referenced by the main model

---

## Setting Up LDCad for VEX IQ

### Option 1: Install LDCad for VEX (Recommended)

If you have SnapCAD installed or want the full VEX IQ experience:

1. **Download LDCad for VEX installer:**
   - Go to: https://www.philohome.com/vexldcad/ldcad4vex.htm
   - Download: `LDCadVEX-1-5-Win-32.exe` (installer) or `LDCadVEX.zip` (portable)

2. **Run the installer:**
   - If you have SnapCAD: Point installer to SnapCAD folder (usually `C:\Program Files(x86)\VEX Robotics\SnapCAD`)
   - If no SnapCAD: Download parts separately (see below)

3. **Launch LDCad and verify parts load**

### Option 2: Manual Setup (Without SnapCAD)

1. **Download VEX IQ LDraw parts:**
   - Unofficial Parts: https://www.philohome.com/vexldraw/vexldraw.htm
   - Download: `VexLdrawParts.zip`

2. **Extract to a folder** (e.g., `C:\VEX_LDraw\`)

3. **Download standard LDCad:**
   - Go to: http://www.melkert.net/LDCad

4. **Configure LDCad:**
   - On first launch, point to your parts folder
   - Set up parts search paths in preferences

### Option 3: Unofficial Parts Updates

The official parts libraries may be outdated. Get newer parts:

1. **Download unofficial SnapCAD parts:**
   - https://www.philohome.com/snapcadunoff/snapcadpartsunoff.htm
   - Download: `snapcadunoff.zip`

2. **Extract and merge:**
   - Unzip contents into your SnapCAD or LDCad for VEX folder
   - This adds parts released after the official library freeze

**Note:** The unofficial library includes:
- Axles and Spacers
- Beams and Plates
- Pins and Standoffs
- Connectors
- Wheels and Tires
- Gears and Motion
- Control System parts
- Panels and Special Beams

---

## LDCad vs SnapCAD Comparison

| Feature | SnapCAD | LDCad |
|---------|---------|-------|
| **Learning Curve** | Easy | Moderate |
| **Interface** | Beginner-friendly | More complex |
| **Parts Snapping** | Basic | Advanced (proximity snap) |
| **Image Quality** | Good | Superior |
| **Flexible Parts** | No | Yes (rubber bands, cables) |
| **System Requirements** | Very low (Win95+) | Higher |
| **File Compatibility** | .ldr, .mpd | .ldr, .mpd (same) |
| **Updates** | Discontinued | Community maintained |
| **Build Instructions** | Built-in | Available |

**Key Insight:** Models are fully compatible between both programs. You can:
- Start in SnapCAD (easier)
- Open in LDCad for advanced editing
- Share .ldr/.mpd files with others using either tool

---

## VEX IQ Parts Library Sources

### 1. Official SnapCAD (Built-in)
- **Status:** No longer updated by VEX
- **Content:** Core VEX IQ parts through ~2020
- **Location:** `C:\Program Files(x86)\VEX Robotics\SnapCAD\`

### 2. Unofficial LDraw Library (Philo)
- **URL:** https://www.philohome.com/vexldraw/vexldraw.htm
- **Status:** Legacy (not updated since 2018)
- **Content:** Most VEX IQ parts through Summer 2014 Refresh
- **Download:** `VexLdrawParts.zip`
- **Note:** Author recommends transitioning to SnapCAD library

### 3. Unofficial SnapCAD Updates (Philo)
- **URL:** https://www.philohome.com/snapcadunoff/snapcadpartsunoff.htm
- **Status:** Community maintained
- **Last Updated:** January 19, 2018
- **Content:** Newer parts not in official releases
- **Download:** `snapcadunoff.zip`

### 4. LPub3D Bundle
- **URL:** https://trevorsandy.github.io/lpub3d/
- **Info:** LPub3D (instruction generator) includes VEX IQ parts
- **Use Case:** Creating step-by-step build instructions

---

## VEX IQ Part Naming Convention

VEX IQ LDraw parts follow the naming pattern:
```
228-XXXX-YYY.dat
```

Where:
- `228` = VEX IQ product line prefix
- `XXXX` = Category code
- `YYY` = Part variant

**Common categories:**
- `2500` = Structural parts (beams, plates)
- `2540` = Electronics (Brain, motors, sensors)
- Other categories for gears, wheels, etc.

**Examples:**
- `228-2500-014.dat` = 1x16 Beam
- `228-2500-011.dat` = 1x12 Beam
- `228-2540.dat` = VEX IQ Brain
- `228-2500-214.dat` = 36 Tooth Gear

---

## Integration with Our Simulator Project

### Current Pipeline
Our simulator uses:
```
STEP files --> FreeCAD --> OBJ --> Blender --> GLB --> Ursina
```

### Potential LDraw Integration

LDraw files could be useful for:

1. **Robot Assembly Reference**
   - Teams can export their LDCad designs
   - We can parse .ldr files to understand part placement
   - Auto-generate simulator robots from LDCad models

2. **Parts Mapping**
   - Create a mapping: LDraw part numbers --> GLB files
   - Example: `228-2500-014.dat` --> `1x16_Beam.glb`

3. **Export from LDCad**
   - LDCad can export to various formats
   - Could potentially export OBJ for our pipeline

### Future Possibilities

If we implement LDraw import:
```python
# Conceptual LDraw importer
def load_ldr_file(filepath):
    """Load a .ldr file and create simulator entities."""
    parts = parse_ldr(filepath)
    for part in parts:
        part_number = part['filename']  # e.g., "228-2500-014.dat"
        glb_file = PART_MAP.get(part_number)
        if glb_file:
            entity = Entity(
                model=glb_file,
                position=part['position'],
                rotation=part['rotation']
            )
```

---

## Resources and Links

### Primary Resources
- **LDCad for VEX IQ:** https://www.philohome.com/vexldcad/ldcad4vex.htm
- **Unofficial LDraw Parts:** https://www.philohome.com/vexldraw/vexldraw.htm
- **Unofficial SnapCAD Parts:** https://www.philohome.com/snapcadunoff/snapcadpartsunoff.htm
- **Official LDCad:** http://www.melkert.net/LDCad

### LDraw Documentation
- **File Format Spec:** https://www.ldraw.org/article/218.html
- **MPD Specification:** https://www.ldraw.org/article/47.html
- **LDraw Wiki - DAT:** https://wiki.ldraw.org/wiki/DAT
- **LDraw Wiki - LDR:** https://wiki.ldraw.org/wiki/LDR
- **LDraw Wiki - MPD:** https://wiki.ldraw.org/wiki/MPD

### Official VEX Resources
- **SnapCAD Download:** https://www.vexrobotics.com/iq/downloads/cad-snapcad
- **SnapCAD Repository:** https://www.vexrobotics.com/iq/downloads/cad-snapcad/snapcad-repository
- **VEX Build Instructions:** https://www.vexrobotics.com/iq/downloads/build-instructions

### Community Resources
- **VEX Forum - LDCad Discussion:** https://www.vexforum.com/t/ldcad-for-vex-iq/2279
- **Student Robotics Education:** https://www.studentroboticseducation.com/vex-iq-ldcad-opt/
- **BuildIn3D VEX IQ Models:** https://platform.buildin3d.com/instructions

---

## Key Takeaways

1. **LDraw is the format, LDCad/SnapCAD are the tools**
   - Both use .ldr/.mpd files
   - Parts are stored as .dat files
   - Files are cross-compatible

2. **Teams use LDCad because:**
   - More powerful than SnapCAD
   - Better for documentation
   - Active community support
   - Handles complex assemblies better

3. **Parts libraries exist but are somewhat dated:**
   - Official SnapCAD library is frozen
   - Philo's unofficial updates add newer parts
   - For newest parts, may need to create custom .dat files

4. **LDraw files are NOT STEP files:**
   - LDraw = LEGO-style building block format
   - STEP = Professional CAD interchange format
   - LDCad cannot directly import STEP files
   - VEX provides both formats separately

5. **For our simulator:**
   - We can potentially import .ldr files in the future
   - Would need a part number --> GLB mapping
   - Allows teams to design in LDCad, simulate in our tool

---

*Guide compiled: January 2025*
*Based on research from Philo's website, LDraw.org, and VEX community resources*
