/*
 * GLB (Binary glTF) Loader
 * Parses GLB files and extracts mesh data for OpenGL rendering.
 * Supports: POSITION, NORMAL, COLOR_0 attributes (vertex colors)
 */

#ifndef GLB_LOADER_H
#define GLB_LOADER_H

#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>

// Maximum vertices/indices we support
#define MAX_VERTICES 100000
#define MAX_INDICES  300000

// Vertex with position, normal, and color
typedef struct Vertex {
    float position[3];
    float normal[3];
    float color[4];     // RGBA (0-1)
} Vertex;

// Loaded mesh data
typedef struct MeshData {
    Vertex* vertices;
    uint32_t vertex_count;

    uint32_t* indices;
    uint32_t index_count;

    // Bounding box
    float min_bounds[3];
    float max_bounds[3];

    char name[128];
} MeshData;

// Load a GLB file and extract mesh data
// Returns true on success, false on failure
// Caller must call mesh_data_free() when done
bool glb_load(const char* path, MeshData* out_mesh);

// Free mesh data
void mesh_data_free(MeshData* mesh);

// Print mesh info for debugging
void mesh_data_print_info(const MeshData* mesh);

#endif // GLB_LOADER_H
