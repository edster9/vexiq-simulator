/*
 * MPD/LDR Loader for LDraw files
 * Parses Multi-Part Document files used by VEX IQ LDCad models
 *
 * This loader reads LDraw MPD files and produces a flat list of part placements.
 * All positions and rotations are in LDraw coordinates (Y-down, Z-back).
 * The rendering code (build_ldraw_model_matrix) handles conversion to OpenGL.
 *
 * See mpd_loader.cpp for detailed documentation on the LDraw file format.
 */

#ifndef MPD_LOADER_H
#define MPD_LOADER_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// Maximum limits
#define MPD_MAX_PARTS 1024
#define MPD_MAX_NAME 128
#define MPD_MAX_SUBMODELS 64

// LDraw color codes (VEX IQ palette from LDConfig.ldr)
typedef struct {
    int code;
    float r, g, b;
    const char* name;
} LDrawColor;

// Get color RGB from LDraw color code
// Returns default gray (0.5, 0.5, 0.5) if not found
void ldraw_get_color(int color_code, float* r, float* g, float* b);

// Part placement in an MPD file
typedef struct {
    char part_name[MPD_MAX_NAME];   // e.g., "228-2500-016.dat"
    int color_code;                  // LDraw color code
    float x, y, z;                   // Position in LDU
    float rotation[9];               // 3x3 rotation matrix (row-major)
    int submodel_index;              // Index into submodel_names (-1 for parts directly in main)
} MpdPart;

// Submodel info (for hierarchical collision)
typedef struct {
    char name[MPD_MAX_NAME];         // Submodel name (e.g., "wheelsleft.ldr")
    uint32_t part_start;             // First part index in parts array
    uint32_t part_count;             // Number of parts in this submodel
} MpdSubmodel;

// Loaded MPD document
typedef struct {
    char name[MPD_MAX_NAME];                  // Model name
    MpdPart parts[MPD_MAX_PARTS];             // Part placements
    uint32_t part_count;                      // Number of parts
    MpdSubmodel submodels[MPD_MAX_SUBMODELS]; // Submodel info for hierarchy
    uint32_t submodel_count;                  // Number of submodels
} MpdDocument;

// Load an MPD or LDR file
// Returns true on success, fills out_doc
bool mpd_load(const char* path, MpdDocument* out_doc);

// Free MPD document resources (if any dynamic allocation)
void mpd_free(MpdDocument* doc);

// Print document info
void mpd_print_info(const MpdDocument* doc);

// Scale constants
// LDU to world units: LDraw uses LDU (0.4mm), our GLB models are 0.02x LDU scale
#define LDU_SCALE 0.02f

// Convert LDraw position to OpenGL world coordinates
// LDraw: Y-down, Z-back -> OpenGL: Y-up, Z-front
// Both Y and Z must be flipped for correct rendering
static inline void ldraw_to_world(float lx, float ly, float lz, float* wx, float* wy, float* wz) {
    *wx = lx * LDU_SCALE;
    *wy = -ly * LDU_SCALE;  // Flip Y (down -> up)
    *wz = -lz * LDU_SCALE;  // Flip Z (back -> front)
}

#ifdef __cplusplus
}
#endif

#endif // MPD_LOADER_H
