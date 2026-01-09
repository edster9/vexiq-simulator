/*
 * GLB Loader Implementation
 * Parses binary glTF 2.0 files for VEX IQ part meshes
 *
 * =============================================================================
 * GLB FILE FORMAT AND VEX IQ PART PIPELINE
 * =============================================================================
 *
 * GLB is the binary container format for glTF 2.0, a standard 3D model format.
 * We use GLB files for VEX IQ part meshes because:
 *   - Compact binary format (faster loading than text-based formats)
 *   - Industry standard with wide tool support
 *   - Supports vertex colors (needed for part coloring)
 *   - Y-up coordinate system matches OpenGL
 *
 * HOW VEX IQ PARTS BECOME GLB FILES:
 *   1. Original parts are LDraw .dat files (text-based geometry)
 *   2. Blender imports .dat files using the LDraw importer addon
 *   3. Blender converts coordinates: LDraw Y-down -> Blender Z-up
 *   4. Parts are scaled to 0.02x (so LDU * 0.02 = GLB units)
 *   5. Vertex colors are set to white for colorable areas
 *   6. Export as GLB with Y-up (glTF standard)
 *   7. Result: GLB in OpenGL coordinates (Y-up, Z-front)
 *
 * VERTEX COLOR CONVENTION:
 *   - White (1,1,1) = Colorable area - shader will tint with LDraw color
 *   - Non-white = Baked color - shader preserves original color
 *   - This allows parts like motors to have fixed black/green areas
 *     while structural parts can be any color
 *
 * GLB STRUCTURE:
 *   [12-byte header]
 *     - magic: "glTF" (0x46546C67)
 *     - version: 2
 *     - length: total file size
 *   [JSON chunk]
 *     - chunk length
 *     - chunk type: "JSON" (0x4E4F534A)
 *     - JSON data describing meshes, accessors, buffer views
 *   [BIN chunk]
 *     - chunk length
 *     - chunk type: "BIN\0" (0x004E4942)
 *     - Binary data (vertices, indices, etc.)
 *
 * WHAT THIS LOADER EXTRACTS:
 *   - Vertex positions (VEC3 float)
 *   - Vertex normals (VEC3 float)
 *   - Vertex colors (VEC3 or VEC4 float) - defaults to white if missing
 *   - Triangle indices (SCALAR unsigned short or unsigned int)
 *
 * COORDINATE SYSTEM:
 *   GLB files are in glTF standard coordinates:
 *     - X: Right
 *     - Y: Up
 *     - Z: Front (toward viewer)
 *   This matches OpenGL, so no conversion needed when rendering.
 *   The coordinate conversion happens in build_ldraw_model_matrix()
 *   which transforms the LDraw positions/rotations to OpenGL space.
 *
 * =============================================================================
 */

#include "glb_loader.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

// GLB constants
#define GLB_MAGIC 0x46546C67  // "glTF"
#define GLB_VERSION 2
#define GLB_CHUNK_JSON 0x4E4F534A  // "JSON"
#define GLB_CHUNK_BIN  0x004E4942  // "BIN\0"

// GLTF accessor component types
#define COMPONENT_BYTE           5120
#define COMPONENT_UNSIGNED_BYTE  5121
#define COMPONENT_SHORT          5122
#define COMPONENT_UNSIGNED_SHORT 5123
#define COMPONENT_UNSIGNED_INT   5125
#define COMPONENT_FLOAT          5126

// Simple JSON parser helpers (finds values by key)
static const char* json_find_key(const char* json, const char* key) {
    char pattern[256];
    snprintf(pattern, sizeof(pattern), "\"%s\"", key);
    const char* pos = strstr(json, pattern);
    if (!pos) return NULL;
    pos = strchr(pos, ':');
    if (!pos) return NULL;
    return pos + 1;
}

static int json_get_int(const char* json, const char* key, int default_val) {
    const char* pos = json_find_key(json, key);
    if (!pos) return default_val;
    while (*pos && (*pos == ' ' || *pos == '\t')) pos++;
    return atoi(pos);
}

