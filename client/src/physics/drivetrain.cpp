/*
 * Drivetrain Physics Implementation
 *
 * Tank drive kinematics using the unicycle model.
 */

#include "drivetrain.h"
#include <math.h>
#include <string.h>

// Default VEX IQ drivetrain configuration
static const DrivetrainConfig DEFAULT_CONFIG = {
    .track_width = 10.0f,       // ~10 inches between wheels
    .wheel_diameter = 4.0f,     // 4" standard wheels
    .max_rpm = 120.0f,          // VEX IQ motor max RPM
    .accel_rate = 0.0f,         // 0 = instant (no acceleration curve)
};

// Math constants
#define PI 3.14159265358979323846f

void drivetrain_init(Drivetrain* dt) {
    drivetrain_init_config(dt, &DEFAULT_CONFIG);
}

void drivetrain_init_config(Drivetrain* dt, const DrivetrainConfig* config) {
    memset(dt, 0, sizeof(Drivetrain));
    dt->config = *config;
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
    dt->left_target = drivetrain_percent_to_velocity(dt, left_percent);
    dt->right_target = drivetrain_percent_to_velocity(dt, right_percent);
}

void drivetrain_set_velocities(Drivetrain* dt, float left_vel, float right_vel) {
    float max_velocity = drivetrain_rpm_to_velocity(dt->config.max_rpm, dt->config.wheel_diameter);

    // Clamp to max velocity
    if (left_vel > max_velocity) left_vel = max_velocity;
    if (left_vel < -max_velocity) left_vel = -max_velocity;
    if (right_vel > max_velocity) right_vel = max_velocity;
    if (right_vel < -max_velocity) right_vel = -max_velocity;

    dt->left_target = left_vel;
    dt->right_target = right_vel;
}

void drivetrain_stop(Drivetrain* dt, int mode) {
    dt->left_target = 0.0f;
    dt->right_target = 0.0f;

    if (mode == 1) {
        // Brake: stop immediately
        dt->left_velocity = 0.0f;
        dt->right_velocity = 0.0f;
    }
    // Coast: let acceleration curve bring to stop
}

void drivetrain_update(Drivetrain* dt, float dt_sec) {
    // Apply acceleration (if configured)
    if (dt->config.accel_rate > 0.0f) {
        float max_delta = dt->config.accel_rate * dt_sec;

        // Left motor
        float left_diff = dt->left_target - dt->left_velocity;
        if (fabsf(left_diff) <= max_delta) {
            dt->left_velocity = dt->left_target;
        } else {
            dt->left_velocity += (left_diff > 0 ? max_delta : -max_delta);
        }

        // Right motor
        float right_diff = dt->right_target - dt->right_velocity;
        if (fabsf(right_diff) <= max_delta) {
            dt->right_velocity = dt->right_target;
        } else {
            dt->right_velocity += (right_diff > 0 ? max_delta : -max_delta);
        }
    } else {
        // Instant response (no acceleration)
        dt->left_velocity = dt->left_target;
        dt->right_velocity = dt->right_target;
    }

    // Compute linear and angular velocity (tank drive kinematics)
    // Linear = average of wheel velocities
    // Angular = difference / track width
    dt->linear_velocity = (dt->left_velocity + dt->right_velocity) / 2.0f;
    dt->angular_velocity = (dt->right_velocity - dt->left_velocity) / dt->config.track_width;

    // Update pose using forward kinematics
    // For small dt, use simple Euler integration
    // For better accuracy, could use Runge-Kutta or exact arc integration

    if (fabsf(dt->angular_velocity) < 0.0001f) {
        // Nearly straight line - avoid division by zero
        // Move in current heading direction
        dt->pos_x += dt->linear_velocity * sinf(dt->heading) * dt_sec;
        dt->pos_z += dt->linear_velocity * cosf(dt->heading) * dt_sec;
    } else {
        // Arc motion - use exact integration
        // Robot moves along an arc with radius R = linear_velocity / angular_velocity
        float theta_old = dt->heading;
        float theta_new = theta_old + dt->angular_velocity * dt_sec;

        // Exact arc integration:
        // dx = R * (sin(theta_new) - sin(theta_old))
        // dz = R * (cos(theta_new) - cos(theta_old))
        // But R = v / omega, so:
        // dx = (v / omega) * (sin(theta_new) - sin(theta_old))
        // dz = (v / omega) * (cos(theta_new) - cos(theta_old))

        float R = dt->linear_velocity / dt->angular_velocity;
        dt->pos_x += R * (sinf(theta_new) - sinf(theta_old));
        dt->pos_z += R * (cosf(theta_new) - cosf(theta_old));
        dt->heading = theta_new;
    }

    // Normalize heading to [-PI, PI]
    while (dt->heading > PI) dt->heading -= 2.0f * PI;
    while (dt->heading < -PI) dt->heading += 2.0f * PI;
}

void drivetrain_set_position(Drivetrain* dt, float x, float z, float heading) {
    dt->pos_x = x;
    dt->pos_z = z;
    dt->heading = heading;
}

Vec3 drivetrain_get_position(const Drivetrain* dt) {
    return (Vec3){dt->pos_x, 0.0f, dt->pos_z};
}

float drivetrain_get_heading(const Drivetrain* dt) {
    return dt->heading;
}
