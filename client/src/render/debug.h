/*
 * Debug Renderer
 * Provides wireframe rendering for debugging collision shapes, bounding boxes, etc.
 */

#ifndef DEBUG_H
#define DEBUG_H

#include <GL/glew.h>
#include "../math/mat4.h"
#include "../math/vec3.h"
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// Initialize debug renderer (call once at startup)
bool debug_init(void);

// Destroy debug renderer
void debug_destroy(void);

// Begin debug rendering frame (call before any debug draw calls)
void debug_begin(const Mat4* view, const Mat4* projection);

// Draw a wireframe box (axis-aligned in local space)
// center: center of box in world coordinates
// half_extents: half-size in each axis
// color: RGB color (0-1)
void debug_draw_box(Vec3 center, Vec3 half_extents, Vec3 color);

// Draw a wireframe box with full transform matrix
// model: transformation matrix
// min_bounds, max_bounds: local-space bounds
// color: RGB color (0-1)
void debug_draw_box_transformed(const Mat4* model, const float* min_bounds, const float* max_bounds, Vec3 color);

// Draw a line from A to B
void debug_draw_line(Vec3 a, Vec3 b, Vec3 color);

// Draw coordinate axes at position (for debugging orientation)
void debug_draw_axes(Vec3 pos, float length);

// Draw a wireframe cylinder (for collision debugging)
// center: center of cylinder
// radius: cylinder radius
// half_height: half-height (full height = 2 * half_height)
// color: RGB color
void debug_draw_cylinder(Vec3 center, float radius, float half_height, Vec3 color);

// End debug rendering (flush all queued primitives)
void debug_end(void);

#ifdef __cplusplus
}
#endif

#endif // DEBUG_H
