/*
 * Scene Loader
 * Loads scene configuration files that define robots and their positions
 *
 * Scene File Format (.scene):
 *   # Comment lines start with #
 *   name <Scene Name>
 *   robot <file.mpd> <x> <y> <z> [rotation_y_degrees]
 *   cylinder <x> <z> <radius> <height> <r> <g> <b>
 *
 * Example:
 *   name Default Scene
 *   robot ClawbotIQ.mpd 0 0 0
 *   robot Ike.mpd 24 0 0 180
 *   cylinder -20 -15 2 7 0.9 0.2 0.2
 */

#ifndef SCENE_H
#define SCENE_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define SCENE_MAX_ROBOTS 16
#define SCENE_MAX_CYLINDERS 32
#define SCENE_MAX_NAME 128
#define SCENE_MAX_PATH 256

// Robot placement in scene
typedef struct {
    char mpd_file[SCENE_MAX_PATH];  // Path to MPD file (relative to robots dir)
    float x, y, z;                   // Position in world units (inches)
    float rotation_y;                // Rotation around Y axis (degrees)
} SceneRobot;

// Cylinder object in scene (movable physics object)
typedef struct {
    float x, z;           // Position on field (inches)
    float radius;         // Radius (inches)
    float height;         // Height (inches)
    float r, g, b;        // Color (0-1)
    // Physics state (for movable cylinders)
    float vel_x, vel_z;   // Velocity (inches/s)
    float mass;           // Mass in pounds (light plastic cup ~0.1 lbs)
} SceneCylinder;

// Scene-level physics parameters
typedef struct {
    float friction_coeff;     // Wheel-ground friction coefficient (rubber on tile ~0.8)
    float cylinder_friction;  // Friction for pushing cylinders (~0.5)
    float gravity;            // Gravity in inches/s^2 (386.1 = 9.81 m/s^2)
} ScenePhysics;

// Loaded scene
typedef struct {
    char name[SCENE_MAX_NAME];       // Scene name
    SceneRobot robots[SCENE_MAX_ROBOTS];
    uint32_t robot_count;
    SceneCylinder cylinders[SCENE_MAX_CYLINDERS];
    uint32_t cylinder_count;
    ScenePhysics physics;            // Physics parameters
} Scene;

// Load scene from file
// robots_dir: directory containing robot MPD files
// Returns true on success
bool scene_load(const char* path, Scene* scene);

// Print scene info
void scene_print(const Scene* scene);

#ifdef __cplusplus
}
#endif

#endif // SCENE_H
