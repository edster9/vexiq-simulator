/*
 * Debug Renderer Implementation
 * Uses immediate-mode style API with batched rendering
 */

#include "debug.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <vector>

// Maximum vertices per batch
#define DEBUG_MAX_VERTICES 65536

// Vertex: position + color
struct DebugVertex {
    float x, y, z;
    float r, g, b;
};

// Shader sources
static const char* debug_vert_src = R"(
#version 330 core
layout (location = 0) in vec3 aPos;
layout (location = 1) in vec3 aColor;
out vec3 vertColor;
uniform mat4 viewProjection;
void main() {
    vertColor = aColor;
    gl_Position = viewProjection * vec4(aPos, 1.0);
}
)";

static const char* debug_frag_src = R"(
#version 330 core
in vec3 vertColor;
out vec4 FragColor;
void main() {
    FragColor = vec4(vertColor, 1.0);
}
)";

// Global state
static struct {
    GLuint shader;
    GLint vp_loc;
    GLuint vao;
    GLuint vbo;

    std::vector<DebugVertex> vertices;
    Mat4 view_projection;
    bool initialized;
    bool in_frame;
} g_debug;

bool debug_init(void) {
    if (g_debug.initialized) return true;

    // Compile shaders
    GLuint vert = glCreateShader(GL_VERTEX_SHADER);
    glShaderSource(vert, 1, &debug_vert_src, NULL);
    glCompileShader(vert);

    GLint success;
    glGetShaderiv(vert, GL_COMPILE_STATUS, &success);
    if (!success) {
        char log[512];
        glGetShaderInfoLog(vert, sizeof(log), NULL, log);
        fprintf(stderr, "[Debug] Vertex shader error: %s\n", log);
        return false;
    }

    GLuint frag = glCreateShader(GL_FRAGMENT_SHADER);
    glShaderSource(frag, 1, &debug_frag_src, NULL);
    glCompileShader(frag);

    glGetShaderiv(frag, GL_COMPILE_STATUS, &success);
    if (!success) {
        char log[512];
        glGetShaderInfoLog(frag, sizeof(log), NULL, log);
        fprintf(stderr, "[Debug] Fragment shader error: %s\n", log);
        glDeleteShader(vert);
        return false;
    }

    g_debug.shader = glCreateProgram();
    glAttachShader(g_debug.shader, vert);
    glAttachShader(g_debug.shader, frag);
    glLinkProgram(g_debug.shader);
    glDeleteShader(vert);
    glDeleteShader(frag);

    glGetProgramiv(g_debug.shader, GL_LINK_STATUS, &success);
    if (!success) {
        char log[512];
        glGetProgramInfoLog(g_debug.shader, sizeof(log), NULL, log);
        fprintf(stderr, "[Debug] Shader link error: %s\n", log);
        return false;
    }

    g_debug.vp_loc = glGetUniformLocation(g_debug.shader, "viewProjection");

    // Create VAO/VBO
    glGenVertexArrays(1, &g_debug.vao);
    glGenBuffers(1, &g_debug.vbo);

    glBindVertexArray(g_debug.vao);
    glBindBuffer(GL_ARRAY_BUFFER, g_debug.vbo);
    glBufferData(GL_ARRAY_BUFFER, DEBUG_MAX_VERTICES * sizeof(DebugVertex), NULL, GL_DYNAMIC_DRAW);

    // Position attribute
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, sizeof(DebugVertex), (void*)0);
    glEnableVertexAttribArray(0);

    // Color attribute
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, sizeof(DebugVertex), (void*)(3 * sizeof(float)));
    glEnableVertexAttribArray(1);

    glBindVertexArray(0);

    g_debug.vertices.reserve(DEBUG_MAX_VERTICES);
    g_debug.initialized = true;
    g_debug.in_frame = false;

    printf("[Debug] Renderer initialized\n");
    return true;
}

