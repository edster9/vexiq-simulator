/*
 * Scene Loader Implementation
 * Parses YAML-like scene configuration files
 */

#include "scene.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

// Get indentation level (number of leading spaces)
static int get_indent(const char* line) {
    int indent = 0;
    while (*line == ' ') {
        indent++;
        line++;
    }
    return indent;
}

// Trim leading/trailing whitespace in place
static char* trim(char* str) {
    while (isspace((unsigned char)*str)) str++;
    if (*str == 0) return str;
    char* end = str + strlen(str) - 1;
    while (end > str && isspace((unsigned char)*end)) end--;
    end[1] = '\0';
    return str;
}

// Parse "key: value" and return pointer to value (after colon and whitespace)
// Returns NULL if not a key-value pair
static const char* parse_key_value(const char* line, char* key_out, size_t key_size) {
    const char* colon = strchr(line, ':');
    if (!colon) return NULL;

    // Copy key (everything before colon)
    size_t key_len = colon - line;
    if (key_len >= key_size) key_len = key_size - 1;
    strncpy(key_out, line, key_len);
    key_out[key_len] = '\0';

    // Trim key
    char* k = key_out;
    while (*k && isspace((unsigned char)*k)) k++;
    if (k != key_out) memmove(key_out, k, strlen(k) + 1);
    k = key_out + strlen(key_out) - 1;
    while (k > key_out && isspace((unsigned char)*k)) *k-- = '\0';

    // Return value (everything after colon, trimmed)
    const char* value = colon + 1;
    while (*value && isspace((unsigned char)*value)) value++;
    return value;
}

// Parse array like [1, 2, 3] or [-20, 0, 0]
static int parse_float_array(const char* str, float* out, int max_count) {
    if (*str != '[') return 0;
    str++;

    int count = 0;
    while (*str && *str != ']' && count < max_count) {
        while (*str && (isspace((unsigned char)*str) || *str == ',')) str++;
        if (*str == ']') break;

        char* end;
        out[count] = strtof(str, &end);
        if (end == str) break;
        count++;
        str = end;
    }
    return count;
}

// Parser state machine
enum ParseSection {
    SECTION_NONE,
    SECTION_PHYSICS,
    SECTION_ROBOTS,
    SECTION_CYLINDERS
};

