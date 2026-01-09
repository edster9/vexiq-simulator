/*
 * Mesh Renderer
 * Renders mesh data with OpenGL using vertex colors and basic lighting
 */

#ifndef MESH_H
#define MESH_H

#include <GL/glew.h>
#include "glb_loader.h"
#include "shader.h"
#include "../math/mat4.h"
#include "../math/vec3.h"

typedef struct Mesh {
    GLuint vao;
    GLuint vbo;
    GLuint ebo;
    GLuint shader_program;  // OpenGL shader program ID

    uint32_t vertex_count;
    uint32_t index_count;

    // Bounding box (from MeshData)
    float min_bounds[3];
    float max_bounds[3];
    float center[3];
    float size[3];
} Mesh;

// Create mesh from loaded MeshData
bool mesh_create(Mesh* mesh, const MeshData* data);

// Render mesh with given transform and camera matrices
// color_override: RGB color to apply to white vertices (NULL = no override)
void mesh_render(Mesh* mesh, const Mat4* model, const Mat4* view, const Mat4* projection, Vec3 light_dir, const float* color_override);

// Destroy mesh and free OpenGL resources
void mesh_destroy(Mesh* mesh);

// Create the shared mesh shader (call once at startup)
bool mesh_shader_create(Shader* shader);

// Set the shared shader for all meshes
void mesh_set_shader(Shader* shader);

#endif // MESH_H
