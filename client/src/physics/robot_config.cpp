/*
 * Robot Configuration Loader Implementation
 *
 * Parses YAML-like .config files to extract motor port assignments.
 * Specifically looks for motors with mechanism: drivetrain.left_wheels
 * and drivetrain.right_wheels
 */

#include "robot_config.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

void robot_config_init(RobotConfig* config) {
    config->left_motor_port = 0;
    config->right_motor_port = 0;
}

// Trim leading/trailing whitespace
static char* trim(char* str) {
    while (isspace((unsigned char)*str)) str++;
    if (*str == 0) return str;
    char* end = str + strlen(str) - 1;
    while (end > str && isspace((unsigned char)*end)) end--;
    end[1] = '\0';
    return str;
}

// Get indentation level (number of leading spaces)
static int get_indent(const char* line) {
    int indent = 0;
    while (*line == ' ') {
        indent++;
        line++;
    }
    return indent;
}

// Parse "key: value" and return pointer to value
static const char* parse_key_value(const char* line, char* key_out, size_t key_size) {
    const char* colon = strchr(line, ':');
    if (!colon) return NULL;

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

bool robot_config_load(const char* path, RobotConfig* config) {
    FILE* file = fopen(path, "r");
    if (!file) {
        return false;
    }

    robot_config_init(config);

    char line[512];
    bool in_motors_section = false;
    char current_motor_name[128] = {0};
    int current_port = 0;

    while (fgets(line, sizeof(line), file)) {
        int indent = get_indent(line);
        char* trimmed = trim(line);

        // Skip empty lines and comments
        if (trimmed[0] == '\0' || trimmed[0] == '#') {
            continue;
        }

        char key[128];
        const char* value = parse_key_value(trimmed, key, sizeof(key));
        if (!value) continue;

        // Check for motors section
        if (indent == 0 && strcmp(key, "motors") == 0) {
            in_motors_section = true;
            current_motor_name[0] = '\0';
            continue;
        }

        // Exit motors section on other top-level keys
        if (indent == 0) {
            in_motors_section = false;
            continue;
        }

        if (!in_motors_section) continue;

        // Motor name (indent 2)
        if (indent == 2 && value[0] == '\0') {
            // This is a motor name key with no value (e.g., "LeftSideDrive_1:")
            strncpy(current_motor_name, key, sizeof(current_motor_name) - 1);
            current_port = 0;
            continue;
        }

        // Motor properties (indent 4)
        if (indent == 4 && current_motor_name[0] != '\0') {
            if (strcmp(key, "port") == 0) {
                current_port = atoi(value);
            }
            else if (strcmp(key, "mechanism") == 0) {
                // Check if this is a drivetrain motor
                if (strstr(value, "drivetrain.left_wheels") || strstr(value, "drivetrain.left")) {
                    config->left_motor_port = current_port;
                }
                else if (strstr(value, "drivetrain.right_wheels") || strstr(value, "drivetrain.right")) {
                    config->right_motor_port = current_port;
                }
            }
        }
    }

    fclose(file);

    if (config->left_motor_port > 0 || config->right_motor_port > 0) {
        printf("  Config: left_motor=port%d, right_motor=port%d\n",
               config->left_motor_port, config->right_motor_port);
    }

    return true;
}
