# VEX IQ Simulator Physics Design

This document outlines the physics requirements and design decisions for the VEX IQ robot simulator.

## Table of Contents

1. [Requirements Overview](#requirements-overview)
2. [Engine Selection](#engine-selection)
3. [Architecture](#architecture)
4. [Implementation Phases](#implementation-phases)
5. [Technical Details](#technical-details)

---

## Requirements Overview

### Drivetrain Simulation

| Requirement | Priority | Description |
|-------------|----------|-------------|
| Kinematic base | High | Robot chassis moves based on motor velocity commands |
| Velocity control | High | Motors respond to `spin(FORWARD, 50, PERCENT)` style API |
| Acceleration curves | Medium | Realistic motor ramp-up/ramp-down |
| Stopping modes | Medium | Coast, brake, and hold behaviors |
| Wheel slip | Low | Traction limits under acceleration |

**Key Insight**: VEX IQ motors are velocity-controlled, not force-controlled. The physics system should use kinematic bodies for the drivetrain base, with motor commands setting target velocities rather than applying forces.

### Robot Collisions

| Requirement | Priority | Description |
|-------------|----------|-------------|
| Robot-robot collision | High | Two robots cannot occupy the same space |
| Robot-wall collision | High | Robots bounce off field walls |
| Complex geometry | Medium | Collision shapes approximate actual robot shape |
| Pushing mechanics | Medium | Robots can push each other |

**Key Insight**: Robot collision shapes should be compound shapes built from the robot's geometry, not simple boxes. This allows for accurate interaction with irregular robot designs.

### Game Pieces (Pins/Objects)

| Requirement | Priority | Description |
|-------------|----------|-------------|
| Stackable pins | High | Small cylindrical game pieces that stack |
| Dynamic physics | High | Pins respond to robot interaction |
| Stable stacking | High | Stacked pins don't wobble/explode |
| Friction | Medium | Pins slide appropriately on surfaces |
| Mass properties | Medium | Accurate weight and inertia |

**VEX IQ Rapid Relay Game Pieces**:
- **Pins**: Small cylindrical objects, ~1" diameter, stackable
- **Must support**: Stacking 5+ pins without instability
- **Must handle**: Robot claw pickup and release

### Articulated Joints

| Requirement | Priority | Description |
|-------------|----------|-------------|
| Motor-driven joints | High | Arms, lifts, claws driven by motors |
| Position control | High | Motors can move to specific angles |
| Torque limits | Medium | Motors stall under excessive load |
| Gravity effects | Medium | Arms affected by gravity when unpowered |
| Joint limits | Medium | Physical stops at rotation limits |

**Joint Types**:
- **Hinge joints**: Single axis rotation (arms, lifts)
- **Continuous rotation**: Wheels, rollers
- **Limited rotation**: Claws (open/close range)

---

## Engine Selection

### Candidates Evaluated

| Engine | Language | Stacking | Performance | Ease of Integration |
|--------|----------|----------|-------------|---------------------|
| **Jolt Physics** | C++ | Excellent | Excellent | Good |
| Bullet Physics | C++ | Good | Good | Good |
| ODE | C | Fair | Good | Excellent |
| Custom | C++ | N/A | Variable | N/A |

### Recommendation: Jolt Physics

**Why Jolt?**

1. **Stacking Stability**: Jolt was designed by Guerrilla Games specifically for scenarios requiring stable stacking. This is critical for VEX IQ games with stackable pins.

2. **Modern C++ API**: Clean C++17 API that integrates well with our existing SDL/OpenGL codebase.

3. **Performance**: Excellent performance with deterministic simulation, important for consistent competition replay.

4. **Active Development**: Actively maintained with regular updates (unlike ODE).

5. **MIT License**: Permissive licensing allows any use.

**Why Not Others?**

- **Bullet**: Good but stacking stability requires significant tuning; Jolt is better out of the box.
- **ODE**: Older codebase, less active maintenance, weaker stacking.
- **Custom**: Would take months to get stacking right; not worth reinventing.

### Jolt Integration

```cpp
// Jolt initialization pattern
#include <Jolt/Jolt.h>
#include <Jolt/Physics/PhysicsSystem.h>

// VEX IQ specific layers
namespace Layers {
    static constexpr uint8 NON_MOVING = 0;  // Field, walls
    static constexpr uint8 MOVING = 1;       // Robots, game pieces
}
```

---

## Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                     VEX IQ Simulator                        │
├─────────────────────────────────────────────────────────────┤
│  Render Layer (OpenGL)                                      │
│  ├── Robot meshes (from LDraw/GLB)                          │
│  ├── Game pieces                                            │
│  └── Field/walls                                            │
├─────────────────────────────────────────────────────────────┤
│  Physics Layer (Jolt)                                       │
│  ├── Kinematic drivetrain bodies                            │
│  ├── Dynamic game piece bodies                              │
│  ├── Articulated joint constraints                          │
│  └── Static field/wall bodies                               │
├─────────────────────────────────────────────────────────────┤
│  Motor Controller Layer                                     │
│  ├── Velocity PID control                                   │
│  ├── Position PID control                                   │
│  └── Stopping behavior (coast/brake/hold)                   │
├─────────────────────────────────────────────────────────────┤
│  VEX IQ API Layer                                           │
│  ├── motor.spin(direction, velocity, units)                 │
│  ├── motor.spin_to_position(angle, units)                   │
│  └── motor.stop(mode)                                       │
└─────────────────────────────────────────────────────────────┘
```

### Body Types

| Object | Jolt Body Type | Collision Shape | Notes |
|--------|----------------|-----------------|-------|
| Robot chassis | Kinematic | Compound/Convex Hull | Moved by motor commands |
| Robot arm | Dynamic | Compound | Attached via hinge constraint |
| Game pins | Dynamic | Cylinder | Full physics |
| Field floor | Static | Box | No movement |
| Field walls | Static | Box | Boundary collision |

### Kinematic Drivetrain Approach

The robot base uses **kinematic** bodies rather than dynamic bodies:

```cpp
// Kinematic approach (recommended)
void update_drivetrain(Robot* robot, float dt) {
    // Motor commands set target velocity
    float left_vel = robot->left_motor.target_velocity;
    float right_vel = robot->right_motor.target_velocity;

    // Calculate chassis velocity from wheel velocities
    float linear_vel = (left_vel + right_vel) / 2.0f;
    float angular_vel = (right_vel - left_vel) / wheel_base;

    // Apply to kinematic body
    robot->body->SetLinearVelocity(forward * linear_vel);
    robot->body->SetAngularVelocity(up * angular_vel);
}
```

**Why kinematic?**
- Motors in VEX IQ are velocity-controlled, not force-controlled
- Avoids complex force calculations and tuning
- More predictable, matches real robot behavior
- Articulated parts (arms, claws) can still be dynamic

---

## Implementation Phases

### Phase 1: Foundation

**Goal**: Basic physics integration with static collisions

- [ ] Integrate Jolt Physics library into CMake build
- [ ] Create physics world with gravity
- [ ] Add static bodies for field floor and walls
- [ ] Add kinematic body for single robot
- [ ] Implement basic collision detection (robot-wall)
- [ ] Synchronize physics transforms with render transforms

**Deliverable**: Robot can drive around field, bounces off walls

### Phase 2: Drivetrain Physics

**Goal**: Realistic drivetrain movement

- [ ] Implement motor velocity controller
- [ ] Add acceleration/deceleration curves
- [ ] Implement stopping modes (coast, brake, hold)
- [ ] Add robot-robot collision (two kinematic bodies)
- [ ] Test with ClawbotIQ and Ike robots

**Deliverable**: Two robots can drive around, push each other

### Phase 3: Game Pieces

**Goal**: Stackable pins with stable physics

- [ ] Create cylinder collision shapes for pins
- [ ] Add pins as dynamic bodies
- [ ] Tune friction and restitution for stable stacking
- [ ] Test stacking 5+ pins
- [ ] Add robot-pin collision

**Deliverable**: Robot can push pins, pins stack stably

### Phase 4: Articulated Joints

**Goal**: Moving robot parts (arms, claws)

- [ ] Parse joint definitions from robot config
- [ ] Create hinge constraints for arm joints
- [ ] Implement motor control for joint motors
- [ ] Add position control (spin_to_position)
- [ ] Add joint limits (min/max angle)

**Deliverable**: Robot arm can move, pick up pins

### Phase 5: Polish

**Goal**: Realistic behavior and edge cases

- [ ] Motor stall simulation
- [ ] Gravity effects on unpowered arms
- [ ] Claw grip mechanics
- [ ] Fine-tune all friction/mass values
- [ ] Add physics debug visualization

**Deliverable**: Production-ready physics simulation

---

## Technical Details

### Coordinate System

| System | Up | Forward | Right |
|--------|-----|---------|-------|
| OpenGL | +Y | -Z | +X |
| Jolt | +Y | +Z | +X |
| LDraw | -Y | -Z | +X |

**Conversion**: LDraw coordinates are converted at load time. Physics and render both use Y-up.

### Units

| Property | Unit | Notes |
|----------|------|-------|
| Distance | Inches | VEX IQ field is 48" x 48" |
| Velocity | Inches/second | Motor velocities |
| Angle | Radians | Internal; degrees for API |
| Mass | Kilograms | Approximate VEX IQ values |
| Time | Seconds | Fixed timestep 1/60s |

### VEX IQ Motor Specifications

| Property | Value | Notes |
|----------|-------|-------|
| Max RPM | 120 | Free speed |
| Stall torque | ~0.3 Nm | Approximate |
| Gear ratio | Configurable | Green/red cartridges |

### Collision Shapes

**Robot chassis** (example for ClawbotIQ):
```cpp
// Build compound shape from major robot sections
CompoundShapeSettings chassis_shape;
chassis_shape.AddShape(Vec3(0, 0, 0), Box(6, 4, 8));  // Main body
chassis_shape.AddShape(Vec3(0, 5, 2), Box(2, 3, 4));  // Brain mount
```

**Game pin**:
```cpp
// Simple cylinder
CylinderShapeSettings pin_shape(0.5f, 1.0f);  // radius, half-height
```

### Physics Step

```cpp
void physics_update(float dt) {
    // 1. Update motor controllers (set target velocities)
    for (auto& robot : robots) {
        update_motor_controllers(robot, dt);
    }

    // 2. Apply kinematic velocities
    for (auto& robot : robots) {
        apply_drivetrain_velocity(robot);
    }

    // 3. Step physics simulation
    physics_system.Update(dt, 1, &temp_allocator, &job_system);

    // 4. Sync render transforms from physics
    for (auto& robot : robots) {
        sync_render_transform(robot);
    }
}
```

### Memory Budget

| Component | Estimated Memory |
|-----------|------------------|
| Jolt physics system | ~2 MB base |
| Per robot (collision) | ~50 KB |
| Per game piece | ~1 KB |
| Total (2 robots, 100 pins) | ~3 MB |

---

## References

- [Jolt Physics GitHub](https://github.com/jrouwe/JoltPhysics)
- [Jolt Physics Samples](https://github.com/jrouwe/JoltPhysics/tree/master/Samples)
- [VEX IQ Motor Specs](https://www.vexrobotics.com/vexiq-electronics)
- [VEX IQ Field Specs](https://www.vexrobotics.com/competition)

---

## Appendix A: Jolt Build Instructions

```bash
# Clone Jolt
git clone https://github.com/jrouwe/JoltPhysics.git
cd JoltPhysics/Build

# Build with CMake
cmake -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)

# Install (optional)
sudo make install
```

CMakeLists.txt addition:
```cmake
# Find Jolt
find_package(Jolt REQUIRED)

# Link
target_link_libraries(vexiq_sim Jolt::Jolt)
```

---

## Appendix B: Alternative - Bullet Physics

If Jolt proves problematic, Bullet is the fallback:

```bash
sudo apt install libbullet-dev
```

```cmake
find_package(Bullet REQUIRED)
target_link_libraries(vexiq_sim ${BULLET_LIBRARIES})
```

Bullet requires more tuning for stacking stability:
- `setSolverIterations(50)` (default 10)
- Lower `erp` values
- Custom contact processing callback

---

*Document Version: 1.0*
*Last Updated: January 2026*
