/*
 * VEX IQ Simulator - C++ SDL Client
 *
 * A 3D visualization client for the VEX IQ Python simulator.
 * Supports loading LDraw MPD files with colored parts.
 *
 * =============================================================================
 * COORDINATE SYSTEMS AND ASSET PIPELINE
 * =============================================================================
 *
 * This simulator uses VEX IQ parts from the LDraw CAD system. Understanding
 * the coordinate transformations is critical for correct rendering.
 *
 * LDRAW COORDINATE SYSTEM (used in .mpd/.ldr files):
 *   - X: Right
 *   - Y: Down (gravity points +Y)
 *   - Z: Back (away from viewer in default LDCad view)
 *   - Units: LDU (LDraw Units), where 1 LDU = 0.4mm
 *
 * OPENGL COORDINATE SYSTEM (used for rendering):
 *   - X: Right
 *   - Y: Up (gravity points -Y)
 *   - Z: Front (toward viewer, -Z is into screen)
 *   - Units: Inches (1 inch = 1 world unit for VEX IQ scale)
 *
 * GLB/GLTF COORDINATE SYSTEM (used in part meshes):
 *   - Same as OpenGL: Y-up, Z-front
 *   - Parts were converted from LDraw .dat files using Blender
 *   - Blender export handles the coordinate conversion automatically
 *   - Scale: 0.02x LDU (so 1 LDU in LDraw = 0.02 units in GLB)
 *
 * TRANSFORMATION PIPELINE:
 *   1. MPD file specifies part positions/rotations in LDraw coordinates (LDU)
 *   2. MPD loader parses and flattens the submodel hierarchy
 *   3. build_ldraw_model_matrix() converts LDraw -> OpenGL:
 *      - Position: Multiply by LDU_SCALE (0.02), flip Y and Z
 *      - Rotation: Apply C*M*C where C = diag(1, -1, -1)
 *   4. GLB meshes are already in OpenGL coordinates (from Blender export)
 *   5. Final transform = LDraw-converted matrix * GLB mesh vertices
 *
 * WHY BOTH Y AND Z ARE FLIPPED:
 *   - LDraw Y-down vs OpenGL Y-up requires Y flip
 *   - LDraw Z-back vs OpenGL Z-front requires Z flip
 *   - The rotation matrix transform C*M*C with C=diag(1,-1,-1) handles both
 *   - Position also needs both Y and Z negated for consistency
 *   - This was discovered through systematic testing with single rotated parts
 *
 * PART COLOR HANDLING:
 *   - LDraw uses color codes (0=black, 72=dark gray, etc.)
 *   - GLB parts have white vertex colors where colorable
 *   - Color code 16 = "inherit from parent" (main color)
 *   - Shader checks vertex color: white areas get tinted, non-white preserved
 *
 * ASSET LOCATIONS:
 *   - models/<name>.mpd         - LDraw model files (robot assemblies)
 *   - models/parts/<name>.glb   - GLB meshes for individual parts
 *   - models/<name>.robotdef    - Robot definition files (kinematics, ports, etc.)
 *
 * FOR CUSTOM (NON-LDRAW) GLB OBJECTS:
 *   - Use build_model_matrix() instead of build_ldraw_model_matrix()
 *   - No coordinate conversion needed - GLB is already in OpenGL coords
 *   - Position directly in world units (inches)
 *
 * =============================================================================
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
#include "render/debug.h"
#include "scene/scene.h"
#include "physics/drivetrain.h"
#include "physics/robotdef.h"
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
#include <cfloat>  // FLT_MAX
#include <cmath>   // cosf, sinf

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
#define WALL_HEIGHT 4.0f    // 4 inch walls around field

// Degrees to radians conversion
#define DEG_TO_RAD_CONST (3.14159265359f / 180.0f)

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

// Wheel assembly for a robot (runtime data)
struct WheelAssembly {
    float world_position[3];   // LDU - center of wheel
    float spin_axis[3];        // Rotation axis (normalized)
    float diameter_mm;         // For calculating spin rate
    float spin_angle;          // Current rotation angle (radians)
    char part_numbers[ROBOTDEF_MAX_WHEEL_PARTS][32];
    int part_count;
    bool is_left;
};

// Robot instance (loaded from scene)
struct RobotInstance {
    float offset[3];      // World position offset (inches)
    float rotation_y;     // Rotation around Y axis (radians)
    float ground_offset;  // Computed ground offset for this robot
    Drivetrain drivetrain; // Physics drivetrain for this robot

    // From robotdef
    float rotation_center[3];  // Drivetrain center in LDU (converted to world coords for rotation)
    float rotation_axis[3];    // Rotation axis (default: [0,1,0] = vertical)
    float track_width;         // Track width in LDU
    bool has_robotdef;         // Whether robotdef was loaded

    // Wheel assemblies
    WheelAssembly wheels[ROBOTDEF_MAX_WHEELS];
    int wheel_count;
};

// Part instance for rendering
struct PartInstance {
    Mesh* mesh;           // Pointer to cached mesh
    float position[3];    // Position in LDraw units (before robot offset)
    float rotation[9];    // 3x3 rotation matrix (row-major)
    float color[3];       // RGB color (0-1)
    bool has_color;       // Whether to apply color override
    int robot_index;      // Which robot this part belongs to (-1 = no robot)
    int wheel_index;      // Which wheel assembly this part belongs to (-1 = not a wheel)
    char part_number[32]; // Part number for wheel matching
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
// robot: robot instance with offset and ground offset (can be NULL for no robot)
// wheel: wheel assembly for spin rotation (can be NULL for no wheel spin)
static Mat4 build_ldraw_model_matrix(const float* pos, const float* rot, const RobotInstance* robot,
                                      const WheelAssembly* wheel = nullptr) {
    // LDraw rotation matrix is row-major: [a b c] [d e f] [g h i]
    float a = rot[0], b = rot[1], c = rot[2];
    float d = rot[3], e = rot[4], f = rot[5];
    float g = rot[6], h = rot[7], i = rot[8];

    // Part position in LDU (LDraw coordinates)
    float px = pos[0];
    float py = pos[1];
    float pz = pos[2];

    // Apply wheel spin rotation if present (before robot rotation)
    if (wheel && wheel->spin_angle != 0.0f) {
        // Wheel center in LDU
        float cx = wheel->world_position[0];
        float cy = wheel->world_position[1];
        float cz = wheel->world_position[2];

        // Rotation axis (already normalized)
        float ax = wheel->spin_axis[0];
        float ay = wheel->spin_axis[1];
        float az = wheel->spin_axis[2];

        // Rodrigues' rotation formula for position
        float rel_x = px - cx;
        float rel_y = py - cy;
        float rel_z = pz - cz;

        float cos_a = cosf(wheel->spin_angle);
        float sin_a = sinf(wheel->spin_angle);
        float one_minus_cos = 1.0f - cos_a;

        // Cross product: axis x rel
        float cross_x = ay * rel_z - az * rel_y;
        float cross_y = az * rel_x - ax * rel_z;
        float cross_z = ax * rel_y - ay * rel_x;

        // Dot product: axis . rel
        float dot = ax * rel_x + ay * rel_y + az * rel_z;

        // Rotated position: rel*cos + (axis x rel)*sin + axis*(axis.rel)*(1-cos)
        float rx = rel_x * cos_a + cross_x * sin_a + ax * dot * one_minus_cos;
        float ry = rel_y * cos_a + cross_y * sin_a + ay * dot * one_minus_cos;
        float rz = rel_z * cos_a + cross_z * sin_a + az * dot * one_minus_cos;

        px = rx + cx;
        py = ry + cy;
        pz = rz + cz;

        // Also rotate the orientation matrix using Rodrigues' formula
        // For each column of the rotation matrix, rotate it around the axis
        // Column 0 (a, d, g)
        float c0_cross_x = ay * g - az * d;
        float c0_cross_y = az * a - ax * g;
        float c0_cross_z = ax * d - ay * a;
        float c0_dot = ax * a + ay * d + az * g;
        float na = a * cos_a + c0_cross_x * sin_a + ax * c0_dot * one_minus_cos;
        float nd = d * cos_a + c0_cross_y * sin_a + ay * c0_dot * one_minus_cos;
        float ng = g * cos_a + c0_cross_z * sin_a + az * c0_dot * one_minus_cos;

        // Column 1 (b, e, h)
        float c1_cross_x = ay * h - az * e;
        float c1_cross_y = az * b - ax * h;
        float c1_cross_z = ax * e - ay * b;
        float c1_dot = ax * b + ay * e + az * h;
        float nb = b * cos_a + c1_cross_x * sin_a + ax * c1_dot * one_minus_cos;
        float ne = e * cos_a + c1_cross_y * sin_a + ay * c1_dot * one_minus_cos;
        float nh = h * cos_a + c1_cross_z * sin_a + az * c1_dot * one_minus_cos;

        // Column 2 (c, f, i)
        float c2_cross_x = ay * i - az * f;
        float c2_cross_y = az * c - ax * i;
        float c2_cross_z = ax * f - ay * c;
        float c2_dot = ax * c + ay * f + az * i;
        float nc = c * cos_a + c2_cross_x * sin_a + ax * c2_dot * one_minus_cos;
        float nf = f * cos_a + c2_cross_y * sin_a + ay * c2_dot * one_minus_cos;
        float ni = i * cos_a + c2_cross_z * sin_a + az * c2_dot * one_minus_cos;

        a = na; b = nb; c = nc;
        d = nd; e = ne; f = nf;
        g = ng; h = nh; i = ni;
    }

    // Apply robot rotation if present (in LDraw space, before coordinate conversion)
    if (robot) {
        // Rotation center in LDU
        float pivot_x = robot->rotation_center[0];
        float pivot_y = robot->rotation_center[1];
        float pivot_z = robot->rotation_center[2];

        // Part position relative to pivot (in LDU)
        float rel_x = px - pivot_x;
        float rel_y = py - pivot_y;
        float rel_z = pz - pivot_z;

        // Rotate around Y axis in LDraw space
        // Note: In LDraw, Y is down, so rotation around Y is still around the vertical axis
        // But the rotation direction might be inverted relative to OpenGL
        float cos_r = cosf(robot->rotation_y);
        float sin_r = sinf(robot->rotation_y);

        // Rotate position (in LDraw XZ plane)
        // Using Ry_ldraw: [cos 0 -sin; 0 1 0; sin 0 cos]
        float rx = rel_x * cos_r - rel_z * sin_r;
        float rz = rel_x * sin_r + rel_z * cos_r;

        // Update position relative to pivot
        px = rx + pivot_x;
        py = rel_y + pivot_y;
        pz = rz + pivot_z;

        // Rotate the orientation matrix (left-multiply by Ry in LDraw space)
        // Ry_ldraw = [cos 0 -sin; 0 1 0; sin 0 cos] (note: different from OpenGL Ry)
        // Because in LDraw, Z points back, so positive rotation is opposite
        float na = cos_r * a - sin_r * g;
        float nb = cos_r * b - sin_r * h;
        float nc = cos_r * c - sin_r * i;
        float ng = sin_r * a + cos_r * g;
        float nh = sin_r * b + cos_r * h;
        float ni = sin_r * c + cos_r * i;
        a = na; b = nb; c = nc;
        g = ng; h = nh; i = ni;
        // d, e, f unchanged (Y row doesn't change for Y-axis rotation)
    }

    // Now convert from LDraw to OpenGL coordinates
    // LDraw: Y-down, Z-back; OpenGL: Y-up, Z-front
    // Apply coordinate change: C * M * C where C = diag(1, -1, -1)
    float a2 = a,  b2 = -b, c2 = -c;
    float d2 = -d, e2 = e,  f2 = f;
    float g2 = -g, h2 = h,  i2 = i;

    // Convert position to OpenGL coordinates
    float wx = px * LDU_SCALE;
    float wy = -py * LDU_SCALE;
    float wz = -pz * LDU_SCALE;

    // Apply robot world offset
    if (robot) {
        // Pivot position in OpenGL coords
        float pivot_gl_x = robot->rotation_center[0] * LDU_SCALE;
        float pivot_gl_y = -robot->rotation_center[1] * LDU_SCALE;
        float pivot_gl_z = -robot->rotation_center[2] * LDU_SCALE;

        // wx, wy, wz is the rotated position relative to robot origin, in OpenGL coords
        // Offset so that the pivot point ends up at robot->offset
        wx = wx - pivot_gl_x + robot->offset[0];
        wy = wy - pivot_gl_y + robot->offset[1] + robot->ground_offset;
        wz = wz - pivot_gl_z + robot->offset[2];
    }

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
    // Column 3 (translation)
    m.m[12] = wx;
    m.m[13] = wy;
    m.m[14] = wz;
    m.m[15] = 1;

    return m;
}

// Compute ground offset for a specific robot from bounding boxes
// Finds the minimum Y value across all parts belonging to robot_index
static float compute_ground_offset(const std::vector<PartInstance>& parts, int robot_index) {
    if (parts.empty()) return 0.0f;

    float min_y = FLT_MAX;

    for (const auto& part : parts) {
        if (!part.mesh) continue;
        if (part.robot_index != robot_index) continue;

        // Transform local bounding box to world space using the same transform as rendering
        // Apply C*M*C rotation (flip Y and Z)
        float d = part.rotation[3], e = part.rotation[4], f = part.rotation[5];
        float d2 = -d, e2 = e,  f2 = f;  // Only need row 2 for Y calculation

        // Transform all 8 corners of bounding box to find true minimum Y
        float min_x = part.mesh->min_bounds[0], max_x = part.mesh->max_bounds[0];
        float min_y_local = part.mesh->min_bounds[1], max_y_local = part.mesh->max_bounds[1];
        float min_z = part.mesh->min_bounds[2], max_z = part.mesh->max_bounds[2];

        float corners[8][3];
        int idx = 0;
        for (int xi = 0; xi < 2; xi++) {
            for (int yi = 0; yi < 2; yi++) {
                for (int zi = 0; zi < 2; zi++) {
                    corners[idx][0] = (xi == 0) ? min_x : max_x;
                    corners[idx][1] = (yi == 0) ? min_y_local : max_y_local;
                    corners[idx][2] = (zi == 0) ? min_z : max_z;
                    idx++;
                }
            }
        }

        // Transform each corner and find minimum Y
        for (int ci = 0; ci < 8; ci++) {
            float lx = corners[ci][0], ly = corners[ci][1], lz = corners[ci][2];

            // Rotated point (using transformed rotation matrix)
            float ry = d2 * lx + e2 * ly + f2 * lz;

            // World Y = rotated Y + translated Y (without ground offset)
            float world_y = ry + (-part.position[1] * LDU_SCALE);

            if (world_y < min_y) {
                min_y = world_y;
            }
        }
    }

    // Return offset to lift robot so min_y becomes 0
    return (min_y == FLT_MAX) ? 0.0f : -min_y;
}

int main(int argc, char** argv) {
    printf("VEX IQ Simulator - C++ Client\n");
    printf("=============================\n\n");

    // Parse command line - accept scene file or default to default.scene
    const char* scene_path = NULL;
    if (argc >= 2) {
        scene_path = argv[1];
        printf("Scene file: %s\n", scene_path);
    } else {
        scene_path = "../scenes/default.scene";
        printf("Using default scene: %s\n", scene_path);
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
    if (!floor_init(&floor, FIELD_WIDTH, GRID_SIZE, FIELD_WIDTH, FIELD_DEPTH, WALL_HEIGHT, "../textures/vex-tile.png")) {
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
    std::vector<RobotInstance> robots;
    uint32_t total_triangles = 0;

    // Load scene file
    Scene scene;
    if (scene_load(scene_path, &scene)) {
        scene_print(&scene);

        // Load each robot in the scene
        for (uint32_t robot_idx = 0; robot_idx < scene.robot_count; robot_idx++) {
            const SceneRobot* scene_robot = &scene.robots[robot_idx];

            // Build full path to MPD file
            char mpd_path[1024];
            snprintf(mpd_path, sizeof(mpd_path), "%s" PATH_SEP "robots" PATH_SEP "%s",
                     models_dir, scene_robot->mpd_file);

            printf("\nLoading robot %u: %s at (%.1f, %.1f, %.1f) rot=%.1f°\n",
                   robot_idx, scene_robot->mpd_file,
                   scene_robot->x, scene_robot->y, scene_robot->z, scene_robot->rotation_y);

            MpdDocument doc;
            if (!mpd_load(mpd_path, &doc)) {
                fprintf(stderr, "  Failed to load: %s\n", mpd_path);
                continue;
            }

            // Create robot instance
            RobotInstance robot;
            robot.offset[0] = scene_robot->x;
            robot.offset[1] = scene_robot->y;
            robot.offset[2] = scene_robot->z;
            robot.rotation_y = scene_robot->rotation_y * DEG_TO_RAD_CONST;
            robot.ground_offset = 0.0f;  // Will compute after loading parts
            robot.has_robotdef = false;
            robot.rotation_center[0] = 0.0f;
            robot.rotation_center[1] = 0.0f;
            robot.rotation_center[2] = 0.0f;
            robot.rotation_axis[0] = 0.0f;
            robot.rotation_axis[1] = 1.0f;  // Default: vertical rotation
            robot.rotation_axis[2] = 0.0f;
            robot.track_width = 0.0f;

            // Try to load robotdef file
            char robotdef_path[1024];
            {
                // Replace .mpd extension with .robotdef
                strncpy(robotdef_path, mpd_path, sizeof(robotdef_path) - 1);
                char* ext = strrchr(robotdef_path, '.');
                if (ext) {
                    strcpy(ext, ".robotdef");
                } else {
                    strncat(robotdef_path, ".robotdef", sizeof(robotdef_path) - strlen(robotdef_path) - 1);
                }

                RobotDef def;
                if (robotdef_load(robotdef_path, &def)) {
                    robot.has_robotdef = true;
                    // Store rotation center (in LDU - will convert during rendering)
                    robot.rotation_center[0] = def.drivetrain.rotation_center[0];
                    robot.rotation_center[1] = def.drivetrain.rotation_center[1];
                    robot.rotation_center[2] = def.drivetrain.rotation_center[2];
                    // Store rotation axis
                    robot.rotation_axis[0] = def.drivetrain.rotation_axis[0];
                    robot.rotation_axis[1] = def.drivetrain.rotation_axis[1];
                    robot.rotation_axis[2] = def.drivetrain.rotation_axis[2];
                    robot.track_width = def.drivetrain.track_width;

                    // Load wheel assemblies
                    robot.wheel_count = def.wheel_count;
                    for (int w = 0; w < def.wheel_count && w < ROBOTDEF_MAX_WHEELS; w++) {
                        const RobotDefWheelAssembly* src = &def.wheel_assemblies[w];
                        WheelAssembly* dst = &robot.wheels[w];
                        dst->world_position[0] = src->world_position[0];
                        dst->world_position[1] = src->world_position[1];
                        dst->world_position[2] = src->world_position[2];
                        dst->spin_axis[0] = src->spin_axis[0];
                        dst->spin_axis[1] = src->spin_axis[1];
                        dst->spin_axis[2] = src->spin_axis[2];
                        dst->diameter_mm = src->outer_diameter_mm;
                        dst->spin_angle = 0.0f;
                        dst->is_left = src->is_left;
                        dst->part_count = src->part_count;
                        for (int p = 0; p < src->part_count && p < ROBOTDEF_MAX_WHEEL_PARTS; p++) {
                            strncpy(dst->part_numbers[p], src->part_numbers[p], 31);
                        }
                    }

                    printf("  Loaded robotdef: rotation_center=[%.1f, %.1f, %.1f] LDU, rotation_axis=[%.1f, %.1f, %.1f], track_width=%.1f LDU, wheels=%d\n",
                           robot.rotation_center[0], robot.rotation_center[1], robot.rotation_center[2],
                           robot.rotation_axis[0], robot.rotation_axis[1], robot.rotation_axis[2],
                           robot.track_width, robot.wheel_count);
                } else {
                    printf("  No robotdef found (tried: %s)\n", robotdef_path);
                }
            }

            // Initialize drivetrain at robot's starting position
            drivetrain_init(&robot.drivetrain);
            drivetrain_set_position(&robot.drivetrain, scene_robot->x, scene_robot->z, robot.rotation_y);

            int current_robot_index = (int)robots.size();
            robots.push_back(robot);

            // Load meshes for all parts in this robot
            size_t robot_part_start = parts.size();
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
                    inst.has_color = (part->color_code != 16);
                    inst.robot_index = current_robot_index;
                    inst.wheel_index = -1;

                    // Store normalized part number (strip .dat and variants)
                    strncpy(inst.part_number, part->part_name, 31);
                    inst.part_number[31] = '\0';
                    // Strip .dat extension
                    char* dot = strrchr(inst.part_number, '.');
                    if (dot) *dot = '\0';
                    // Strip c## suffix (LDraw composite parts)
                    size_t len = strlen(inst.part_number);
                    if (len > 3 && inst.part_number[len-3] == 'c' &&
                        isdigit(inst.part_number[len-2]) && isdigit(inst.part_number[len-1])) {
                        inst.part_number[len-3] = '\0';
                    }

                    parts.push_back(inst);
                    total_triangles += mesh->index_count / 3;
                }
            }

            mpd_free(&doc);

            // Compute ground offset for this robot
            robots[current_robot_index].ground_offset = compute_ground_offset(parts, current_robot_index);

            // Adjust ground offset for rotation center Y position
            // Rendering applies: wy = wy - pivot_gl_y + ground_offset
            // The pivot_gl_y offset shifts all parts, so ground_offset must compensate
            float pivot_gl_y = -robots[current_robot_index].rotation_center[1] * LDU_SCALE;
            robots[current_robot_index].ground_offset += pivot_gl_y;

            // Match parts to wheel assemblies by part number
            int wheel_parts_matched = 0;
            RobotInstance& r = robots[current_robot_index];
            // Note: For now, use wheel 0 for left side, wheel 2 for right side (first of each)
            // This makes all same-side wheels spin together (correct for tank drive)
            int left_wheel_idx = -1, right_wheel_idx = -1;
            for (int wi = 0; wi < r.wheel_count; wi++) {
                if (r.wheels[wi].is_left && left_wheel_idx < 0) left_wheel_idx = wi;
                if (!r.wheels[wi].is_left && right_wheel_idx < 0) right_wheel_idx = wi;
            }

            for (size_t pi = robot_part_start; pi < parts.size(); pi++) {
                PartInstance& p = parts[pi];
                // Check all wheels for matching part number
                for (int wi = 0; wi < r.wheel_count; wi++) {
                    WheelAssembly& w = r.wheels[wi];
                    for (int wpi = 0; wpi < w.part_count; wpi++) {
                        if (strcmp(p.part_number, w.part_numbers[wpi]) == 0) {
                            // Assign to left or right wheel based on part X position
                            // Negative X = left side, Positive X = right side
                            p.wheel_index = (p.position[0] < 0) ? left_wheel_idx : right_wheel_idx;
                            if (p.wheel_index >= 0) wheel_parts_matched++;
                            break;
                        }
                    }
                    if (p.wheel_index >= 0) break;
                }
            }

            printf("  Loaded %zu parts, ground offset: %.3f inches (pivot_y: %.3f), wheel parts: %d\n",
                   parts.size() - robot_part_start,
                   robots[current_robot_index].ground_offset,
                   pivot_gl_y,
                   wheel_parts_matched);
        }

        printf("\nScene loaded: %zu robots, %zu total parts, %zu unique meshes, %u triangles\n",
               robots.size(), parts.size(), mesh_cache.size(), total_triangles);
    } else {
        printf("No scene loaded - running with empty scene\n");
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

    // Initialize debug renderer
    if (!debug_init()) {
        fprintf(stderr, "Warning: Failed to initialize debug renderer\n");
    }

    // Debug display flags
    bool show_bounding_boxes = false;
    bool show_robot_bounds = true;  // Show combined robot bounding box

    printf("\nControls:\n");
    printf("  Robot 1: WASD        - Drive (W/S forward/back, A/D turn)\n");
    printf("  Robot 2: Arrow Keys  - Drive (Up/Down/Left/Right)\n");
    printf("  Middle Mouse + Drag  - Orbit camera\n");
    printf("  Shift + MMB + Drag   - Pan camera\n");
    printf("  Scroll Wheel         - Zoom in/out\n");
    printf("  B                    - Toggle bounding boxes\n");
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

        // Toggle bounding box display
        if (input.keys_pressed[SDL_SCANCODE_B]) {
            show_bounding_boxes = !show_bounding_boxes;
            printf("Bounding boxes: %s\n", show_bounding_boxes ? "ON" : "OFF");
        }

        // Robot driving controls (WASD for first robot, Arrow keys for second)
        // First robot: WASD
        if (!robots.empty()) {
            float left_pct = 0.0f;
            float right_pct = 0.0f;

            // W = forward, S = backward
            if (input.keys[SDL_SCANCODE_W]) {
                left_pct += 50.0f;
                right_pct += 50.0f;
            }
            if (input.keys[SDL_SCANCODE_S]) {
                left_pct -= 50.0f;
                right_pct -= 50.0f;
            }
            // A = turn left (right faster than left)
            if (input.keys[SDL_SCANCODE_A]) {
                left_pct -= 30.0f;
                right_pct += 30.0f;
            }
            // D = turn right (left faster than right)
            if (input.keys[SDL_SCANCODE_D]) {
                left_pct += 30.0f;
                right_pct -= 30.0f;
            }

            drivetrain_set_motors(&robots[0].drivetrain, left_pct, right_pct);
        }

        // Second robot: Arrow keys
        if (robots.size() > 1) {
            float left_pct = 0.0f;
            float right_pct = 0.0f;

            if (input.keys[SDL_SCANCODE_UP]) {
                left_pct += 50.0f;
                right_pct += 50.0f;
            }
            if (input.keys[SDL_SCANCODE_DOWN]) {
                left_pct -= 50.0f;
                right_pct -= 50.0f;
            }
            if (input.keys[SDL_SCANCODE_LEFT]) {
                left_pct -= 30.0f;
                right_pct += 30.0f;
            }
            if (input.keys[SDL_SCANCODE_RIGHT]) {
                left_pct += 30.0f;
                right_pct -= 30.0f;
            }

            drivetrain_set_motors(&robots[1].drivetrain, left_pct, right_pct);
        }

        // Update drivetrain physics and sync positions
        for (auto& robot : robots) {
            drivetrain_update(&robot.drivetrain, dt);

            // Sync drivetrain position back to robot offset for rendering
            robot.offset[0] = robot.drivetrain.pos_x;
            robot.offset[2] = robot.drivetrain.pos_z;
            robot.rotation_y = robot.drivetrain.heading;

            // Update wheel spin angles based on drivetrain velocity
            for (int w = 0; w < robot.wheel_count; w++) {
                WheelAssembly& wheel = robot.wheels[w];
                // Get wheel velocity (left or right side)
                float wheel_vel = wheel.is_left ?
                    robot.drivetrain.left_velocity :
                    robot.drivetrain.right_velocity;
                // Convert diameter mm to radius in inches
                float radius_in = (wheel.diameter_mm / 25.4f) / 2.0f;
                if (radius_in > 0.0f) {
                    // Angular velocity = linear velocity / radius
                    float angular_vel = wheel_vel / radius_in;
                    wheel.spin_angle += angular_vel * dt;
                    // Keep angle in reasonable range
                    while (wheel.spin_angle > 6.28318f) wheel.spin_angle -= 6.28318f;
                    while (wheel.spin_angle < -6.28318f) wheel.spin_angle += 6.28318f;
                }
            }
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
            // Get robot instance for this part (if any)
            const RobotInstance* robot = nullptr;
            const WheelAssembly* wheel = nullptr;
            if (part.robot_index >= 0 && part.robot_index < (int)robots.size()) {
                robot = &robots[part.robot_index];
                // Get wheel assembly if this is a wheel part
                if (part.wheel_index >= 0 && part.wheel_index < robot->wheel_count) {
                    wheel = &robot->wheels[part.wheel_index];
                }
            }
            Mat4 model = build_ldraw_model_matrix(part.position, part.rotation, robot, wheel);
            const float* color = part.has_color ? part.color : nullptr;
            mesh_render(part.mesh, &model, &view, &projection, light_dir, color);
        }

        // Debug rendering (bounding boxes)
        if (show_bounding_boxes) {
            debug_begin(&view, &projection);

            // Colors for different robots
            Vec3 robot_colors[] = {
                vec3(0.0f, 1.0f, 0.0f),   // Green
                vec3(0.0f, 0.5f, 1.0f),   // Blue
                vec3(1.0f, 0.5f, 0.0f),   // Orange
                vec3(1.0f, 0.0f, 1.0f),   // Magenta
            };
            int num_colors = sizeof(robot_colors) / sizeof(robot_colors[0]);

            // Track robot bounding boxes for combined display
            struct RobotBounds {
                float min_x, min_y, min_z;
                float max_x, max_y, max_z;
                bool initialized;
            };
            std::vector<RobotBounds> robot_bounds(robots.size());
            for (auto& rb : robot_bounds) {
                rb.initialized = false;
                rb.min_x = rb.min_y = rb.min_z = FLT_MAX;
                rb.max_x = rb.max_y = rb.max_z = -FLT_MAX;
            }

            // Draw bounding box for each part
            for (const auto& part : parts) {
                if (!part.mesh) continue;

                const RobotInstance* robot = nullptr;
                const WheelAssembly* wheel = nullptr;
                if (part.robot_index >= 0 && part.robot_index < (int)robots.size()) {
                    robot = &robots[part.robot_index];
                    if (part.wheel_index >= 0 && part.wheel_index < robot->wheel_count) {
                        wheel = &robot->wheels[part.wheel_index];
                    }
                }
                Mat4 model = build_ldraw_model_matrix(part.position, part.rotation, robot, wheel);

                // Get color based on robot index
                Vec3 color = vec3(0.5f, 0.5f, 0.5f);  // Gray for no robot
                if (part.robot_index >= 0) {
                    color = robot_colors[part.robot_index % num_colors];
                    // Dim it for per-part boxes
                    color = vec3(color.x * 0.4f, color.y * 0.4f, color.z * 0.4f);
                }

                // Draw part bounding box (transformed)
                debug_draw_box_transformed(&model, part.mesh->min_bounds, part.mesh->max_bounds, color);

                // Accumulate robot bounds
                if (part.robot_index >= 0 && show_robot_bounds) {
                    RobotBounds& rb = robot_bounds[part.robot_index];

                    // Transform all 8 corners of the part's bounding box
                    for (int corner = 0; corner < 8; corner++) {
                        float lx = (corner & 1) ? part.mesh->max_bounds[0] : part.mesh->min_bounds[0];
                        float ly = (corner & 2) ? part.mesh->max_bounds[1] : part.mesh->min_bounds[1];
                        float lz = (corner & 4) ? part.mesh->max_bounds[2] : part.mesh->min_bounds[2];

                        // Transform to world space
                        float wx = model.m[0]*lx + model.m[4]*ly + model.m[8]*lz + model.m[12];
                        float wy = model.m[1]*lx + model.m[5]*ly + model.m[9]*lz + model.m[13];
                        float wz = model.m[2]*lx + model.m[6]*ly + model.m[10]*lz + model.m[14];

                        // Expand robot bounds
                        if (wx < rb.min_x) rb.min_x = wx;
                        if (wy < rb.min_y) rb.min_y = wy;
                        if (wz < rb.min_z) rb.min_z = wz;
                        if (wx > rb.max_x) rb.max_x = wx;
                        if (wy > rb.max_y) rb.max_y = wy;
                        if (wz > rb.max_z) rb.max_z = wz;
                        rb.initialized = true;
                    }
                }
            }

            // Draw combined robot bounding boxes (brighter)
            if (show_robot_bounds) {
                for (size_t i = 0; i < robot_bounds.size(); i++) {
                    const RobotBounds& rb = robot_bounds[i];
                    if (!rb.initialized) continue;

                    Vec3 color = robot_colors[i % num_colors];
                    Vec3 center = vec3(
                        (rb.min_x + rb.max_x) / 2.0f,
                        (rb.min_y + rb.max_y) / 2.0f,
                        (rb.min_z + rb.max_z) / 2.0f
                    );
                    Vec3 half_extents = vec3(
                        (rb.max_x - rb.min_x) / 2.0f,
                        (rb.max_y - rb.min_y) / 2.0f,
                        (rb.max_z - rb.min_z) / 2.0f
                    );

                    debug_draw_box(center, half_extents, color);

                    // Draw robot origin axes
                    Vec3 origin = vec3(robots[i].offset[0], robots[i].ground_offset, robots[i].offset[2]);
                    debug_draw_axes(origin, 6.0f);  // 6 inch axes
                }
            }

            debug_end();
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
    debug_destroy();
    gamepad_destroy(&gamepad);
    axis_gizmo_destroy(&axis_gizmo);
    floor_destroy(&floor);
    platform_shutdown(&platform);

    printf("Shutdown complete.\n");
    return 0;
}
