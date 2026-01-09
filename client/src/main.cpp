/*
 * VEX IQ Simulator - C++ SDL Client
 *
 * A 3D visualization client for the VEX IQ Python simulator.
 * Supports loading LDraw MPD files with colored parts.
 */

#include "platform/platform.h"
#include "math/vec3.h"
#include "math/mat4.h"
#include "render/camera.h"
#include "render/floor.h"
#include "render/glb_loader.h"
#include "render/mesh.h"
#include "render/mpd_loader.h"
#include "render/text.h"
#include "ipc/gamepad.h"
#include "ipc/python_bridge.h"

#include <GL/glew.h>
#include <SDL.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <map>
#include <string>
#include <vector>

#ifdef _WIN32
#include <windows.h>
#define PATH_SEP "\\"
#else
#include <unistd.h>
#include <libgen.h>
#define PATH_SEP "/"
#endif

#define WINDOW_WIDTH 1280
#define WINDOW_HEIGHT 720
#define WINDOW_TITLE "VEX IQ Simulator"

// World scale: 1 unit = 1 inch
// VEX IQ field is 8ft x 6ft = 96" x 72"
#define FIELD_WIDTH 96.0f   // 8 feet in inches
#define FIELD_DEPTH 72.0f   // 6 feet in inches
#define GRID_SIZE 12.0f     // 1 foot grid (12 inches)

// ============================================================================
// Orientation Gizmo - screen-space indicator showing camera orientation
// X (red), Y (green), Z (blue) with arrows
// ============================================================================
static const char* axis_vert_src = R"(
#version 330 core
layout (location = 0) in vec3 aPos;
layout (location = 1) in vec3 aColor;
out vec3 vertColor;
uniform mat4 rotation;  // Camera rotation only (no translation)
void main() {
    vertColor = aColor;
    // Apply camera rotation, then project orthographically
    vec4 rotated = rotation * vec4(aPos, 1.0);
    // Simple orthographic projection for the gizmo (scale down to fit in viewport)
    // Use 0.7 scale with Z for depth sorting, ensures arrows fit at any rotation
    gl_Position = vec4(rotated.xy * 0.7, rotated.z * 0.1, 1.0);
}
)";

static const char* axis_frag_src = R"(
#version 330 core
in vec3 vertColor;
out vec4 FragColor;
void main() {
    FragColor = vec4(vertColor, 1.0);
}
)";

struct AxisGizmo {
    GLuint vao, vbo;
    GLuint arrow_vao, arrow_vbo;
    GLuint shader;
    GLint rotation_loc;
    int arrow_vertex_count;
};

