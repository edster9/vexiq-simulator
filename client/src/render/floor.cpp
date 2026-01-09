#include "floor.h"
#include <stdio.h>
#include <stdlib.h>

// stb_image for texture loading
#define STB_IMAGE_IMPLEMENTATION
#include "../third_party/stb_image.h"

// Floor vertex shader (with texture coords)
static const char* floor_vert_src = R"(
#version 330 core
layout (location = 0) in vec3 aPos;
layout (location = 1) in vec2 aTexCoord;
out vec3 worldPos;
out vec2 texCoord;
uniform mat4 view;
uniform mat4 projection;
void main() {
    worldPos = aPos;
    texCoord = aTexCoord;
    gl_Position = projection * view * vec4(aPos, 1.0);
}
)";

// Floor fragment shader - VEX IQ field with optional tile texture
static const char* floor_frag_src = R"(
#version 330 core
in vec3 worldPos;
in vec2 texCoord;
out vec4 FragColor;

uniform float gridSize;
uniform vec3 cameraPos;
uniform float fieldWidth;   // 96 inches (8 ft)
uniform float fieldDepth;   // 72 inches (6 ft)
uniform sampler2D tileTexture;
uniform int useTexture;

void main() {
    // Check if we're inside the VEX IQ field bounds
    float halfW = fieldWidth * 0.5;
    float halfD = fieldDepth * 0.5;
    bool insideField = abs(worldPos.x) <= halfW && abs(worldPos.z) <= halfD;

    // Base color from texture or solid color
    vec3 baseColor;
    if (useTexture == 1 && insideField) {
        // Tile the texture every 12 inches (1 foot), offset by 50% to center tiles
        vec2 tileCoord = worldPos.xz / 12.0 + 0.5;
        baseColor = texture(tileTexture, tileCoord).rgb;
    } else {
        // Solid colors
        vec3 fieldGray = vec3(0.5, 0.5, 0.52);
        vec3 outsideGray = vec3(0.25, 0.25, 0.27);
        baseColor = insideField ? fieldGray : outsideGray;
    }

    // Grid lines - only outside field or if no texture
    if (useTexture == 0 || !insideField) {
        vec2 gridCoord = worldPos.xz / gridSize;
        vec2 grid = abs(fract(gridCoord - 0.5) - 0.5);
        vec2 lineWidth = fwidth(gridCoord) * 1.5;
        vec2 gridLines = smoothstep(lineWidth, vec2(0.0), grid);
        float gridLine = max(gridLines.x, gridLines.y);
        vec3 gridColor = insideField ? vec3(0.35, 0.35, 0.38) : vec3(0.2, 0.2, 0.22);
        baseColor = mix(baseColor, gridColor, gridLine * 0.5);
    }

    // Field boundary (yellow lines at edges)
    float boundaryWidth = 0.5;
    float boundaryX = smoothstep(boundaryWidth, 0.0, abs(abs(worldPos.x) - halfW));
    float boundaryZ = smoothstep(boundaryWidth, 0.0, abs(abs(worldPos.z) - halfD));
    float boundary = max(boundaryX, boundaryZ);
    baseColor = mix(baseColor, vec3(0.9, 0.9, 0.2), boundary * 0.9);

    // Origin marker (subtle cross at center)
    float axisWidth = 0.25;
    float xAxis = smoothstep(axisWidth, 0.0, abs(worldPos.z)) * step(abs(worldPos.x), 6.0);
    float zAxis = smoothstep(axisWidth, 0.0, abs(worldPos.x)) * step(abs(worldPos.z), 6.0);
    baseColor = mix(baseColor, vec3(1.0, 0.3, 0.3), xAxis * 0.5);
    baseColor = mix(baseColor, vec3(0.3, 0.3, 1.0), zAxis * 0.5);

    // Subtle distance fog
    float dist = length(worldPos.xz - cameraPos.xz);
    float fog = 1.0 - exp(-dist * 0.001);
    baseColor = mix(baseColor, vec3(0.15, 0.15, 0.18), fog * 0.3);

    FragColor = vec4(baseColor, 1.0);
}
)";

// Wall vertex shader
static const char* wall_vert_src = R"(
#version 330 core
layout (location = 0) in vec3 aPos;
layout (location = 1) in vec3 aNormal;
out vec3 worldPos;
out vec3 normal;
uniform mat4 view;
uniform mat4 projection;
void main() {
    worldPos = aPos;
    normal = aNormal;
    gl_Position = projection * view * vec4(aPos, 1.0);
}
)";

