/*
 * Robot Configuration Loader
 *
 * Parses .config files to get motor port assignments for drivetrain.
 */

#ifndef ROBOT_CONFIG_H
#define ROBOT_CONFIG_H

#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// Motor assignment for drivetrain
typedef struct {
    int left_motor_port;   // Port number for left wheel motor (1-12, 0 = not assigned)
    int right_motor_port;  // Port number for right wheel motor (1-12, 0 = not assigned)
} RobotConfig;

// Initialize config with defaults (no assignments)
void robot_config_init(RobotConfig* config);

// Load config from file
// Returns true if file was loaded (even if no drivetrain motors found)
bool robot_config_load(const char* path, RobotConfig* config);

#ifdef __cplusplus
}
#endif

#endif // ROBOT_CONFIG_H
