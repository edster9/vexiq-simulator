/*
 * Oriented Bounding Box (OBB) Implementation
 *
 * Uses Separating Axis Theorem for OBB-OBB intersection testing.
 * Reference: "Real-Time Collision Detection" by Christer Ericson
 */

#include "obb.h"
#include <math.h>
#include <float.h>

// Helper: absolute value
static inline float absf(float x) { return x < 0 ? -x : x; }

// Helper: min/max
static inline float minf(float a, float b) { return a < b ? a : b; }
static inline float maxf(float a, float b) { return a > b ? a : b; }

// ============================================================================
// Matrix operations
// ============================================================================

void mat3_multiply(const float* a, const float* b, float* out) {
    out[0] = a[0]*b[0] + a[1]*b[3] + a[2]*b[6];
    out[1] = a[0]*b[1] + a[1]*b[4] + a[2]*b[7];
    out[2] = a[0]*b[2] + a[1]*b[5] + a[2]*b[8];
    out[3] = a[3]*b[0] + a[4]*b[3] + a[5]*b[6];
    out[4] = a[3]*b[1] + a[4]*b[4] + a[5]*b[7];
    out[5] = a[3]*b[2] + a[4]*b[5] + a[5]*b[8];
    out[6] = a[6]*b[0] + a[7]*b[3] + a[8]*b[6];
    out[7] = a[6]*b[1] + a[7]*b[4] + a[8]*b[7];
    out[8] = a[6]*b[2] + a[7]*b[5] + a[8]*b[8];
}

void mat3_rotation_y(float angle_rad, float* out) {
    float c = cosf(angle_rad);
    float s = sinf(angle_rad);
    // Row-major:
    // | c  0  s |
    // | 0  1  0 |
    // |-s  0  c |
    out[0] = c;  out[1] = 0;  out[2] = s;
    out[3] = 0;  out[4] = 1;  out[5] = 0;
    out[6] = -s; out[7] = 0;  out[8] = c;
}

// Transform point by 3x3 rotation matrix
static void mat3_transform_point(const float* rot, float x, float y, float z,
                                  float* ox, float* oy, float* oz) {
    *ox = rot[0]*x + rot[1]*y + rot[2]*z;
    *oy = rot[3]*x + rot[4]*y + rot[5]*z;
    *oz = rot[6]*x + rot[7]*y + rot[8]*z;
}

// ============================================================================
// OBB Construction
// ============================================================================

void obb_from_bounds(OBB* obb, Vec3 min_bounds, Vec3 max_bounds) {
    // Center is midpoint
    obb->center.x = (min_bounds.x + max_bounds.x) * 0.5f;
    obb->center.y = (min_bounds.y + max_bounds.y) * 0.5f;
    obb->center.z = (min_bounds.z + max_bounds.z) * 0.5f;

    // Half extents
    obb->half_extents.x = (max_bounds.x - min_bounds.x) * 0.5f;
    obb->half_extents.y = (max_bounds.y - min_bounds.y) * 0.5f;
    obb->half_extents.z = (max_bounds.z - min_bounds.z) * 0.5f;

    // Identity rotation
    obb->rotation[0] = 1; obb->rotation[1] = 0; obb->rotation[2] = 0;
    obb->rotation[3] = 0; obb->rotation[4] = 1; obb->rotation[5] = 0;
    obb->rotation[6] = 0; obb->rotation[7] = 0; obb->rotation[8] = 1;
}

void obb_transform(const OBB* local_obb, Vec3 world_pos, float world_rot_y, OBB* out_obb) {
    float rot[9];
    mat3_rotation_y(world_rot_y, rot);
    obb_transform_matrix(local_obb, world_pos, rot, out_obb);
}

