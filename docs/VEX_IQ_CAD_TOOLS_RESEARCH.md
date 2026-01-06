# VEX IQ CAD Tools & Robot Design Research

This document summarizes research on official and community CAD tools for VEX IQ robot design.

## Executive Summary

VEX IQ has multiple CAD options, but **no single "official" tool** is mandated. VEX provides STEP files for all parts and supports multiple CAD platforms through sponsorships (Autodesk, PTC). The community has developed additional tools like SnapCAD and LDCad specifically for VEX IQ.

---

## Official VEX Resources

### 1. STEP Files (Official CAD)
- **Source:** [VEX Robotics Product Pages](https://www.vexrobotics.com)
- **Format:** STEP (.stp) - Universal ISO format
- **Compatibility:** SolidWorks, Autodesk Inventor, Fusion 360, Onshape, FreeCAD, and most CAD software
- **Status:** ✅ Actively maintained, new parts added with product releases

### 2. 3D Build Instructions (Cadasio)
- **Source:** [VEX IQ Build Instructions](https://www.vexrobotics.com/iq/downloads/build-instructions)
- **Platform:** [instructions.online](https://instructions.online/) (powered by Cadasio)
- **Features:** Interactive 3D step-by-step assembly instructions
- **Available Builds:**
  - Hero Bot for Mix & Match (2025-26)
  - Hero Bot for Rapid Relay (2024-25)
  - Hero Bot for Full Volume (2023-24)
  - BaseBot (foundation robot)
  - Transition builds (BaseBot + attachments)
- **Status:** ✅ Actively maintained, new Hero Bots each season

### 3. SnapCAD
- **Source:** [VEX CAD & SnapCAD Page](https://www.vexrobotics.com/iq/downloads/cad-snapcad)
- **Repository:** [SnapCAD Repository](https://www.vexrobotics.com/iq/downloads/cad-snapcad/snapcad-repository)
- **Format:** LDraw (.ldr, .mpd files)
- **Status:** ⚠️ **No longer supported** - VEX states: "SnapCAD is no longer supported. However, you can still download and use SnapCAD, but VEX is no longer making updates or adding new parts."
- **Features:**
  - Community-built solution for virtual VEX IQ models
  - Create printable, shareable step-by-step instructions
  - Free download, Windows 95+ compatible
  - Repository has community-designed robots

---

## Community & Third-Party Tools

### 1. LDCad for VEX IQ
- **Creator:** Roland Melkert (LDCad), adapted by Philippe "Philo" Hurbain
- **Website:** [philohome.com/vexldcad/ldcad4vex.htm](https://www.philohome.com/vexldcad/ldcad4vex.htm)
- **Format:** LDraw (compatible with SnapCAD files)
- **Status:** ✅ Community maintained

**Advantages over SnapCAD:**
- Parts snapping (automatic alignment)
- Superior image quality
- Flexible parts tool (rubber bands, cables, chain)
- More advanced modeling capabilities

**Disadvantages:**
- Steeper learning curve
- More complex interface

**Installation:**
1. With SnapCAD: Point installer to SnapCAD folder
2. Without SnapCAD: Download parts library separately

### 2. Onshape VEX IQ Parts Library
- **Source:** [Onshape VEX Libraries](https://www.onshape.com/en/blog/vex-iq-vex-v5-parts-libraries)
- **Creator:** Onshape Education Team (official)
- **Status:** ✅ Maintained by Onshape
- **Features:**
  - Cloud-based, browser accessible
  - Free with Education account
  - Configurable parts (adjustable beam lengths, etc.)
  - Collaborative real-time editing
  - Correct materials, weights, part numbers

### 3. Fusion 360 / Inventor Libraries
- **Source:** [Autodesk Education](https://www.autodesk.com/education/competitions/vex)
- **Libraries:**
  - Official Autodesk-created libraries
  - [VEX CAD Fusion 360 Library 2.0.0](https://www.vexforum.com/t/vex-cad-fusion-360-parts-library-2-0-0-release/120228) (community)
  - Purdue SIGBots libraries
- **Status:** ✅ Community maintained, updated with new parts

### 4. BuildIn3D / FLLCasts
- **Website:** [platform.buildin3d.com](https://platform.buildin3d.com/instructions?in_categories%5B%5D=4&in_categories%5B%5D=13)
- **Content:** 35+ VEX IQ 3D instructions
- **Examples:** Crane, Moon Rover, Bulldozer, Humanoid
- **Note:** Some content requires FLLCasts subscription

### 5. GrabCAD
- **Website:** [grabcad.com/library/tag/vex](https://grabcad.com/library/tag/vex)
- **Content:** Community-uploaded VEX robot designs
- **Formats:** Various CAD formats

---

## CAD Software Comparison for VEX IQ

| Software | Cost | Platform | VEX IQ Library | Best For |
|----------|------|----------|----------------|----------|
| **SnapCAD** | Free | Windows | Built-in | Beginners, quick builds |
| **LDCad** | Free | Windows | Via SnapCAD parts | Advanced LDraw users |
| **Onshape** | Free (Education) | Web browser | Official library | Teams, collaboration |
| **Fusion 360** | Free (Education) | Win/Mac | Community libraries | Full CAD workflow |
| **Inventor** | Free (Education) | Windows | Community libraries | Professional CAD |
| **SolidWorks** | Sponsorship | Windows | STEP import | Competition teams |
| **FreeCAD** | Free | All platforms | STEP import | Linux users |

---

## File Format Summary

| Format | Extension | Use Case | Notes |
|--------|-----------|----------|-------|
| **STEP** | .step, .stp | Universal CAD exchange | Official VEX format |
| **LDraw** | .ldr, .mpd | SnapCAD/LDCad | LEGO-compatible format |
| **OBJ** | .obj | 3D rendering/games | Mesh only, no materials |
| **STL** | .stl | 3D printing | Triangulated mesh |
| **glTF/GLB** | .gltf, .glb | Web/game engines | Modern 3D format |
| **COLLADA** | .dae | Interchange format | XML-based |

---

## Robot Design Sharing Platforms

### Official
1. **SnapCAD Repository** - Community VEX IQ designs with instructions
2. **VEX Build Instructions** - Official Hero Bots and educational builds

### Community
1. **VEX Forum** - [vexforum.com](https://www.vexforum.com/) - Active discussion, design sharing
2. **GrabCAD** - 3D model sharing platform
3. **BuildIn3D/FLLCasts** - 3D assembly instructions
4. **Student Robotics Education** - Competition robot archives

---

## Key Findings

### What VEX Officially Supports
1. **STEP files** for all parts (downloadable from product pages)
2. **3D Build Instructions** via Cadasio for official robots
3. **SnapCAD Repository** for community designs (but software is unsupported)

### What VEX Does NOT Officially Maintain
1. SnapCAD software itself (legacy, no updates)
2. Any specific CAD program preference (due to sponsor neutrality)
3. Community parts libraries for third-party CAD

### VEX Sponsor Considerations
> "Autodesk (makers of many CAD apps, including Fusion 360 and Inventor) is a big sponsor of VEX, and so is PTC (makers of Onshape). VEX can't show favoritism to one or the other, and supporting all CAD apps would be a never-ending task."

---

## Recommendations for Our Simulator Project

### For Parts Library
- Use official **STEP files** as source of truth
- Convert to OBJ/glTF for game engine rendering
- Apply decimation for performance

### For Robot Assembly Reference
- Download models from **SnapCAD Repository** (.ldr format)
- Use **LDCad** to view/edit LDraw files
- Reference **VEX 3D Build Instructions** for official designs

### For Colors/Materials
- VEX IQ standard colors: Light grey, dark grey, red, green, blue, yellow, orange
- Electronics: Green PCB, black plastic
- Reference Cadasio renders for visual style

---

## Sources

### Official VEX
- [VEX IQ CAD & SnapCAD](https://www.vexrobotics.com/iq/downloads/cad-snapcad)
- [VEX IQ Build Instructions](https://www.vexrobotics.com/iq/downloads/build-instructions)
- [CAD Resources for VEX IQ](https://kb.vex.com/hc/en-us/articles/360044338912-CAD-Resources-for-VEX-IQ)
- [SnapCAD Repository](https://www.vexrobotics.com/iq/downloads/cad-snapcad/snapcad-repository)

### Community Tools
- [LDCad for VEX IQ](https://www.philohome.com/vexldcad/ldcad4vex.htm)
- [Onshape VEX Libraries](https://www.onshape.com/en/blog/vex-iq-vex-v5-parts-libraries)
- [Autodesk VEX Resources](https://www.autodesk.com/education/competitions/vex)
- [Purdue SIGBots CAD Wiki](https://wiki.purduesigbots.com/vex-cad/cad-programs)

### VEX Forum Discussions
- [LDCad for VEX IQ](https://www.vexforum.com/t/ldcad-for-vex-iq/2279)
- [LDCad vs SnapCAD](https://www.vexforum.com/t/ldcad-vs-snapcad/88702)
- [CAD use for IQ](https://www.vexforum.com/t/cad-use-for-iq/81419)
- [Best free CAD software for VEX IQ](https://www.vexforum.com/t/best-free-cad-software-for-vex-iq/116029)

### Third-Party Platforms
- [BuildIn3D VEX IQ](https://platform.buildin3d.com/instructions?in_categories%5B%5D=4&in_categories%5B%5D=13)
- [GrabCAD VEX Library](https://grabcad.com/library/tag/vex)
- [Student Robotics Education](https://www.studentroboticseducation.com/)

---

*Research compiled: January 2025*
