/*
 * Oriented Bounding Box (OBB) for hierarchical collision detection
 *
 * OBBs rotate with objects, providing tighter fits than axis-aligned boxes.
 * Uses Separating Axis Theorem (SAT) for intersection tests.
 */

#ifndef OBB_H
#define OBB_H

#include "../math/vec3.h"
#include "../math/mat4.h"
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// Oriented Bounding Box
typedef struct {
    Vec3 center;           // Center in local space
    Vec3 half_extents;     // Half-size along local X, Y, Z
    float rotation[9];     // 3x3 rotation matrix (row-major), local-to-world
} OBB;

// Axis-Aligned Bounding Box (for field walls, etc.)
typedef struct {
    Vec3 min;
    Vec3 max;
} AABB;

// ============================================================================
// OBB Construction
// ============================================================================

// Initialize OBB from min/max bounds in local space
void obb_from_bounds(OBB* obb, Vec3 min_bounds, Vec3 max_bounds);

// Transform OBB to world space given world position and rotation
// out_obb receives the transformed OBB
void obb_transform(const OBB* local_obb, Vec3 world_pos, float world_rot_y, OBB* out_obb);

// Transform OBB using a full 3x3 rotation matrix
void obb_transform_matrix(const OBB* local_obb, Vec3 world_pos, const float* rot_3x3, OBB* out_obb);

// ============================================================================
// Intersection Tests
// ============================================================================

// Test OBB vs OBB intersection using Separating Axis Theorem
// Returns true if the boxes intersect
bool obb_intersects_obb(const OBB* a, const OBB* b);

// Test OBB vs AABB intersection
// Returns true if they intersect
bool obb_intersects_aabb(const OBB* obb, const AABB* aabb);

// Test OBB vs circle (cylinder from top-down view)
// circle_x, circle_z: center of circle on XZ plane
// circle_radius: radius of circle
// Returns true if they intersect
bool obb_intersects_circle(const OBB* obb, float circle_x, float circle_z, float circle_radius);

// ============================================================================
// Utility
// ============================================================================

// Compute AABB that encloses the OBB (for broad phase)
void obb_get_enclosing_aabb(const OBB* obb, AABB* out_aabb);

// Get the 8 corners of the OBB in world space
void obb_get_corners(const OBB* obb, Vec3 corners[8]);

// Multiply 3x3 matrices (row-major): out = a * b
void mat3_multiply(const float* a, const float* b, float* out);

// Create Y-axis rotation matrix (3x3)
void mat3_rotation_y(float angle_rad, float* out);

#ifdef __cplusplus
}
#endif

#endif // OBB_H