static void json_get_string(const char* json, const char* key, char* out, size_t out_size) {
    out[0] = '\0';
    const char* pos = json_find_key(json, key);
    if (!pos) return;
    while (*pos && *pos != '"') pos++;
    if (*pos != '"') return;
    pos++;
    size_t i = 0;
    while (*pos && *pos != '"' && i < out_size - 1) {
        out[i++] = *pos++;
    }
    out[i] = '\0';
}

// Find array element by index: finds the Nth {...} or [...] block
static const char* json_array_element(const char* array_start, int index) {
    const char* pos = array_start;
    while (*pos && *pos != '[') pos++;
    if (*pos != '[') return NULL;
    pos++;

    int depth = 0;
    int current_index = 0;
    const char* element_start = NULL;

    while (*pos) {
        if (*pos == '{' || *pos == '[') {
            if (depth == 0 && current_index == index) {
                element_start = pos;
            }
            depth++;
        } else if (*pos == '}' || *pos == ']') {
            depth--;
            if (depth == 0) {
                if (current_index == index && element_start) {
                    return element_start;
                }
                current_index++;
            }
            if (depth < 0) break;
        }
        pos++;
    }
    return NULL;
}

// Read data from buffer based on accessor info
static bool read_accessor_data(
    const uint8_t* bin_data,
    size_t bin_size,
    const char* json,
    int accessor_index,
    void* out_data,
    size_t element_size,
    size_t* out_count
) {
    // Find accessor
    const char* accessors = json_find_key(json, "accessors");
    if (!accessors) return false;

    const char* accessor = json_array_element(accessors, accessor_index);
    if (!accessor) return false;

    int buffer_view = json_get_int(accessor, "bufferView", -1);
    int count = json_get_int(accessor, "count", 0);
    int component_type = json_get_int(accessor, "componentType", 0);
    int byte_offset_acc = json_get_int(accessor, "byteOffset", 0);

    if (buffer_view < 0 || count == 0) return false;

    // Find buffer view
    const char* buffer_views = json_find_key(json, "bufferViews");
    if (!buffer_views) return false;

    const char* bv = json_array_element(buffer_views, buffer_view);
    if (!bv) return false;

    int byte_offset_bv = json_get_int(bv, "byteOffset", 0);
    int byte_length = json_get_int(bv, "byteLength", 0);
    int byte_stride = json_get_int(bv, "byteStride", 0);

    size_t total_offset = byte_offset_bv + byte_offset_acc;
    if (total_offset + byte_length > bin_size) return false;

    const uint8_t* src = bin_data + total_offset;
    uint8_t* dst = (uint8_t*)out_data;

    // Calculate actual stride
    size_t actual_stride = byte_stride > 0 ? byte_stride : element_size;

    for (int i = 0; i < count; i++) {
        memcpy(dst + i * element_size, src + i * actual_stride, element_size);
    }

    *out_count = count;
    return true;
}

// Read indices (handles different component types)
static bool read_indices(
    const uint8_t* bin_data,
    size_t bin_size,
    const char* json,
    int accessor_index,
    uint32_t* out_indices,
    size_t* out_count
) {
    const char* accessors = json_find_key(json, "accessors");
    if (!accessors) return false;

    const char* accessor = json_array_element(accessors, accessor_index);
    if (!accessor) return false;

    int buffer_view = json_get_int(accessor, "bufferView", -1);
    int count = json_get_int(accessor, "count", 0);
    int component_type = json_get_int(accessor, "componentType", 0);
    int byte_offset_acc = json_get_int(accessor, "byteOffset", 0);

    if (buffer_view < 0 || count == 0) return false;

    const char* buffer_views = json_find_key(json, "bufferViews");
    const char* bv = json_array_element(buffer_views, buffer_view);
    if (!bv) return false;

    int byte_offset_bv = json_get_int(bv, "byteOffset", 0);

    size_t total_offset = byte_offset_bv + byte_offset_acc;
    const uint8_t* src = bin_data + total_offset;

    for (int i = 0; i < count; i++) {
        switch (component_type) {
            case COMPONENT_UNSIGNED_BYTE:
                out_indices[i] = src[i];
                break;
            case COMPONENT_UNSIGNED_SHORT:
                out_indices[i] = ((const uint16_t*)src)[i];
                break;
            case COMPONENT_UNSIGNED_INT:
                out_indices[i] = ((const uint32_t*)src)[i];
                break;
            default:
                return false;
        }
    }

    *out_count = count;
    return true;
}

