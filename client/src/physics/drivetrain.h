/*
 * Drivetrain Physics
 *
 * Tank drive (differential drive) kinematics for VEX IQ robots.
 *
 * Tank Drive Model:
 *   - Two sides: left and right, each with independent motors
 *   - Linear velocity = (Vl + Vr) / 2
 *   - Angular velocity = (Vr - Vl) / track_width
 *
 * Coordinate System:
 *   - X: Right
 *   - Y: Up
 *   - Z: Forward (robot faces +Z by default)
 *   - Rotation: Positive = counter-clockwise when viewed from above
 *
 * Motor velocity is in inches/second (converted from RPM and wheel diameter)
 */

#ifndef DRIVETRAIN_H
#define DRIVETRAIN_H

#include <stdbool.h>
#include "../math/vec3.h"

#ifdef __cplusplus
extern "C" {
#endif

// Drivetrain configuration
typedef struct {
    float track_width;      // Distance between wheel centers (inches)
    float wheel_diameter;   // Wheel diameter (inches)
    float max_rpm;          // Maximum motor RPM (typically 120 for VEX IQ)
    float accel_rate;       // Acceleration in inches/s^2 (0 = instant)
} DrivetrainConfig;

// Drivetrain state
typedef struct {
    // Configuration
    DrivetrainConfig config;

    // Current motor velocities (inches/second at wheel)
    float left_velocity;
    float right_velocity;

    // Target velocities (what the motors are trying to reach)
    float left_target;
    float right_target;

    // Robot pose in world space
    float pos_x;            // X position (inches)
    float pos_z;            // Z position (inches) - forward axis
    float heading;          // Heading angle (radians, 0 = +Z, positive = CCW)

    // Derived values (computed each frame)
    float linear_velocity;  // Forward speed (inches/s)
    float angular_velocity; // Turning rate (radians/s)
} Drivetrain;

// Initialize drivetrain with default VEX IQ configuration
void drivetrain_init(Drivetrain* dt);

// Initialize with custom configuration
void drivetrain_init_config(Drivetrain* dt, const DrivetrainConfig* config);

// Set target motor velocities (as percentage of max: -100 to +100)
// This is how VEX IQ motors are controlled: motor.spin(FORWARD, 50, PERCENT)
void drivetrain_set_motors(Drivetrain* dt, float left_percent, float right_percent);

// Set target motor velocities directly (inches/second)
void drivetrain_set_velocities(Drivetrain* dt, float left_vel, float right_vel);

// Stop both motors
// mode: 0 = coast (decelerate naturally), 1 = brake (stop quickly)
void drivetrain_stop(Drivetrain* dt, int mode);

// Update drivetrain physics
// dt_sec: time step in seconds
void drivetrain_update(Drivetrain* dt, float dt_sec);

// Set robot position directly (for initialization or teleportation)
void drivetrain_set_position(Drivetrain* dt, float x, float z, float heading);

// Get robot position as Vec3 (Y is always 0)
Vec3 drivetrain_get_position(const Drivetrain* dt);

// Get robot heading in radians
float drivetrain_get_heading(const Drivetrain* dt);

// Convert RPM to inches/second for given wheel diameter
float drivetrain_rpm_to_velocity(float rpm, float wheel_diameter);

// Convert percent (-100 to 100) to velocity (inches/second)
float drivetrain_percent_to_velocity(const Drivetrain* dt, float percent);

#ifdef __cplusplus
}
#endif

#endif // DRIVETRAIN_H
