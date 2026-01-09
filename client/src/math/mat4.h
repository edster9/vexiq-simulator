#ifndef MAT4_H
#define MAT4_H

#include "vec3.h"
#include <string.h>

// Column-major 4x4 matrix (OpenGL convention)
// m[col][row] or m[col * 4 + row]
typedef struct Mat4 {
    float m[16];
} Mat4;

// Identity matrix
static inline Mat4 mat4_identity(void) {
    Mat4 result;
    memset(&result, 0, sizeof(Mat4));
    result.m[0] = 1.0f;
    result.m[5] = 1.0f;
    result.m[10] = 1.0f;
    result.m[15] = 1.0f;
    return result;
}

// Matrix multiplication
Mat4 mat4_mul(Mat4 a, Mat4 b);

// Transform operations
Mat4 mat4_translate(Vec3 v);
Mat4 mat4_scale(Vec3 v);
Mat4 mat4_rotate_x(float radians);
Mat4 mat4_rotate_y(float radians);
Mat4 mat4_rotate_z(float radians);

// View and projection
Mat4 mat4_look_at(Vec3 eye, Vec3 target, Vec3 up);
Mat4 mat4_perspective(float fov_radians, float aspect, float near, float far);
Mat4 mat4_ortho(float left, float right, float bottom, float top, float near, float far);

// Utility
Vec3 mat4_transform_point(Mat4 m, Vec3 p);
Vec3 mat4_transform_direction(Mat4 m, Vec3 d);

#endif // MAT4_H
