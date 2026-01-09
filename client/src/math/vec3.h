#ifndef VEC3_H
#define VEC3_H

#include <math.h>

typedef struct Vec3 {
    float x, y, z;
} Vec3;

// Creation
static inline Vec3 vec3(float x, float y, float z) {
    return (Vec3){x, y, z};
}

static inline Vec3 vec3_zero(void) {
    return (Vec3){0, 0, 0};
}

static inline Vec3 vec3_one(void) {
    return (Vec3){1, 1, 1};
}

static inline Vec3 vec3_up(void) {
    return (Vec3){0, 1, 0};
}

static inline Vec3 vec3_forward(void) {
    return (Vec3){0, 0, -1};
}

static inline Vec3 vec3_right(void) {
    return (Vec3){1, 0, 0};
}

// Basic operations
static inline Vec3 vec3_add(Vec3 a, Vec3 b) {
    return (Vec3){a.x + b.x, a.y + b.y, a.z + b.z};
}

static inline Vec3 vec3_sub(Vec3 a, Vec3 b) {
    return (Vec3){a.x - b.x, a.y - b.y, a.z - b.z};
}

static inline Vec3 vec3_mul(Vec3 a, Vec3 b) {
    return (Vec3){a.x * b.x, a.y * b.y, a.z * b.z};
}

static inline Vec3 vec3_scale(Vec3 v, float s) {
    return (Vec3){v.x * s, v.y * s, v.z * s};
}

static inline Vec3 vec3_negate(Vec3 v) {
    return (Vec3){-v.x, -v.y, -v.z};
}

// Dot and cross
static inline float vec3_dot(Vec3 a, Vec3 b) {
    return a.x * b.x + a.y * b.y + a.z * b.z;
}

static inline Vec3 vec3_cross(Vec3 a, Vec3 b) {
    return (Vec3){
        a.y * b.z - a.z * b.y,
        a.z * b.x - a.x * b.z,
        a.x * b.y - a.y * b.x
    };
}

// Length
static inline float vec3_length_sq(Vec3 v) {
    return v.x * v.x + v.y * v.y + v.z * v.z;
}

static inline float vec3_length(Vec3 v) {
    return sqrtf(vec3_length_sq(v));
}

static inline Vec3 vec3_normalize(Vec3 v) {
    float len = vec3_length(v);
    if (len > 0.0001f) {
        float inv = 1.0f / len;
        return (Vec3){v.x * inv, v.y * inv, v.z * inv};
    }
    return vec3_zero();
}

// Lerp
static inline Vec3 vec3_lerp(Vec3 a, Vec3 b, float t) {
    return (Vec3){
        a.x + (b.x - a.x) * t,
        a.y + (b.y - a.y) * t,
        a.z + (b.z - a.z) * t
    };
}

#endif // VEC3_H
