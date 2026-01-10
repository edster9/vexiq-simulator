/*
 * Robot Definition Loader Implementation
 *
 * Simple YAML-like parser for .robotdef files.
 */

#include "robotdef.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

// Trim leading and trailing whitespace
static char* trim(char* str) {
    while (isspace((unsigned char)*str)) str++;
    if (*str == '\0') return str;

    char* end = str + strlen(str) - 1;
    while (end > str && isspace((unsigned char)*end)) end--;
    end[1] = '\0';

    return str;
}

// Parse a float array from "[x, y, z]" format
static bool parse_float_array(const char* str, float* out, int count) {
    const char* p = strchr(str, '[');
    if (!p) return false;
    p++;

    for (int i = 0; i < count; i++) {
        while (isspace((unsigned char)*p)) p++;
        out[i] = (float)strtod(p, (char**)&p);
        // Skip comma and whitespace
        while (*p == ',' || isspace((unsigned char)*p)) p++;
    }
    return true;
}

// Check if line starts with key (after trimming)
static bool starts_with(const char* line, const char* key) {
    size_t key_len = strlen(key);
    return strncmp(line, key, key_len) == 0;
}

// Get value after colon
static const char* get_value(const char* line) {
    const char* colon = strchr(line, ':');
    if (!colon) return NULL;
    return trim((char*)(colon + 1));
}

void robotdef_init(RobotDef* def) {
    memset(def, 0, sizeof(RobotDef));
    def->version = 1;
    def->drivetrain.type = DRIVETRAIN_UNKNOWN;
    // Default rotation axis is vertical (Y-up)
    def->drivetrain.rotation_axis[0] = 0.0f;
    def->drivetrain.rotation_axis[1] = 1.0f;
    def->drivetrain.rotation_axis[2] = 0.0f;
}