// Wall fragment shader - simple gray walls
static const char* wall_frag_src = R"(
#version 330 core
in vec3 worldPos;
in vec3 normal;
out vec4 FragColor;
uniform vec3 cameraPos;
uniform float wallHeight;

void main() {
    // Simple directional lighting
    vec3 lightDir = normalize(vec3(0.5, 1.0, 0.3));
    float diff = max(dot(normalize(normal), lightDir), 0.0);
    float ambient = 0.4;
    float lighting = ambient + diff * 0.6;

    // Wall color (mid gray)
    vec3 wallColor = vec3(0.5, 0.5, 0.5) * lighting;

    // Top edge highlight
    float topEdge = smoothstep(0.2, 0.0, abs(worldPos.y - wallHeight));
    wallColor += vec3(0.1) * topEdge;

    FragColor = vec4(wallColor, 1.0);
}
)";

// Helper to add a wall segment (6 vertices with position + normal)
static void add_wall_segment(float* verts, int* idx,
                             float x1, float z1, float x2, float z2,
                             float height, float nx, float nz) {
    int i = *idx;
    // Triangle 1: bottom-left, bottom-right, top-right
    verts[i++] = x1; verts[i++] = 0;      verts[i++] = z1;
    verts[i++] = nx; verts[i++] = 0;      verts[i++] = nz;
    verts[i++] = x2; verts[i++] = 0;      verts[i++] = z2;
    verts[i++] = nx; verts[i++] = 0;      verts[i++] = nz;
    verts[i++] = x2; verts[i++] = height; verts[i++] = z2;
    verts[i++] = nx; verts[i++] = 0;      verts[i++] = nz;
    // Triangle 2: bottom-left, top-right, top-left
    verts[i++] = x1; verts[i++] = 0;      verts[i++] = z1;
    verts[i++] = nx; verts[i++] = 0;      verts[i++] = nz;
    verts[i++] = x2; verts[i++] = height; verts[i++] = z2;
    verts[i++] = nx; verts[i++] = 0;      verts[i++] = nz;
    verts[i++] = x1; verts[i++] = height; verts[i++] = z1;
    verts[i++] = nx; verts[i++] = 0;      verts[i++] = nz;
    *idx = i;
}

