/*
 * VEX IQ Physics Configuration
 *
 * Global physics constants for VEX IQ robots.
 * These are based on standardized VEX IQ parts and motors.
 */

#ifndef PHYSICS_CONFIG_H
#define PHYSICS_CONFIG_H

#ifdef __cplusplus
extern "C" {
#endif

// =============================================================================
// VEX IQ Motor Constants
// Based on VEX IQ Smart Motor specifications
// =============================================================================

// Motor RPM at no load
#define VEXIQ_MOTOR_MAX_RPM 120.0f

// Motor stall torque in inch-pounds (0.52 N·m = ~4.6 in·lbf)
#define VEXIQ_MOTOR_STALL_TORQUE 4.6f

// Motor stall force at wheel surface (torque / wheel_radius)
// For 4" wheel (2" radius): 4.6 / 2 = 2.3 lbf per motor
#define VEXIQ_MOTOR_STALL_FORCE_4IN 2.3f

// =============================================================================
// VEX IQ Robot Physical Properties
// =============================================================================

// Typical robot mass in pounds (adjustable per robot if needed)
#define VEXIQ_DEFAULT_ROBOT_MASS 3.0f

// Robot mass in slugs for force calculations (mass_lb / 386.1)
// 3 lbs = 0.00777 slugs
#define VEXIQ_DEFAULT_ROBOT_MASS_SLUGS 0.00777f

// Moment of inertia estimate (for rotation)
// Approximating robot as a 10" x 10" square plate: I = (1/12) * m * (w^2 + h^2)
// I = (1/12) * 0.00777 * (100 + 100) = 0.1295 slug·in²
#define VEXIQ_DEFAULT_MOMENT_OF_INERTIA 0.13f

// =============================================================================
// Wheel Constants
// =============================================================================

// Standard wheel diameters (inches)
#define VEXIQ_WHEEL_DIAMETER_SMALL 2.75f
#define VEXIQ_WHEEL_DIAMETER_MEDIUM 3.25f
#define VEXIQ_WHEEL_DIAMETER_LARGE 4.0f

// Default wheel diameter
#define VEXIQ_DEFAULT_WHEEL_DIAMETER 4.0f

// =============================================================================
// Friction and Damping
// =============================================================================

// Linear damping (air resistance, rolling resistance)
// Velocity decay factor per frame (1.0 = no damping)
// Lower values = faster stopping when motors off
#define VEXIQ_LINEAR_DAMPING 0.90f

// Angular damping for rotation
#define VEXIQ_ANGULAR_DAMPING 0.85f

// Collision restitution (bounciness, 0 = no bounce, 1 = perfect bounce)
#define VEXIQ_COLLISION_RESTITUTION 0.2f

// =============================================================================
// Conversion Helpers
// =============================================================================

// Convert pounds to slugs (for F = ma in imperial units)
#define LBS_TO_SLUGS(lbs) ((lbs) / 386.1f)

// Convert RPM to radians/second
#define RPM_TO_RAD_S(rpm) ((rpm) * 0.10472f)

// Convert RPM to inches/second for given wheel diameter
#define RPM_TO_IN_S(rpm, diameter) ((rpm) / 60.0f * 3.14159f * (diameter))

#ifdef __cplusplus
}
#endif

#endif // PHYSICS_CONFIG_H
