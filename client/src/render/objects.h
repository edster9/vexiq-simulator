/*
 * Game Objects Renderer
 * Renders game objects like cylinders on the field
 */

#ifndef OBJECTS_H
#define OBJECTS_H

#include <stdbool.h>
#include <GL/glew.h>
#include "shader.h"
#include "../math/mat4.h"
#include "../math/vec3.h"

#define MAX_GAME_OBJECTS 32

typedef struct GameObject {
    float x, y, z;        // Position (y is height above ground)
    float radius;         // For cylinders: radius
    float height;         // For cylinders: height
    float r, g, b;        // Color
    bool active;
} GameObject;

typedef struct GameObjects {
    GameObject objects[MAX_GAME_OBJECTS];
    int count;

    // OpenGL resources for cylinder
    GLuint cylinder_vao;
    GLuint cylinder_vbo;
    int cylinder_vertex_count;
    Shader shader;
} GameObjects;

// Initialize the game objects system
bool objects_init(GameObjects* objs);

// Cleanup
void objects_destroy(GameObjects* objs);

// Add a cylinder at position (x, z) on the field
// radius and height in inches
int objects_add_cylinder(GameObjects* objs, float x, float z, float radius, float height,
                         float r, float g, float b);

// Clear all objects
void objects_clear(GameObjects* objs);

// Render all objects
void objects_render(GameObjects* objs, Mat4* view, Mat4* projection, Vec3 camera_pos);

#endif // OBJECTS_H