// Find attribute accessor index
static int find_attribute_accessor(const char* primitive, const char* attr_name) {
    const char* attrs = json_find_key(primitive, "attributes");
    if (!attrs) return -1;
    return json_get_int(attrs, attr_name, -1);
}

bool glb_load(const char* path, MeshData* out_mesh) {
    memset(out_mesh, 0, sizeof(MeshData));

    // Open file
    FILE* f = fopen(path, "rb");
    if (!f) {
        fprintf(stderr, "[GLB] Failed to open: %s\n", path);
        return false;
    }

    // Get file size
    fseek(f, 0, SEEK_END);
    size_t file_size = ftell(f);
    fseek(f, 0, SEEK_SET);

    // Read entire file
    uint8_t* file_data = (uint8_t*)malloc(file_size);
    if (!file_data) {
        fclose(f);
        return false;
    }
    fread(file_data, 1, file_size, f);
    fclose(f);

    // Parse header
    if (file_size < 12) {
        fprintf(stderr, "[GLB] File too small\n");
        free(file_data);
        return false;
    }

    uint32_t magic = *(uint32_t*)(file_data);
    uint32_t version = *(uint32_t*)(file_data + 4);
    uint32_t length = *(uint32_t*)(file_data + 8);

    if (magic != GLB_MAGIC || version != GLB_VERSION) {
        fprintf(stderr, "[GLB] Invalid header (magic=0x%X, version=%u)\n", magic, version);
        free(file_data);
        return false;
    }

    // Parse JSON chunk
    size_t offset = 12;
    if (offset + 8 > file_size) {
        free(file_data);
        return false;
    }

    uint32_t json_length = *(uint32_t*)(file_data + offset);
    uint32_t json_type = *(uint32_t*)(file_data + offset + 4);
    offset += 8;

    if (json_type != GLB_CHUNK_JSON || offset + json_length > file_size) {
        fprintf(stderr, "[GLB] Invalid JSON chunk\n");
        free(file_data);
        return false;
    }

    char* json = (char*)malloc(json_length + 1);
    memcpy(json, file_data + offset, json_length);
    json[json_length] = '\0';
    offset += json_length;

    // Parse binary chunk
    if (offset + 8 > file_size) {
        fprintf(stderr, "[GLB] Missing binary chunk\n");
        free(json);
        free(file_data);
        return false;
    }

    uint32_t bin_length = *(uint32_t*)(file_data + offset);
    uint32_t bin_type = *(uint32_t*)(file_data + offset + 4);
    offset += 8;

    if (bin_type != GLB_CHUNK_BIN || offset + bin_length > file_size) {
        fprintf(stderr, "[GLB] Invalid binary chunk\n");
        free(json);
        free(file_data);
        return false;
    }

    const uint8_t* bin_data = file_data + offset;

    // Get mesh name
    const char* meshes = json_find_key(json, "meshes");
    if (meshes) {
        const char* mesh0 = json_array_element(meshes, 0);
        if (mesh0) {
            json_get_string(mesh0, "name", out_mesh->name, sizeof(out_mesh->name));
        }
    }

    // Find first primitive
    const char* primitives = json_find_key(json, "primitives");
    if (!primitives) {
        // Try to find it under meshes[0]
        if (meshes) {
            const char* mesh0 = json_array_element(meshes, 0);
            if (mesh0) {
                primitives = json_find_key(mesh0, "primitives");
            }
        }
    }

    if (!primitives) {
        fprintf(stderr, "[GLB] No primitives found\n");
        free(json);
        free(file_data);
        return false;
    }

    const char* prim0 = json_array_element(primitives, 0);
    if (!prim0) {
        fprintf(stderr, "[GLB] No primitive[0] found\n");
        free(json);
        free(file_data);
        return false;
    }

    // Get attribute accessors
    int pos_accessor = find_attribute_accessor(prim0, "POSITION");
    int norm_accessor = find_attribute_accessor(prim0, "NORMAL");
    int color_accessor = find_attribute_accessor(prim0, "COLOR_0");
    int indices_accessor = json_get_int(prim0, "indices", -1);

    if (pos_accessor < 0) {
        fprintf(stderr, "[GLB] No POSITION attribute\n");
        free(json);
        free(file_data);
        return false;
    }

    // Read positions
    float* positions = (float*)malloc(MAX_VERTICES * 3 * sizeof(float));
    size_t pos_count = 0;
    if (!read_accessor_data(bin_data, bin_length, json, pos_accessor, positions, 3 * sizeof(float), &pos_count)) {
        fprintf(stderr, "[GLB] Failed to read positions\n");
        free(positions);
        free(json);
        free(file_data);
        return false;
    }

    // Read normals (optional)
    float* normals = (float*)calloc(MAX_VERTICES * 3, sizeof(float));
    size_t norm_count = 0;
    if (norm_accessor >= 0) {
        read_accessor_data(bin_data, bin_length, json, norm_accessor, normals, 3 * sizeof(float), &norm_count);
    }

    // Read vertex colors (optional) - can be vec3 or vec4, float or normalized byte
    float* colors = (float*)malloc(MAX_VERTICES * 4 * sizeof(float));
    for (size_t i = 0; i < MAX_VERTICES; i++) {
        colors[i * 4 + 0] = 0.7f;  // Default gray
        colors[i * 4 + 1] = 0.7f;
        colors[i * 4 + 2] = 0.7f;
        colors[i * 4 + 3] = 1.0f;
    }

    size_t color_count = 0;
    if (color_accessor >= 0) {
        // Check component type and element count
        const char* accessors = json_find_key(json, "accessors");
        const char* acc = json_array_element(accessors, color_accessor);
        if (acc) {
            int comp_type = json_get_int(acc, "componentType", COMPONENT_FLOAT);
            char type_str[32] = "";
            json_get_string(acc, "type", type_str, sizeof(type_str));

            bool is_vec4 = (strcmp(type_str, "VEC4") == 0);
            int components = is_vec4 ? 4 : 3;

            if (comp_type == COMPONENT_FLOAT) {
                float* temp_colors = (float*)malloc(MAX_VERTICES * 4 * sizeof(float));
                if (read_accessor_data(bin_data, bin_length, json, color_accessor, temp_colors, components * sizeof(float), &color_count)) {
                    for (size_t i = 0; i < color_count; i++) {
                        colors[i * 4 + 0] = temp_colors[i * components + 0];
                        colors[i * 4 + 1] = temp_colors[i * components + 1];
                        colors[i * 4 + 2] = temp_colors[i * components + 2];
                        colors[i * 4 + 3] = is_vec4 ? temp_colors[i * components + 3] : 1.0f;
                    }
                }
                free(temp_colors);
            } else if (comp_type == COMPONENT_UNSIGNED_BYTE) {
                uint8_t* temp_colors = (uint8_t*)malloc(MAX_VERTICES * 4);
                if (read_accessor_data(bin_data, bin_length, json, color_accessor, temp_colors, components, &color_count)) {
                    for (size_t i = 0; i < color_count; i++) {
                        colors[i * 4 + 0] = temp_colors[i * components + 0] / 255.0f;
                        colors[i * 4 + 1] = temp_colors[i * components + 1] / 255.0f;
                        colors[i * 4 + 2] = temp_colors[i * components + 2] / 255.0f;
                        colors[i * 4 + 3] = is_vec4 ? temp_colors[i * components + 3] / 255.0f : 1.0f;
                    }
                }
                free(temp_colors);
            } else if (comp_type == COMPONENT_UNSIGNED_SHORT) {
                uint16_t* temp_colors = (uint16_t*)malloc(MAX_VERTICES * 4 * sizeof(uint16_t));
                if (read_accessor_data(bin_data, bin_length, json, color_accessor, temp_colors, components * sizeof(uint16_t), &color_count)) {
                    for (size_t i = 0; i < color_count; i++) {
                        colors[i * 4 + 0] = temp_colors[i * components + 0] / 65535.0f;
                        colors[i * 4 + 1] = temp_colors[i * components + 1] / 65535.0f;
                        colors[i * 4 + 2] = temp_colors[i * components + 2] / 65535.0f;
                        colors[i * 4 + 3] = is_vec4 ? temp_colors[i * components + 3] / 65535.0f : 1.0f;
                    }
                }
                free(temp_colors);
            }
        }
    }

    // Read indices
    uint32_t* indices = NULL;
    size_t index_count = 0;
    if (indices_accessor >= 0) {
        indices = (uint32_t*)malloc(MAX_INDICES * sizeof(uint32_t));
        if (!read_indices(bin_data, bin_length, json, indices_accessor, indices, &index_count)) {
            free(indices);
            indices = NULL;
            index_count = 0;
        }
    }

    // Build vertex array
    out_mesh->vertex_count = pos_count;
    out_mesh->vertices = (Vertex*)malloc(pos_count * sizeof(Vertex));

    // Initialize bounds
    out_mesh->min_bounds[0] = out_mesh->min_bounds[1] = out_mesh->min_bounds[2] = 1e10f;
    out_mesh->max_bounds[0] = out_mesh->max_bounds[1] = out_mesh->max_bounds[2] = -1e10f;

    for (size_t i = 0; i < pos_count; i++) {
        Vertex* v = &out_mesh->vertices[i];

        v->position[0] = positions[i * 3 + 0];
        v->position[1] = positions[i * 3 + 1];
        v->position[2] = positions[i * 3 + 2];

        if (i < norm_count) {
            v->normal[0] = normals[i * 3 + 0];
            v->normal[1] = normals[i * 3 + 1];
            v->normal[2] = normals[i * 3 + 2];
        } else {
            v->normal[0] = 0;
            v->normal[1] = 1;
            v->normal[2] = 0;
        }

        v->color[0] = colors[i * 4 + 0];
        v->color[1] = colors[i * 4 + 1];
        v->color[2] = colors[i * 4 + 2];
        v->color[3] = colors[i * 4 + 3];

        // Update bounds
        for (int j = 0; j < 3; j++) {
            if (v->position[j] < out_mesh->min_bounds[j]) out_mesh->min_bounds[j] = v->position[j];
            if (v->position[j] > out_mesh->max_bounds[j]) out_mesh->max_bounds[j] = v->position[j];
        }
    }

    // Copy indices
    if (indices && index_count > 0) {
        out_mesh->index_count = index_count;
        out_mesh->indices = (uint32_t*)malloc(index_count * sizeof(uint32_t));
        memcpy(out_mesh->indices, indices, index_count * sizeof(uint32_t));
    }

    // Cleanup
    free(positions);
    free(normals);
    free(colors);
    free(indices);
    free(json);
    free(file_data);

    printf("[GLB] Loaded: %s (%u vertices, %u indices)\n",
           out_mesh->name[0] ? out_mesh->name : path,
           out_mesh->vertex_count, out_mesh->index_count);

    return true;
}

void mesh_data_free(MeshData* mesh) {
    if (mesh->vertices) {
        free(mesh->vertices);
        mesh->vertices = NULL;
    }
    if (mesh->indices) {
        free(mesh->indices);
        mesh->indices = NULL;
    }
    mesh->vertex_count = 0;
    mesh->index_count = 0;
}

void mesh_data_print_info(const MeshData* mesh) {
    printf("Mesh: %s\n", mesh->name[0] ? mesh->name : "(unnamed)");
    printf("  Vertices: %u\n", mesh->vertex_count);
    printf("  Indices:  %u\n", mesh->index_count);
    printf("  Bounds:   (%.3f, %.3f, %.3f) - (%.3f, %.3f, %.3f)\n",
           mesh->min_bounds[0], mesh->min_bounds[1], mesh->min_bounds[2],
           mesh->max_bounds[0], mesh->max_bounds[1], mesh->max_bounds[2]);

    float size[3] = {
        mesh->max_bounds[0] - mesh->min_bounds[0],
        mesh->max_bounds[1] - mesh->min_bounds[1],
        mesh->max_bounds[2] - mesh->min_bounds[2]
    };
    printf("  Size:     %.3f x %.3f x %.3f\n", size[0], size[1], size[2]);
}
