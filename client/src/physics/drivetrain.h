/*
 * Drivetrain Physics
 *
 * Force-based tank drive (differential drive) physics for VEX IQ robots.
 *
 * Physics Model:
 *   - Motors apply torque to wheels
 *   - Wheels apply force to ground via friction
 *   - External forces (collisions) oppose wheel forces
 *   - Net force determines acceleration (F = ma)
 *   - Wheels slip when motor force exceeds friction limit
 *
 * Coordinate System:
 *   - X: Right
 *   - Y: Up
 *   - Z: Forward (robot faces +Z by default)
 *   - Rotation: Positive = counter-clockwise when viewed from above
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
    float robot_mass;       // Robot mass in pounds
    float moment_of_inertia; // Rotational inertia (slug·in²)
} DrivetrainConfig;

// Drivetrain state
typedef struct {
    // Configuration
    DrivetrainConfig config;

    // Motor commands (percentage -100 to +100)
    float left_motor_pct;
    float right_motor_pct;

    // Robot velocity (actual physics velocity, not motor command)
    float vel_x;            // X velocity (inches/s)
    float vel_z;            // Z velocity (inches/s) - forward axis
    float angular_vel;      // Angular velocity (radians/s)

    // Robot pose in world space
    float pos_x;            // X position (inches)
    float pos_z;            // Z position (inches) - forward axis
    float heading;          // Heading angle (radians, 0 = +Z, positive = CCW)

    // External forces (from collisions, applied before next update)
    float ext_force_x;      // External force X component (lbf)
    float ext_force_z;      // External force Z component (lbf)
    float ext_torque;       // External torque (in·lbf)

    // Friction coefficient (from scene)
    float friction_coeff;

    // Wheel slip state (for visual feedback)
    bool left_wheels_slipping;
    bool right_wheels_slipping;

    // Derived values (computed each frame)
    float linear_velocity;  // Forward speed (inches/s)
    float left_wheel_vel;   // Left wheel surface velocity (inches/s)
    float right_wheel_vel;  // Right wheel surface velocity (inches/s)
} Drivetrain;

// Initialize drivetrain with default VEX IQ configuration
void drivetrain_init(Drivetrain* dt);

// Initialize with custom configuration
void drivetrain_init_config(Drivetrain* dt, const DrivetrainConfig* config);

// Set motor power (as percentage of max: -100 to +100)
// This is how VEX IQ motors are controlled: motor.spin(FORWARD, 50, PERCENT)
void drivetrain_set_motors(Drivetrain* dt, float left_percent, float right_percent);

// Stop both motors
// mode: 0 = coast (let friction slow down), 1 = brake (active braking)
void drivetrain_stop(Drivetrain* dt, int mode);

// Apply external force (from collision) - accumulated until next update
void drivetrain_apply_force(Drivetrain* dt, float force_x, float force_z);

// Apply external torque (from off-center collision)
void drivetrain_apply_torque(Drivetrain* dt, float torque);

// Set friction coefficient (from scene physics)
void drivetrain_set_friction(Drivetrain* dt, float friction_coeff);

// Update drivetrain physics
// dt_sec: time step in seconds
void drivetrain_update(Drivetrain* dt, float dt_sec);

// Set robot position directly (for initialization or teleportation)
void drivetrain_set_position(Drivetrain* dt, float x, float z, float heading);

// Get robot position as Vec3 (Y is always 0)
Vec3 drivetrain_get_position(const Drivetrain* dt);

// Get robot heading in radians
float drivetrain_get_heading(const Drivetrain* dt);

// Get robot velocity as Vec3
Vec3 drivetrain_get_velocity(const Drivetrain* dt);

// Check if wheels are slipping
bool drivetrain_is_slipping(const Drivetrain* dt);

// Legacy compatibility
float drivetrain_rpm_to_velocity(float rpm, float wheel_diameter);
float drivetrain_percent_to_velocity(const Drivetrain* dt, float percent);

// For backwards compatibility - expose wheel velocities
#define left_velocity left_wheel_vel
#define right_velocity right_wheel_vel

#ifdef __cplusplus
}
#endif

#endif // DRIVETRAIN_H
