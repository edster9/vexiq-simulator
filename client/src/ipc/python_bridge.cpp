/*
 * Python Bridge implementation
 * Handles subprocess management and JSON message parsing
 */

#include "python_bridge.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

#ifdef _WIN32
#include <windows.h>
#else
#include <unistd.h>
#endif

// Simple JSON parsing helpers (no external dependencies)
static const char* json_find_key(const char* json, const char* key) {
    char search[128];
    snprintf(search, sizeof(search), "\"%s\":", key);
    return strstr(json, search);
}

static int json_get_int(const char* json, const char* key, int default_val) {
    const char* pos = json_find_key(json, key);
    if (!pos) return default_val;

    pos = strchr(pos, ':');
    if (!pos) return default_val;
    pos++;

    while (*pos && isspace(*pos)) pos++;
    return atoi(pos);
}

static float json_get_float(const char* json, const char* key, float default_val) {
    const char* pos = json_find_key(json, key);
    if (!pos) return default_val;

    pos = strchr(pos, ':');
    if (!pos) return default_val;
    pos++;

    while (*pos && isspace(*pos)) pos++;
    return (float)atof(pos);
}

static bool json_get_bool(const char* json, const char* key, bool default_val) {
    const char* pos = json_find_key(json, key);
    if (!pos) return default_val;

    pos = strchr(pos, ':');
    if (!pos) return default_val;
    pos++;

    while (*pos && isspace(*pos)) pos++;
    return (strncmp(pos, "true", 4) == 0);
}

static void json_get_string(const char* json, const char* key, char* out, size_t out_size) {
    out[0] = '\0';
    const char* pos = json_find_key(json, key);
    if (!pos) return;

    pos = strchr(pos, ':');
    if (!pos) return;
    pos++;

    while (*pos && isspace(*pos)) pos++;
    if (*pos != '"') return;
    pos++;

    size_t i = 0;
    while (*pos && *pos != '"' && i < out_size - 1) {
        out[i++] = *pos++;
    }
    out[i] = '\0';
}

// Parse motor states from JSON
static void parse_motors(const char* json, RobotState* state) {
    state->motor_count = 0;

    const char* motors_pos = json_find_key(json, "motors");
    if (!motors_pos) return;

    // Find the opening brace for motors object
    motors_pos = strchr(motors_pos, '{');
    if (!motors_pos) return;
    motors_pos++;

    // Simple parsing: look for "port":{...} patterns
    // Format: "1":{"speed":0,"spinning":false,"position":0.0}
    while (*motors_pos && state->motor_count < MAX_MOTORS) {
        // Skip whitespace
        while (*motors_pos && isspace(*motors_pos)) motors_pos++;

        if (*motors_pos == '}') break;  // End of motors object
        if (*motors_pos == ',') { motors_pos++; continue; }

        // Look for port number in quotes
        if (*motors_pos == '"') {
            motors_pos++;
            int port = atoi(motors_pos);
            if (port > 0) {
                // Find the motor object
                const char* motor_start = strchr(motors_pos, '{');
                if (motor_start) {
                    // Find matching closing brace
                    const char* motor_end = strchr(motor_start, '}');
                    if (motor_end) {
                        char motor_json[256];
                        size_t len = motor_end - motor_start + 1;
                        if (len < sizeof(motor_json)) {
                            memcpy(motor_json, motor_start, len);
                            motor_json[len] = '\0';

                            MotorState* m = &state->motors[state->motor_count];
                            m->port = port;
                            m->speed = json_get_int(motor_json, "speed", 0);
                            m->spinning = json_get_bool(motor_json, "spinning", false);
                            m->position = json_get_float(motor_json, "position", 0.0f);
                            state->motor_count++;
                        }
                        motors_pos = motor_end + 1;
                        continue;
                    }
                }
            }
        }
        motors_pos++;
    }
}

