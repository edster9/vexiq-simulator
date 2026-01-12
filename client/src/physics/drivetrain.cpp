/*
 * Drivetrain Physics Implementation
 *
 * Force-based tank drive physics using wheel friction model.
 */

#include "drivetrain.h"
#include "physics_config.h"
#include <math.h>
#include <string.h>

// Math constants
#define PI 3.14159265358979323846f

// Default VEX IQ drivetrain configuration
static const DrivetrainConfig DEFAULT_CONFIG = {
    .track_width = 10.0f,                      // ~10 inches between wheels
    .wheel_diameter = VEXIQ_DEFAULT_WHEEL_DIAMETER,
    .max_rpm = VEXIQ_MOTOR_MAX_RPM,
    .robot_mass = VEXIQ_DEFAULT_ROBOT_MASS,
    .moment_of_inertia = VEXIQ_DEFAULT_MOMENT_OF_INERTIA,
};

void drivetrain_init(Drivetrain* dt) {
    drivetrain_init_config(dt, &DEFAULT_CONFIG);
}

void drivetrain_init_config(Drivetrain* dt, const DrivetrainConfig* config) {
    memset(dt, 0, sizeof(Drivetrain));
    dt->config = *config;
    dt->friction_coeff = 0.8f;  // Default, will be set from scene
}

float drivetrain_rpm_to_velocity(float rpm, float wheel_diameter) {
    // Circumference = pi * diameter
    // Velocity = (RPM / 60) * circumference
    float circumference = PI * wheel_diameter;
    return (rpm / 60.0f) * circumference;
}

float drivetrain_percent_to_velocity(const Drivetrain* dt, float percent) {
    // Clamp percent to -100 to +100
    if (percent > 100.0f) percent = 100.0f;
    if (percent < -100.0f) percent = -100.0f;

    // Convert max RPM to max velocity
    float max_velocity = drivetrain_rpm_to_velocity(dt->config.max_rpm, dt->config.wheel_diameter);

    return (percent / 100.0f) * max_velocity;
}

void drivetrain_set_motors(Drivetrain* dt, float left_percent, float right_percent) {
    // Clamp to valid range
    if (left_percent > 100.0f) left_percent = 100.0f;
    if (left_percent < -100.0f) left_percent = -100.0f;
    if (right_percent > 100.0f) right_percent = 100.0f;
    if (right_percent < -100.0f) right_percent = -100.0f;

    dt->left_motor_pct = left_percent;
    dt->right_motor_pct = right_percent;
}

void drivetrain_stop(Drivetrain* dt, int mode) {
    dt->left_motor_pct = 0.0f;
    dt->right_motor_pct = 0.0f;

    if (mode == 1) {
        // Brake: stop immediately
        dt->vel_x = 0.0f;
        dt->vel_z = 0.0f;
        dt->angular_vel = 0.0f;
    }
}

void drivetrain_apply_force(Drivetrain* dt, float force_x, float force_z) {
    dt->ext_force_x += force_x;
    dt->ext_force_z += force_z;
}

void drivetrain_apply_torque(Drivetrain* dt, float torque) {
    dt->ext_torque += torque;
}

void drivetrain_set_friction(Drivetrain* dt, float friction_coeff) {
    dt->friction_coeff = friction_coeff;
}

