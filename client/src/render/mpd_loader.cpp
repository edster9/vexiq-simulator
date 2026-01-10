/*
 * MPD/LDR Loader Implementation
 * Parses LDraw Multi-Part Document files with submodel support
 *
 * =============================================================================
 * LDRAW FILE FORMAT OVERVIEW
 * =============================================================================
 *
 * LDraw is a CAD system for LEGO and compatible brick systems (including VEX IQ).
 * VEX IQ parts are available as LDraw parts created by Philo (Philippe Hurbain).
 *
 * FILE TYPES:
 *   .dat - Single part definition (primitive geometry)
 *   .ldr - Model file (assembly of parts)
 *   .mpd - Multi-Part Document (multiple .ldr models in one file)
 *
 * MPD STRUCTURE:
 *   0 FILE ModelName.ldr       <- Start of a submodel
 *   0 Name: ModelName          <- Optional name meta-command
 *   1 <color> <x> <y> <z> <rotation matrix 9 values> <part.dat or submodel.ldr>
 *   ...
 *   0 FILE AnotherModel.ldr    <- Next submodel
 *   ...
 *
 * TYPE 1 LINE FORMAT (part/submodel placement):
 *   1 <color> <x> <y> <z> <a> <b> <c> <d> <e> <f> <g> <h> <i> <part>
 *
 *   - color: LDraw color code (see LDRAW_COLORS below)
 *   - x, y, z: Position in LDU (LDraw Units)
 *   - a-i: 3x3 rotation matrix in ROW-MAJOR order:
 *       | a b c |
 *       | d e f |
 *       | g h i |
 *   - part: Either a .dat part file or .ldr submodel reference
 *
 * COORDINATE SYSTEM (LDraw):
 *   - X: Right
 *   - Y: Down (gravity is +Y)
 *   - Z: Back (away from viewer)
 *   - Units: LDU where 1 LDU = 0.4mm
 *
 * COLOR INHERITANCE:
 *   - Color 16 means "inherit from parent"
 *   - When a submodel uses color 16, it takes the color specified by its parent
 *   - This allows reusable submodels that can be different colors
 *
 * HIERARCHY FLATTENING:
 *   This loader expands the submodel hierarchy into a flat list of parts.
 *   Each part gets its final world position and composed rotation matrix.
 *   The expand_submodel() function handles recursive composition:
 *     - world_position = parent_position + parent_rotation * local_position
 *     - world_rotation = parent_rotation * local_rotation
 *
 * VEX IQ PARTS:
 *   VEX IQ parts use the 228-xxxx numbering scheme (228 = VEX IQ in LDraw).
 *   Part files are named like: 228-2500-021.dat (structural beam)
 *   Special parts include:
 *     - 228-2560*.dat - Smart motors
 *     - 228-2540*.dat - Robot brain
 *     - 228-3010.dat  - Touch LED
 *     - 228-3011.dat  - Bumper switch
 *     - 228-3012.dat  - Color sensor
 *     - 228-3014.dat  - Gyro sensor
 *     - 228-2500-208/209.dat - Wheels and tires
 *
 * =============================================================================
 */

#include "mpd_loader.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <map>
#include <string>
#include <vector>

