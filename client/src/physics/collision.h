/*
 * Collision Detection and Response
 *
 * Simple 2D collision system for VEX IQ field.
 * Uses circles for robots and cylinders (top-down view).
 * Uses axis-aligned rectangle for field boundaries.
 */

#ifndef COLLISION_H
#define COLLISION_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define COLLISION_MAX_ROBOTS 16
#define COLLISION_MAX_CYLINDERS 32

// Collision body types
typedef enum {
    COLLISION_BODY_ROBOT,
    COLLISION_BODY_CYLINDER
} CollisionBodyType;

// Circle collider (for robots and cylinders)
typedef struct {
    float x, z;           // Center position
    float radius;         // Collision radius
    bool active;
    CollisionBodyType type;
    int index;            // Index into robots/cylinders array
} CollisionCircle;

// Field boundaries (axis-aligned rectangle)
typedef struct {
    float min_x, max_x;
    float min_z, max_z;
} CollisionField;

// Collision world
typedef struct {
    CollisionField field;
    CollisionCircle robots[COLLISION_MAX_ROBOTS];
    int robot_count;
    CollisionCircle cylinders[COLLISION_MAX_CYLINDERS];
    int cylinder_count;
} CollisionWorld;

// Initialize collision world with field boundaries
void collision_init(CollisionWorld* world, float field_width, float field_depth);

// Add a robot collider (returns index, or -1 on failure)
int collision_add_robot(CollisionWorld* world, float x, float z, float radius);

// Add a cylinder collider (returns index, or -1 on failure)
int collision_add_cylinder(CollisionWorld* world, float x, float z, float radius);

// Update robot position (call before collision check)
void collision_update_robot(CollisionWorld* world, int index, float x, float z);

// Collision result for a single robot
typedef struct {
    float force_x;          // Force in X direction (lbf)
    float force_z;          // Force in Z direction (lbf)
    float torque;           // Torque around Y axis (in·lbf)
    bool hit_wall;          // True if robot hit field boundary
    bool hit_cylinder;      // True if robot hit a cylinder
    bool hit_robot;         // True if robot hit another robot
} CollisionResult;

// Collision stiffness constant (force per inch of penetration)
// Keep very low - position clamping handles the actual collision
#define COLLISION_STIFFNESS 1.0f

// Collision damping constant (force per inch/s of velocity)
// Must be very low to avoid overshoot (high values reverse velocity)
#define COLLISION_DAMPING 0.2f

// Maximum penetration allowed before hard position correction (inches)
// Keep small so position clamping kicks in early
#define COLLISION_MAX_PENETRATION 0.1f

// Check and resolve all collisions, returning forces
// velocities: array of robot velocities [vx0, vz0, vx1, vz1, ...] for damping (can be NULL)
// Results array should have space for robot_count entries
// Returns true if any collision occurred
bool collision_resolve_forces(CollisionWorld* world, const float* velocities, CollisionResult* results);

// Hard position clamp to prevent deep penetration (call after force resolution)
// Directly modifies positions if penetration exceeds COLLISION_MAX_PENETRATION
// out_positions: array to receive clamped positions [x0, z0, x1, z1, ...]
void collision_clamp_positions(CollisionWorld* world, float* out_positions);

// Legacy: Check and resolve all collisions with position correction
// Returns true if any collision occurred
// out_positions: array to receive corrected positions [x0, z0, x1, z1, ...]
bool collision_resolve(CollisionWorld* world, float* out_robot_positions);

// Check if a point is inside the field
bool collision_point_in_field(const CollisionWorld* world, float x, float z);

// Check circle-circle collision
bool collision_circle_circle(float x1, float z1, float r1, float x2, float z2, float r2);

// Check circle-field collision (returns true if circle is outside field)
bool collision_circle_field(const CollisionField* field, float x, float z, float radius);

#ifdef __cplusplus
}
#endif

#endif // COLLISION_H
