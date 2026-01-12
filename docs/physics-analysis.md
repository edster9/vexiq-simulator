# Physics System Analysis: VEX IQ Simulator vs Car Battle Simulator

## Executive Summary

The VEX IQ simulator has collision physics issues (bouncing, jitter, strange sliding after angled collisions). This document analyzes a working reference implementation (3D Game Engine car battle simulator) that uses Jolt Physics and achieves smooth, natural collision behavior.

---

## Current Problems in VEX IQ Simulator

1. **Wall bounce**: Robot bounces back when hitting wall head-on
2. **Jitter**: Robot jitters when pushing against a wall
3. **Strange sliding**: After angled collision, robot continues sliding even after turning away
4. **Velocity manipulation issues**: Manual velocity adjustments fight against drivetrain physics

---

## Reference Implementation: 3D Game Engine (Car Battle Simulator)

**Location**: `/home/edster/projects/esahakian/3d-game-engine/client`

### Architecture Overview

The car simulator uses **Jolt Physics** (a modern C++ physics engine) with these key files:

```
client/src/physics/
├── jolt_physics.h      # Complete physics API (~300 lines)
├── jolt_physics.cpp    # Implementation (~2,290 lines)
client/src/game/
├── handling.h/cpp      # Tabletop handling system
├── config_loader.h/cpp # Configuration with friction curves
```

### Core Components

```
PhysicsWorld (container)
  ├── PhysicsWorldImpl (Jolt internals)
  │   ├── PhysicsSystem (main Jolt engine)
  │   ├── JobSystemThreadPool (async physics)
  │   ├── BroadPhaseLayerInterface (collision layers)
  │   └── BodyInterface (body management)
  └── PhysicsVehicle[] (up to 8 vehicles)
       └── PhysicsVehicleImpl
           ├── BodyID (Jolt rigid body)
           ├── VehicleConstraint (wheeled vehicle)
           └── WheeledVehicleController (engine/transmission)
```

---

## Why the Car Simulator Works

### 1. Friction-Based Collision Response

The car simulator uses **friction curves** that maintain grip even at extreme slip:

```json
// Longitudinal friction curve (arcade/generous mode)
[
  [0.00, 0.0],      // No slip = ramping up
  [0.06, 1.2],      // Peak grip at 6% slip (120%)
  [0.20, 1.0],      // Still 100% at 20% slip
  [1.00, 0.9],      // 90% grip at 100% slip
  [10.0, 0.85]      // 85% grip even at extreme slip
]
```

**Key insight**: Even at extreme collision/slip, 85-90% friction remains. Energy is absorbed through friction, not bouncing.

### 2. NO Special Wall Collision Code

The car game has **zero special wall handling**:
- No velocity zeroing
- No contact normals stored
- No special angled collision logic
- Just creates static wall bodies and lets Jolt handle everything

```c
void physics_add_arena_walls(PhysicsWorld* pw, float arena_size,
                             float wall_height, float wall_thickness) {
    // Just create 4 box shapes as static bodies
    // Jolt handles ALL collision response automatically
}
```

### 3. Kinematic Mode for Precise Movement

During maneuvers, vehicles switch to **kinematic mode**:

```c
if (maneuver_is_active(&v->autopilot)) {
    physics_vehicle_set_kinematic(pw, i, true);
    physics_vehicle_move_kinematic(pw, i, pose.position, pose.heading, dt);
}
```

Kinematic bodies:
- Position set directly (no forces applied)
- Still collide with other objects
- No jitter because physics doesn't "fight" the movement

### 4. Collision Layer System

```c
namespace Layers {
    static constexpr ObjectLayer NON_MOVING = 0;  // Walls, ground
    static constexpr ObjectLayer MOVING = 1;      // Vehicles
};

// Collision rules:
// - MOVING collides with everything
// - NON_MOVING only collides with MOVING (not other static)
```

---