static bool axis_gizmo_init(AxisGizmo* axis, float length) {
    float L = length;      // Axis length
    float A = L * 0.25f;   // Arrow head length
    float W = L * 0.08f;   // Arrow head width

    // Axis lines: position (3) + color (3)
    float lines[] = {
        // X axis (red)
        0.0f, 0.0f, 0.0f,  1.0f, 0.2f, 0.2f,
        L,    0.0f, 0.0f,  1.0f, 0.2f, 0.2f,
        // Y axis (green)
        0.0f, 0.0f, 0.0f,  0.2f, 1.0f, 0.2f,
        0.0f, L,    0.0f,  0.2f, 1.0f, 0.2f,
        // Z axis (blue)
        0.0f, 0.0f, 0.0f,  0.4f, 0.4f, 1.0f,
        0.0f, 0.0f, L,     0.4f, 0.4f, 1.0f,
    };

    // Arrow heads (triangles)
    float arrows[] = {
        // X arrow (red) - pointing +X
        L, 0.0f, 0.0f,      1.0f, 0.2f, 0.2f,
        L-A, W, 0.0f,       1.0f, 0.2f, 0.2f,
        L-A, -W, 0.0f,      1.0f, 0.2f, 0.2f,
        L, 0.0f, 0.0f,      1.0f, 0.2f, 0.2f,
        L-A, 0.0f, W,       1.0f, 0.2f, 0.2f,
        L-A, 0.0f, -W,      1.0f, 0.2f, 0.2f,
        // Y arrow (green) - pointing +Y
        0.0f, L, 0.0f,      0.2f, 1.0f, 0.2f,
        W, L-A, 0.0f,       0.2f, 1.0f, 0.2f,
        -W, L-A, 0.0f,      0.2f, 1.0f, 0.2f,
        0.0f, L, 0.0f,      0.2f, 1.0f, 0.2f,
        0.0f, L-A, W,       0.2f, 1.0f, 0.2f,
        0.0f, L-A, -W,      0.2f, 1.0f, 0.2f,
        // Z arrow (blue) - pointing +Z
        0.0f, 0.0f, L,      0.4f, 0.4f, 1.0f,
        W, 0.0f, L-A,       0.4f, 0.4f, 1.0f,
        -W, 0.0f, L-A,      0.4f, 0.4f, 1.0f,
        0.0f, 0.0f, L,      0.4f, 0.4f, 1.0f,
        0.0f, W, L-A,       0.4f, 0.4f, 1.0f,
        0.0f, -W, L-A,      0.4f, 0.4f, 1.0f,
    };
    axis->arrow_vertex_count = 18;

    // Create shader
    GLuint vert = glCreateShader(GL_VERTEX_SHADER);
    glShaderSource(vert, 1, &axis_vert_src, NULL);
    glCompileShader(vert);

    GLuint frag = glCreateShader(GL_FRAGMENT_SHADER);
    glShaderSource(frag, 1, &axis_frag_src, NULL);
    glCompileShader(frag);

    axis->shader = glCreateProgram();
    glAttachShader(axis->shader, vert);
    glAttachShader(axis->shader, frag);
    glLinkProgram(axis->shader);
    glDeleteShader(vert);
    glDeleteShader(frag);

    axis->rotation_loc = glGetUniformLocation(axis->shader, "rotation");

    // Create line VAO/VBO
    glGenVertexArrays(1, &axis->vao);
    glGenBuffers(1, &axis->vbo);
    glBindVertexArray(axis->vao);
    glBindBuffer(GL_ARRAY_BUFFER, axis->vbo);
    glBufferData(GL_ARRAY_BUFFER, sizeof(lines), lines, GL_STATIC_DRAW);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)(3 * sizeof(float)));
    glEnableVertexAttribArray(1);

    // Create arrow VAO/VBO
    glGenVertexArrays(1, &axis->arrow_vao);
    glGenBuffers(1, &axis->arrow_vbo);
    glBindVertexArray(axis->arrow_vao);
    glBindBuffer(GL_ARRAY_BUFFER, axis->arrow_vbo);
    glBufferData(GL_ARRAY_BUFFER, sizeof(arrows), arrows, GL_STATIC_DRAW);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)(3 * sizeof(float)));
    glEnableVertexAttribArray(1);

    glBindVertexArray(0);
    return true;
}

