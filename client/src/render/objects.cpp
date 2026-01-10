#include "objects.h"
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <vector>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// Object vertex shader
static const char* object_vert_src = R"(
#version 330 core
layout (location = 0) in vec3 aPos;
layout (location = 1) in vec3 aNormal;
out vec3 worldPos;
out vec3 normal;
uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;
void main() {
    vec4 world = model * vec4(aPos, 1.0);
    worldPos = world.xyz;
    normal = mat3(transpose(inverse(model))) * aNormal;
    gl_Position = projection * view * world;
}
)";

// Object fragment shader
static const char* object_frag_src = R"(
#version 330 core
in vec3 worldPos;
in vec3 normal;
out vec4 FragColor;
uniform vec3 objectColor;
uniform vec3 cameraPos;

void main() {
    // Simple directional lighting
    vec3 lightDir = normalize(vec3(0.5, 1.0, 0.3));
    vec3 norm = normalize(normal);
    float diff = max(dot(norm, lightDir), 0.0);
    float ambient = 0.3;
    float lighting = ambient + diff * 0.7;

    vec3 color = objectColor * lighting;

    // Simple specular highlight
    vec3 viewDir = normalize(cameraPos - worldPos);
    vec3 reflectDir = reflect(-lightDir, norm);
    float spec = pow(max(dot(viewDir, reflectDir), 0.0), 32.0);
    color += vec3(0.3) * spec;

    FragColor = vec4(color, 1.0);
}
)";

// Generate cylinder mesh (unit cylinder: radius=1, height=1, centered at origin)
static void generate_cylinder_mesh(std::vector<float>& verts, int segments) {
    // Each vertex: position (3) + normal (3) = 6 floats
    // Cylinder sides: segments * 2 triangles * 3 vertices = segments * 6 vertices
    // Top cap: segments triangles * 3 vertices = segments * 3 vertices
    // Bottom cap: segments triangles * 3 vertices = segments * 3 vertices
    // Total: segments * 12 vertices

    float angleStep = 2.0f * M_PI / segments;

    // Cylinder sides
    for (int i = 0; i < segments; i++) {
        float a0 = i * angleStep;
        float a1 = (i + 1) * angleStep;
        float x0 = cosf(a0), z0 = sinf(a0);
        float x1 = cosf(a1), z1 = sinf(a1);

        // Normal for this segment (average of the two edge normals)
        float nx0 = x0, nz0 = z0;
        float nx1 = x1, nz1 = z1;

        // Triangle 1: bottom-left, bottom-right, top-right
        verts.push_back(x0); verts.push_back(0.0f); verts.push_back(z0);
        verts.push_back(nx0); verts.push_back(0.0f); verts.push_back(nz0);

        verts.push_back(x1); verts.push_back(0.0f); verts.push_back(z1);
        verts.push_back(nx1); verts.push_back(0.0f); verts.push_back(nz1);

        verts.push_back(x1); verts.push_back(1.0f); verts.push_back(z1);
        verts.push_back(nx1); verts.push_back(0.0f); verts.push_back(nz1);

        // Triangle 2: bottom-left, top-right, top-left
        verts.push_back(x0); verts.push_back(0.0f); verts.push_back(z0);
        verts.push_back(nx0); verts.push_back(0.0f); verts.push_back(nz0);

        verts.push_back(x1); verts.push_back(1.0f); verts.push_back(z1);
        verts.push_back(nx1); verts.push_back(0.0f); verts.push_back(nz1);

        verts.push_back(x0); verts.push_back(1.0f); verts.push_back(z0);
        verts.push_back(nx0); verts.push_back(0.0f); verts.push_back(nz0);
    }

    // Top cap (y = 1, normal = up)
    for (int i = 0; i < segments; i++) {
        float a0 = i * angleStep;
        float a1 = (i + 1) * angleStep;
        float x0 = cosf(a0), z0 = sinf(a0);
        float x1 = cosf(a1), z1 = sinf(a1);

        // Center vertex
        verts.push_back(0.0f); verts.push_back(1.0f); verts.push_back(0.0f);
        verts.push_back(0.0f); verts.push_back(1.0f); verts.push_back(0.0f);

        verts.push_back(x0); verts.push_back(1.0f); verts.push_back(z0);
        verts.push_back(0.0f); verts.push_back(1.0f); verts.push_back(0.0f);

        verts.push_back(x1); verts.push_back(1.0f); verts.push_back(z1);
        verts.push_back(0.0f); verts.push_back(1.0f); verts.push_back(0.0f);
    }

    // Bottom cap (y = 0, normal = down)
    for (int i = 0; i < segments; i++) {
        float a0 = i * angleStep;
        float a1 = (i + 1) * angleStep;
        float x0 = cosf(a0), z0 = sinf(a0);
        float x1 = cosf(a1), z1 = sinf(a1);

        // Center vertex
        verts.push_back(0.0f); verts.push_back(0.0f); verts.push_back(0.0f);
        verts.push_back(0.0f); verts.push_back(-1.0f); verts.push_back(0.0f);

        // Reverse winding for bottom face
        verts.push_back(x1); verts.push_back(0.0f); verts.push_back(z1);
        verts.push_back(0.0f); verts.push_back(-1.0f); verts.push_back(0.0f);

        verts.push_back(x0); verts.push_back(0.0f); verts.push_back(z0);
        verts.push_back(0.0f); verts.push_back(-1.0f); verts.push_back(0.0f);
    }
}