## Key Physics Parameters (Car Simulator)

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Gravity | -9.81 m/s² | Standard Earth gravity |
| Timestep | 1/60s (60Hz) | Fixed, deterministic |
| Tire friction μ | 1.0 | Base friction coefficient |
| Lateral friction boost | 3× | Keeps cars planted in turns |
| Suspension damping | 0.5 | Critical damping (no oscillation) |
| Restitution | ~0 (implicit) | No bounce - friction absorbs energy |
| Max bodies | 1024 | Capacity |
| Max contact constraints | 1024 | Collision capacity |

### Suspension Configuration

```c
float suspension_frequency;      // Hz (1.0-2.0 typical, 1.5 default)
float suspension_damping;        // Ratio (0.5 = critical damping)
float suspension_travel;         // Max compression (0.3m default)
```

Damping interpretation:
- 0.0: Oscillates forever (underdamped)
- 0.5: Returns to rest without overshoot (critically damped)
- 1.0: Very slow return (overdamped)

### Brake Configuration

```c
float mMaxBrakeTorque = 1500.0f;      // All wheels
float mMaxHandBrakeTorque = 4000.0f;  // Rear wheels only
```

---

## Why Our VEX IQ Approach Fails

### Current Implementation (Problematic)

```c
// Position correction + velocity hacks
if (collision) {
    robot->pos += push_out;           // Teleport out of wall
    robot->vel_x = ???;               // Manual velocity manipulation
}
```

**Problems**:
1. Position correction causes "teleporting" (discontinuous motion)
2. Manual velocity changes fight against drivetrain physics
3. Diagonal collisions create incorrect velocity components
4. No natural energy absorption - either zero velocity (jarring) or don't (bouncing)

### Jolt's Approach (What Works)

- Constraint solver handles penetration over multiple frames (smooth)
- Friction naturally absorbs kinetic energy
- No teleporting - continuous motion
- Physics is internally consistent

---

## Recommended Solutions for VEX IQ Simulator

### Option A: Integrate Jolt Physics (Best Results, Most Work)

**Effort**: High (1-2 weeks)
**Results**: Excellent

- Replace hand-rolled collision with Jolt
- Get proper friction-based response for free
- Requires significant refactoring
- Reference: `3d-game-engine/client/src/physics/jolt_physics.cpp`

**Steps**:
1. Add Jolt as dependency (header-only or library)
2. Create physics world wrapper similar to car game
3. Replace robot collision circles with Jolt bodies
4. Replace wall collision with static Jolt bodies
5. Remove all manual collision code
6. Configure friction curves for VEX IQ feel

### Option B: Implement Friction-Based Damping (Medium Effort)

**Effort**: Medium (2-3 days)
**Results**: Good

Keep position correction but improve damping model:

```c
// When in contact with wall:
// 1. Apply spring force to push out (current)
// 2. Apply continuous friction force opposing tangential motion (NEW)
// 3. Apply damping force opposing normal motion (current, needs tuning)

if (in_contact_with_wall) {
    // Friction opposes sliding along wall
    float tangent_vel = get_tangent_velocity(robot, wall_normal);
    float friction_force = -friction_coeff * normal_force * sign(tangent_vel);
    apply_force(robot, friction_force * tangent_dir);
}
```

**Key changes**:
1. Add tangential friction when sliding along walls
2. Use friction curves (not constant friction)
3. Higher base friction (0.85-0.90 even at high slip)
4. Remove all velocity manipulation - only apply forces

### Option C: Simplify to Pure Position Correction (Quick Fix)

**Effort**: Low (1 hour)
**Results**: Acceptable

Remove ALL velocity manipulation, rely on natural damping:

```c
// Wall collision - ONLY position correction
if (penetration > 0) {
    robot->pos += push_out;
    // NO velocity changes at all
}
```

