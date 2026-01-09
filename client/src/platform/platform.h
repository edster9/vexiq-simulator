#ifndef PLATFORM_H
#define PLATFORM_H

#include <stdbool.h>
#include <stdint.h>

#define MAX_KEYS 512

typedef struct Platform {
    void* window;       // SDL_Window* internally
    void* gl_context;   // SDL_GLContext internally
    int width;
    int height;
    bool should_quit;
    bool fullscreen;
} Platform;

typedef struct InputState {
    // Keyboard
    bool keys[MAX_KEYS];           // Currently held
    bool keys_pressed[MAX_KEYS];   // Just pressed this frame
    bool keys_released[MAX_KEYS];  // Just released this frame

    // Mouse
    int mouse_x, mouse_y;          // Absolute position
    int mouse_dx, mouse_dy;        // Delta since last frame
    bool mouse_buttons[5];         // Left, Middle, Right, X1, X2
    bool mouse_pressed[5];
    bool mouse_released[5];
    float scroll_y;                // Scroll wheel delta
    bool mouse_captured;           // Is mouse captured (relative mode)
    bool mouse_capture_just_started; // First frame after capture (ignore delta)
} InputState;

// Platform lifecycle
bool platform_init(Platform* p, const char* title, int width, int height);
void platform_shutdown(Platform* p);

// Event callback type (for custom event handlers like gamepad)
// The event parameter is SDL_Event* but typed as void* to avoid SDL dependency in header
typedef void (*PlatformEventCallback)(void* event, void* user_data);

// Frame handling
void platform_poll_events(Platform* p, InputState* input);
void platform_poll_events_ex(Platform* p, InputState* input, PlatformEventCallback callback, void* user_data);
void platform_swap_buffers(Platform* p);

// Timing
double platform_get_time(void);
void platform_sleep(uint32_t ms);

// Mouse capture (for fly camera)
void platform_capture_mouse(Platform* p, InputState* input, bool capture);

// Window
void platform_set_title(Platform* p, const char* title);
void platform_toggle_fullscreen(Platform* p);

// Key codes (matching SDL2 scancodes for common keys)
#define KEY_UNKNOWN     0
#define KEY_A           4
#define KEY_B           5
#define KEY_C           6
#define KEY_D           7
#define KEY_E           8
#define KEY_F           9
#define KEY_G           10
#define KEY_H           11
#define KEY_I           12
#define KEY_J           13
#define KEY_K           14
#define KEY_L           15
#define KEY_M           16
#define KEY_N           17
#define KEY_O           18
#define KEY_P           19
#define KEY_Q           20
#define KEY_R           21
#define KEY_S           22
#define KEY_T           23
#define KEY_U           24
#define KEY_V           25
#define KEY_W           26
#define KEY_X           27
#define KEY_Y           28
#define KEY_Z           29
#define KEY_1           30
#define KEY_2           31
#define KEY_3           32
#define KEY_4           33
#define KEY_5           34
#define KEY_6           35
#define KEY_7           36
#define KEY_8           37
#define KEY_9           38
#define KEY_0           39
#define KEY_ESCAPE      41
#define KEY_TAB         43
#define KEY_SPACE       44
#define KEY_MINUS       45
#define KEY_EQUALS      46
#define KEY_BACKSPACE   42
#define KEY_ENTER       40
#define KEY_LSHIFT      225
#define KEY_RSHIFT      229
#define KEY_LCTRL       224
#define KEY_RCTRL       228
#define KEY_LALT        226
#define KEY_RALT        230
#define KEY_F1          58
#define KEY_F2          59
#define KEY_F3          60
#define KEY_F4          61
#define KEY_F5          62
#define KEY_F6          63
#define KEY_F7          64
#define KEY_F8          65
#define KEY_F9          66
#define KEY_F10         67
#define KEY_F11         68
#define KEY_F12         69

// Arrow keys
#define KEY_RIGHT       79
#define KEY_LEFT        80
#define KEY_DOWN        81
#define KEY_UP          82

#define MOUSE_LEFT      0
#define MOUSE_MIDDLE    1
#define MOUSE_RIGHT     2

#endif // PLATFORM_H