bool objects_init(GameObjects* objs) {
    objs->count = 0;
    for (int i = 0; i < MAX_GAME_OBJECTS; i++) {
        objs->objects[i].active = false;
    }

    // Create shader
    if (!shader_create(&objs->shader, object_vert_src, object_frag_src)) {
        fprintf(stderr, "Failed to create object shader\n");
        return false;
    }

    // Generate cylinder mesh
    std::vector<float> cylinder_verts;
    generate_cylinder_mesh(cylinder_verts, 32);  // 32 segments for smooth cylinder

    objs->cylinder_vertex_count = cylinder_verts.size() / 6;  // 6 floats per vertex

    // Create VAO/VBO
    glGenVertexArrays(1, &objs->cylinder_vao);
    glGenBuffers(1, &objs->cylinder_vbo);
    glBindVertexArray(objs->cylinder_vao);
    glBindBuffer(GL_ARRAY_BUFFER, objs->cylinder_vbo);
    glBufferData(GL_ARRAY_BUFFER, cylinder_verts.size() * sizeof(float),
                 cylinder_verts.data(), GL_STATIC_DRAW);

    // Position attribute
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);
    // Normal attribute
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)(3 * sizeof(float)));
    glEnableVertexAttribArray(1);

    glBindVertexArray(0);

    printf("[Objects] Initialized with %d cylinder vertices\n", objs->cylinder_vertex_count);
    return true;
}

void objects_destroy(GameObjects* objs) {
    shader_destroy(&objs->shader);
    glDeleteVertexArrays(1, &objs->cylinder_vao);
    glDeleteBuffers(1, &objs->cylinder_vbo);
}

int objects_add_cylinder(GameObjects* objs, float x, float z, float radius, float height,
                         float r, float g, float b) {
    if (objs->count >= MAX_GAME_OBJECTS) {
        fprintf(stderr, "[Objects] Max objects reached\n");
        return -1;
    }

    int idx = objs->count++;
    GameObject* obj = &objs->objects[idx];
    obj->x = x;
    obj->y = 0.0f;  // On the ground
    obj->z = z;
    obj->radius = radius;
    obj->height = height;
    obj->r = r;
    obj->g = g;
    obj->b = b;
    obj->active = true;

    printf("[Objects] Added cylinder at (%.1f, %.1f) radius=%.1f height=%.1f\n",
           x, z, radius, height);
    return idx;
}

void objects_clear(GameObjects* objs) {
    objs->count = 0;
    for (int i = 0; i < MAX_GAME_OBJECTS; i++) {
        objs->objects[i].active = false;
    }
}

void objects_render(GameObjects* objs, Mat4* view, Mat4* projection, Vec3 camera_pos) {
    if (objs->count == 0) return;

    shader_use(&objs->shader);
    shader_set_mat4(&objs->shader, "view", view);
    shader_set_mat4(&objs->shader, "projection", projection);
    shader_set_vec3(&objs->shader, "cameraPos", camera_pos);

    glBindVertexArray(objs->cylinder_vao);

    for (int i = 0; i < objs->count; i++) {
        GameObject* obj = &objs->objects[i];
        if (!obj->active) continue;

        // Create model matrix: translate then scale
        Mat4 model = mat4_identity();

        // Scale: radius for X/Z, height for Y
        Mat4 scale = mat4_identity();
        scale.m[0] = obj->radius;   // X scale
        scale.m[5] = obj->height;   // Y scale
        scale.m[10] = obj->radius;  // Z scale

        // Translate to position
        Mat4 translate = mat4_identity();
        translate.m[12] = obj->x;
        translate.m[13] = obj->y;
        translate.m[14] = obj->z;

        // Model = translate * scale
        model = mat4_mul(translate, scale);

        shader_set_mat4(&objs->shader, "model", &model);
        shader_set_vec3(&objs->shader, "objectColor", vec3(obj->r, obj->g, obj->b));

        glDrawArrays(GL_TRIANGLES, 0, objs->cylinder_vertex_count);
    }

    glBindVertexArray(0);
    glUseProgram(0);
}