// Render in bottom-left corner, showing camera orientation
static void axis_gizmo_render(AxisGizmo* axis, const Mat4* view, int screen_width, int screen_height) {
    // Extract rotation from view matrix (upper-left 3x3)
    // View matrix transforms world->camera, so apply directly to show world axes in camera space
    Mat4 rot;
    rot.m[0]  = view->m[0];  rot.m[4]  = view->m[4];  rot.m[8]  = view->m[8];   rot.m[12] = 0;
    rot.m[1]  = view->m[1];  rot.m[5]  = view->m[5];  rot.m[9]  = view->m[9];   rot.m[13] = 0;
    rot.m[2]  = view->m[2];  rot.m[6]  = view->m[6];  rot.m[10] = view->m[10];  rot.m[14] = 0;
    rot.m[3]  = 0;           rot.m[7]  = 0;           rot.m[11] = 0;            rot.m[15] = 1;

    // Set up viewport in bottom-left corner
    int gizmo_size = 150;
    int margin = 20;
    glViewport(margin, margin, gizmo_size, gizmo_size);

    // Disable depth test so gizmo is always visible
    glDisable(GL_DEPTH_TEST);

    glUseProgram(axis->shader);
    glUniformMatrix4fv(axis->rotation_loc, 1, GL_FALSE, rot.m);

    // Draw lines
    glBindVertexArray(axis->vao);
    glLineWidth(2.0f);
    glDrawArrays(GL_LINES, 0, 6);

    // Draw arrows
    glBindVertexArray(axis->arrow_vao);
    glDrawArrays(GL_TRIANGLES, 0, axis->arrow_vertex_count);

    glBindVertexArray(0);

    // Re-enable depth test and restore viewport
    glEnable(GL_DEPTH_TEST);
    glViewport(0, 0, screen_width, screen_height);
}

static void axis_gizmo_destroy(AxisGizmo* axis) {
    glDeleteVertexArrays(1, &axis->vao);
    glDeleteBuffers(1, &axis->vbo);
    glDeleteVertexArrays(1, &axis->arrow_vao);
    glDeleteBuffers(1, &axis->arrow_vbo);
    glDeleteProgram(axis->shader);
}
// ============================================================================

// Part instance for rendering
struct PartInstance {
    Mesh* mesh;           // Pointer to cached mesh
    float position[3];    // World position
    float rotation[9];    // 3x3 rotation matrix (row-major)
    float color[3];       // RGB color (0-1)
    bool has_color;       // Whether to apply color override
};

// Get the directory containing the executable
static void get_exe_dir(char* buffer, size_t size) {
#ifdef _WIN32
    GetModuleFileNameA(NULL, buffer, (DWORD)size);
    char* last_sep = strrchr(buffer, '\\');
    if (last_sep) *last_sep = '\0';
#else
    ssize_t len = readlink("/proc/self/exe", buffer, size - 1);
    if (len > 0) {
        buffer[len] = '\0';
        char* dir = dirname(buffer);
        memmove(buffer, dir, strlen(dir) + 1);
    } else {
        buffer[0] = '.';
        buffer[1] = '\0';
    }
#endif
}

// Find simulator directory relative to executable
static void get_simulator_dir(char* buffer, size_t size) {
    char exe_dir[512];
    get_exe_dir(exe_dir, sizeof(exe_dir));
    snprintf(buffer, size, "%s" PATH_SEP ".." PATH_SEP ".." PATH_SEP "simulator", exe_dir);
}

// Find models directory relative to executable
static void get_models_dir(char* buffer, size_t size) {
    char exe_dir[512];
    get_exe_dir(exe_dir, sizeof(exe_dir));
    snprintf(buffer, size, "%s" PATH_SEP ".." PATH_SEP ".." PATH_SEP "models", exe_dir);
}

// Convert .dat part name to .glb path
static std::string part_name_to_glb(const char* part_name) {
    std::string name(part_name);
    // Replace .dat with .glb (case insensitive)
    size_t pos = name.rfind(".dat");
    if (pos == std::string::npos) pos = name.rfind(".DAT");
    if (pos != std::string::npos) {
        name = name.substr(0, pos) + ".glb";
    }
    return name;
}

// Build model matrix for standard GLB objects (no coordinate conversion)
// pos: world position, rot_y: rotation around Y axis in radians, scale: uniform scale
static Mat4 build_model_matrix(Vec3 pos, float rot_y, float scale) {
    float c = cosf(rot_y);
    float s = sinf(rot_y);

    Mat4 m;
    // Rotation around Y axis, with scale
    m.m[0]  = c * scale;   m.m[4]  = 0;       m.m[8]  = s * scale;   m.m[12] = pos.x;
    m.m[1]  = 0;           m.m[5]  = scale;   m.m[9]  = 0;           m.m[13] = pos.y;
    m.m[2]  = -s * scale;  m.m[6]  = 0;       m.m[10] = c * scale;   m.m[14] = pos.z;
    m.m[3]  = 0;           m.m[7]  = 0;       m.m[11] = 0;           m.m[15] = 1;

    return m;
}