// Parse pneumatic states from JSON
static void parse_pneumatics(const char* json, RobotState* state) {
    state->pneumatic_count = 0;

    const char* pneu_pos = json_find_key(json, "pneumatics");
    if (!pneu_pos) return;

    pneu_pos = strchr(pneu_pos, '{');
    if (!pneu_pos) return;
    pneu_pos++;

    while (*pneu_pos && state->pneumatic_count < MAX_PNEUMATICS) {
        while (*pneu_pos && isspace(*pneu_pos)) pneu_pos++;

        if (*pneu_pos == '}') break;
        if (*pneu_pos == ',') { pneu_pos++; continue; }

        if (*pneu_pos == '"') {
            pneu_pos++;
            int port = atoi(pneu_pos);
            if (port > 0) {
                const char* pneu_start = strchr(pneu_pos, '{');
                if (pneu_start) {
                    const char* pneu_end = strchr(pneu_start, '}');
                    if (pneu_end) {
                        char pneu_json[128];
                        size_t len = pneu_end - pneu_start + 1;
                        if (len < sizeof(pneu_json)) {
                            memcpy(pneu_json, pneu_start, len);
                            pneu_json[len] = '\0';

                            PneumaticState* p = &state->pneumatics[state->pneumatic_count];
                            p->port = port;
                            p->extended = json_get_bool(pneu_json, "extended", false);
                            p->pump_on = json_get_bool(pneu_json, "pump", false);
                            state->pneumatic_count++;
                        }
                        pneu_pos = pneu_end + 1;
                        continue;
                    }
                }
            }
        }
        pneu_pos++;
    }
}

// Process a complete JSON message from Python
static void process_message(PythonBridge* bridge, const char* json) {
    char type[32];
    json_get_string(json, "type", type, sizeof(type));

    if (strcmp(type, "ready") == 0) {
        json_get_string(json, "project", bridge->project_name, sizeof(bridge->project_name));
        bridge->robot_ready = true;
        printf("[Bridge] Robot ready: %s\n", bridge->project_name);
    }
    else if (strcmp(type, "state") == 0) {
        parse_motors(json, &bridge->state);
        parse_pneumatics(json, &bridge->state);
    }
    else if (strcmp(type, "status") == 0) {
        json_get_string(json, "message", bridge->state.status, sizeof(bridge->state.status));
        printf("[Bridge] Status: %s\n", bridge->state.status);
    }
    else if (strcmp(type, "error") == 0) {
        json_get_string(json, "message", bridge->state.error, sizeof(bridge->state.error));
        fprintf(stderr, "[Bridge] Error: %s\n", bridge->state.error);
    }
    else if (strcmp(type, "shutdown") == 0) {
        printf("[Bridge] Python shutdown\n");
        bridge->connected = false;
    }
}

bool python_bridge_init(PythonBridge* bridge, const char* iqpython_path, const char* simulator_dir) {
    memset(bridge, 0, sizeof(PythonBridge));
    bridge->tick_interval = 1.0 / 60.0;  // 60 Hz default

    // Get path to bundled Python
    // Exe is at: client/build-*/vexiq_sim
    // Python is at: python-linux/bin/python3 or python-win/python.exe
    char python_path[512];
    char command[1024];

#ifdef _WIN32
    // Get exe directory
    char exe_dir[512];
    GetModuleFileNameA(NULL, exe_dir, sizeof(exe_dir));
    char* last_sep = strrchr(exe_dir, '\\');
    if (last_sep) *last_sep = '\0';

    // Try bundled Python first, fall back to system Python
    snprintf(python_path, sizeof(python_path), "%s\\..\\..\\python-win\\python.exe", exe_dir);

    // Check if bundled Python exists
    DWORD attr = GetFileAttributesA(python_path);
    if (attr == INVALID_FILE_ATTRIBUTES) {
        // Fall back to system Python
        strcpy(python_path, "python");
        printf("[Bridge] Using system Python (bundled not found)\n");
    } else {
        printf("[Bridge] Using bundled Python: %s\n", python_path);
    }

    snprintf(command, sizeof(command), "\"%s\" \"%s\\ipc_bridge.py\" \"%s\"",
             python_path, simulator_dir, iqpython_path);
#else
    // Get exe directory via /proc/self/exe
    char exe_dir[512];
    ssize_t len = readlink("/proc/self/exe", exe_dir, sizeof(exe_dir) - 1);
    if (len > 0) {
        exe_dir[len] = '\0';
        char* last_sep = strrchr(exe_dir, '/');
        if (last_sep) *last_sep = '\0';
    } else {
        strcpy(exe_dir, ".");
    }

    // Try bundled Python first
    snprintf(python_path, sizeof(python_path), "%s/../../python-linux/bin/python3", exe_dir);

    // Check if bundled Python exists
    if (access(python_path, X_OK) != 0) {
        // Fall back to system Python
        strcpy(python_path, "python3");
        printf("[Bridge] Using system Python (bundled not found)\n");
    } else {
        printf("[Bridge] Using bundled Python: %s\n", python_path);
    }

    snprintf(command, sizeof(command), "\"%s\" \"%s/ipc_bridge.py\" \"%s\"",
             python_path, simulator_dir, iqpython_path);
#endif

    printf("[Bridge] Spawning: %s\n", command);

    if (!subprocess_spawn(&bridge->process, command, NULL)) {
        fprintf(stderr, "[Bridge] Failed to spawn Python process\n");
        return false;
    }

    bridge->connected = true;
    printf("[Bridge] Python process started\n");

    return true;
}