// VEX IQ LDraw color palette (from LDConfig.ldr by Philo)
static const LDrawColor LDRAW_COLORS[] = {
    // Special
    {16,  1.00f, 1.00f, 1.00f, "Main Color"},
    {24,  0.50f, 0.50f, 0.50f, "Edge Color"},

    // VEX IQ Solid Colors
    {0,   0.145f, 0.157f, 0.165f, "VEX Black"},
    {2,   0.000f, 0.588f, 0.224f, "VEX Green"},
    {4,   0.824f, 0.149f, 0.188f, "VEX Red"},
    {5,   0.898f, 0.427f, 0.694f, "VEX Pink"},
    {7,   0.698f, 0.706f, 0.698f, "VEX Light Gray"},
    {10,  0.263f, 0.690f, 0.165f, "VEX Bright Green"},
    {11,  0.000f, 0.698f, 0.765f, "VEX Teal"},
    {14,  1.000f, 0.804f, 0.000f, "VEX Yellow"},
    {15,  1.000f, 1.000f, 1.000f, "VEX Bright White"},
    {17,  0.761f, 0.855f, 0.722f, "Light Green"},
    {22,  0.373f, 0.145f, 0.624f, "VEX Purple"},
    {25,  1.000f, 0.404f, 0.122f, "VEX Orange"},
    {26,  0.882f, 0.000f, 0.596f, "VEX Magenta"},
    {27,  0.710f, 0.741f, 0.000f, "VEX Chartreuse"},
    {71,  0.537f, 0.553f, 0.553f, "VEX Medium Gray"},
    {72,  0.329f, 0.345f, 0.353f, "VEX Dark Gray"},
    {73,  0.000f, 0.467f, 0.784f, "VEX Blue"},
    {80,  0.816f, 0.816f, 0.816f, "Metal"},
    {84,  0.796f, 0.376f, 0.082f, "VEX Burnt Orange"},
    {89,  0.000f, 0.200f, 0.627f, "VEX Navy Blue"},
    {112, 0.420f, 0.357f, 0.780f, "VEX Lavender"},
    {115, 0.592f, 0.843f, 0.000f, "VEX Lime Green"},
    {150, 0.733f, 0.780f, 0.839f, "VEX Light Slate Gray"},
    {151, 0.851f, 0.851f, 0.839f, "VEX White"},
    {191, 0.855f, 0.667f, 0.000f, "VEX Gold"},
    {212, 0.384f, 0.710f, 0.898f, "VEX Sky Blue"},
    {216, 0.463f, 0.137f, 0.184f, "VEX Maroon"},
    {272, 0.000f, 0.298f, 0.592f, "VEX Royal Blue"},
    {288, 0.125f, 0.361f, 0.251f, "VEX Dark Green"},
    {320, 0.651f, 0.098f, 0.180f, "VEX Crimson Red"},
    {321, 0.196f, 0.384f, 0.584f, "VEX Denim Blue"},
    {462, 1.000f, 0.596f, 0.000f, "VEX Citrus Orange"},
    {503, 0.780f, 0.788f, 0.780f, "VEX Very Light Gray"},

    // Rubber
    {256, 0.129f, 0.129f, 0.129f, "Rubber Black"},
    {504, 0.537f, 0.529f, 0.533f, "Rubber Gray"},

    {-1, 0, 0, 0, NULL}  // End marker
};

void ldraw_get_color(int color_code, float* r, float* g, float* b) {
    for (int i = 0; LDRAW_COLORS[i].code >= 0; i++) {
        if (LDRAW_COLORS[i].code == color_code) {
            *r = LDRAW_COLORS[i].r;
            *g = LDRAW_COLORS[i].g;
            *b = LDRAW_COLORS[i].b;
            return;
        }
    }
    *r = 0.5f;
    *g = 0.5f;
    *b = 0.5f;
}

// Internal submodel structure
struct SubmodelRef {
    std::string name;
    int color_code;
    float x, y, z;
    float rotation[9];
};

struct Submodel {
    std::string name;
    std::vector<MpdPart> parts;           // Direct .dat part references
    std::vector<SubmodelRef> submodels;   // References to other submodels
};

// Multiply 3x3 rotation matrices (row-major)
static void matrix_multiply(const float* a, const float* b, float* out) {
    out[0] = a[0]*b[0] + a[1]*b[3] + a[2]*b[6];
    out[1] = a[0]*b[1] + a[1]*b[4] + a[2]*b[7];
    out[2] = a[0]*b[2] + a[1]*b[5] + a[2]*b[8];
    out[3] = a[3]*b[0] + a[4]*b[3] + a[5]*b[6];
    out[4] = a[3]*b[1] + a[4]*b[4] + a[5]*b[7];
    out[5] = a[3]*b[2] + a[4]*b[5] + a[5]*b[8];
    out[6] = a[6]*b[0] + a[7]*b[3] + a[8]*b[6];
    out[7] = a[6]*b[1] + a[7]*b[4] + a[8]*b[7];
    out[8] = a[6]*b[2] + a[7]*b[5] + a[8]*b[8];
}

// Transform point by rotation matrix
static void transform_point(const float* rot, float x, float y, float z, float* ox, float* oy, float* oz) {
    *ox = rot[0]*x + rot[1]*y + rot[2]*z;
    *oy = rot[3]*x + rot[4]*y + rot[5]*z;
    *oz = rot[6]*x + rot[7]*y + rot[8]*z;
}

// Parse a type 1 line
static bool parse_type1_line(const char* line, int* color, float* x, float* y, float* z,
                             float* rot, char* part_name, size_t name_size) {
    while (*line && isspace(*line)) line++;
    if (line[0] != '1' || !isspace(line[1])) return false;

    int n = sscanf(line, "1 %d %f %f %f %f %f %f %f %f %f %f %f %f %127s",
                   color, x, y, z,
                   &rot[0], &rot[1], &rot[2],
                   &rot[3], &rot[4], &rot[5],
                   &rot[6], &rot[7], &rot[8],
                   part_name);
    return n >= 14;
}

