/*
 * Robot Definition Loader
 *
 * Parses .robotdef files to extract robot structure, drivetrain configuration,
 * and kinematics for simulation.
 */

#ifndef ROBOTDEF_H
#define ROBOTDEF_H

#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// Maximum lengths for strings
#define ROBOTDEF_MAX_NAME 128
#define ROBOTDEF_MAX_SUBMODELS 64
#define ROBOTDEF_MAX_WHEELS 8
#define ROBOTDEF_MAX_WHEEL_PARTS 4

// Drivetrain types
typedef enum {
    DRIVETRAIN_UNKNOWN = 0,
    DRIVETRAIN_TANK,
    DRIVETRAIN_MECANUM,
    DRIVETRAIN_OMNI,
    DRIVETRAIN_ACKERMANN
} DrivetrainType;

// Drivetrain configuration from robotdef
typedef struct {
    DrivetrainType type;
    char left_drive[ROBOTDEF_MAX_NAME];
    char right_drive[ROBOTDEF_MAX_NAME];
    float rotation_center[3];  // LDU coordinates
    float rotation_axis[3];    // Axis for robot rotation (default: [0,1,0] = vertical)
    float track_width;         // LDU
    float wheel_diameter;      // mm (0 if not specified)
} RobotDefDrivetrain;

// Motor configuration
typedef struct {
    char submodel[ROBOTDEF_MAX_NAME];
    int port;           // VEX IQ port 1-12, 0 = not assigned
    int count;          // Number of motors in this submodel
} RobotDefMotor;

// Submodel kinematics (for articulated parts)
typedef struct {
    char name[ROBOTDEF_MAX_NAME];
    float position[3];          // LDU
    float rotation_axis[3];     // Local rotation axis (0,0,0 = none)
    float rotation_origin[3];   // Pivot point in local coords
    float rotation_limits[2];   // [min_deg, max_deg]
    bool has_kinematics;
} RobotDefSubmodel;

// Wheel assembly (hub + tire that spin together)
typedef struct {
    char id[ROBOTDEF_MAX_NAME];           // e.g., "left_front"
    float world_position[3];              // LDU - center of wheel
    float spin_axis[3];                   // Axis of rotation (normalized)
    float outer_diameter_mm;              // Wheel diameter
    char part_numbers[ROBOTDEF_MAX_WHEEL_PARTS][32];  // Part numbers in this assembly
    int part_count;
    bool is_left;                         // true = left side, false = right
} RobotDefWheelAssembly;

// Complete robot definition
typedef struct {
    // Metadata
    int version;
    char source_file[ROBOTDEF_MAX_NAME];
    char main_model[ROBOTDEF_MAX_NAME];

    // Drivetrain
    RobotDefDrivetrain drivetrain;

    // Motors
    RobotDefMotor motors[12];  // Max 12 ports
    int motor_count;

    // Submodels with kinematics
    RobotDefSubmodel submodels[ROBOTDEF_MAX_SUBMODELS];
    int submodel_count;

    // Wheel assemblies
    RobotDefWheelAssembly wheel_assemblies[ROBOTDEF_MAX_WHEELS];
    int wheel_count;

    // Summary
    int total_wheels;
    int total_motors;
    int total_sensors;
    bool has_brain;
} RobotDef;

// Initialize robot definition with defaults
void robotdef_init(RobotDef* def);

// Load robot definition from file
// Returns true on success, false on failure
bool robotdef_load(const char* path, RobotDef* def);

// Get a submodel by name (returns NULL if not found)
const RobotDefSubmodel* robotdef_get_submodel(const RobotDef* def, const char* name);

// Print robot definition summary (for debugging)
void robotdef_print(const RobotDef* def);

#ifdef __cplusplus
}
#endif

#endif // ROBOTDEF_H
