#ifndef FLOOR_H
#define FLOOR_H

#include <stdbool.h>
#include <GL/glew.h>
#include "shader.h"
#include "../math/mat4.h"
#include "../math/vec3.h"

typedef struct Floor {
    GLuint vao;
    GLuint vbo;
    Shader shader;
    float size;        // Total floor size
    float grid_size;   // Size of each grid cell
} Floor;

// Initialize floor with given size and grid cell size
bool floor_init(Floor* f, float size, float grid_size);

// Cleanup
void floor_destroy(Floor* f);

// Render floor
void floor_render(Floor* f, Mat4* view, Mat4* projection, Vec3 camera_pos);

#endif // FLOOR_H