// Check if name is a submodel reference (.ldr)
static bool is_submodel_ref(const char* name) {
    const char* ext = strrchr(name, '.');
    if (!ext) return false;
    return (strcasecmp(ext, ".ldr") == 0 || strcasecmp(ext, ".mpd") == 0);
}

// Recursively expand submodel into flat part list
// current_submodel_idx: index of the top-level submodel we're inside (-1 for main or when not tracking)
static void expand_submodel(const std::string& name,
                           const std::map<std::string, Submodel>& submodels,
                           float px, float py, float pz,
                           const float* parent_rot,
                           int parent_color,
                           MpdDocument* out_doc,
                           int depth = 0,
                           int current_submodel_idx = -1) {
    if (depth > 20) {
        fprintf(stderr, "[MPD] Warning: Max recursion depth reached for %s\n", name.c_str());
        return;
    }

    auto it = submodels.find(name);
    if (it == submodels.end()) {
        // Try lowercase
        std::string lower_name = name;
        for (auto& c : lower_name) c = tolower(c);
        it = submodels.find(lower_name);
        if (it == submodels.end()) {
            return;
        }
    }

    const Submodel& sub = it->second;

    // Add all direct parts with transformed position and composed rotation
    for (const auto& part : sub.parts) {
        if (out_doc->part_count >= MPD_MAX_PARTS) {
            fprintf(stderr, "[MPD] Warning: Too many parts (max %d)\n", MPD_MAX_PARTS);
            return;
        }

        MpdPart out_part;
        strncpy(out_part.part_name, part.part_name, MPD_MAX_NAME - 1);
        out_part.part_name[MPD_MAX_NAME - 1] = '\0';

        // Color inheritance: color 16 inherits from parent
        out_part.color_code = (part.color_code == 16) ? parent_color : part.color_code;

        // Transform local position by parent rotation, add to parent position
        float rx, ry, rz;
        transform_point(parent_rot, part.x, part.y, part.z, &rx, &ry, &rz);
        out_part.x = px + rx;
        out_part.y = py + ry;
        out_part.z = pz + rz;

        // Compose rotations
        matrix_multiply(parent_rot, part.rotation, out_part.rotation);

        // Track which submodel this part belongs to
        out_part.submodel_index = current_submodel_idx;

        out_doc->parts[out_doc->part_count++] = out_part;
    }

    // Recursively expand submodel references
    for (const auto& ref : sub.submodels) {
        // Transform submodel position
        float rx, ry, rz;
        transform_point(parent_rot, ref.x, ref.y, ref.z, &rx, &ry, &rz);
        float new_x = px + rx;
        float new_y = py + ry;
        float new_z = pz + rz;

        // Compose rotations
        float new_rot[9];
        matrix_multiply(parent_rot, ref.rotation, new_rot);

        // Color inheritance
        int new_color = (ref.color_code == 16) ? parent_color : ref.color_code;

        // At depth 0 (main model), each submodel reference becomes a top-level submodel
        int submodel_idx = current_submodel_idx;
        if (depth == 0 && out_doc->submodel_count < MPD_MAX_SUBMODELS) {
            submodel_idx = (int)out_doc->submodel_count;
            MpdSubmodel* sm = &out_doc->submodels[out_doc->submodel_count++];
            strncpy(sm->name, ref.name.c_str(), MPD_MAX_NAME - 1);
            sm->name[MPD_MAX_NAME - 1] = '\0';
            sm->part_start = out_doc->part_count;
            sm->part_count = 0;  // Will be updated after expansion
        }

        uint32_t parts_before = out_doc->part_count;
        expand_submodel(ref.name, submodels, new_x, new_y, new_z, new_rot, new_color, out_doc, depth + 1, submodel_idx);

        // Update part count for top-level submodels
        if (depth == 0 && submodel_idx >= 0 && submodel_idx < (int)out_doc->submodel_count) {
            out_doc->submodels[submodel_idx].part_count = out_doc->part_count - parts_before;
        }
    }
}