bool scene_load(const char* path, Scene* scene) {
    FILE* file = fopen(path, "r");
    if (!file) {
        fprintf(stderr, "[Scene] Failed to open: %s\n", path);
        return false;
    }

    // Initialize scene
    memset(scene, 0, sizeof(Scene));
    strncpy(scene->name, "Unnamed Scene", SCENE_MAX_NAME - 1);

    // Default physics parameters
    scene->physics.friction_coeff = 0.8f;
    scene->physics.cylinder_friction = 0.5f;
    scene->physics.gravity = 386.1f;

    char line[512];
    int line_num = 0;
    ParseSection current_section = SECTION_NONE;
    SceneRobot* current_robot = NULL;
    SceneCylinder* current_cylinder = NULL;

    while (fgets(line, sizeof(line), file)) {
        line_num++;

        // Get indentation before trimming
        int indent = get_indent(line);
        char* trimmed = trim(line);

        // Skip empty lines and comments
        if (trimmed[0] == '\0' || trimmed[0] == '#') {
            continue;
        }

        // Check for list item (starts with -)
        bool is_list_item = (trimmed[0] == '-');
        if (is_list_item) {
            trimmed++;
            while (*trimmed && isspace((unsigned char)*trimmed)) trimmed++;
        }

        // Parse key: value
        char key[64];
        const char* value = parse_key_value(trimmed, key, sizeof(key));

        if (!value) {
            // Not a key-value pair, might be a section header
            continue;
        }

        // Top-level keys (no indent or section headers)
        if (indent == 0 && !is_list_item) {
            if (strcmp(key, "name") == 0) {
                strncpy(scene->name, value, SCENE_MAX_NAME - 1);
            }
            else if (strcmp(key, "physics") == 0) {
                current_section = SECTION_PHYSICS;
                current_robot = NULL;
                current_cylinder = NULL;
            }
            else if (strcmp(key, "robots") == 0) {
                current_section = SECTION_ROBOTS;
                current_robot = NULL;
                current_cylinder = NULL;
            }
            else if (strcmp(key, "cylinders") == 0) {
                current_section = SECTION_CYLINDERS;
                current_robot = NULL;
                current_cylinder = NULL;
            }
        }
        // Physics section properties
        else if (current_section == SECTION_PHYSICS && indent >= 2) {
            if (strcmp(key, "friction") == 0) {
                scene->physics.friction_coeff = (float)atof(value);
            }
            else if (strcmp(key, "cylinder_friction") == 0) {
                scene->physics.cylinder_friction = (float)atof(value);
            }
            else if (strcmp(key, "gravity") == 0) {
                scene->physics.gravity = (float)atof(value);
            }
        }
        // Robots section
        else if (current_section == SECTION_ROBOTS) {
            // New robot list item
            if (is_list_item && strcmp(key, "mpd") == 0) {
                if (scene->robot_count >= SCENE_MAX_ROBOTS) {
                    fprintf(stderr, "[Scene] Warning: Max robots exceeded at line %d\n", line_num);
                    current_robot = NULL;
                } else {
                    current_robot = &scene->robots[scene->robot_count];
                    memset(current_robot, 0, sizeof(SceneRobot));
                    strncpy(current_robot->mpd_file, value, SCENE_MAX_PATH - 1);
                    scene->robot_count++;
                }
            }
            // Robot properties
            else if (current_robot && indent >= 4) {
                if (strcmp(key, "position") == 0) {
                    float pos[3] = {0, 0, 0};
                    parse_float_array(value, pos, 3);
                    current_robot->x = pos[0];
                    current_robot->y = pos[1];
                    current_robot->z = pos[2];
                }
                else if (strcmp(key, "rotation") == 0) {
                    current_robot->rotation_y = (float)atof(value);
                }
                else if (strcmp(key, "iqpython") == 0) {
                    strncpy(current_robot->iqpython_file, value, SCENE_MAX_PATH - 1);
                    current_robot->has_program = true;
                }
                else if (strcmp(key, "config") == 0) {
                    strncpy(current_robot->config_file, value, SCENE_MAX_PATH - 1);
                }
            }
        }
        // Cylinders section
        else if (current_section == SECTION_CYLINDERS) {
            // New cylinder list item
            if (is_list_item && strcmp(key, "position") == 0) {
                if (scene->cylinder_count >= SCENE_MAX_CYLINDERS) {
                    fprintf(stderr, "[Scene] Warning: Max cylinders exceeded at line %d\n", line_num);
                    current_cylinder = NULL;
                } else {
                    current_cylinder = &scene->cylinders[scene->cylinder_count];
                    memset(current_cylinder, 0, sizeof(SceneCylinder));
                    current_cylinder->mass = 0.1f;  // Default mass

                    float pos[2] = {0, 0};
                    parse_float_array(value, pos, 2);
                    current_cylinder->x = pos[0];
                    current_cylinder->z = pos[1];
                    scene->cylinder_count++;
                }
            }
            // Cylinder properties
            else if (current_cylinder && indent >= 4) {
                if (strcmp(key, "radius") == 0) {
                    current_cylinder->radius = (float)atof(value);
                }
                else if (strcmp(key, "height") == 0) {
                    current_cylinder->height = (float)atof(value);
                }
                else if (strcmp(key, "color") == 0) {
                    float color[3] = {1, 1, 1};
                    parse_float_array(value, color, 3);
                    current_cylinder->r = color[0];
                    current_cylinder->g = color[1];
                    current_cylinder->b = color[2];
                }
            }
        }
    }

    fclose(file);

    printf("[Scene] Loaded: %s (%u robots, %u cylinders, friction=%.2f)\n",
           scene->name, scene->robot_count, scene->cylinder_count,
           scene->physics.friction_coeff);
    return true;
}

void scene_print(const Scene* scene) {
    printf("Scene: %s\n", scene->name);
    printf("  Physics: friction=%.2f, cylinder_friction=%.2f, gravity=%.1f\n",
           scene->physics.friction_coeff, scene->physics.cylinder_friction,
           scene->physics.gravity);
    printf("  Robots: %u\n", scene->robot_count);
    for (uint32_t i = 0; i < scene->robot_count; i++) {
        const SceneRobot* r = &scene->robots[i];
        printf("    [%u] %s at (%.1f, %.1f, %.1f) rot=%.1f deg\n",
               i, r->mpd_file, r->x, r->y, r->z, r->rotation_y);
        if (r->has_program) {
            printf("        iqpython: %s\n", r->iqpython_file);
        }
        if (r->config_file[0]) {
            printf("        config: %s\n", r->config_file);
        }
    }
    printf("  Cylinders: %u\n", scene->cylinder_count);
    for (uint32_t i = 0; i < scene->cylinder_count; i++) {
        const SceneCylinder* c = &scene->cylinders[i];
        printf("    [%u] at (%.1f, %.1f) r=%.1f h=%.1f color=(%.2f,%.2f,%.2f)\n",
               i, c->x, c->z, c->radius, c->height, c->r, c->g, c->b);
    }
}
