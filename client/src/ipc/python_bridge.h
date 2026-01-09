/*
 * Python Bridge - High-level interface for Python IPC
 *
 * Manages the Python subprocess and handles JSON message exchange
 * for the VEX IQ robot harness.
 */

#ifndef PYTHON_BRIDGE_H
#define PYTHON_BRIDGE_H

#include <stdbool.h>
#include "subprocess.h"
#include "gamepad.h"

#define MAX_MOTORS 12
#define MAX_PNEUMATICS 12
#define MAX_MESSAGE_SIZE 4096

// Motor state received from Python
typedef struct MotorState {
    int port;
    int speed;         // Current velocity (-100 to 100)
    bool spinning;     // Is motor actively spinning
    float position;    // Position in degrees
} MotorState;

// Pneumatic state received from Python
typedef struct PneumaticState {
    int port;
    bool extended;     // Piston extended
    bool pump_on;      // Pump running
} PneumaticState;

// Robot state received from Python
typedef struct RobotState {
    MotorState motors[MAX_MOTORS];
    int motor_count;

    PneumaticState pneumatics[MAX_PNEUMATICS];
    int pneumatic_count;

    bool ready;        // Robot code is ready
    char status[128];  // Status message
    char error[256];   // Error message (if any)
} RobotState;

typedef struct PythonBridge {
    Subprocess process;
    bool connected;
    bool robot_ready;

    char project_name[128];
    RobotState state;

    // Internal buffer for reading
    char read_buffer[MAX_MESSAGE_SIZE];
    int read_pos;

    // Tick timing
    double last_tick_time;
    double tick_interval;  // seconds between ticks (e.g., 0.016 for 60fps)
} PythonBridge;

// Initialize and spawn Python bridge
// iqpython_path: Path to the .iqpython file to run
// simulator_dir: Path to the simulator directory containing ipc_bridge.py
bool python_bridge_init(PythonBridge* bridge, const char* iqpython_path, const char* simulator_dir);

// Send gamepad state to Python
void python_bridge_send_gamepad(PythonBridge* bridge, Gamepad* gamepad);

// Send tick message (triggers Python to send state back)
void python_bridge_send_tick(PythonBridge* bridge, float dt);

// Process incoming messages from Python (call each frame)
// Returns true if new state was received
bool python_bridge_update(PythonBridge* bridge);

// Check if bridge is connected and robot is ready
bool python_bridge_is_ready(PythonBridge* bridge);

// Get current robot state
RobotState* python_bridge_get_state(PythonBridge* bridge);

// Shutdown bridge
void python_bridge_destroy(PythonBridge* bridge);

#endif // PYTHON_BRIDGE_H