bool mpd_load(const char* path, MpdDocument* out_doc) {
    memset(out_doc, 0, sizeof(MpdDocument));

    FILE* f = fopen(path, "r");
    if (!f) {
        fprintf(stderr, "[MPD] Failed to open: %s\n", path);
        return false;
    }

    std::map<std::string, Submodel> submodels;
    std::string main_model;
    std::string current_model;
    Submodel* current = nullptr;

    char line[1024];
    while (fgets(line, sizeof(line), f)) {
        // Remove trailing newline
        size_t len = strlen(line);
        while (len > 0 && (line[len-1] == '\n' || line[len-1] == '\r')) {
            line[--len] = '\0';
        }
        if (len == 0) continue;

        // Check for FILE marker
        if (strncmp(line, "0 FILE ", 7) == 0) {
            // Save previous model if any
            if (current) {
                submodels[current_model] = *current;
            }

            current_model = line + 7;
            // Trim whitespace
            while (!current_model.empty() && isspace(current_model.back())) {
                current_model.pop_back();
            }

            // First FILE is main model
            if (main_model.empty()) {
                main_model = current_model;
            }

            submodels[current_model] = Submodel();
            current = &submodels[current_model];
            current->name = current_model;
            continue;
        }

        // Skip if no current model
        if (!current) continue;

        // Skip meta-commands
        if (line[0] == '0') continue;

        // Parse type 1 lines
        if (line[0] == '1') {
            int color;
            float x, y, z;
            float rot[9];
            char part_name[MPD_MAX_NAME];

            if (parse_type1_line(line, &color, &x, &y, &z, rot, part_name, sizeof(part_name))) {
                if (is_submodel_ref(part_name)) {
                    // Submodel reference
                    SubmodelRef ref;
                    ref.name = part_name;
                    ref.color_code = color;
                    ref.x = x;
                    ref.y = y;
                    ref.z = z;
                    memcpy(ref.rotation, rot, sizeof(rot));
                    current->submodels.push_back(ref);
                } else {
                    // Direct part reference
                    MpdPart part;
                    strncpy(part.part_name, part_name, MPD_MAX_NAME - 1);
                    part.part_name[MPD_MAX_NAME - 1] = '\0';
                    part.color_code = color;
                    part.x = x;
                    part.y = y;
                    part.z = z;
                    memcpy(part.rotation, rot, sizeof(rot));
                    current->parts.push_back(part);
                }
            }
        }
    }

    // Save last model
    if (current) {
        submodels[current_model] = *current;
    }

    fclose(f);

    // Expand main model recursively
    if (main_model.empty()) {
        fprintf(stderr, "[MPD] No main model found\n");
        return false;
    }

    strncpy(out_doc->name, main_model.c_str(), MPD_MAX_NAME - 1);

    // Identity rotation for root
    float identity[9] = {1, 0, 0, 0, 1, 0, 0, 0, 1};

    // Default color (VEX dark gray)
    int default_color = 72;

    expand_submodel(main_model, submodels, 0, 0, 0, identity, default_color, out_doc);

    printf("[MPD] Loaded: %s (%u parts, %u top-level submodels from %zu total submodels)\n",
           out_doc->name, out_doc->part_count, out_doc->submodel_count, submodels.size());

    return out_doc->part_count > 0;
}

void mpd_free(MpdDocument* doc) {
    memset(doc, 0, sizeof(MpdDocument));
}

void mpd_print_info(const MpdDocument* doc) {
    printf("MPD Document: %s\n", doc->name[0] ? doc->name : "(unnamed)");
    printf("  Parts: %u\n", doc->part_count);
    printf("  Submodels: %u\n", doc->submodel_count);

    // Print submodel info
    for (uint32_t i = 0; i < doc->submodel_count; i++) {
        const MpdSubmodel* sm = &doc->submodels[i];
        printf("    [%u] %s: %u parts (start=%u)\n", i, sm->name, sm->part_count, sm->part_start);
    }

    // Count parts not in any submodel (directly in main)
    uint32_t main_parts = 0;
    for (uint32_t i = 0; i < doc->part_count; i++) {
        if (doc->parts[i].submodel_index < 0) main_parts++;
    }
    if (main_parts > 0) {
        printf("    [main] %u parts directly in main model\n", main_parts);
    }

    // Just print first 10 and last 5 for large models
    uint32_t show_first = (doc->part_count > 15) ? 10 : doc->part_count;
    uint32_t show_last = (doc->part_count > 15) ? 5 : 0;

    printf("  Part list:\n");
    for (uint32_t i = 0; i < show_first; i++) {
        const MpdPart* p = &doc->parts[i];
        printf("    [%u] %s (color %d, submodel %d)\n", i, p->part_name, p->color_code, p->submodel_index);
    }

    if (show_last > 0) {
        printf("    ... (%u more parts) ...\n", doc->part_count - show_first - show_last);
        for (uint32_t i = doc->part_count - show_last; i < doc->part_count; i++) {
            const MpdPart* p = &doc->parts[i];
            printf("    [%u] %s (color %d, submodel %d)\n", i, p->part_name, p->color_code, p->submodel_index);
        }
    }
}
