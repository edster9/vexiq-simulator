#ifndef FLOOR_H
#define FLOOR_H

#include <stdbool.h>
#include <GL/glew.h>
#include "shader.h"
#include "../math/mat4.h"
#include "../math/vec3.h"

typedef struct Floor {
    // Floor surface
    GLuint vao;
    GLuint vbo;
    Shader shader;
    GLuint texture;

    // Walls
    GLuint wall_vao;
    GLuint wall_vbo;
    Shader wall_shader;
    int wall_vertex_count;

    // Dimensions
    float size;         // Total floor size (square)
    float grid_size;    // Size of each grid cell
    float field_width;  // VEX IQ field width (96" = 8ft)
    float field_depth;  // VEX IQ field depth (72" = 6ft)
    float wall_height;  // Wall height (4")
} Floor;

// Initialize floor with given size and grid cell size
// field_width and field_depth define the VEX IQ competition area
// texture_path can be NULL for no texture
bool floor_init(Floor* f, float size, float grid_size, float field_width, float field_depth,
                float wall_height, const char* texture_path);

// Cleanup
void floor_destroy(Floor* f);

// Render floor and walls
void floor_render(Floor* f, Mat4* view, Mat4* projection, Vec3 camera_pos);

#endif // FLOOR_H