void debug_destroy(void) {
    if (!g_debug.initialized) return;

    glDeleteVertexArrays(1, &g_debug.vao);
    glDeleteBuffers(1, &g_debug.vbo);
    glDeleteProgram(g_debug.shader);

    g_debug.vertices.clear();
    g_debug.initialized = false;
}

void debug_begin(const Mat4* view, const Mat4* projection) {
    if (!g_debug.initialized) return;

    // Compute view-projection matrix
    g_debug.view_projection = mat4_mul(*projection, *view);
    g_debug.vertices.clear();
    g_debug.in_frame = true;
}

// Add a line to the batch
static void add_line(float x1, float y1, float z1, float x2, float y2, float z2, float r, float g, float b) {
    if (g_debug.vertices.size() + 2 > DEBUG_MAX_VERTICES) return;

    g_debug.vertices.push_back({x1, y1, z1, r, g, b});
    g_debug.vertices.push_back({x2, y2, z2, r, g, b});
}

void debug_draw_line(Vec3 a, Vec3 b, Vec3 color) {
    if (!g_debug.in_frame) return;
    add_line(a.x, a.y, a.z, b.x, b.y, b.z, color.x, color.y, color.z);
}

void debug_draw_box(Vec3 center, Vec3 half_extents, Vec3 color) {
    if (!g_debug.in_frame) return;

    float cx = center.x, cy = center.y, cz = center.z;
    float hx = half_extents.x, hy = half_extents.y, hz = half_extents.z;
    float r = color.x, g = color.y, b = color.z;

    // 8 corners
    float x0 = cx - hx, x1 = cx + hx;
    float y0 = cy - hy, y1 = cy + hy;
    float z0 = cz - hz, z1 = cz + hz;

    // Bottom face (y0)
    add_line(x0, y0, z0, x1, y0, z0, r, g, b);
    add_line(x1, y0, z0, x1, y0, z1, r, g, b);
    add_line(x1, y0, z1, x0, y0, z1, r, g, b);
    add_line(x0, y0, z1, x0, y0, z0, r, g, b);

    // Top face (y1)
    add_line(x0, y1, z0, x1, y1, z0, r, g, b);
    add_line(x1, y1, z0, x1, y1, z1, r, g, b);
    add_line(x1, y1, z1, x0, y1, z1, r, g, b);
    add_line(x0, y1, z1, x0, y1, z0, r, g, b);

    // Vertical edges
    add_line(x0, y0, z0, x0, y1, z0, r, g, b);
    add_line(x1, y0, z0, x1, y1, z0, r, g, b);
    add_line(x1, y0, z1, x1, y1, z1, r, g, b);
    add_line(x0, y0, z1, x0, y1, z1, r, g, b);
}

