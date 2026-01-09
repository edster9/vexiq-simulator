#include "camera.h"
#include <math.h>

#define PI 3.14159265358979323846f
#define DEG_TO_RAD (PI / 180.0f)

void camera_init(FlyCamera* cam) {
    cam->position = vec3(0, 3, 8);  // Start looking at VEX field from above
    cam->yaw = 0;
    cam->pitch = -0.3f;  // Slight downward angle

    cam->move_speed = 5.0f;
    cam->fast_speed = 15.0f;
    cam->mouse_sensitivity = 0.002f;

    cam->fov = 60.0f * DEG_TO_RAD;
    cam->near = 0.1f;
    cam->far = 500.0f;
}

Vec3 camera_forward(FlyCamera* cam) {
    return (Vec3){
        sinf(cam->yaw) * cosf(cam->pitch),
        sinf(cam->pitch),
        -cosf(cam->yaw) * cosf(cam->pitch)
    };
}

Vec3 camera_right(FlyCamera* cam) {
    return (Vec3){
        cosf(cam->yaw),
        0,
        sinf(cam->yaw)
    };
}

Vec3 camera_up(FlyCamera* cam) {
    (void)cam;
    return vec3(0, 1, 0);
}

void camera_update(FlyCamera* cam, InputState* input, float dt) {
    // Mouse look when captured
    if (input->mouse_captured) {
        bool has_movement = (input->mouse_dx != 0 || input->mouse_dy != 0);

        if (input->mouse_capture_just_started) {
            if (has_movement) {
                input->mouse_capture_just_started = false;
            }
        } else {
            cam->yaw -= input->mouse_dx * cam->mouse_sensitivity;
            cam->pitch += input->mouse_dy * cam->mouse_sensitivity;
        }
    }

    // Clamp pitch
    float max_pitch = 89.0f * DEG_TO_RAD;
    if (cam->pitch > max_pitch) cam->pitch = max_pitch;
    if (cam->pitch < -max_pitch) cam->pitch = -max_pitch;

    // Movement
    float speed = cam->move_speed;
    if (input->keys[KEY_LSHIFT] || input->keys[KEY_RSHIFT]) {
        speed = cam->fast_speed;
    }

    Vec3 forward = camera_forward(cam);
    Vec3 right = camera_right(cam);
    Vec3 move = vec3_zero();

    if (input->keys[KEY_W]) move = vec3_add(move, forward);
    if (input->keys[KEY_S]) move = vec3_sub(move, forward);
    if (input->keys[KEY_D]) move = vec3_add(move, right);
    if (input->keys[KEY_A]) move = vec3_sub(move, right);
    if (input->keys[KEY_E] || input->keys[KEY_SPACE]) move.y += 1.0f;
    if (input->keys[KEY_Q] || input->keys[KEY_LCTRL]) move.y -= 1.0f;

    float len = vec3_length(move);
    if (len > 0.001f) {
        move = vec3_scale(move, speed * dt / len);
        cam->position = vec3_add(cam->position, move);
    }

    // Scroll to adjust speed
    if (input->scroll_y != 0) {
        cam->move_speed += input->scroll_y * 1.0f;
        if (cam->move_speed < 1.0f) cam->move_speed = 1.0f;
        if (cam->move_speed > 50.0f) cam->move_speed = 50.0f;
        cam->fast_speed = cam->move_speed * 3.0f;
    }
}

Mat4 camera_view_matrix(FlyCamera* cam) {
    Vec3 forward = camera_forward(cam);
    Vec3 target = vec3_add(cam->position, forward);
    return mat4_look_at(cam->position, target, vec3_up());
}

Mat4 camera_projection_matrix(FlyCamera* cam, float aspect) {
    return mat4_perspective(cam->fov, aspect, cam->near, cam->far);
}