// Build model matrix for LDraw parts (converts from LDraw to OpenGL coordinates)
// pos: position in LDU, rot: 3x3 rotation matrix (row-major) from MPD file
static Mat4 build_ldraw_model_matrix(const float* pos, const float* rot) {
    // LDraw rotation matrix is row-major: [a b c] [d e f] [g h i]
    float a = rot[0], b = rot[1], c = rot[2];
    float d = rot[3], e = rot[4], f = rot[5];
    float g = rot[6], h = rot[7], i = rot[8];

    // LDraw: Y-down, Z-back; OpenGL: Y-up, Z-front
    // Apply coordinate change: C * M * C where C = diag(1, -1, -1)
    // This flips both Y and Z axes
    float a2 = a,  b2 = -b, c2 = -c;
    float d2 = -d, e2 = e,  f2 = f;
    float g2 = -g, h2 = h,  i2 = i;

    // OpenGL column-major matrix
    Mat4 m;
    // Column 0
    m.m[0]  = a2;
    m.m[1]  = d2;
    m.m[2]  = g2;
    m.m[3]  = 0;
    // Column 1
    m.m[4]  = b2;
    m.m[5]  = e2;
    m.m[6]  = h2;
    m.m[7]  = 0;
    // Column 2
    m.m[8]  = c2;
    m.m[9]  = f2;
    m.m[10] = i2;
    m.m[11] = 0;
    // Column 3 (translation) - also flip Y and Z to match rotation transform
    m.m[12] = pos[0] * LDU_SCALE;
    m.m[13] = -pos[1] * LDU_SCALE;
    m.m[14] = -pos[2] * LDU_SCALE;
    m.m[15] = 1;

    return m;
}