void debug_draw_box_transformed(const Mat4* model, const float* min_bounds, const float* max_bounds, Vec3 color) {
    if (!g_debug.in_frame) return;

    float r = color.x, g = color.y, b = color.z;

    // 8 corners in local space
    float corners[8][3];
    for (int i = 0; i < 8; i++) {
        corners[i][0] = (i & 1) ? max_bounds[0] : min_bounds[0];
        corners[i][1] = (i & 2) ? max_bounds[1] : min_bounds[1];
        corners[i][2] = (i & 4) ? max_bounds[2] : min_bounds[2];
    }

    // Transform corners to world space
    float world[8][3];
    for (int i = 0; i < 8; i++) {
        float x = corners[i][0], y = corners[i][1], z = corners[i][2];
        world[i][0] = model->m[0]*x + model->m[4]*y + model->m[8]*z + model->m[12];
        world[i][1] = model->m[1]*x + model->m[5]*y + model->m[9]*z + model->m[13];
        world[i][2] = model->m[2]*x + model->m[6]*y + model->m[10]*z + model->m[14];
    }

    // Draw 12 edges
    // Bottom face: 0-1, 1-3, 3-2, 2-0
    add_line(world[0][0], world[0][1], world[0][2], world[1][0], world[1][1], world[1][2], r, g, b);
    add_line(world[1][0], world[1][1], world[1][2], world[3][0], world[3][1], world[3][2], r, g, b);
    add_line(world[3][0], world[3][1], world[3][2], world[2][0], world[2][1], world[2][2], r, g, b);
    add_line(world[2][0], world[2][1], world[2][2], world[0][0], world[0][1], world[0][2], r, g, b);

    // Top face: 4-5, 5-7, 7-6, 6-4
    add_line(world[4][0], world[4][1], world[4][2], world[5][0], world[5][1], world[5][2], r, g, b);
    add_line(world[5][0], world[5][1], world[5][2], world[7][0], world[7][1], world[7][2], r, g, b);
    add_line(world[7][0], world[7][1], world[7][2], world[6][0], world[6][1], world[6][2], r, g, b);
    add_line(world[6][0], world[6][1], world[6][2], world[4][0], world[4][1], world[4][2], r, g, b);

    // Vertical edges: 0-4, 1-5, 2-6, 3-7
    add_line(world[0][0], world[0][1], world[0][2], world[4][0], world[4][1], world[4][2], r, g, b);
    add_line(world[1][0], world[1][1], world[1][2], world[5][0], world[5][1], world[5][2], r, g, b);
    add_line(world[2][0], world[2][1], world[2][2], world[6][0], world[6][1], world[6][2], r, g, b);
    add_line(world[3][0], world[3][1], world[3][2], world[7][0], world[7][1], world[7][2], r, g, b);
}

void debug_draw_axes(Vec3 pos, float length) {
    if (!g_debug.in_frame) return;

    // X axis (red)
    add_line(pos.x, pos.y, pos.z, pos.x + length, pos.y, pos.z, 1, 0, 0);
    // Y axis (green)
    add_line(pos.x, pos.y, pos.z, pos.x, pos.y + length, pos.z, 0, 1, 0);
    // Z axis (blue)
    add_line(pos.x, pos.y, pos.z, pos.x, pos.y, pos.z + length, 0, 0, 1);
}

void debug_draw_cylinder(Vec3 center, float radius, float half_height, Vec3 color) {
    if (!g_debug.in_frame) return;

    float r = color.x, g = color.y, b = color.z;
    int segments = 16;
    float y_top = center.y + half_height;
    float y_bot = center.y - half_height;

    float prev_x = center.x + radius;
    float prev_z = center.z;

    for (int i = 1; i <= segments; i++) {
        float angle = (float)i / segments * 2.0f * 3.14159265f;
        float x = center.x + radius * cosf(angle);
        float z = center.z + radius * sinf(angle);

        // Top circle
        add_line(prev_x, y_top, prev_z, x, y_top, z, r, g, b);
        // Bottom circle
        add_line(prev_x, y_bot, prev_z, x, y_bot, z, r, g, b);
        // Vertical lines (every 4th segment)
        if (i % 4 == 0) {
            add_line(x, y_bot, z, x, y_top, z, r, g, b);
        }

        prev_x = x;
        prev_z = z;
    }
}

void debug_end(void) {
    if (!g_debug.initialized || !g_debug.in_frame) return;
    if (g_debug.vertices.empty()) {
        g_debug.in_frame = false;
        return;
    }

    // Upload vertex data
    glBindBuffer(GL_ARRAY_BUFFER, g_debug.vbo);
    glBufferSubData(GL_ARRAY_BUFFER, 0,
                    g_debug.vertices.size() * sizeof(DebugVertex),
                    g_debug.vertices.data());

    // Render
    glUseProgram(g_debug.shader);
    glUniformMatrix4fv(g_debug.vp_loc, 1, GL_FALSE, g_debug.view_projection.m);

    glBindVertexArray(g_debug.vao);
    glDrawArrays(GL_LINES, 0, (GLsizei)g_debug.vertices.size());
    glBindVertexArray(0);

    g_debug.in_frame = false;
}
