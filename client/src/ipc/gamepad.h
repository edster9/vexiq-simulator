/*
 * SDL Gamepad Input for VEX IQ Controller Mapping
 *
 * Maps standard gamepad to VEX IQ Controller layout:
 * - Left stick: Axis A (vertical), Axis B (horizontal)
 * - Right stick: Axis D (vertical), Axis C (horizontal)
 * - Shoulder buttons: L-Up, L-Down, R-Up, R-Down
 * - Face buttons: E-Up, E-Down, F-Up, F-Down
 */

#ifndef GAMEPAD_H
#define GAMEPAD_H

#include <stdbool.h>
#include <SDL.h>

// VEX IQ Controller axes (-100 to 100)
typedef struct VexAxes {
    int a;  // Left stick Y (up = positive)
    int b;  // Left stick X (right = positive)
    int c;  // Right stick X (right = positive)
    int d;  // Right stick Y (up = positive)
} VexAxes;

// VEX IQ Controller buttons
typedef struct VexButtons {
    bool l_up;      // Left shoulder up
    bool l_down;    // Left shoulder down
    bool r_up;      // Right shoulder up
    bool r_down;    // Right shoulder down
    bool e_up;      // E button up state (Y on Xbox)
    bool e_down;    // E button down state (A on Xbox)
    bool f_up;      // F button up state (X on Xbox)
    bool f_down;    // F button down state (B on Xbox)
} VexButtons;

typedef struct Gamepad {
    SDL_GameController* controller;
    SDL_JoystickID joystick_id;
    bool connected;
    char name[128];

    VexAxes axes;
    VexButtons buttons;

    // Previous state for edge detection
    VexButtons prev_buttons;
} Gamepad;

// Initialize gamepad system (call after SDL_Init)
void gamepad_init(Gamepad* gp);

// Poll for gamepad connection/disconnection events
// Call this in your main event loop
void gamepad_handle_event(Gamepad* gp, SDL_Event* event);

// Update gamepad state (call each frame)
void gamepad_update(Gamepad* gp);

// Get axes as JSON string for IPC
// Buffer must be at least 128 bytes
void gamepad_axes_to_json(Gamepad* gp, char* buffer, size_t buffer_size);

// Get full state as JSON string for IPC
// Buffer must be at least 256 bytes
void gamepad_to_json(Gamepad* gp, char* buffer, size_t buffer_size);

// Cleanup
void gamepad_destroy(Gamepad* gp);

#endif // GAMEPAD_H