void obb_transform_matrix(const OBB* local_obb, Vec3 world_pos, const float* rot_3x3, OBB* out_obb) {
    // Transform center to world space
    float cx, cy, cz;
    mat3_transform_point(rot_3x3, local_obb->center.x, local_obb->center.y, local_obb->center.z,
                         &cx, &cy, &cz);
    out_obb->center.x = world_pos.x + cx;
    out_obb->center.y = world_pos.y + cy;
    out_obb->center.z = world_pos.z + cz;

    // Half extents stay the same (they're in local space)
    out_obb->half_extents = local_obb->half_extents;

    // Compose rotations: world_rot * local_rot
    mat3_multiply(rot_3x3, local_obb->rotation, out_obb->rotation);
}

// ============================================================================
// OBB-OBB Intersection (Separating Axis Theorem)
// ============================================================================

bool obb_intersects_obb(const OBB* a, const OBB* b) {
    // Translation between centers
    Vec3 t;
    t.x = b->center.x - a->center.x;
    t.y = b->center.y - a->center.y;
    t.z = b->center.z - a->center.z;

    // Get axes of both OBBs (columns of rotation matrices)
    // A's axes
    float ax[3] = {a->rotation[0], a->rotation[3], a->rotation[6]};
    float ay[3] = {a->rotation[1], a->rotation[4], a->rotation[7]};
    float az[3] = {a->rotation[2], a->rotation[5], a->rotation[8]};

    // B's axes
    float bx[3] = {b->rotation[0], b->rotation[3], b->rotation[6]};
    float by[3] = {b->rotation[1], b->rotation[4], b->rotation[7]};
    float bz[3] = {b->rotation[2], b->rotation[5], b->rotation[8]};

    // Compute rotation matrix expressing B in A's coordinate frame
    // R[i][j] = dot(A_axis_i, B_axis_j)
    float R[3][3], AbsR[3][3];

    R[0][0] = ax[0]*bx[0] + ax[1]*bx[1] + ax[2]*bx[2];
    R[0][1] = ax[0]*by[0] + ax[1]*by[1] + ax[2]*by[2];
    R[0][2] = ax[0]*bz[0] + ax[1]*bz[1] + ax[2]*bz[2];

    R[1][0] = ay[0]*bx[0] + ay[1]*bx[1] + ay[2]*bx[2];
    R[1][1] = ay[0]*by[0] + ay[1]*by[1] + ay[2]*by[2];
    R[1][2] = ay[0]*bz[0] + ay[1]*bz[1] + ay[2]*bz[2];

    R[2][0] = az[0]*bx[0] + az[1]*bx[1] + az[2]*bx[2];
    R[2][1] = az[0]*by[0] + az[1]*by[1] + az[2]*by[2];
    R[2][2] = az[0]*bz[0] + az[1]*bz[1] + az[2]*bz[2];

    // Compute AbsR with epsilon for numerical robustness
    const float EPSILON = 1e-6f;
    for (int i = 0; i < 3; i++) {
        for (int j = 0; j < 3; j++) {
            AbsR[i][j] = absf(R[i][j]) + EPSILON;
        }
    }

    // Translation in A's coordinate frame
    float ta[3];
    ta[0] = t.x*ax[0] + t.y*ax[1] + t.z*ax[2];
    ta[1] = t.x*ay[0] + t.y*ay[1] + t.z*ay[2];
    ta[2] = t.x*az[0] + t.y*az[1] + t.z*az[2];

    float ra, rb;

    // Test axes L = A0, A1, A2
    for (int i = 0; i < 3; i++) {
        float ae[3] = {a->half_extents.x, a->half_extents.y, a->half_extents.z};
        float be[3] = {b->half_extents.x, b->half_extents.y, b->half_extents.z};
        ra = ae[i];
        rb = be[0]*AbsR[i][0] + be[1]*AbsR[i][1] + be[2]*AbsR[i][2];
        if (absf(ta[i]) > ra + rb) return false;
    }

    // Test axes L = B0, B1, B2
    for (int i = 0; i < 3; i++) {
        float ae[3] = {a->half_extents.x, a->half_extents.y, a->half_extents.z};
        float be[3] = {b->half_extents.x, b->half_extents.y, b->half_extents.z};
        ra = ae[0]*AbsR[0][i] + ae[1]*AbsR[1][i] + ae[2]*AbsR[2][i];
        rb = be[i];
        float tb = t.x*bx[i] + t.y*by[i] + t.z*bz[i];
        if (absf(tb) > ra + rb) return false;
    }

    // Test 9 cross product axes
    float ae[3] = {a->half_extents.x, a->half_extents.y, a->half_extents.z};
    float be[3] = {b->half_extents.x, b->half_extents.y, b->half_extents.z};

    // L = A0 x B0
    ra = ae[1]*AbsR[2][0] + ae[2]*AbsR[1][0];
    rb = be[1]*AbsR[0][2] + be[2]*AbsR[0][1];
    if (absf(ta[2]*R[1][0] - ta[1]*R[2][0]) > ra + rb) return false;

    // L = A0 x B1
    ra = ae[1]*AbsR[2][1] + ae[2]*AbsR[1][1];
    rb = be[0]*AbsR[0][2] + be[2]*AbsR[0][0];
    if (absf(ta[2]*R[1][1] - ta[1]*R[2][1]) > ra + rb) return false;

    // L = A0 x B2
    ra = ae[1]*AbsR[2][2] + ae[2]*AbsR[1][2];
    rb = be[0]*AbsR[0][1] + be[1]*AbsR[0][0];
    if (absf(ta[2]*R[1][2] - ta[1]*R[2][2]) > ra + rb) return false;

    // L = A1 x B0
    ra = ae[0]*AbsR[2][0] + ae[2]*AbsR[0][0];
    rb = be[1]*AbsR[1][2] + be[2]*AbsR[1][1];
    if (absf(ta[0]*R[2][0] - ta[2]*R[0][0]) > ra + rb) return false;

    // L = A1 x B1
    ra = ae[0]*AbsR[2][1] + ae[2]*AbsR[0][1];
    rb = be[0]*AbsR[1][2] + be[2]*AbsR[1][0];
    if (absf(ta[0]*R[2][1] - ta[2]*R[0][1]) > ra + rb) return false;

    // L = A1 x B2
    ra = ae[0]*AbsR[2][2] + ae[2]*AbsR[0][2];
    rb = be[0]*AbsR[1][1] + be[1]*AbsR[1][0];
    if (absf(ta[0]*R[2][2] - ta[2]*R[0][2]) > ra + rb) return false;

    // L = A2 x B0
    ra = ae[0]*AbsR[1][0] + ae[1]*AbsR[0][0];
    rb = be[1]*AbsR[2][2] + be[2]*AbsR[2][1];
    if (absf(ta[1]*R[0][0] - ta[0]*R[1][0]) > ra + rb) return false;

    // L = A2 x B1
    ra = ae[0]*AbsR[1][1] + ae[1]*AbsR[0][1];
    rb = be[0]*AbsR[2][2] + be[2]*AbsR[2][0];
    if (absf(ta[1]*R[0][1] - ta[0]*R[1][1]) > ra + rb) return false;

    // L = A2 x B2
    ra = ae[0]*AbsR[1][2] + ae[1]*AbsR[0][2];
    rb = be[0]*AbsR[2][1] + be[1]*AbsR[2][0];
    if (absf(ta[1]*R[0][2] - ta[0]*R[1][2]) > ra + rb) return false;

    // No separating axis found - boxes intersect
    return true;
}

