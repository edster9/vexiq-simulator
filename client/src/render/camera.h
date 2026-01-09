#ifndef CAMERA_H
#define CAMERA_H

#include "../math/vec3.h"
#include "../math/mat4.h"
#include "../platform/platform.h"

// Blender-style orbit camera
typedef struct OrbitCamera {
    Vec3 target;        // Point camera orbits around
    float distance;     // Distance from target
    float yaw;          // Horizontal orbit angle (radians)
    float pitch;        // Vertical orbit angle (radians)

    float orbit_sensitivity;
    float pan_sensitivity;
    float zoom_sensitivity;

    float min_distance;
    float max_distance;

    float fov;          // Field of view (radians)
    float near;
    float far;
} OrbitCamera;

// Initialize camera with defaults
void camera_init(OrbitCamera* cam);

// Update camera from input (Blender-style: MMB=orbit, Shift+MMB=pan, Scroll=zoom)
void camera_update(OrbitCamera* cam, InputState* input, float dt);

// Get camera position (computed from target + distance + angles)
Vec3 camera_position(OrbitCamera* cam);

// Get matrices
Mat4 camera_view_matrix(OrbitCamera* cam);
Mat4 camera_projection_matrix(OrbitCamera* cam, float aspect);

// Legacy alias for compatibility
typedef OrbitCamera FlyCamera;

#endif // CAMERA_H
