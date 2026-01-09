#include "floor.h"
#include <stdio.h>

// Vertex shader
static const char* floor_vert_src =
    "#version 330 core\n"
    "layout (location = 0) in vec3 aPos;\n"
    "out vec3 worldPos;\n"
    "uniform mat4 view;\n"
    "uniform mat4 projection;\n"
    "void main() {\n"
    "    worldPos = aPos;\n"
    "    gl_Position = projection * view * vec4(aPos, 1.0);\n"
    "}\n";

// Fragment shader - VEX IQ field style (gray tiles with grid)
// World scale: 1 unit = 1 inch, grid = 12" (1 foot)
static const char* floor_frag_src =
    "#version 330 core\n"
    "in vec3 worldPos;\n"
    "out vec4 FragColor;\n"
    "uniform float gridSize;\n"
    "uniform vec3 cameraPos;\n"
    "uniform float fieldWidth;\n"   // 96 inches (8 ft)
    "uniform float fieldDepth;\n"   // 72 inches (6 ft)
    "\n"
    "void main() {\n"
    "    // Check if we're inside the VEX IQ field bounds\n"
    "    float halfW = fieldWidth * 0.5;\n"
    "    float halfD = fieldDepth * 0.5;\n"
    "    bool insideField = abs(worldPos.x) <= halfW && abs(worldPos.z) <= halfD;\n"
    "\n"
    "    // Base color: field gray inside, darker outside\n"
    "    vec3 fieldGray = vec3(0.5, 0.5, 0.52);\n"
    "    vec3 outsideGray = vec3(0.25, 0.25, 0.27);\n"
    "    vec3 baseColor = insideField ? fieldGray : outsideGray;\n"
    "\n"
    "    // Grid lines every gridSize (12 inches = 1 foot)\n"
    "    vec2 gridCoord = worldPos.xz / gridSize;\n"
    "    vec2 grid = abs(fract(gridCoord - 0.5) - 0.5);\n"
    "    vec2 lineWidth = fwidth(gridCoord) * 1.5;\n"
    "    vec2 gridLines = smoothstep(lineWidth, vec2(0.0), grid);\n"
    "    float gridLine = max(gridLines.x, gridLines.y);\n"
    "\n"
    "    // Field boundary (thicker lines at edges)\n"
    "    float boundaryX = smoothstep(0.5, 0.0, abs(abs(worldPos.x) - halfW) / 0.5);\n"
    "    float boundaryZ = smoothstep(0.5, 0.0, abs(abs(worldPos.z) - halfD) / 0.5);\n"
    "    float boundary = max(boundaryX, boundaryZ);\n"
    "\n"
    "    // Origin axes (thicker)\n"
    "    float axisWidth = 0.25;  // 1/4 inch wide\n"
    "    float xAxis = smoothstep(axisWidth, 0.0, abs(worldPos.z));\n"
    "    float zAxis = smoothstep(axisWidth, 0.0, abs(worldPos.x));\n"
    "\n"
    "    // Combine colors\n"
    "    vec3 color = baseColor;\n"
    "    vec3 gridColor = insideField ? vec3(0.35, 0.35, 0.38) : vec3(0.2, 0.2, 0.22);\n"
    "    color = mix(color, gridColor, gridLine * 0.7);\n"
    "    color = mix(color, vec3(1.0, 0.3, 0.3), xAxis * 0.8);  // X axis red\n"
    "    color = mix(color, vec3(0.3, 0.3, 1.0), zAxis * 0.8);  // Z axis blue\n"
    "    color = mix(color, vec3(0.9, 0.9, 0.2), boundary * 0.8);  // Yellow field boundary\n"
    "\n"
    "    // Subtle distance fog (adjusted for inch scale)\n"
    "    float dist = length(worldPos.xz - cameraPos.xz);\n"
    "    float fog = 1.0 - exp(-dist * 0.001);\n"
    "    color = mix(color, vec3(0.15, 0.15, 0.18), fog * 0.5);\n"
    "\n"
    "    FragColor = vec4(color, 1.0);\n"
    "}\n";

bool floor_init(Floor* f, float size, float grid_size, float field_width, float field_depth) {
    f->size = size;
    f->grid_size = grid_size;
    f->field_width = field_width;
    f->field_depth = field_depth;

    if (!shader_create(&f->shader, floor_vert_src, floor_frag_src)) {
        fprintf(stderr, "Failed to create floor shader\n");
        return false;
    }

    float half = size / 2.0f;
    float vertices[] = {
        -half, 0.0f, -half,
         half, 0.0f, -half,
         half, 0.0f,  half,

        -half, 0.0f, -half,
         half, 0.0f,  half,
        -half, 0.0f,  half,
    };

    glGenVertexArrays(1, &f->vao);
    glGenBuffers(1, &f->vbo);

    glBindVertexArray(f->vao);
    glBindBuffer(GL_ARRAY_BUFFER, f->vbo);
    glBufferData(GL_ARRAY_BUFFER, sizeof(vertices), vertices, GL_STATIC_DRAW);

    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);

    glBindVertexArray(0);

    return true;
}

void floor_destroy(Floor* f) {
    shader_destroy(&f->shader);
    glDeleteVertexArrays(1, &f->vao);
    glDeleteBuffers(1, &f->vbo);
}

void floor_render(Floor* f, Mat4* view, Mat4* projection, Vec3 camera_pos) {
    shader_use(&f->shader);
    shader_set_mat4(&f->shader, "view", view);
    shader_set_mat4(&f->shader, "projection", projection);
    shader_set_float(&f->shader, "gridSize", f->grid_size);
    shader_set_float(&f->shader, "fieldWidth", f->field_width);
    shader_set_float(&f->shader, "fieldDepth", f->field_depth);
    shader_set_vec3(&f->shader, "cameraPos", camera_pos);

    glBindVertexArray(f->vao);
    glDrawArrays(GL_TRIANGLES, 0, 6);
    glBindVertexArray(0);

    glUseProgram(0);
}