// ============================================================================
// OBB-AABB Intersection
// ============================================================================

bool obb_intersects_aabb(const OBB* obb, const AABB* aabb) {
    // Convert AABB to OBB and use OBB-OBB test
    OBB aabb_obb;
    aabb_obb.center.x = (aabb->min.x + aabb->max.x) * 0.5f;
    aabb_obb.center.y = (aabb->min.y + aabb->max.y) * 0.5f;
    aabb_obb.center.z = (aabb->min.z + aabb->max.z) * 0.5f;
    aabb_obb.half_extents.x = (aabb->max.x - aabb->min.x) * 0.5f;
    aabb_obb.half_extents.y = (aabb->max.y - aabb->min.y) * 0.5f;
    aabb_obb.half_extents.z = (aabb->max.z - aabb->min.z) * 0.5f;
    // Identity rotation for AABB
    aabb_obb.rotation[0] = 1; aabb_obb.rotation[1] = 0; aabb_obb.rotation[2] = 0;
    aabb_obb.rotation[3] = 0; aabb_obb.rotation[4] = 1; aabb_obb.rotation[5] = 0;
    aabb_obb.rotation[6] = 0; aabb_obb.rotation[7] = 0; aabb_obb.rotation[8] = 1;

    return obb_intersects_obb(obb, &aabb_obb);
}

