/*
 * SDL Gamepad implementation for VEX IQ Controller mapping
 */

#include "gamepad.h"
#include <stdio.h>
#include <string.h>

// Deadzone for analog sticks (SDL uses -32768 to 32767)
#define DEADZONE 3200

// Convert SDL axis value (-32768 to 32767) to VEX value (-100 to 100)
static int scale_axis(int value) {
    // Apply deadzone
    if (value > -DEADZONE && value < DEADZONE) {
        return 0;
    }

    // Scale to -100 to 100
    if (value < 0) {
        return (value + DEADZONE) * 100 / (32768 - DEADZONE);
    } else {
        return (value - DEADZONE) * 100 / (32767 - DEADZONE);
    }
}

void gamepad_init(Gamepad* gp) {
    memset(gp, 0, sizeof(Gamepad));

    // Initialize game controller subsystem if not already done
    if (!SDL_WasInit(SDL_INIT_GAMECONTROLLER)) {
        if (SDL_InitSubSystem(SDL_INIT_GAMECONTROLLER) < 0) {
            printf("[Gamepad] Warning: Could not init gamecontroller: %s\n", SDL_GetError());
            return;
        }
    }

    // Check for already connected controllers
    for (int i = 0; i < SDL_NumJoysticks(); i++) {
        if (SDL_IsGameController(i)) {
            gp->controller = SDL_GameControllerOpen(i);
            if (gp->controller) {
                gp->joystick_id = SDL_JoystickInstanceID(
                    SDL_GameControllerGetJoystick(gp->controller));
                gp->connected = true;
                const char* name = SDL_GameControllerName(gp->controller);
                if (name) {
                    strncpy(gp->name, name, sizeof(gp->name) - 1);
                }
                printf("[Gamepad] Connected: %s\n", gp->name);
                break;
            }
        }
    }

    if (!gp->connected) {
        printf("[Gamepad] No controller found. Connect a gamepad to control the robot.\n");
    }
}

void gamepad_handle_event(Gamepad* gp, SDL_Event* event) {
    switch (event->type) {
        case SDL_CONTROLLERDEVICEADDED:
            if (!gp->connected) {
                gp->controller = SDL_GameControllerOpen(event->cdevice.which);
                if (gp->controller) {
                    gp->joystick_id = SDL_JoystickInstanceID(
                        SDL_GameControllerGetJoystick(gp->controller));
                    gp->connected = true;
                    const char* name = SDL_GameControllerName(gp->controller);
                    if (name) {
                        strncpy(gp->name, name, sizeof(gp->name) - 1);
                    }
                    printf("[Gamepad] Connected: %s\n", gp->name);
                }
            }
            break;

        case SDL_CONTROLLERDEVICEREMOVED:
            if (gp->connected && event->cdevice.which == gp->joystick_id) {
                printf("[Gamepad] Disconnected: %s\n", gp->name);
                SDL_GameControllerClose(gp->controller);
                gp->controller = NULL;
                gp->connected = false;
                gp->joystick_id = 0;
                memset(gp->name, 0, sizeof(gp->name));
                memset(&gp->axes, 0, sizeof(gp->axes));
                memset(&gp->buttons, 0, sizeof(gp->buttons));
            }
            break;
    }
}

void gamepad_update(Gamepad* gp) {
    // Save previous button state
    gp->prev_buttons = gp->buttons;

    if (!gp->connected || !gp->controller) {
        return;
    }

    // Read axes
    // VEX IQ: A = left Y, B = left X, C = right X, D = right Y
    // SDL: Left stick = LEFTX/LEFTY, Right stick = RIGHTX/RIGHTY
    // Note: SDL Y axis is inverted (up is negative), VEX expects up = positive
    gp->axes.a = -scale_axis(SDL_GameControllerGetAxis(gp->controller, SDL_CONTROLLER_AXIS_LEFTY));
    gp->axes.b = scale_axis(SDL_GameControllerGetAxis(gp->controller, SDL_CONTROLLER_AXIS_LEFTX));
    gp->axes.c = scale_axis(SDL_GameControllerGetAxis(gp->controller, SDL_CONTROLLER_AXIS_RIGHTX));
    gp->axes.d = -scale_axis(SDL_GameControllerGetAxis(gp->controller, SDL_CONTROLLER_AXIS_RIGHTY));

    // Read buttons - map to VEX IQ controller layout
    // L-Up/L-Down: Left shoulder (LB) / Left trigger
    gp->buttons.l_up = SDL_GameControllerGetButton(gp->controller, SDL_CONTROLLER_BUTTON_LEFTSHOULDER);
    gp->buttons.l_down = SDL_GameControllerGetAxis(gp->controller, SDL_CONTROLLER_AXIS_TRIGGERLEFT) > 16000;

    // R-Up/R-Down: Right shoulder (RB) / Right trigger
    gp->buttons.r_up = SDL_GameControllerGetButton(gp->controller, SDL_CONTROLLER_BUTTON_RIGHTSHOULDER);
    gp->buttons.r_down = SDL_GameControllerGetAxis(gp->controller, SDL_CONTROLLER_AXIS_TRIGGERRIGHT) > 16000;

    // E-Up/E-Down: Y (top) / A (bottom) - Xbox layout
    gp->buttons.e_up = SDL_GameControllerGetButton(gp->controller, SDL_CONTROLLER_BUTTON_Y);
    gp->buttons.e_down = SDL_GameControllerGetButton(gp->controller, SDL_CONTROLLER_BUTTON_A);

    // F-Up/F-Down: X (left) / B (right) - Xbox layout
    gp->buttons.f_up = SDL_GameControllerGetButton(gp->controller, SDL_CONTROLLER_BUTTON_X);
    gp->buttons.f_down = SDL_GameControllerGetButton(gp->controller, SDL_CONTROLLER_BUTTON_B);
}

void gamepad_axes_to_json(Gamepad* gp, char* buffer, size_t buffer_size) {
    snprintf(buffer, buffer_size,
        "{\"A\":%d,\"B\":%d,\"C\":%d,\"D\":%d}",
        gp->axes.a, gp->axes.b, gp->axes.c, gp->axes.d);
}

void gamepad_to_json(Gamepad* gp, char* buffer, size_t buffer_size) {
    snprintf(buffer, buffer_size,
        "{\"type\":\"gamepad\","
        "\"axes\":{\"A\":%d,\"B\":%d,\"C\":%d,\"D\":%d},"
        "\"buttons\":{"
        "\"LUp\":%s,\"LDown\":%s,"
        "\"RUp\":%s,\"RDown\":%s,"
        "\"EUp\":%s,\"EDown\":%s,"
        "\"FUp\":%s,\"FDown\":%s"
        "}}",
        gp->axes.a, gp->axes.b, gp->axes.c, gp->axes.d,
        gp->buttons.l_up ? "true" : "false",
        gp->buttons.l_down ? "true" : "false",
        gp->buttons.r_up ? "true" : "false",
        gp->buttons.r_down ? "true" : "false",
        gp->buttons.e_up ? "true" : "false",
        gp->buttons.e_down ? "true" : "false",
        gp->buttons.f_up ? "true" : "false",
        gp->buttons.f_down ? "true" : "false");
}

void gamepad_destroy(Gamepad* gp) {
    if (gp->controller) {
        SDL_GameControllerClose(gp->controller);
        gp->controller = NULL;
    }
    gp->connected = false;
}
