/*
 * Scene Loader
 * Loads scene configuration files that define robots and their positions
 *
 * Scene File Format (.scene):
 *   # Comment lines start with #
 *   name <Scene Name>
 *   robot <file.mpd> <x> <y> <z> [rotation_y_degrees]
 *
 * Example:
 *   name Default Scene
 *   robot ClawbotIQ.mpd 0 0 0
 *   robot Ike.mpd 24 0 0 180
 */

#ifndef SCENE_H
#define SCENE_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define SCENE_MAX_ROBOTS 16
#define SCENE_MAX_NAME 128
#define SCENE_MAX_PATH 256

// Robot placement in scene
typedef struct {
    char mpd_file[SCENE_MAX_PATH];  // Path to MPD file (relative to robots dir)
    float x, y, z;                   // Position in world units (inches)
    float rotation_y;                // Rotation around Y axis (degrees)
} SceneRobot;

// Loaded scene
typedef struct {
    char name[SCENE_MAX_NAME];       // Scene name
    SceneRobot robots[SCENE_MAX_ROBOTS];
    uint32_t robot_count;
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