bool floor_init(Floor* f, float size, float grid_size, float field_width, float field_depth,
                float wall_height, const char* texture_path) {
    f->size = size;
    f->grid_size = grid_size;
    f->field_width = field_width;
    f->field_depth = field_depth;
    f->wall_height = wall_height;
    f->texture = 0;

    // Create floor shader
    if (!shader_create(&f->shader, floor_vert_src, floor_frag_src)) {
        fprintf(stderr, "Failed to create floor shader\n");
        return false;
    }

    // Create wall shader
    if (!shader_create(&f->wall_shader, wall_vert_src, wall_frag_src)) {
        fprintf(stderr, "Failed to create wall shader\n");
        shader_destroy(&f->shader);
        return false;
    }

    // Load texture if provided
    if (texture_path) {
        int width, height, channels;
        stbi_set_flip_vertically_on_load(1);
        unsigned char* data = stbi_load(texture_path, &width, &height, &channels, 0);
        if (data) {
            glGenTextures(1, &f->texture);
            glBindTexture(GL_TEXTURE_2D, f->texture);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);

            GLenum format = (channels == 4) ? GL_RGBA : GL_RGB;
            glTexImage2D(GL_TEXTURE_2D, 0, format, width, height, 0, format, GL_UNSIGNED_BYTE, data);
            glGenerateMipmap(GL_TEXTURE_2D);

            stbi_image_free(data);
            printf("[Floor] Loaded texture: %s (%dx%d)\n", texture_path, width, height);
        } else {
            printf("[Floor] Warning: Failed to load texture: %s\n", texture_path);
        }
    }

    // Create floor quad (position + texcoord) - only covers the field area
    float halfW = field_width / 2.0f;
    float halfD = field_depth / 2.0f;

    // Floor vertices: pos (3) + texcoord (2)
    float floor_verts[] = {
        -halfW, 0.0f, -halfD,  -halfW/12.0f, -halfD/12.0f,
         halfW, 0.0f, -halfD,   halfW/12.0f, -halfD/12.0f,
         halfW, 0.0f,  halfD,   halfW/12.0f,  halfD/12.0f,

        -halfW, 0.0f, -halfD,  -halfW/12.0f, -halfD/12.0f,
         halfW, 0.0f,  halfD,   halfW/12.0f,  halfD/12.0f,
        -halfW, 0.0f,  halfD,  -halfW/12.0f,  halfD/12.0f,
    };

    glGenVertexArrays(1, &f->vao);
    glGenBuffers(1, &f->vbo);
    glBindVertexArray(f->vao);
    glBindBuffer(GL_ARRAY_BUFFER, f->vbo);
    glBufferData(GL_ARRAY_BUFFER, sizeof(floor_verts), floor_verts, GL_STATIC_DRAW);

    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 5 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 5 * sizeof(float), (void*)(3 * sizeof(float)));
    glEnableVertexAttribArray(1);
    glBindVertexArray(0);

    // Create wall geometry (4 walls around the field)
    // Each wall: 6 vertices * 6 floats (pos + normal) = 36 floats
    // 4 walls = 144 floats
    float wall_verts[144];
    int idx = 0;
    float h = wall_height;

    // Front wall (+Z, facing inward -Z)
    add_wall_segment(wall_verts, &idx, -halfW, halfD, halfW, halfD, h, 0, -1);
    // Back wall (-Z, facing inward +Z)
    add_wall_segment(wall_verts, &idx, halfW, -halfD, -halfW, -halfD, h, 0, 1);
    // Left wall (-X, facing inward +X)
    add_wall_segment(wall_verts, &idx, -halfW, -halfD, -halfW, halfD, h, 1, 0);
    // Right wall (+X, facing inward -X)
    add_wall_segment(wall_verts, &idx, halfW, halfD, halfW, -halfD, h, -1, 0);

    f->wall_vertex_count = 24;  // 4 walls * 6 vertices

    glGenVertexArrays(1, &f->wall_vao);
    glGenBuffers(1, &f->wall_vbo);
    glBindVertexArray(f->wall_vao);
    glBindBuffer(GL_ARRAY_BUFFER, f->wall_vbo);
    glBufferData(GL_ARRAY_BUFFER, sizeof(wall_verts), wall_verts, GL_STATIC_DRAW);

    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)(3 * sizeof(float)));
    glEnableVertexAttribArray(1);
    glBindVertexArray(0);

    printf("[Floor] Initialized: %.0fx%.0f\" field with %.0f\" walls\n",
           field_width, field_depth, wall_height);
    return true;
}

void floor_destroy(Floor* f) {
    shader_destroy(&f->shader);
    shader_destroy(&f->wall_shader);
    glDeleteVertexArrays(1, &f->vao);
    glDeleteBuffers(1, &f->vbo);
    glDeleteVertexArrays(1, &f->wall_vao);
    glDeleteBuffers(1, &f->wall_vbo);
    if (f->texture) {
        glDeleteTextures(1, &f->texture);
    }
}

void floor_render(Floor* f, Mat4* view, Mat4* projection, Vec3 camera_pos) {
    // Render floor
    shader_use(&f->shader);
    shader_set_mat4(&f->shader, "view", view);
    shader_set_mat4(&f->shader, "projection", projection);
    shader_set_float(&f->shader, "gridSize", f->grid_size);
    shader_set_float(&f->shader, "fieldWidth", f->field_width);
    shader_set_float(&f->shader, "fieldDepth", f->field_depth);
    shader_set_vec3(&f->shader, "cameraPos", camera_pos);

    // Bind texture if available
    if (f->texture) {
        glActiveTexture(GL_TEXTURE0);
        glBindTexture(GL_TEXTURE_2D, f->texture);
        shader_set_int(&f->shader, "tileTexture", 0);
        shader_set_int(&f->shader, "useTexture", 1);
    } else {
        shader_set_int(&f->shader, "useTexture", 0);
    }

    glBindVertexArray(f->vao);
    glDrawArrays(GL_TRIANGLES, 0, 6);
    glBindVertexArray(0);

    // Render walls
    shader_use(&f->wall_shader);
    shader_set_mat4(&f->wall_shader, "view", view);
    shader_set_mat4(&f->wall_shader, "projection", projection);
    shader_set_vec3(&f->wall_shader, "cameraPos", camera_pos);
    shader_set_float(&f->wall_shader, "wallHeight", f->wall_height);

    glBindVertexArray(f->wall_vao);
    glDrawArrays(GL_TRIANGLES, 0, f->wall_vertex_count);
    glBindVertexArray(0);

    glUseProgram(0);
}