bool robotdef_load(const char* path, RobotDef* def) {
    FILE* f = fopen(path, "r");
    if (!f) {
        fprintf(stderr, "robotdef: Cannot open %s\n", path);
        return false;
    }

    robotdef_init(def);

    char line[512];
    int indent = 0;
    enum { SECTION_NONE, SECTION_SUMMARY, SECTION_DRIVETRAIN, SECTION_MOTORS, SECTION_SUBMODELS, SECTION_WHEEL_ASSEMBLIES } section = SECTION_NONE;
    int current_motor = -1;
    int current_submodel = -1;
    int current_wheel = -1;
    bool in_wheel_parts = false;

    while (fgets(line, sizeof(line), f)) {
        // Remove newline
        char* nl = strchr(line, '\n');
        if (nl) *nl = '\0';

        // Skip empty lines and comments
        char* trimmed = trim(line);
        if (*trimmed == '\0' || *trimmed == '#') continue;

        // Calculate indent (for section detection)
        indent = 0;
        for (const char* p = line; *p == ' '; p++) indent++;

        // Top-level keys
        if (indent == 0) {
            if (starts_with(trimmed, "version:")) {
                def->version = atoi(get_value(trimmed));
            } else if (starts_with(trimmed, "source_file:")) {
                strncpy(def->source_file, get_value(trimmed), ROBOTDEF_MAX_NAME - 1);
            } else if (starts_with(trimmed, "main_model:")) {
                strncpy(def->main_model, get_value(trimmed), ROBOTDEF_MAX_NAME - 1);
            } else if (starts_with(trimmed, "summary:")) {
                section = SECTION_SUMMARY;
            } else if (starts_with(trimmed, "drivetrain:")) {
                section = SECTION_DRIVETRAIN;
            } else if (starts_with(trimmed, "motors:")) {
                section = SECTION_MOTORS;
                current_motor = -1;
            } else if (starts_with(trimmed, "submodels:")) {
                section = SECTION_SUBMODELS;
                current_submodel = -1;
            } else if (starts_with(trimmed, "wheel_assemblies:")) {
                section = SECTION_WHEEL_ASSEMBLIES;
                current_wheel = -1;
                in_wheel_parts = false;
            }
            continue;
        }

        // Section contents
        switch (section) {
            case SECTION_SUMMARY:
                if (starts_with(trimmed, "total_wheels:")) {
                    def->total_wheels = atoi(get_value(trimmed));
                } else if (starts_with(trimmed, "total_motors:")) {
                    def->total_motors = atoi(get_value(trimmed));
                } else if (starts_with(trimmed, "total_sensors:")) {
                    def->total_sensors = atoi(get_value(trimmed));
                } else if (starts_with(trimmed, "has_brain:")) {
                    def->has_brain = strcmp(get_value(trimmed), "true") == 0;
                }
                break;

            case SECTION_DRIVETRAIN:
                if (starts_with(trimmed, "type:")) {
                    const char* val = get_value(trimmed);
                    if (strncmp(val, "tank", 4) == 0) {
                        def->drivetrain.type = DRIVETRAIN_TANK;
                    } else if (strncmp(val, "mecanum", 7) == 0) {
                        def->drivetrain.type = DRIVETRAIN_MECANUM;
                    } else if (strncmp(val, "omni", 4) == 0) {
                        def->drivetrain.type = DRIVETRAIN_OMNI;
                    } else if (strncmp(val, "ackermann", 9) == 0) {
                        def->drivetrain.type = DRIVETRAIN_ACKERMANN;
                    }
                } else if (starts_with(trimmed, "left_drive:")) {
                    strncpy(def->drivetrain.left_drive, get_value(trimmed), ROBOTDEF_MAX_NAME - 1);
                } else if (starts_with(trimmed, "right_drive:")) {
                    strncpy(def->drivetrain.right_drive, get_value(trimmed), ROBOTDEF_MAX_NAME - 1);
                } else if (starts_with(trimmed, "rotation_center:")) {
                    parse_float_array(trimmed, def->drivetrain.rotation_center, 3);
                } else if (starts_with(trimmed, "rotation_axis:")) {
                    parse_float_array(trimmed, def->drivetrain.rotation_axis, 3);
                } else if (starts_with(trimmed, "track_width:")) {
                    def->drivetrain.track_width = (float)atof(get_value(trimmed));
                } else if (starts_with(trimmed, "wheel_diameter:")) {
                    def->drivetrain.wheel_diameter = (float)atof(get_value(trimmed));
                }
                break;

            case SECTION_MOTORS:
                if (starts_with(trimmed, "- submodel:")) {
                    current_motor++;
                    if (current_motor < 12) {
                        def->motor_count = current_motor + 1;
                        strncpy(def->motors[current_motor].submodel, get_value(trimmed), ROBOTDEF_MAX_NAME - 1);
                    }
                } else if (current_motor >= 0 && current_motor < 12) {
                    if (starts_with(trimmed, "port:")) {
                        const char* val = get_value(trimmed);
                        def->motors[current_motor].port = (strcmp(val, "null") == 0) ? 0 : atoi(val);
                    } else if (starts_with(trimmed, "count:")) {
                        def->motors[current_motor].count = atoi(get_value(trimmed));
                    }
                }
                break;

            case SECTION_SUBMODELS:
                // Check for new submodel (starts with name ending in .ldr:)
                if (indent == 2 && strchr(trimmed, ':') && strstr(trimmed, ".ldr:")) {
                    current_submodel++;
                    if (current_submodel < ROBOTDEF_MAX_SUBMODELS) {
                        def->submodel_count = current_submodel + 1;
                        // Extract name (everything before the colon)
                        char name[ROBOTDEF_MAX_NAME];
                        strncpy(name, trimmed, ROBOTDEF_MAX_NAME - 1);
                        char* colon = strchr(name, ':');
                        if (colon) *colon = '\0';
                        strncpy(def->submodels[current_submodel].name, name, ROBOTDEF_MAX_NAME - 1);
                    }
                } else if (current_submodel >= 0 && current_submodel < ROBOTDEF_MAX_SUBMODELS) {
                    RobotDefSubmodel* sm = &def->submodels[current_submodel];
                    if (starts_with(trimmed, "position:")) {
                        parse_float_array(trimmed, sm->position, 3);
                    } else if (starts_with(trimmed, "rotation_axis:")) {
                        parse_float_array(trimmed, sm->rotation_axis, 3);
                        sm->has_kinematics = true;
                    } else if (starts_with(trimmed, "rotation_origin:")) {
                        parse_float_array(trimmed, sm->rotation_origin, 3);
                    } else if (starts_with(trimmed, "rotation_limits:")) {
                        parse_float_array(trimmed, sm->rotation_limits, 2);
                    }
                }
                break;

            case SECTION_WHEEL_ASSEMBLIES:
                // Wheel assembly ID at indent 2 (e.g., "left_front:")
                if (indent == 2 && strchr(trimmed, ':') && !starts_with(trimmed, "- ")) {
                    current_wheel++;
                    in_wheel_parts = false;
                    if (current_wheel < ROBOTDEF_MAX_WHEELS) {
                        def->wheel_count = current_wheel + 1;
                        // Extract ID (everything before the colon)
                        char id[ROBOTDEF_MAX_NAME];
                        strncpy(id, trimmed, ROBOTDEF_MAX_NAME - 1);
                        char* colon = strchr(id, ':');
                        if (colon) *colon = '\0';
                        strncpy(def->wheel_assemblies[current_wheel].id, id, ROBOTDEF_MAX_NAME - 1);
                        // Determine left/right from ID
                        def->wheel_assemblies[current_wheel].is_left = (strstr(id, "left") != NULL);
                    }
                } else if (current_wheel >= 0 && current_wheel < ROBOTDEF_MAX_WHEELS) {
                    RobotDefWheelAssembly* wa = &def->wheel_assemblies[current_wheel];
                    if (indent == 4) {
                        if (starts_with(trimmed, "world_position:")) {
                            parse_float_array(trimmed, wa->world_position, 3);
                        } else if (starts_with(trimmed, "spin_axis:")) {
                            parse_float_array(trimmed, wa->spin_axis, 3);
                        } else if (starts_with(trimmed, "outer_diameter_mm:")) {
                            wa->outer_diameter_mm = (float)atof(get_value(trimmed));
                        } else if (starts_with(trimmed, "parts:")) {
                            in_wheel_parts = true;
                        }
                    } else if (indent == 6 && in_wheel_parts) {
                        // Parse "- part: 228-2500-208"
                        if (starts_with(trimmed, "- part:")) {
                            if (wa->part_count < ROBOTDEF_MAX_WHEEL_PARTS) {
                                const char* val = get_value(trimmed);
                                strncpy(wa->part_numbers[wa->part_count], val, 31);
                                wa->part_numbers[wa->part_count][31] = '\0';
                                // Strip c## suffix (LDraw composite parts)
                                char* pn = wa->part_numbers[wa->part_count];
                                size_t len = strlen(pn);
                                if (len > 3 && pn[len-3] == 'c' &&
                                    isdigit((unsigned char)pn[len-2]) &&
                                    isdigit((unsigned char)pn[len-1])) {
                                    pn[len-3] = '\0';
                                }
                                wa->part_count++;
                            }
                        }
                    }
                }
                break;

            default:
                break;
        }
    }

    fclose(f);
    return true;
}

