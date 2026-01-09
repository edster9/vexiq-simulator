/*
 * Simple Text Renderer
 * Renders text using a built-in bitmap font
 */

#ifndef TEXT_H
#define TEXT_H

#include <stdbool.h>

// Initialize text rendering system
bool text_init(void);

// Cleanup
void text_destroy(void);

// Render text at screen position (0,0 = top-left)
// x, y are in pixels from top-left
// screen_width, screen_height are the viewport dimensions
void text_render(const char* str, float x, float y, int screen_width, int screen_height);

// Render text aligned to right edge
void text_render_right(const char* str, float margin, float y, int screen_width, int screen_height);

#endif // TEXT_H