void python_bridge_send_gamepad(PythonBridge* bridge, Gamepad* gamepad) {
    if (!bridge->connected) return;

    char buffer[512];
    gamepad_to_json(gamepad, buffer, sizeof(buffer));

    // Add newline for line-based protocol
    strcat(buffer, "\n");
    subprocess_write_str(&bridge->process, buffer);
}

void python_bridge_send_tick(PythonBridge* bridge, float dt) {
    if (!bridge->connected) return;

    char buffer[64];
    snprintf(buffer, sizeof(buffer), "{\"type\":\"tick\",\"dt\":%.4f}\n", dt);
    subprocess_write_str(&bridge->process, buffer);
}

bool python_bridge_update(PythonBridge* bridge) {
    if (!bridge->connected) return false;

    // Check if process is still running
    if (!subprocess_is_running(&bridge->process)) {
        bridge->connected = false;
        return false;
    }

    bool got_message = false;

    // Read available data
    char temp[1024];
    int bytes = subprocess_read(&bridge->process, temp, sizeof(temp) - 1);
    if (bytes > 0) {
        temp[bytes] = '\0';

        // Append to read buffer
        int space = MAX_MESSAGE_SIZE - bridge->read_pos - 1;
        if (bytes < space) {
            memcpy(bridge->read_buffer + bridge->read_pos, temp, bytes);
            bridge->read_pos += bytes;
            bridge->read_buffer[bridge->read_pos] = '\0';
        }
    }

    // Process complete lines
    char* line_start = bridge->read_buffer;
    char* newline;
    while ((newline = strchr(line_start, '\n')) != NULL) {
        *newline = '\0';

        // Process this message
        if (line_start[0] == '{') {
            process_message(bridge, line_start);
            got_message = true;
        }

        line_start = newline + 1;
    }

    // Move remaining data to start of buffer
    if (line_start > bridge->read_buffer) {
        size_t remaining = bridge->read_pos - (line_start - bridge->read_buffer);
        memmove(bridge->read_buffer, line_start, remaining);
        bridge->read_pos = (int)remaining;
        bridge->read_buffer[bridge->read_pos] = '\0';
    }

    return got_message;
}

bool python_bridge_is_ready(PythonBridge* bridge) {
    return bridge->connected && bridge->robot_ready;
}

RobotState* python_bridge_get_state(PythonBridge* bridge) {
    return &bridge->state;
}

void python_bridge_destroy(PythonBridge* bridge) {
    if (bridge->connected) {
        // Send shutdown message
        subprocess_write_str(&bridge->process, "{\"type\":\"shutdown\"}\n");

        // Give Python time to shutdown gracefully
#ifdef _WIN32
        Sleep(100);
#else
        usleep(100000);
#endif
    }

    subprocess_destroy(&bridge->process);
    memset(bridge, 0, sizeof(PythonBridge));
}
