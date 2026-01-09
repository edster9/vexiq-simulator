#include "mat4.h"
#include <math.h>

Mat4 mat4_mul(Mat4 a, Mat4 b) {
    Mat4 result;
    for (int col = 0; col < 4; col++) {
        for (int row = 0; row < 4; row++) {
            result.m[col * 4 + row] =
                a.m[0 * 4 + row] * b.m[col * 4 + 0] +
                a.m[1 * 4 + row] * b.m[col * 4 + 1] +
                a.m[2 * 4 + row] * b.m[col * 4 + 2] +
                a.m[3 * 4 + row] * b.m[col * 4 + 3];
        }
    }
    return result;
}

Mat4 mat4_translate(Vec3 v) {
    Mat4 m = mat4_identity();
    m.m[12] = v.x;
    m.m[13] = v.y;
    m.m[14] = v.z;
    return m;
}

Mat4 mat4_scale(Vec3 v) {
    Mat4 m = mat4_identity();
    m.m[0] = v.x;
    m.m[5] = v.y;
    m.m[10] = v.z;
    return m;
}

Mat4 mat4_rotate_x(float radians) {
    float c = cosf(radians);
    float s = sinf(radians);
    Mat4 m = mat4_identity();
    m.m[5] = c;
    m.m[6] = s;
    m.m[9] = -s;
    m.m[10] = c;
    return m;
}

Mat4 mat4_rotate_y(float radians) {
    float c = cosf(radians);
    float s = sinf(radians);
    Mat4 m = mat4_identity();
    m.m[0] = c;
    m.m[2] = -s;
    m.m[8] = s;
    m.m[10] = c;
    return m;
}

Mat4 mat4_rotate_z(float radians) {
    float c = cosf(radians);
    float s = sinf(radians);
    Mat4 m = mat4_identity();
    m.m[0] = c;
    m.m[1] = s;
    m.m[4] = -s;
    m.m[5] = c;
    return m;
}

Mat4 mat4_look_at(Vec3 eye, Vec3 target, Vec3 up) {
    Vec3 f = vec3_normalize(vec3_sub(target, eye));  // Forward
    Vec3 r = vec3_normalize(vec3_cross(f, up));       // Right
    Vec3 u = vec3_cross(r, f);                        // Up

    Mat4 m = mat4_identity();

    m.m[0] = r.x;
    m.m[4] = r.y;
    m.m[8] = r.z;

    m.m[1] = u.x;
    m.m[5] = u.y;
    m.m[9] = u.z;

    m.m[2] = -f.x;
    m.m[6] = -f.y;
    m.m[10] = -f.z;

    m.m[12] = -vec3_dot(r, eye);
    m.m[13] = -vec3_dot(u, eye);
    m.m[14] = vec3_dot(f, eye);

    return m;
}

Mat4 mat4_perspective(float fov_radians, float aspect, float near, float far) {
    float tan_half_fov = tanf(fov_radians / 2.0f);

    Mat4 m;
    memset(&m, 0, sizeof(Mat4));

    m.m[0] = 1.0f / (aspect * tan_half_fov);
    m.m[5] = 1.0f / tan_half_fov;
    m.m[10] = -(far + near) / (far - near);
    m.m[11] = -1.0f;
    m.m[14] = -(2.0f * far * near) / (far - near);

    return m;
}

Mat4 mat4_ortho(float left, float right, float bottom, float top, float near, float far) {
    Mat4 m = mat4_identity();

    m.m[0] = 2.0f / (right - left);
    m.m[5] = 2.0f / (top - bottom);
    m.m[10] = -2.0f / (far - near);

    m.m[12] = -(right + left) / (right - left);
    m.m[13] = -(top + bottom) / (top - bottom);
    m.m[14] = -(far + near) / (far - near);

    return m;
}

Vec3 mat4_transform_point(Mat4 m, Vec3 p) {
    float w = m.m[3] * p.x + m.m[7] * p.y + m.m[11] * p.z + m.m[15];
    return (Vec3){
        (m.m[0] * p.x + m.m[4] * p.y + m.m[8] * p.z + m.m[12]) / w,
        (m.m[1] * p.x + m.m[5] * p.y + m.m[9] * p.z + m.m[13]) / w,
        (m.m[2] * p.x + m.m[6] * p.y + m.m[10] * p.z + m.m[14]) / w
    };
}

Vec3 mat4_transform_direction(Mat4 m, Vec3 d) {
    return (Vec3){
        m.m[0] * d.x + m.m[4] * d.y + m.m[8] * d.z,
        m.m[1] * d.x + m.m[5] * d.y + m.m[9] * d.z,
        m.m[2] * d.x + m.m[6] * d.y + m.m[10] * d.z
    };
}
