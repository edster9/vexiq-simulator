#include "camera.h"
#include <math.h>

#define PI 3.14159265358979323846f
#define DEG_TO_RAD (PI / 180.0f)

void camera_init(OrbitCamera* cam) {
    // World scale: 1 unit = 1 inch
    // VEX IQ table is 96" x 72" (8ft x 6ft)
    // Start camera above and behind the table, looking down at it
    cam->position = vec3(0, 80, 120);  // 80" up, 120" back (10 feet)
    cam->yaw = 0.0f;                    // Looking along -Z (toward table)
    cam->pitch = -0.5f;                 // Looking down ~30 degrees

    cam->look_sensitivity = 0.005f;
    cam->move_speed = 60.0f;            // 60 inches per second

    cam->fov = 60.0f * DEG_TO_RAD;
    cam->near = 0.1f;
    cam->far = 2000.0f;                 // ~160 feet far plane
}

// Get forward direction from yaw/pitch
static Vec3 camera_forward(OrbitCamera* cam) {
    float cos_pitch = cosf(cam->pitch);
    return vec3(
        -sinf(cam->yaw) * cos_pitch,
        sinf(cam->pitch),
        -cosf(cam->yaw) * cos_pitch
    );
}

// Get right direction from yaw (horizontal only)
static Vec3 camera_right(OrbitCamera* cam) {
    return vec3(-cosf(cam->yaw), 0, sinf(cam->yaw));
}

Vec3 camera_position(OrbitCamera* cam) {
    return cam->position;
}

void camera_update(OrbitCamera* cam, InputState* input, float dt) {
    bool mmb_held = input->mouse_buttons[MOUSE_MIDDLE];

    // Middle mouse: look around (first-person style)
    if (mmb_held) {
        float dx = (float)input->mouse_dx;
        float dy = (float)input->mouse_dy;

        cam->yaw -= dx * cam->look_sensitivity;
        cam->pitch -= dy * cam->look_sensitivity;

        // Clamp pitch to avoid flipping
        float max_pitch = 89.0f * DEG_TO_RAD;
        if (cam->pitch > max_pitch) cam->pitch = max_pitch;
        if (cam->pitch < -max_pitch) cam->pitch = -max_pitch;
    }

    // Scroll to move forward/back (zoom feel)
    if (input->scroll_y != 0) {
        Vec3 forward = camera_forward(cam);
        float scroll_speed = 10.0f;  // 10 inches per scroll tick
        cam->position = vec3_add(cam->position, vec3_scale(forward, input->scroll_y * scroll_speed));
    }

    // WASD movement - first-person style
    bool w_held = input->keys[KEY_W];
    bool s_held = input->keys[KEY_S];
    bool a_held = input->keys[KEY_A];
    bool d_held = input->keys[KEY_D];

    if (w_held || s_held || a_held || d_held) {
        float move_speed = cam->move_speed * dt;

        Vec3 forward = camera_forward(cam);
        Vec3 right = camera_right(cam);

        // W/S: move forward/back in look direction
        if (w_held) cam->position = vec3_add(cam->position, vec3_scale(forward, move_speed));
        if (s_held) cam->position = vec3_add(cam->position, vec3_scale(forward, -move_speed));

        // A/D: strafe left/right
        if (a_held) cam->position = vec3_add(cam->position, vec3_scale(right, -move_speed));
        if (d_held) cam->position = vec3_add(cam->position, vec3_scale(right, move_speed));
    }
}

Mat4 camera_view_matrix(OrbitCamera* cam) {
    Vec3 forward = camera_forward(cam);
    Vec3 target = vec3_add(cam->position, forward);
    return mat4_look_at(cam->position, target, vec3_up());
}

Mat4 camera_projection_matrix(OrbitCamera* cam, float aspect) {
    return mat4_perspective(cam->fov, aspect, cam->near, cam->far);
}
