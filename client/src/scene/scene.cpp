/*
 * Scene Loader Implementation
 */

#include "scene.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

// Trim leading/trailing whitespace in place
static char* trim(char* str) {
    // Leading
    while (isspace((unsigned char)*str)) str++;
    if (*str == 0) return str;

    // Trailing
    char* end = str + strlen(str) - 1;
    while (end > str && isspace((unsigned char)*end)) end--;
    end[1] = '\0';

    return str;
}

bool scene_load(const char* path, Scene* scene) {
    FILE* file = fopen(path, "r");
    if (!file) {
        fprintf(stderr, "[Scene] Failed to open: %s\n", path);
        return false;
    }

    // Initialize scene
    memset(scene, 0, sizeof(Scene));
    strncpy(scene->name, "Unnamed Scene", SCENE_MAX_NAME - 1);

    char line[512];
    int line_num = 0;

    while (fgets(line, sizeof(line), file)) {
        line_num++;

        // Trim and skip empty lines / comments
        char* trimmed = trim(line);
        if (trimmed[0] == '\0' || trimmed[0] == '#') {
            continue;
        }

        // Parse command
        char cmd[64];
        if (sscanf(trimmed, "%63s", cmd) != 1) {
            continue;
        }

        if (strcmp(cmd, "name") == 0) {
            // name <Scene Name>
            char* name_start = trimmed + 4;
            while (isspace((unsigned char)*name_start)) name_start++;
            strncpy(scene->name, name_start, SCENE_MAX_NAME - 1);
        }
        else if (strcmp(cmd, "robot") == 0) {
            // robot <file> <x> <y> <z> [rotation_y]
            if (scene->robot_count >= SCENE_MAX_ROBOTS) {
                fprintf(stderr, "[Scene] Warning: Max robots (%d) exceeded at line %d\n",
                        SCENE_MAX_ROBOTS, line_num);
                continue;
            }

            SceneRobot* robot = &scene->robots[scene->robot_count];
            robot->rotation_y = 0.0f;  // Default rotation

            char file_path[SCENE_MAX_PATH];
            int parsed = sscanf(trimmed, "robot %255s %f %f %f %f",
                               file_path, &robot->x, &robot->y, &robot->z, &robot->rotation_y);

            if (parsed >= 4) {
                strncpy(robot->mpd_file, file_path, SCENE_MAX_PATH - 1);
                scene->robot_count++;
            } else {
                fprintf(stderr, "[Scene] Warning: Invalid robot line %d: %s\n", line_num, trimmed);
            }
        }
        else {
            fprintf(stderr, "[Scene] Warning: Unknown command '%s' at line %d\n", cmd, line_num);
        }
    }

    fclose(file);

    printf("[Scene] Loaded: %s (%u robots)\n", scene->name, scene->robot_count);
    return true;
}

void scene_print(const Scene* scene) {
    printf("Scene: %s\n", scene->name);
    printf("  Robots: %u\n", scene->robot_count);
    for (uint32_t i = 0; i < scene->robot_count; i++) {
        const SceneRobot* r = &scene->robots[i];
        printf("    [%u] %s at (%.1f, %.1f, %.1f) rot=%.1f°\n",
               i, r->mpd_file, r->x, r->y, r->z, r->rotation_y);
    }
}
