#include "camera.h"
#include <math.h>

#define PI 3.14159265358979323846f
#define DEG_TO_RAD (PI / 180.0f)

void camera_init(OrbitCamera* cam) {
    // World scale: 1 unit = 1 inch
    // VEX IQ table is 96" x 72" (8ft x 6ft)
    cam->target = vec3(0, 0, 0);     // Look at center of table
    cam->distance = 120.0f;          // ~10 feet back to see whole table
    cam->yaw = 0.0f;                 // Looking straight at table
    cam->pitch = -0.6f;              // Looking down at ~35 degrees

    cam->orbit_sensitivity = 0.005f;
    cam->pan_sensitivity = 0.01f;
    cam->zoom_sensitivity = 1.0f;

    cam->min_distance = 0.5f;        // ~0.5 inches minimum (allow close zoom)
    cam->max_distance = 500.0f;      // ~40 feet max

    cam->fov = 60.0f * DEG_TO_RAD;
    cam->near = 0.1f;
    cam->far = 2000.0f;              // ~160 feet far plane
}

Vec3 camera_position(OrbitCamera* cam) {
    // Spherical coordinates: position on sphere around target
    float x = cam->target.x + cam->distance * sinf(cam->yaw) * cosf(cam->pitch);
    float y = cam->target.y - cam->distance * sinf(cam->pitch);
    float z = cam->target.z + cam->distance * cosf(cam->yaw) * cosf(cam->pitch);
    return vec3(x, y, z);
}

void camera_update(OrbitCamera* cam, InputState* input, float dt) {
    (void)dt;  // Not used for orbit camera

    bool mmb_held = input->mouse_buttons[MOUSE_MIDDLE];
    bool shift_held = input->keys[KEY_LSHIFT] || input->keys[KEY_RSHIFT];

    if (mmb_held) {
        float dx = (float)input->mouse_dx;
        float dy = (float)input->mouse_dy;

        if (shift_held) {
            // Pan: move target in screen space
            // Calculate camera right and up vectors in world space
            float cos_yaw = cosf(cam->yaw);
            float sin_yaw = sinf(cam->yaw);

            // Right vector (always horizontal)
            Vec3 right = vec3(cos_yaw, 0, sin_yaw);

            // Up vector (perpendicular to view direction, mostly vertical)
            Vec3 up = vec3(0, 1, 0);

            // Scale pan by distance for consistent feel
            float pan_scale = cam->pan_sensitivity * cam->distance * 0.1f;

            // Blender-style pan: drag right = view moves right = target moves right
            cam->target = vec3_add(cam->target, vec3_scale(right, dx * pan_scale));
            cam->target = vec3_add(cam->target, vec3_scale(up, dy * pan_scale));
        } else {
            // Orbit: rotate around target
            cam->yaw -= dx * cam->orbit_sensitivity;
            cam->pitch -= dy * cam->orbit_sensitivity;

            // Clamp pitch to avoid flipping
            float max_pitch = 89.0f * DEG_TO_RAD;
            if (cam->pitch > max_pitch) cam->pitch = max_pitch;
            if (cam->pitch < -max_pitch) cam->pitch = -max_pitch;
        }
    }

    // Scroll to zoom
    if (input->scroll_y != 0) {
        // Zoom factor: scroll up = zoom in (reduce distance)
        float zoom_factor = 1.0f - input->scroll_y * 0.1f;
        cam->distance *= zoom_factor;

        // Clamp distance
        if (cam->distance < cam->min_distance) cam->distance = cam->min_distance;
        if (cam->distance > cam->max_distance) cam->distance = cam->max_distance;
    }
}

Mat4 camera_view_matrix(OrbitCamera* cam) {
    Vec3 pos = camera_position(cam);
    return mat4_look_at(pos, cam->target, vec3_up());
}

Mat4 camera_projection_matrix(OrbitCamera* cam, float aspect) {
    return mat4_perspective(cam->fov, aspect, cam->near, cam->far);
}