int main(int argc, char** argv) {
    printf("VEX IQ Simulator - C++ Client\n");
    printf("=============================\n\n");

    // Parse command line
    const char* mpd_path = NULL;
    if (argc >= 2) {
        mpd_path = argv[1];
        printf("Model file: %s\n", mpd_path);
    } else {
        printf("Usage: %s <model.mpd>\n", argv[0]);
        printf("  Example: %s models/scale.mpd\n\n", argv[0]);
    }

    // Initialize platform (SDL + OpenGL)
    Platform platform;
    if (!platform_init(&platform, WINDOW_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT)) {
        fprintf(stderr, "Failed to initialize platform\n");
        return 1;
    }

    // Initialize input state
    InputState input;
    memset(&input, 0, sizeof(input));

    // Initialize camera
    FlyCamera camera;
    camera_init(&camera);

    // Initialize floor
    Floor floor;
    if (!floor_init(&floor, FIELD_WIDTH, GRID_SIZE, FIELD_WIDTH, FIELD_DEPTH)) {
        fprintf(stderr, "Failed to initialize floor\n");
        platform_shutdown(&platform);
        return 1;
    }

    // Initialize axis gizmo (normalized 1.0 length for screen-space rendering)
    AxisGizmo axis_gizmo;
    axis_gizmo_init(&axis_gizmo, 1.0f);

    // Initialize mesh shader
    Shader mesh_shader;
    if (!mesh_shader_create(&mesh_shader)) {
        fprintf(stderr, "Failed to create mesh shader\n");
        floor_destroy(&floor);
        platform_shutdown(&platform);
        return 1;
    }
    mesh_set_shader(&mesh_shader);

    // Get paths
    char models_dir[512];
    get_models_dir(models_dir, sizeof(models_dir));
    printf("Models dir: %s\n", models_dir);

    // Mesh cache: part name -> mesh
    std::map<std::string, Mesh*> mesh_cache;

    // Part instances to render
    std::vector<PartInstance> parts;
    uint32_t total_triangles = 0;

    // Load MPD file if provided
    if (mpd_path) {
        MpdDocument doc;
        if (mpd_load(mpd_path, &doc)) {
            mpd_print_info(&doc);

            // Load meshes for all parts
            for (uint32_t i = 0; i < doc.part_count; i++) {
                const MpdPart* part = &doc.parts[i];
                std::string glb_name = part_name_to_glb(part->part_name);

                // Check cache
                Mesh* mesh = nullptr;
                auto it = mesh_cache.find(glb_name);
                if (it != mesh_cache.end()) {
                    mesh = it->second;
                } else {
                    // Load the GLB file
                    char glb_path[1024];
                    snprintf(glb_path, sizeof(glb_path), "%s" PATH_SEP "parts" PATH_SEP "%s",
                             models_dir, glb_name.c_str());

                    MeshData mesh_data;
                    if (glb_load(glb_path, &mesh_data)) {
                        mesh = new Mesh();
                        if (mesh_create(mesh, &mesh_data)) {
                            mesh_cache[glb_name] = mesh;
                        } else {
                            delete mesh;
                            mesh = nullptr;
                        }
                        mesh_data_free(&mesh_data);
                    } else {
                        // File not found - store nullptr to avoid retrying
                        mesh_cache[glb_name] = nullptr;
                    }
                }

                if (mesh) {
                    PartInstance inst;
                    inst.mesh = mesh;
                    inst.position[0] = part->x;
                    inst.position[1] = part->y;
                    inst.position[2] = part->z;
                    memcpy(inst.rotation, part->rotation, 9 * sizeof(float));

                    // Get color from LDraw color code
                    ldraw_get_color(part->color_code, &inst.color[0], &inst.color[1], &inst.color[2]);

                    // Color 16 means "main color" - use default, don't override
                    // Any other color should be applied to white vertices
                    inst.has_color = (part->color_code != 16);

                    parts.push_back(inst);

                    // Count triangles per instance (not just unique meshes)
                    total_triangles += mesh->index_count / 3;
                }
            }

            mpd_free(&doc);
            printf("\nLoaded %zu part instances, %zu unique meshes, %u triangles\n",
                   parts.size(), mesh_cache.size(), total_triangles);

            // Debug: print transformation data for first 5 parts
            printf("\n=== DEBUG: First 5 parts transformation data ===\n");
            for (size_t i = 0; i < parts.size() && i < 5; i++) {
                const PartInstance& p = parts[i];
                // Calculate scaled position like Python does
                float pos_x = p.position[0] * LDU_SCALE;
                float pos_y = -p.position[1] * LDU_SCALE;  // Negate Y
                float pos_z = p.position[2] * LDU_SCALE;

                printf("\nPart %zu:\n", i + 1);
                printf("  Position (scaled): (%.2f, %.2f, %.2f)\n", pos_x, pos_y, pos_z);
                printf("  LDraw rotation matrix (row-major):\n");
                printf("    [%.2f, %.2f, %.2f]\n", p.rotation[0], p.rotation[1], p.rotation[2]);
                printf("    [%.2f, %.2f, %.2f]\n", p.rotation[3], p.rotation[4], p.rotation[5]);
                printf("    [%.2f, %.2f, %.2f]\n", p.rotation[6], p.rotation[7], p.rotation[8]);

                // Show C*M*C transformed matrix
                float a = p.rotation[0], b = p.rotation[1], c = p.rotation[2];
                float d = p.rotation[3], e = p.rotation[4], f = p.rotation[5];
                float g = p.rotation[6], h = p.rotation[7], i_r = p.rotation[8];
                float a2 = a,  b2 = -b, c2 = c;
                float d2 = -d, e2 = e,  f2 = -f;
                float g2 = g,  h2 = -h, i2 = i_r;

                printf("  After C*M*C transform:\n");
                printf("    [%.2f, %.2f, %.2f]\n", a2, b2, c2);
                printf("    [%.2f, %.2f, %.2f]\n", d2, e2, f2);
                printf("    [%.2f, %.2f, %.2f]\n", g2, h2, i2);
            }
            printf("=================================================\n\n");
        }
    }

    // Initialize gamepad (disabled for now - may cause issues on Linux)
    Gamepad gamepad;
    memset(&gamepad, 0, sizeof(gamepad));

    // OpenGL setup
    glEnable(GL_DEPTH_TEST);
    glClearColor(0.15f, 0.15f, 0.18f, 1.0f);

    // Initialize text renderer
    if (!text_init()) {
        fprintf(stderr, "Warning: Failed to initialize text renderer\n");
    }

    printf("\nControls (Blender-style):\n");
    printf("  Middle Mouse + Drag  - Orbit camera\n");
    printf("  Shift + MMB + Drag   - Pan camera\n");
    printf("  Scroll Wheel         - Zoom in/out\n");
    printf("  F11                  - Toggle fullscreen\n");
    printf("  Escape               - Quit\n\n");

    // Timing and FPS tracking
    double last_time = platform_get_time();
    double fps_update_time = last_time;
    int frame_count = 0;
    float current_fps = 0.0f;

    // Main loop
    while (!platform.should_quit) {
        // Calculate delta time
        double current_time = platform_get_time();
        float dt = (float)(current_time - last_time);
        last_time = current_time;

        // Cap dt to prevent physics explosions on lag spikes
        if (dt > 0.1f) dt = 0.1f;

        // Update FPS counter
        frame_count++;
        if (current_time - fps_update_time >= 0.5) {
            current_fps = frame_count / (float)(current_time - fps_update_time);
            frame_count = 0;
            fps_update_time = current_time;
        }

        // Poll events
        platform_poll_events(&platform, &input);

        // Handle keyboard input
        if (input.keys_pressed[KEY_ESCAPE]) {
            platform.should_quit = true;
        }

        if (input.keys_pressed[KEY_F11]) {
            platform_toggle_fullscreen(&platform);
        }

        // Update camera
        camera_update(&camera, &input, dt);

        // Render
        glViewport(0, 0, platform.width, platform.height);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        // Get camera matrices
        float aspect = (float)platform.width / (float)platform.height;
        Mat4 view = camera_view_matrix(&camera);
        Mat4 projection = camera_projection_matrix(&camera, aspect);

        // Render floor
        floor_render(&floor, &view, &projection, camera_position(&camera));

        // Render all parts
        Vec3 light_dir = vec3_normalize(vec3(0.5f, 1.0f, 0.3f));

        for (const auto& part : parts) {
            Mat4 model = build_ldraw_model_matrix(part.position, part.rotation);
            const float* color = part.has_color ? part.color : nullptr;
            mesh_render(part.mesh, &model, &view, &projection, light_dir, color);
        }

        // Render orientation gizmo in bottom-left corner
        axis_gizmo_render(&axis_gizmo, &view, platform.width, platform.height);

        // Render stats overlay
        char stats[128];
        snprintf(stats, sizeof(stats), "FPS: %.0f  Parts: %zu  Tris: %u",
                 current_fps, parts.size(), total_triangles);
        text_render_right(stats, 10.0f, 10.0f, platform.width, platform.height);

        // Swap buffers
        platform_swap_buffers(&platform);
    }

    // Cleanup
    for (auto& pair : mesh_cache) {
        if (pair.second) {
            mesh_destroy(pair.second);
            delete pair.second;
        }
    }
    mesh_cache.clear();
    parts.clear();

    shader_destroy(&mesh_shader);
    text_destroy();
    gamepad_destroy(&gamepad);
    axis_gizmo_destroy(&axis_gizmo);
    floor_destroy(&floor);
    platform_shutdown(&platform);

    printf("Shutdown complete.\n");
    return 0;
}