**Additional changes**:
1. Increase drivetrain damping (0.95 instead of 0.99)
2. Remove contact normal system entirely
3. Remove collision.cpp force-based system (unused with OBB collision)
4. Accept some minor jitter in exchange for simplicity

---

## Incremental Bounding Box Strategy

To properly tune the new physics, we need to simplify collision detection first and gradually add complexity. This allows us to isolate physics issues from collision detection issues.

### Level 0: Single OBB Per Robot (Start Here)

**Complexity**: Lowest
**Use case**: Initial physics tuning

One OBB around the entire robot. This gives us the simplest collision shape to debug physics behavior.

```c
// Single OBB enclosing entire robot
OBB robot_obb;
compute_robot_bounding_obb(robot, &robot_obb);

// Collision check is simple
if (obb_intersects_wall(&robot_obb, wall)) {
    // Single push-out calculation
}
```

**Advantages**:
- Easiest to visualize and debug
- Fastest collision detection
- Physics issues are clearly visible (not masked by complex collision)
- Good enough for basic wall/robot collisions

**Disadvantages**:
- Imprecise for irregular robot shapes
- Can't detect which part of robot hit

**Debug visualization**: Draw single box around robot (green = no collision, red = collision)

---

### Level 1: OBB Per Submodel

**Complexity**: Medium
**Use case**: After physics is tuned, for better collision accuracy

One OBB per submodel (chassis, arm, claw, etc.). This is our current implementation.

```c
// OBB for each submodel
for (int sm = 0; sm < robot->submodel_count; sm++) {
    OBB world_obb;
    transform_obb_to_world(&robot->submodel_obbs[sm], robot, &world_obb);

    if (obb_intersects_wall(&world_obb, wall)) {
        // Track which submodel hit
        robot->submodel_collision_state[sm] = COLLISION_SUBMODEL;
    }
}
```

**Advantages**:
- Better accuracy for articulated robots
- Can identify which part hit (useful for game logic)
- Still reasonably fast

**Disadvantages**:
- More complex collision response (multiple contact points)
- Need to merge/average push directions

**Debug visualization**: Draw box around each submodel (different colors per submodel)

---

### Level 2: OBB Per Part (In Active Collision Zone Only)

**Complexity**: Highest
**Use case**: Final polish, precision collision for game elements

Full part-level collision, but only for submodels already detected as colliding (hierarchical).

```c
// First pass: submodel level (fast rejection)
for (int sm = 0; sm < robot->submodel_count; sm++) {
    OBB world_sm_obb;
    transform_obb_to_world(&robot->submodel_obbs[sm], robot, &world_sm_obb);

    if (!obb_intersects_wall(&world_sm_obb, wall)) continue;  // Skip if submodel doesn't hit

    // Second pass: part level (only for colliding submodels)
    for (int p = 0; p < robot->part_count; p++) {
        if (robot->parts[p].submodel_index != sm) continue;

        OBB world_part_obb;
        transform_obb_to_world(&robot->part_obbs[p], robot, &world_part_obb);

        if (obb_intersects_wall(&world_part_obb, wall)) {
            // Precise collision at part level
        }
    }
}
```

**Advantages**:
- Most accurate collision detection
- Can detect exactly which part hit (for damage, scoring, etc.)
- Hierarchical approach keeps it efficient

**Disadvantages**:
- Most complex to implement and debug
- Collision response needs careful handling of multiple contacts

**Debug visualization**:
- Level 1 boxes in wireframe
- Level 2 (part) boxes solid for colliding parts only

---

### Implementation Plan

#### Phase 1: Simplify to Level 0
1. Add config flag: `COLLISION_LEVEL` (0, 1, or 2)
2. Implement single-robot OBB calculation
3. Modify collision functions to use single OBB when level = 0
4. Add debug rendering for Level 0 OBB

#### Phase 2: Tune Physics at Level 0
1. Implement chosen physics option (A, B, or C)
2. Test all collision scenarios with simple bounding box
3. Tune damping, friction, restitution until smooth
4. Document working parameter values