const RobotDefSubmodel* robotdef_get_submodel(const RobotDef* def, const char* name) {
    for (int i = 0; i < def->submodel_count; i++) {
        if (strcmp(def->submodels[i].name, name) == 0) {
            return &def->submodels[i];
        }
    }
    return NULL;
}

void robotdef_print(const RobotDef* def) {
    printf("Robot Definition:\n");
    printf("  Version: %d\n", def->version);
    printf("  Source: %s\n", def->source_file);
    printf("  Main Model: %s\n", def->main_model);
    printf("  Summary: %d wheels, %d motors, %d sensors, brain: %s\n",
           def->total_wheels, def->total_motors, def->total_sensors,
           def->has_brain ? "yes" : "no");

    printf("  Drivetrain:\n");
    const char* type_names[] = {"unknown", "tank", "mecanum", "omni", "ackermann"};
    printf("    Type: %s\n", type_names[def->drivetrain.type]);
    printf("    Left: %s\n", def->drivetrain.left_drive);
    printf("    Right: %s\n", def->drivetrain.right_drive);
    printf("    Rotation Center: [%.1f, %.1f, %.1f] LDU\n",
           def->drivetrain.rotation_center[0],
           def->drivetrain.rotation_center[1],
           def->drivetrain.rotation_center[2]);
    printf("    Rotation Axis: [%.1f, %.1f, %.1f]\n",
           def->drivetrain.rotation_axis[0],
           def->drivetrain.rotation_axis[1],
           def->drivetrain.rotation_axis[2]);
    printf("    Track Width: %.1f LDU\n", def->drivetrain.track_width);

    if (def->motor_count > 0) {
        printf("  Motors:\n");
        for (int i = 0; i < def->motor_count; i++) {
            printf("    - %s (port %d, count %d)\n",
                   def->motors[i].submodel,
                   def->motors[i].port,
                   def->motors[i].count);
        }
    }

    if (def->wheel_count > 0) {
        printf("  Wheel Assemblies:\n");
        for (int i = 0; i < def->wheel_count; i++) {
            const RobotDefWheelAssembly* wa = &def->wheel_assemblies[i];
            printf("    - %s (%s): pos=[%.1f,%.1f,%.1f] axis=[%.2f,%.2f,%.2f] dia=%.1fmm parts=%d\n",
                   wa->id,
                   wa->is_left ? "left" : "right",
                   wa->world_position[0], wa->world_position[1], wa->world_position[2],
                   wa->spin_axis[0], wa->spin_axis[1], wa->spin_axis[2],
                   wa->outer_diameter_mm,
                   wa->part_count);
        }
    }
}
