# VEX IQ Simulator Roadmap

This document outlines the planned development phases for the VEX IQ Simulator. Contributions are welcome!

## Current State (v0.2)

- [x] Parse and execute `.iqpython` files
- [x] Virtual controller with mouse support
- [x] USB gamepad support (Xbox 360/One, Windows & Linux)
- [x] Motor visualization (velocity, direction)
- [x] Pneumatic indicators (extend/retract)
- [x] All 6 VEX IQ drive modes
- [x] Button callbacks (pressed/released)
- [x] WSL2 compatibility
- [x] **3D field visualization with Ursina engine**
- [x] **Robot movement in 3D world**
- [x] **Autonomous code testing (no gamepad required)**
- [x] **Cross-platform gamepad support (Windows/Linux)**

---

## Phase 1: Enhanced Simulation

### 1.1 Physics Simulation
- [ ] Motor acceleration/deceleration curves
- [ ] Inertia simulation for drivetrain
- [ ] Realistic stopping behavior (coast, brake, hold)
- [ ] Motor stall detection and current simulation

### 1.2 Sensor Simulation
- [ ] Distance sensor with configurable obstacles
- [ ] Color sensor with virtual color targets
- [ ] Bumper/touch sensor simulation
- [ ] Optical sensor (line following simulation)
- [ ] Inertial sensor (heading, rotation, acceleration)

### 1.3 Timing Improvements
- [ ] Accurate timing for `wait()` and `sleep()`
- [ ] Synchronized threads matching VEX IQ behavior
- [ ] Competition timer simulation (driver/autonomous periods)

---

## Phase 2: 2D Field Visualization

### 2.1 Top-Down Field View
- [ ] Render standard VEX IQ competition field
- [ ] Show robot position and orientation
- [ ] Display wheel rotation indicators
- [ ] Arm/mechanism position overlay

### 2.2 Field Interaction
- [ ] Draggable game objects (balls, cubes, rings)
- [ ] Scoring zone indicators
- [ ] Collision detection with field walls
- [ ] Starting position configuration

### 2.3 Path Visualization
- [ ] Record and display robot path history
- [ ] Autonomous routine visualization
- [ ] Odometry tracking display

---

## Phase 3: 3D World Simulation ✓ (In Progress)

### 3.1 3D Engine Integration ✓
- [x] Evaluate engines: **Ursina (built on Panda3D)** selected
- [x] Basic 3D field rendering (VEX IQ field with grid)
- [x] Camera controls (toggle views with 'C' key)
- [x] Multiple view modes (angled, overhead)

### 3.2 Robot Visualization (Partial)
- [x] Generic robot chassis model (placeholder cube)
- [x] Movement based on motor velocity
- [ ] Wheel animation (visual spinning)
- [ ] Arm/lift mechanism animation
- [ ] Claw/intake visualization

### 3.3 Physics Engine
- [x] Basic movement physics (velocity, turning)
- [x] Field boundary collision
- [ ] Rigid body physics (PyBullet integration)
- [ ] Game piece physics (balls, cubes rolling/stacking)
- [ ] Friction and weight simulation

---

## Phase 4: Robot Designer

### 4.1 Component Library
- [ ] VEX IQ structural parts catalog
- [ ] Motor models with accurate dimensions
- [ ] Sensor models with mounting points
- [ ] Wheel and gear options

### 4.2 Visual Builder
- [ ] Drag-and-drop part placement
- [ ] Snap-to-grid and alignment tools
- [ ] Part connection validation
- [ ] Real-time mass and balance calculation

### 4.3 Robot Configuration
- [ ] Define motor ports and positions
- [ ] Set gear ratios and wheel sizes
- [ ] Configure sensor placements
- [ ] Export configuration to `.iqpython` format

### 4.4 Design Validation
- [ ] Size constraint checking (fits in sizing box)
- [ ] Motor count limits
- [ ] Part count tracking
- [ ] Center of gravity visualization

---

## Phase 5: Advanced Features

### 5.1 Autonomous Development Tools
- [ ] Point-and-click autonomous path creation
- [ ] Path recording from manual driving
- [ ] Motion profiling tools
- [ ] PID tuning interface

### 5.2 Competition Simulation
- [ ] Full match simulation (autonomous + driver)
- [ ] Skills challenge mode
- [ ] Score calculation
- [ ] Match replay and analysis

### 5.3 Multi-Robot Support
- [ ] Two-robot alliance simulation
- [ ] Head-to-head competition mode
- [ ] Network play (two computers)

### 5.4 Learning Tools
- [ ] Step-by-step code execution (debugger)
- [ ] Variable inspector
- [ ] Sensor value visualization
- [ ] Code tutorials and challenges

---

## Technical Considerations

### 3D Engine Options

| Engine | Pros | Cons |
|--------|------|------|
| **PyBullet** | Great physics, Python native | Steeper learning curve |
| **Panda3D** | Full game engine, good docs | Larger dependency |
| **Godot + Python** | Modern, visual editor | Requires GDScript bridge |
| **Pygame + OpenGL** | Minimal dependencies | Manual 3D implementation |
| **Three.js (web)** | Cross-platform, no install | Requires web architecture |

### Current Implementation

- **3D Rendering**: Ursina engine (Python-friendly wrapper around Panda3D)
- **UI**: Ursina's built-in UI system with custom control panel
- **Gamepad**: pygame for cross-platform controller support
- **Next**: PyBullet for advanced physics simulation

### File Formats

- **Robot Design**: JSON-based format compatible with `.iqpython`
- **Field Layout**: JSON with object positions and properties
- **Autonomous Paths**: JSON waypoints with timing data

---

## Contributing

We welcome contributions! Here's how to help:

1. **Pick a task** from any phase above
2. **Open an issue** to discuss your approach
3. **Submit a PR** with your implementation

### Priority Areas (Help Wanted)

- [ ] Distance sensor simulation
- [ ] 2D field renderer
- [ ] PyBullet integration prototype
- [ ] Robot path recording

### Development Setup

```bash
git clone https://github.com/edster9/vexiq-simulator.git
cd vexiq-simulator
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development tools
```

---

## Version History

| Version | Status | Features |
|---------|--------|----------|
| 0.1 | Released | Basic simulation, controller, motor/pneumatic viz |
| 0.2 | **Current** | 3D field (Ursina), robot movement, Windows/Linux gamepad |
| 0.3 | Planned | Sensor simulation, robot model improvements |
| 0.4 | Planned | PyBullet physics, game pieces |
| 1.0 | Planned | Full 3D physics, competition mode |
| 2.0 | Future | Robot designer, multi-robot support |

---

## Inspiration & References

- [VEXcode VR](https://vr.vex.com/) - Official VEX virtual robot environment
- [RobotMesh Studio](https://www.robotmesh.com/) - Alternative VEX programming environment
- [Gazebo](https://gazebosim.org/) - Professional robotics simulator
- [PyBullet](https://pybullet.org/) - Physics simulation library

---

*This roadmap is a living document. Priorities may shift based on community feedback and contributions.*
