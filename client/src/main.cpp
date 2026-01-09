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

#include <GL/glew.h>
#include <stdio.h>
#include <stdlib.h>

#define WINDOW_WIDTH 1280
#define WINDOW_HEIGHT 720
#define WINDOW_TITLE "VEX IQ Simulator"

// VEX IQ field is 6ft x 8ft, we use 1 unit = 1 foot
#define FIELD_SIZE 50.0f   // Large floor for now
#define GRID_SIZE 1.0f     // 1 foot grid

int main(int argc, char** argv) {
    (void)argc;
    (void)argv;

    printf("VEX IQ Simulator - C++ Client\n");
    printf("=============================\n\n");

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
    printf("  Escape    - Quit\n\n");

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

        // Poll events
        platform_poll_events(&platform, &input);

        // Handle input
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
    floor_destroy(&floor);
    platform_shutdown(&platform);

    printf("Shutdown complete.\n");
    return 0;
}