void drivetrain_update(Drivetrain* dt, float dt_sec) {
    // =========================================================================
    // Step 1: Calculate motor forces with torque curve
    // =========================================================================

    // Real motors have a torque curve: torque decreases as speed increases
    // At stall (0 RPM): full torque, at max RPM (no load): 0 torque
    // available_torque = stall_torque * (1 - current_rpm / max_rpm)

    float wheel_radius = dt->config.wheel_diameter / 2.0f;
    float wheel_circumference = PI * dt->config.wheel_diameter;

    // Max wheel surface velocity at no-load RPM
    float max_wheel_velocity = (dt->config.max_rpm / 60.0f) * wheel_circumference;

    // Current wheel velocities (from last frame)
    float left_wheel_speed = fabsf(dt->left_wheel_vel);
    float right_wheel_speed = fabsf(dt->right_wheel_vel);

    // Calculate available torque based on current speed (linear torque curve)
    // Clamp speed ratio to [0, 1] to avoid negative torque
    float left_speed_ratio = left_wheel_speed / max_wheel_velocity;
    float right_speed_ratio = right_wheel_speed / max_wheel_velocity;
    if (left_speed_ratio > 1.0f) left_speed_ratio = 1.0f;
    if (right_speed_ratio > 1.0f) right_speed_ratio = 1.0f;

    float left_available_torque = VEXIQ_MOTOR_STALL_TORQUE * (1.0f - left_speed_ratio);
    float right_available_torque = VEXIQ_MOTOR_STALL_TORQUE * (1.0f - right_speed_ratio);

    // Motor force = (percent/100) * available_force
    float left_motor_force = (dt->left_motor_pct / 100.0f) * (left_available_torque / wheel_radius);
    float right_motor_force = (dt->right_motor_pct / 100.0f) * (right_available_torque / wheel_radius);

    // =========================================================================
    // Step 2: Calculate friction limits
    // =========================================================================

    // Weight per side (assuming 4 wheels, 2 per side)
    // Normal force = weight = mass * gravity (in lbf, mass already in lbs)
    float weight = dt->config.robot_mass;  // lbf (weight = mass in imperial when using lbs)
    float weight_per_side = weight / 2.0f;

    // Maximum friction force per side
    float max_friction = weight_per_side * dt->friction_coeff;

    // =========================================================================
    // Step 3: Apply friction limits (wheel slip)
    // =========================================================================

    float left_actual_force, right_actual_force;

    if (fabsf(left_motor_force) > max_friction) {
        // Left wheels slipping
        left_actual_force = (left_motor_force > 0) ? max_friction : -max_friction;
        dt->left_wheels_slipping = true;
    } else {
        left_actual_force = left_motor_force;
        dt->left_wheels_slipping = false;
    }

    if (fabsf(right_motor_force) > max_friction) {
        // Right wheels slipping
        right_actual_force = (right_motor_force > 0) ? max_friction : -max_friction;
        dt->right_wheels_slipping = true;
    } else {
        right_actual_force = right_motor_force;
        dt->right_wheels_slipping = false;
    }

    // =========================================================================
    // Step 4: Calculate net forces in robot frame
    // =========================================================================

    // Forward force (both sides push forward)
    float forward_force = left_actual_force + right_actual_force;

    // Torque from differential drive
    // Torque = (right - left) * (track_width / 2)
    float track_half = dt->config.track_width / 2.0f;
    float drive_torque = (right_actual_force - left_actual_force) * track_half;

    // Apply speed scaling for tuning feel
    forward_force *= VEXIQ_FORWARD_SPEED_SCALE;
    drive_torque *= VEXIQ_TURN_SPEED_SCALE;

    // =========================================================================
    // Step 5: Transform external forces to robot frame and add
    // =========================================================================

    // Transform world-frame external forces to robot frame
    float cos_h = cosf(dt->heading);
    float sin_h = sinf(dt->heading);

    // External force in robot frame (forward = +Z in robot frame)
    float ext_forward = dt->ext_force_z * cos_h + dt->ext_force_x * sin_h;
    float ext_lateral = -dt->ext_force_z * sin_h + dt->ext_force_x * cos_h;

    // Add external forces
    forward_force += ext_forward;
    float lateral_force = ext_lateral;  // Robot can be pushed sideways

    // Add external torque
    float total_torque = drive_torque + dt->ext_torque;

    // Clear external forces for next frame
    dt->ext_force_x = 0.0f;
    dt->ext_force_z = 0.0f;
    dt->ext_torque = 0.0f;

    // =========================================================================
    // Step 6: Calculate accelerations (F = ma)
    // =========================================================================

    // Convert mass to slugs for F=ma (lbs / 386.1)
    float mass_slugs = dt->config.robot_mass / 386.1f;

    // Linear accelerations in robot frame
    float forward_accel = forward_force / mass_slugs;   // in/s²
    float lateral_accel = lateral_force / mass_slugs;

    // Angular acceleration (torque / moment of inertia)
    float angular_accel = total_torque / dt->config.moment_of_inertia;  // rad/s²

    // =========================================================================
    // Step 7: Integrate velocities
    // =========================================================================

    // Current velocity in robot frame
    float vel_forward = dt->vel_z * cos_h + dt->vel_x * sin_h;
    float vel_lateral = -dt->vel_z * sin_h + dt->vel_x * cos_h;

    // Update velocities
    vel_forward += forward_accel * dt_sec;
    vel_lateral += lateral_accel * dt_sec;
    dt->angular_vel += angular_accel * dt_sec;

    // Apply damping (air resistance, rolling resistance)
    vel_forward *= VEXIQ_LINEAR_DAMPING;
    vel_lateral *= VEXIQ_LINEAR_DAMPING;
    dt->angular_vel *= VEXIQ_ANGULAR_DAMPING;

    // Apply motor braking when motors are at zero (VEX motors brake by default)
    // This simulates back-EMF braking - motors resist motion when unpowered
    bool motors_off = (fabsf(dt->left_motor_pct) < 1.0f && fabsf(dt->right_motor_pct) < 1.0f);
    if (motors_off) {
        // Strong braking when motors are off - stop quickly
        float brake_factor = 0.85f;  // Aggressive braking
        vel_forward *= brake_factor;
        dt->angular_vel *= brake_factor;

        // Stop completely if very slow (prevents drift)
        if (fabsf(vel_forward) < 0.5f) vel_forward = 0.0f;
        if (fabsf(dt->angular_vel) < 0.01f) dt->angular_vel = 0.0f;
    }

    // Transform back to world frame
    dt->vel_x = vel_forward * sin_h + vel_lateral * cos_h;
    dt->vel_z = vel_forward * cos_h - vel_lateral * sin_h;

    // =========================================================================
    // Step 8: Integrate position
    // =========================================================================

    dt->pos_x += dt->vel_x * dt_sec;
    dt->pos_z += dt->vel_z * dt_sec;
    dt->heading += dt->angular_vel * dt_sec;

    // Normalize heading to [-PI, PI]
    while (dt->heading > PI) dt->heading -= 2.0f * PI;
    while (dt->heading < -PI) dt->heading += 2.0f * PI;

    // =========================================================================
    // Step 9: Update derived values
    // =========================================================================

    // Linear velocity (forward speed)
    dt->linear_velocity = vel_forward;

    // Wheel surface velocities (for animation)
    // In tank drive: wheel_vel = linear_vel ± (angular_vel * track_width/2)
    dt->left_wheel_vel = vel_forward - dt->angular_vel * track_half;
    dt->right_wheel_vel = vel_forward + dt->angular_vel * track_half;
}

void drivetrain_set_position(Drivetrain* dt, float x, float z, float heading) {
    dt->pos_x = x;
    dt->pos_z = z;
    dt->heading = heading;
    // Reset velocities when teleporting
    dt->vel_x = 0.0f;
    dt->vel_z = 0.0f;
    dt->angular_vel = 0.0f;
}

Vec3 drivetrain_get_position(const Drivetrain* dt) {
    return (Vec3){dt->pos_x, 0.0f, dt->pos_z};
}

float drivetrain_get_heading(const Drivetrain* dt) {
    return dt->heading;
}

Vec3 drivetrain_get_velocity(const Drivetrain* dt) {
    return (Vec3){dt->vel_x, 0.0f, dt->vel_z};
}

bool drivetrain_is_slipping(const Drivetrain* dt) {
    return dt->left_wheels_slipping || dt->right_wheels_slipping;
}
