#include "platform.h"
#include <SDL2/SDL.h>
#include <GL/glew.h>
#include <stdio.h>
#include <string.h>

static bool sdl_initialized = false;

bool platform_init(Platform* p, const char* title, int width, int height) {
    memset(p, 0, sizeof(Platform));
    p->width = width;
    p->height = height;

    // Initialize SDL
    if (!sdl_initialized) {
        if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_TIMER | SDL_INIT_GAMECONTROLLER) < 0) {
            fprintf(stderr, "Failed to initialize SDL: %s\n", SDL_GetError());
            return false;
        }
        sdl_initialized = true;
    }

    // OpenGL attributes (before window creation)
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 3);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 3);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_COMPATIBILITY);
    SDL_GL_SetAttribute(SDL_GL_DOUBLEBUFFER, 1);
    SDL_GL_SetAttribute(SDL_GL_DEPTH_SIZE, 24);
    SDL_GL_SetAttribute(SDL_GL_STENCIL_SIZE, 8);

    // Create window
    SDL_Window* window = SDL_CreateWindow(
        title,
        SDL_WINDOWPOS_CENTERED,
        SDL_WINDOWPOS_CENTERED,
        width,
        height,
        SDL_WINDOW_OPENGL | SDL_WINDOW_RESIZABLE | SDL_WINDOW_SHOWN
    );

    if (!window) {
        fprintf(stderr, "Failed to create window: %s\n", SDL_GetError());
        return false;
    }
    p->window = window;

    // Create OpenGL context
    SDL_GLContext gl_context = SDL_GL_CreateContext(window);
    if (!gl_context) {
        fprintf(stderr, "Failed to create OpenGL context: %s\n", SDL_GetError());
        SDL_DestroyWindow(window);
        return false;
    }
    p->gl_context = gl_context;

    // Initialize GLEW
    glewExperimental = GL_TRUE;
    GLenum glew_err = glewInit();
    if (glew_err != GLEW_OK) {
        fprintf(stderr, "Failed to initialize GLEW: %s\n", glewGetErrorString(glew_err));
        SDL_GL_DeleteContext(gl_context);
        SDL_DestroyWindow(window);
        return false;
    }

    // Clear any GLEW errors
    glGetError();

    // Enable VSync
    SDL_GL_SetSwapInterval(1);

    // Print OpenGL info
    printf("OpenGL Vendor:   %s\n", glGetString(GL_VENDOR));
    printf("OpenGL Renderer: %s\n", glGetString(GL_RENDERER));
    printf("OpenGL Version:  %s\n", glGetString(GL_VERSION));
    printf("GLSL Version:    %s\n", glGetString(GL_SHADING_LANGUAGE_VERSION));

    return true;
}

void platform_shutdown(Platform* p) {
    if (p->gl_context) {
        SDL_GL_DeleteContext(p->gl_context);
        p->gl_context = NULL;
    }
    if (p->window) {
        SDL_DestroyWindow((SDL_Window*)p->window);
        p->window = NULL;
    }
    SDL_Quit();
    sdl_initialized = false;
}

void platform_poll_events_ex(Platform* p, InputState* input, PlatformEventCallback callback, void* user_data) {
    // Reset per-frame state
    memset(input->keys_pressed, 0, sizeof(input->keys_pressed));
    memset(input->keys_released, 0, sizeof(input->keys_released));
    memset(input->mouse_pressed, 0, sizeof(input->mouse_pressed));
    memset(input->mouse_released, 0, sizeof(input->mouse_released));
    input->mouse_dx = 0;
    input->mouse_dy = 0;
    input->scroll_y = 0;

    SDL_Event event;
    while (SDL_PollEvent(&event)) {
        // Call custom event handler if provided
        if (callback) {
            callback(&event, user_data);
        }

        switch (event.type) {
            case SDL_QUIT:
                p->should_quit = true;
                break;

            case SDL_WINDOWEVENT:
                if (event.window.event == SDL_WINDOWEVENT_RESIZED) {
                    p->width = event.window.data1;
                    p->height = event.window.data2;
                }
                break;

            case SDL_KEYDOWN:
                if (!event.key.repeat) {
                    int scancode = event.key.keysym.scancode;
                    if (scancode < MAX_KEYS) {
                        input->keys[scancode] = true;
                        input->keys_pressed[scancode] = true;
                    }
                }
                break;

            case SDL_KEYUP: {
                int scancode = event.key.keysym.scancode;
                if (scancode < MAX_KEYS) {
                    input->keys[scancode] = false;
                    input->keys_released[scancode] = true;
                }
                break;
            }

            case SDL_MOUSEMOTION:
                input->mouse_x = event.motion.x;
                input->mouse_y = event.motion.y;
                input->mouse_dx += event.motion.xrel;
                input->mouse_dy += event.motion.yrel;
                break;

            case SDL_MOUSEBUTTONDOWN:
                if (event.button.button <= 5) {
                    int btn = event.button.button - 1;
                    input->mouse_buttons[btn] = true;
                    input->mouse_pressed[btn] = true;
                }
                break;

            case SDL_MOUSEBUTTONUP:
                if (event.button.button <= 5) {
                    int btn = event.button.button - 1;
                    input->mouse_buttons[btn] = false;
                    input->mouse_released[btn] = true;
                }
                break;

            case SDL_MOUSEWHEEL:
                input->scroll_y = event.wheel.y;
                break;
        }
    }
}

void platform_poll_events(Platform* p, InputState* input) {
    platform_poll_events_ex(p, input, NULL, NULL);
}

void platform_swap_buffers(Platform* p) {
    SDL_GL_SwapWindow((SDL_Window*)p->window);
}

double platform_get_time(void) {
    return (double)SDL_GetTicks64() / 1000.0;
}

void platform_sleep(uint32_t ms) {
    SDL_Delay(ms);
}

void platform_capture_mouse(Platform* p, InputState* input, bool capture) {
    (void)p;
    SDL_SetRelativeMouseMode(capture ? SDL_TRUE : SDL_FALSE);
    input->mouse_captured = capture;
    if (capture) {
        input->mouse_capture_just_started = true;
    }
}

void platform_set_title(Platform* p, const char* title) {
    SDL_SetWindowTitle((SDL_Window*)p->window, title);
}

void platform_toggle_fullscreen(Platform* p) {
    p->fullscreen = !p->fullscreen;
    SDL_SetWindowFullscreen(
        (SDL_Window*)p->window,
        p->fullscreen ? SDL_WINDOW_FULLSCREEN_DESKTOP : 0
    );
}
