/*
 * Mesh Renderer Implementation
 */

#include "mesh.h"
#include "shader.h"
#include <stdio.h>
#include <string.h>

// Shared shader for all meshes (pointer to external shader)
static Shader* s_mesh_shader = NULL;

// Vertex shader for mesh rendering
static const char* mesh_vertex_shader = R"(
#version 330 core

layout(location = 0) in vec3 a_position;
layout(location = 1) in vec3 a_normal;
layout(location = 2) in vec4 a_color;

uniform mat4 u_model;
uniform mat4 u_view;
uniform mat4 u_projection;
uniform mat3 u_normal_matrix;

out vec3 v_position;
out vec3 v_normal;
out vec4 v_color;

void main() {
    vec4 world_pos = u_model * vec4(a_position, 1.0);
    v_position = world_pos.xyz;
    v_normal = normalize(u_normal_matrix * a_normal);
    v_color = a_color;
    gl_Position = u_projection * u_view * world_pos;
}
)";

// Fragment shader with basic lighting and color override
static const char* mesh_fragment_shader = R"(
#version 330 core

in vec3 v_position;
in vec3 v_normal;
in vec4 v_color;

uniform vec3 u_light_dir;
uniform vec3 u_camera_pos;
uniform vec3 u_color_override;   // RGB override color
uniform float u_use_override;    // 1.0 = apply override to white vertices, 0.0 = no override

out vec4 frag_color;

void main() {
    // Normalize inputs
    vec3 N = normalize(v_normal);
    vec3 L = normalize(u_light_dir);
    vec3 V = normalize(u_camera_pos - v_position);
    vec3 H = normalize(L + V);

    // Lighting
    float ambient = 0.3;
    float diffuse = max(dot(N, L), 0.0) * 0.6;
    float specular = pow(max(dot(N, H), 0.0), 32.0) * 0.2;

    // Check if vertex is white (colorable) - threshold 0.95
    float is_white = step(0.95, v_color.r) * step(0.95, v_color.g) * step(0.95, v_color.b);

    // Apply color override to white vertices when override is enabled
    vec3 base_color = mix(v_color.rgb, u_color_override, is_white * u_use_override);

    // Combine with lighting
    vec3 color = base_color * (ambient + diffuse) + vec3(specular);

    // Slight fresnel for plastic look
    float fresnel = pow(1.0 - max(dot(N, V), 0.0), 3.0) * 0.15;
    color += vec3(fresnel);

    frag_color = vec4(color, v_color.a);
}
)";

bool mesh_shader_create(Shader* shader) {
    if (!shader_create(shader, mesh_vertex_shader, mesh_fragment_shader)) {
        fprintf(stderr, "[Mesh] Failed to create shader\n");
        return false;
    }
    return true;
}

void mesh_set_shader(Shader* shader) {
    s_mesh_shader = shader;
}

bool mesh_create(Mesh* mesh, const MeshData* data) {
    memset(mesh, 0, sizeof(Mesh));

    if (!data || data->vertex_count == 0) {
        fprintf(stderr, "[Mesh] No vertex data\n");
        return false;
    }

    // Copy bounds
    memcpy(mesh->min_bounds, data->min_bounds, sizeof(mesh->min_bounds));
    memcpy(mesh->max_bounds, data->max_bounds, sizeof(mesh->max_bounds));

    // Calculate center and size
    for (int i = 0; i < 3; i++) {
        mesh->center[i] = (data->min_bounds[i] + data->max_bounds[i]) * 0.5f;
        mesh->size[i] = data->max_bounds[i] - data->min_bounds[i];
    }

    mesh->vertex_count = data->vertex_count;
    mesh->index_count = data->index_count;

    // Create VAO
    glGenVertexArrays(1, &mesh->vao);
    glBindVertexArray(mesh->vao);

    // Create VBO
    glGenBuffers(1, &mesh->vbo);
    glBindBuffer(GL_ARRAY_BUFFER, mesh->vbo);
    glBufferData(GL_ARRAY_BUFFER, data->vertex_count * sizeof(Vertex), data->vertices, GL_STATIC_DRAW);

    // Position attribute (location 0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, sizeof(Vertex), (void*)offsetof(Vertex, position));
    glEnableVertexAttribArray(0);

    // Normal attribute (location 1)
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, sizeof(Vertex), (void*)offsetof(Vertex, normal));
    glEnableVertexAttribArray(1);

    // Color attribute (location 2)
    glVertexAttribPointer(2, 4, GL_FLOAT, GL_FALSE, sizeof(Vertex), (void*)offsetof(Vertex, color));
    glEnableVertexAttribArray(2);

    // Create EBO if we have indices
    if (data->indices && data->index_count > 0) {
        glGenBuffers(1, &mesh->ebo);
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, mesh->ebo);
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, data->index_count * sizeof(uint32_t), data->indices, GL_STATIC_DRAW);
    }

    glBindVertexArray(0);

    // Use shared shader
    mesh->shader_program = s_mesh_shader ? s_mesh_shader->program : 0;

    printf("[Mesh] Created: %u vertices, %u indices, size=(%.2f, %.2f, %.2f)\n",
           mesh->vertex_count, mesh->index_count,
           mesh->size[0], mesh->size[1], mesh->size[2]);

    return true;
}

