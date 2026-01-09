/*
 * VEX IQ Simulator - C++ SDL Client
 *
 * A 3D visualization client for the VEX IQ Python simulator.
 * Communicates with Python robot harness via IPC.
 */

#include "platform/platform.h"
#include "math/vec3.h"
#include "math/mat4.h"
#include "render/camera.h"
#include "render/floor.h"
#include "ipc/gamepad.h"
#include "ipc/python_bridge.h"

#include <GL/glew.h>
#include <SDL.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

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

// VEX IQ field is 6ft x 8ft, we use 1 unit = 1 foot
#define FIELD_SIZE 50.0f   // Large floor for now
#define GRID_SIZE 1.0f     // 1 foot grid

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

    // Assuming: exe is in client/build-*/vexiq_sim
    // Simulator is in ../simulator relative to client/
    snprintf(buffer, size, "%s" PATH_SEP ".." PATH_SEP ".." PATH_SEP "simulator", exe_dir);
}

// SDL event callback for gamepad handling
static void sdl_event_callback(void* event, void* user_data) {
    Gamepad* gp = (Gamepad*)user_data;
    gamepad_handle_event(gp, (SDL_Event*)event);
}

int main(int argc, char** argv) {
    printf("VEX IQ Simulator - C++ Client\n");
    printf("=============================\n\n");

    // Parse command line
    const char* iqpython_path = NULL;
    if (argc >= 2) {
        iqpython_path = argv[1];
        printf("Robot file: %s\n", iqpython_path);
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
    if (!floor_init(&floor, FIELD_SIZE, GRID_SIZE)) {
        fprintf(stderr, "Failed to initialize floor\n");
        platform_shutdown(&platform);
        return 1;
    }

    // Initialize gamepad
    Gamepad gamepad;
    gamepad_init(&gamepad);

    // Initialize Python bridge if .iqpython file provided
    PythonBridge bridge;
    bool use_bridge = false;
    if (iqpython_path) {
        char simulator_dir[512];
        get_simulator_dir(simulator_dir, sizeof(simulator_dir));
        printf("Simulator dir: %s\n", simulator_dir);

        if (python_bridge_init(&bridge, iqpython_path, simulator_dir)) {
            use_bridge = true;
            printf("Python bridge initialized\n");
        } else {
            fprintf(stderr, "Warning: Failed to initialize Python bridge\n");
        }
    }

    // OpenGL setup
    glEnable(GL_DEPTH_TEST);
    glClearColor(0.15f, 0.15f, 0.18f, 1.0f);  // Dark gray background

    printf("\nControls:\n");
    printf("  WASD      - Move camera\n");
    printf("  E/Space   - Move up\n");
    printf("  Q/Ctrl    - Move down\n");
    printf("  Right-click + Mouse - Look around\n");
    printf("  Shift     - Move faster\n");
    printf("  Scroll    - Adjust speed\n");
    printf("  F11       - Toggle fullscreen\n");
    printf("  Escape    - Quit\n");
    if (gamepad.connected) {
        printf("  Gamepad   - Control robot\n");
    }
    printf("\n");

    // Timing
    double last_time = platform_get_time();

    // Main loop
    while (!platform.should_quit) {
        // Calculate delta time
        double current_time = platform_get_time();
        float dt = (float)(current_time - last_time);
        last_time = current_time;

        // Cap dt to prevent physics explosions on lag spikes
        if (dt > 0.1f) dt = 0.1f;

        // Poll events (with gamepad callback)
        platform_poll_events_ex(&platform, &input, sdl_event_callback, &gamepad);

        // Handle keyboard input
        if (input.keys_pressed[KEY_ESCAPE]) {
            platform.should_quit = true;
        }

        if (input.keys_pressed[KEY_F11]) {
            platform_toggle_fullscreen(&platform);
        }

        // Right-click to look around
        if (input.mouse_pressed[MOUSE_RIGHT]) {
            platform_capture_mouse(&platform, &input, true);
        }
        if (input.mouse_released[MOUSE_RIGHT]) {
            platform_capture_mouse(&platform, &input, false);
        }

        // Update gamepad state
        gamepad_update(&gamepad);

        // Send gamepad to Python bridge and process responses
        if (use_bridge) {
            // Send gamepad state
            python_bridge_send_gamepad(&bridge, &gamepad);

            // Send tick to trigger state response
            python_bridge_send_tick(&bridge, dt);

            // Process incoming messages
            if (python_bridge_update(&bridge)) {
                // Got new state from Python - could update robot visualization here
                RobotState* state = python_bridge_get_state(&bridge);
                (void)state;  // Will use for robot rendering later
            }

            // Check if bridge disconnected
            if (!bridge.connected) {
                fprintf(stderr, "Python bridge disconnected\n");
                use_bridge = false;
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
        floor_render(&floor, &view, &projection, camera.position);

        // Swap buffers
        platform_swap_buffers(&platform);
    }

    // Cleanup
    if (use_bridge) {
        python_bridge_destroy(&bridge);
    }
    gamepad_destroy(&gamepad);
    floor_destroy(&floor);
    platform_shutdown(&platform);

    printf("Shutdown complete.\n");
    return 0;
}