#### Phase 3: Add Level 1 (Current System)
1. Switch to `COLLISION_LEVEL = 1`
2. Verify physics still works with submodel OBBs
3. Adjust parameters if needed
4. Add debug rendering for Level 1

#### Phase 4: Add Level 2 (If Needed)
1. Switch to `COLLISION_LEVEL = 2`
2. Implement part-level collision within active submodels
3. Verify and tune
4. Add debug rendering for Level 2

---

### Debug Visualization Keys

Add keyboard shortcuts for debugging:

| Key | Action |
|-----|--------|
| `B` | Cycle collision level (0 → 1 → 2 → 0) |
| `V` | Toggle bounding box visualization |
| `Shift+V` | Toggle collision state colors |

**Color scheme**:
- Green wireframe: No collision
- Yellow wireframe: Broad-phase hit (parent level)
- Red solid: Actual collision detected
- Blue: Wall/static object bounds

---

### Code Structure for Incremental Levels

```c
// In physics_config.h
#define COLLISION_LEVEL 0  // 0=robot, 1=submodel, 2=part

// In collision detection
void detect_robot_wall_collision(RobotInstance* robot, ...) {
    #if COLLISION_LEVEL == 0
        // Single OBB for entire robot
        OBB robot_obb = compute_full_robot_obb(robot);
        if (obb_intersects_wall(&robot_obb, wall)) {
            apply_collision_response(robot, &robot_obb, wall);
        }
    #elif COLLISION_LEVEL == 1
        // Current submodel-based approach
        for (int sm = 0; sm < robot->submodel_count; sm++) {
            // ... existing code ...
        }
    #elif COLLISION_LEVEL == 2
        // Hierarchical: submodel then part
        for (int sm = 0; sm < robot->submodel_count; sm++) {
            if (!submodel_intersects_wall(robot, sm, wall)) continue;
            for (int p : submodel_parts[sm]) {
                // ... part level ...
            }
        }
    #endif
}
```

---

## Implementation Details for Each Option

### Option A: Jolt Integration

**Files to create**:
```
client/src/physics/jolt_wrapper.h
client/src/physics/jolt_wrapper.cpp
```

**Key Jolt setup**:
```cpp
#include <Jolt/Jolt.h>
#include <Jolt/Physics/PhysicsSystem.h>
#include <Jolt/Physics/Body/BodyCreationSettings.h>
#include <Jolt/Physics/Collision/Shape/BoxShape.h>
#include <Jolt/Physics/Collision/Shape/CylinderShape.h>

// Initialize
JPH::PhysicsSystem physicsSystem;
physicsSystem.Init(maxBodies, 0, maxBodyPairs, maxContactConstraints, ...);
physicsSystem.SetGravity(JPH::Vec3(0, -386.1f, 0));  // in/s² for imperial

// Create robot body (cylinder shape)
CylinderShapeSettings robotShape(radius, height/2);
BodyCreationSettings robotSettings(robotShape, position, rotation,
    EMotionType::Dynamic, Layers::MOVING);
robotSettings.mFriction = 0.9f;      // High friction
robotSettings.mRestitution = 0.0f;   // No bounce

// Create wall (box shape, static)
BoxShapeSettings wallShape(Vec3(thickness/2, height/2, length/2));
BodyCreationSettings wallSettings(wallShape, position, rotation,
    EMotionType::Static, Layers::NON_MOVING);
wallSettings.mFriction = 0.9f;
wallSettings.mRestitution = 0.0f;

// Step physics
physicsSystem.Update(dt, 1, tempAllocator, jobSystem);
```

### Option B: Friction-Based Damping

**Modify** `client/src/main.cpp` wall collision:

```c
// After position correction, apply friction force
if (max_push_x != 0.0f || max_push_z != 0.0f) {
    // Position correction (keep)
    robot->drivetrain.pos_x += max_push_x;
    robot->drivetrain.pos_z += max_push_z;

    // Calculate wall normal
    float push_len = sqrtf(max_push_x * max_push_x + max_push_z * max_push_z);
    float nx = max_push_x / push_len;
    float nz = max_push_z / push_len;

    // Calculate tangent (perpendicular to normal)
    float tx = -nz;
    float tz = nx;

    // Tangential velocity (sliding speed)
    float vel_tangent = robot->drivetrain.vel_x * tx + robot->drivetrain.vel_z * tz;

    // Apply friction force opposing slide
    float friction_coeff = 0.85f;  // High friction
    float normal_force = push_len * COLLISION_STIFFNESS;
    float friction_force = -friction_coeff * normal_force * (vel_tangent > 0 ? 1 : -1);

    // Apply as force, not velocity change
    robot->drivetrain.ext_force_x += friction_force * tx;
    robot->drivetrain.ext_force_z += friction_force * tz;

    // Damping on normal velocity (prevent bounce)
    float vel_normal = robot->drivetrain.vel_x * nx + robot->drivetrain.vel_z * nz;
    if (vel_normal < 0) {  // Moving into wall
        float damping = 0.95f;  // Strong damping
        robot->drivetrain.vel_x -= vel_normal * nx * damping;
        robot->drivetrain.vel_z -= vel_normal * nz * damping;
    }
}
```

### Option C: Pure Position Correction

**Modify** `client/src/main.cpp`:

```c
// Wall collision - position only, no velocity
if (max_push_x != 0.0f || max_push_z != 0.0f) {
    robot->drivetrain.pos_x += max_push_x;
    robot->drivetrain.pos_z += max_push_z;
    robot->offset[0] = robot->drivetrain.pos_x;
    robot->offset[2] = robot->drivetrain.pos_z;
    // That's it - no velocity manipulation
}
```

**Modify** `client/src/physics/physics_config.h`:

```c
#define VEXIQ_LINEAR_DAMPING 0.95f   // Was 0.99, more aggressive
#define VEXIQ_ANGULAR_DAMPING 0.93f  // Was 0.98, more aggressive
```

---

## Testing Criteria

After implementing any option, test these scenarios:

1. **Head-on wall collision**: Drive straight into wall at full speed
   - Expected: Stop without bouncing back

2. **Wall push**: Drive into wall and hold throttle
   - Expected: Stay against wall without jitter

3. **45-degree collision**: Hit wall at 45-degree angle
   - Expected: Slide along wall, gradually align with it

4. **Shallow angle collision**: Hit wall at ~20 degrees
   - Expected: Deflect slightly, continue mostly forward

5. **Corner collision**: Drive into corner
   - Expected: Stop cleanly, no oscillation

---

## Files Currently Involved in VEX IQ Collision

### Main collision code (OBB-based):
- `client/src/main.cpp` lines 1000-1200 (apply_wall_collision_response, apply_robot_collision_response)

### Force-based collision (circle approximation, currently unused for walls):
- `client/src/physics/collision.cpp` (collision_resolve_forces)
- `client/src/physics/collision.h`

### Drivetrain physics:
- `client/src/physics/drivetrain.cpp` (velocity integration, damping)
- `client/src/physics/drivetrain.h`
- `client/src/physics/physics_config.h` (damping constants)

### Contact constraint system (removed):
- Previously in drivetrain.cpp (Step 7b) - removed as it caused sliding issues
- `in_contact`, `contact_nx`, `contact_nz` fields in Drivetrain struct (now unused)

---

## Conclusion

The fundamental difference is:
- **Car game**: Real physics engine (Jolt) with proper constraint solving and friction
- **VEX IQ**: Hand-rolled position correction with ad-hoc velocity adjustments

For best results, integrate Jolt Physics. For quick improvement, try Option C (pure position correction with higher damping) first, then Option B if more refinement needed.