void mesh_render(Mesh* mesh, const Mat4* model, const Mat4* view, const Mat4* projection, Vec3 light_dir, const float* color_override) {
    if (!mesh->vao || !mesh->shader_program) return;

    glUseProgram(mesh->shader_program);

    // Set uniforms
    glUniformMatrix4fv(glGetUniformLocation(mesh->shader_program, "u_model"), 1, GL_FALSE, model->m);
    glUniformMatrix4fv(glGetUniformLocation(mesh->shader_program, "u_view"), 1, GL_FALSE, view->m);
    glUniformMatrix4fv(glGetUniformLocation(mesh->shader_program, "u_projection"), 1, GL_FALSE, projection->m);

    // Calculate normal matrix (transpose of inverse of upper-left 3x3 of model)
    // For simple transforms (no non-uniform scale), we can just use upper 3x3
    float normal_matrix[9] = {
        model->m[0], model->m[1], model->m[2],
        model->m[4], model->m[5], model->m[6],
        model->m[8], model->m[9], model->m[10]
    };
    glUniformMatrix3fv(glGetUniformLocation(mesh->shader_program, "u_normal_matrix"), 1, GL_FALSE, normal_matrix);

    glUniform3f(glGetUniformLocation(mesh->shader_program, "u_light_dir"), light_dir.x, light_dir.y, light_dir.z);

    // Get camera position from inverse view matrix (position is -transpose(R) * t)
    // For simplicity, approximate with view matrix column 3 negated
    float cam_x = -(view->m[0] * view->m[12] + view->m[1] * view->m[13] + view->m[2] * view->m[14]);
    float cam_y = -(view->m[4] * view->m[12] + view->m[5] * view->m[13] + view->m[6] * view->m[14]);
    float cam_z = -(view->m[8] * view->m[12] + view->m[9] * view->m[13] + view->m[10] * view->m[14]);
    glUniform3f(glGetUniformLocation(mesh->shader_program, "u_camera_pos"), cam_x, cam_y, cam_z);

    // Set color override
    if (color_override) {
        glUniform3f(glGetUniformLocation(mesh->shader_program, "u_color_override"),
                    color_override[0], color_override[1], color_override[2]);
        glUniform1f(glGetUniformLocation(mesh->shader_program, "u_use_override"), 1.0f);
    } else {
        glUniform3f(glGetUniformLocation(mesh->shader_program, "u_color_override"), 1.0f, 1.0f, 1.0f);
        glUniform1f(glGetUniformLocation(mesh->shader_program, "u_use_override"), 0.0f);
    }

    // Draw
    glBindVertexArray(mesh->vao);

    if (mesh->index_count > 0) {
        glDrawElements(GL_TRIANGLES, mesh->index_count, GL_UNSIGNED_INT, 0);
    } else {
        glDrawArrays(GL_TRIANGLES, 0, mesh->vertex_count);
    }

    glBindVertexArray(0);
}

void mesh_destroy(Mesh* mesh) {
    if (mesh->vao) {
        glDeleteVertexArrays(1, &mesh->vao);
        mesh->vao = 0;
    }
    if (mesh->vbo) {
        glDeleteBuffers(1, &mesh->vbo);
        mesh->vbo = 0;
    }
    if (mesh->ebo) {
        glDeleteBuffers(1, &mesh->ebo);
        mesh->ebo = 0;
    }
    // Don't delete shader - it's shared
    mesh->shader_program = 0;
}