// ============================================================================
// OBB-Circle Intersection (for top-down cylinder collision)
// ============================================================================

bool obb_intersects_circle(const OBB* obb, float circle_x, float circle_z, float circle_radius) {
    // Get OBB corners projected onto XZ plane
    Vec3 corners[8];
    obb_get_corners(obb, corners);

    // Find closest point on OBB to circle center (in XZ plane)
    // We project the OBB onto the XZ plane and find the closest point

    // Get OBB's X and Z axes (for 2D projection)
    float ax_x = obb->rotation[0];
    float ax_z = obb->rotation[6];
    float az_x = obb->rotation[2];
    float az_z = obb->rotation[8];

    // Vector from OBB center to circle center (XZ plane)
    float dx = circle_x - obb->center.x;
    float dz = circle_z - obb->center.z;

    // Project onto OBB's local axes (2D)
    float proj_x = dx * ax_x + dz * ax_z;
    float proj_z = dx * az_x + dz * az_z;

    // Clamp to OBB extents
    float clamped_x = maxf(-obb->half_extents.x, minf(obb->half_extents.x, proj_x));
    float clamped_z = maxf(-obb->half_extents.z, minf(obb->half_extents.z, proj_z));

    // Transform back to world space
    float closest_x = obb->center.x + clamped_x * ax_x + clamped_z * az_x;
    float closest_z = obb->center.z + clamped_x * ax_z + clamped_z * az_z;

    // Distance from closest point to circle center
    float dist_x = circle_x - closest_x;
    float dist_z = circle_z - closest_z;
    float dist_sq = dist_x * dist_x + dist_z * dist_z;

    return dist_sq <= circle_radius * circle_radius;
}

// ============================================================================
// Utility
// ============================================================================

void obb_get_enclosing_aabb(const OBB* obb, AABB* out_aabb) {
    Vec3 corners[8];
    obb_get_corners(obb, corners);

    out_aabb->min = corners[0];
    out_aabb->max = corners[0];

    for (int i = 1; i < 8; i++) {
        out_aabb->min.x = minf(out_aabb->min.x, corners[i].x);
        out_aabb->min.y = minf(out_aabb->min.y, corners[i].y);
        out_aabb->min.z = minf(out_aabb->min.z, corners[i].z);
        out_aabb->max.x = maxf(out_aabb->max.x, corners[i].x);
        out_aabb->max.y = maxf(out_aabb->max.y, corners[i].y);
        out_aabb->max.z = maxf(out_aabb->max.z, corners[i].z);
    }
}

void obb_get_corners(const OBB* obb, Vec3 corners[8]) {
    float ex = obb->half_extents.x;
    float ey = obb->half_extents.y;
    float ez = obb->half_extents.z;

    // Local corners relative to center
    float local[8][3] = {
        {-ex, -ey, -ez},
        { ex, -ey, -ez},
        { ex,  ey, -ez},
        {-ex,  ey, -ez},
        {-ex, -ey,  ez},
        { ex, -ey,  ez},
        { ex,  ey,  ez},
        {-ex,  ey,  ez}
    };

    for (int i = 0; i < 8; i++) {
        float wx, wy, wz;
        mat3_transform_point(obb->rotation, local[i][0], local[i][1], local[i][2],
                             &wx, &wy, &wz);
        corners[i].x = obb->center.x + wx;
        corners[i].y = obb->center.y + wy;
        corners[i].z = obb->center.z + wz;
    }
}
