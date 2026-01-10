/*
 * Collision Detection and Response Implementation
 */

#include "collision.h"
#include <math.h>
#include <string.h>
#include <stdio.h>

void collision_init(CollisionWorld* world, float field_width, float field_depth) {
    memset(world, 0, sizeof(CollisionWorld));

    // Field boundaries (centered at origin)
    world->field.min_x = -field_width / 2.0f;
    world->field.max_x = field_width / 2.0f;
    world->field.min_z = -field_depth / 2.0f;
    world->field.max_z = field_depth / 2.0f;

    printf("[Collision] Initialized field: %.0f x %.0f inches\n", field_width, field_depth);
}

int collision_add_robot(CollisionWorld* world, float x, float z, float radius) {
    if (world->robot_count >= COLLISION_MAX_ROBOTS) {
        fprintf(stderr, "[Collision] Max robots reached\n");
        return -1;
    }

    int idx = world->robot_count++;
    CollisionCircle* c = &world->robots[idx];
    c->x = x;
    c->z = z;
    c->radius = radius;
    c->active = true;
    c->type = COLLISION_BODY_ROBOT;
    c->index = idx;

    printf("[Collision] Added robot %d at (%.1f, %.1f) radius=%.1f\n", idx, x, z, radius);
    return idx;
}

int collision_add_cylinder(CollisionWorld* world, float x, float z, float radius) {
    if (world->cylinder_count >= COLLISION_MAX_CYLINDERS) {
        fprintf(stderr, "[Collision] Max cylinders reached\n");
        return -1;
    }

    int idx = world->cylinder_count++;
    CollisionCircle* c = &world->cylinders[idx];
    c->x = x;
    c->z = z;
    c->radius = radius;
    c->active = true;
    c->type = COLLISION_BODY_CYLINDER;
    c->index = idx;

    printf("[Collision] Added cylinder %d at (%.1f, %.1f) radius=%.1f\n", idx, x, z, radius);
    return idx;
}

void collision_update_robot(CollisionWorld* world, int index, float x, float z) {
    if (index >= 0 && index < world->robot_count) {
        world->robots[index].x = x;
        world->robots[index].z = z;
    }
}

bool collision_point_in_field(const CollisionWorld* world, float x, float z) {
    return x >= world->field.min_x && x <= world->field.max_x &&
           z >= world->field.min_z && z <= world->field.max_z;
}

bool collision_circle_circle(float x1, float z1, float r1, float x2, float z2, float r2) {
    float dx = x2 - x1;
    float dz = z2 - z1;
    float dist_sq = dx * dx + dz * dz;
    float min_dist = r1 + r2;
    return dist_sq < min_dist * min_dist;
}

bool collision_circle_field(const CollisionField* field, float x, float z, float radius) {
    // Check if circle extends outside field boundaries
    return (x - radius < field->min_x) ||
           (x + radius > field->max_x) ||
           (z - radius < field->min_z) ||
           (z + radius > field->max_z);
}

// Push circle back inside field boundaries
static void clamp_circle_to_field(const CollisionField* field, float* x, float* z, float radius) {
    if (*x - radius < field->min_x) *x = field->min_x + radius;
    if (*x + radius > field->max_x) *x = field->max_x - radius;
    if (*z - radius < field->min_z) *z = field->min_z + radius;
    if (*z + radius > field->max_z) *z = field->max_z - radius;
}

// Separate two overlapping circles
// Moves circle1 to resolve the overlap (circle2 is assumed static or will be handled separately)
static void separate_circles(float* x1, float* z1, float r1,
                            float x2, float z2, float r2,
                            bool both_mobile) {
    float dx = *x1 - x2;
    float dz = *z1 - z2;
    float dist = sqrtf(dx * dx + dz * dz);

    if (dist < 0.0001f) {
        // Circles are at same position - push in arbitrary direction
        dx = 1.0f;
        dz = 0.0f;
        dist = 1.0f;
    }

    float overlap = (r1 + r2) - dist;
    if (overlap <= 0) return;  // No overlap

    // Normalize direction
    float nx = dx / dist;
    float nz = dz / dist;

    // Push apart
    if (both_mobile) {
        // Both move half the overlap distance
        *x1 += nx * overlap * 0.5f;
        *z1 += nz * overlap * 0.5f;
    } else {
        // Only circle1 moves (circle2 is static, like a cylinder)
        *x1 += nx * overlap;
        *z1 += nz * overlap;
    }
}

bool collision_resolve_forces(CollisionWorld* world, const float* velocities, CollisionResult* results) {
    bool any_collision = false;

    // Initialize results
    for (int i = 0; i < world->robot_count; i++) {
        results[i].force_x = 0.0f;
        results[i].force_z = 0.0f;
        results[i].torque = 0.0f;
        results[i].hit_wall = false;
        results[i].hit_cylinder = false;
        results[i].hit_robot = false;
    }

    // Check robot-field collisions (walls)
    for (int i = 0; i < world->robot_count; i++) {
        if (!world->robots[i].active) continue;
        CollisionCircle* robot = &world->robots[i];
        CollisionResult* result = &results[i];

        // Get robot velocity for damping
        float vx = velocities ? velocities[i * 2] : 0.0f;
        float vz = velocities ? velocities[i * 2 + 1] : 0.0f;

        // Check each wall and calculate force based on penetration + damping
        float penetration;

        // Left wall (min_x)
        penetration = (world->field.min_x + robot->radius) - robot->x;
        if (penetration > 0) {
            result->force_x += COLLISION_STIFFNESS * penetration;
            // Damping: oppose ALL velocity when in contact (prevents bounce)
            result->force_x -= COLLISION_DAMPING * vx;
            result->hit_wall = true;
            any_collision = true;
        }

        // Right wall (max_x)
        penetration = robot->x - (world->field.max_x - robot->radius);
        if (penetration > 0) {
            result->force_x -= COLLISION_STIFFNESS * penetration;
            // Damping: oppose ALL velocity when in contact
            result->force_x -= COLLISION_DAMPING * vx;
            result->hit_wall = true;
            any_collision = true;
        }

        // Back wall (min_z)
        penetration = (world->field.min_z + robot->radius) - robot->z;
        if (penetration > 0) {
            result->force_z += COLLISION_STIFFNESS * penetration;
            // Damping: oppose ALL velocity when in contact
            result->force_z -= COLLISION_DAMPING * vz;
            result->hit_wall = true;
            any_collision = true;
        }

        // Front wall (max_z)
        penetration = robot->z - (world->field.max_z - robot->radius);
        if (penetration > 0) {
            result->force_z -= COLLISION_STIFFNESS * penetration;
            // Damping: oppose ALL velocity when in contact
            result->force_z -= COLLISION_DAMPING * vz;
            result->hit_wall = true;
            any_collision = true;
        }
    }

    // Check robot-cylinder collisions
    for (int i = 0; i < world->robot_count; i++) {
        if (!world->robots[i].active) continue;
        CollisionCircle* robot = &world->robots[i];
        CollisionResult* result = &results[i];

        float vx = velocities ? velocities[i * 2] : 0.0f;
        float vz = velocities ? velocities[i * 2 + 1] : 0.0f;

        for (int j = 0; j < world->cylinder_count; j++) {
            if (!world->cylinders[j].active) continue;
            CollisionCircle* cyl = &world->cylinders[j];

            float dx = robot->x - cyl->x;
            float dz = robot->z - cyl->z;
            float dist = sqrtf(dx * dx + dz * dz);
            float min_dist = robot->radius + cyl->radius;

            if (dist < min_dist && dist > 0.0001f) {
                float penetration = min_dist - dist;
                float nx = dx / dist;  // Normal direction (away from cylinder)
                float nz = dz / dist;

                // Spring force
                result->force_x += COLLISION_STIFFNESS * penetration * nx;
                result->force_z += COLLISION_STIFFNESS * penetration * nz;

                // Damping: oppose ALL velocity along collision normal (prevents bounce)
                float vel_normal = vx * nx + vz * nz;
                result->force_x -= COLLISION_DAMPING * vel_normal * nx;
                result->force_z -= COLLISION_DAMPING * vel_normal * nz;

                result->hit_cylinder = true;
                any_collision = true;
            }
        }
    }

    // Check robot-robot collisions
    for (int i = 0; i < world->robot_count; i++) {
        if (!world->robots[i].active) continue;
        CollisionCircle* robot1 = &world->robots[i];
        CollisionResult* result1 = &results[i];

        float vx1 = velocities ? velocities[i * 2] : 0.0f;
        float vz1 = velocities ? velocities[i * 2 + 1] : 0.0f;

        for (int j = i + 1; j < world->robot_count; j++) {
            if (!world->robots[j].active) continue;
            CollisionCircle* robot2 = &world->robots[j];
            CollisionResult* result2 = &results[j];

            float vx2 = velocities ? velocities[j * 2] : 0.0f;
            float vz2 = velocities ? velocities[j * 2 + 1] : 0.0f;

            float dx = robot1->x - robot2->x;
            float dz = robot1->z - robot2->z;
            float dist = sqrtf(dx * dx + dz * dz);
            float min_dist = robot1->radius + robot2->radius;

            if (dist < min_dist && dist > 0.0001f) {
                float penetration = min_dist - dist;
                float nx = dx / dist;  // Normal from robot2 to robot1
                float nz = dz / dist;

                // Spring force (equal and opposite)
                float spring_force = COLLISION_STIFFNESS * penetration;
                result1->force_x += spring_force * nx;
                result1->force_z += spring_force * nz;
                result2->force_x -= spring_force * nx;
                result2->force_z -= spring_force * nz;

                // Damping: oppose ALL relative velocity along collision normal (prevents bounce)
                float rel_vx = vx1 - vx2;
                float rel_vz = vz1 - vz2;
                float rel_vel_normal = rel_vx * nx + rel_vz * nz;
                float damping_force = -COLLISION_DAMPING * rel_vel_normal;
                result1->force_x += damping_force * nx;
                result1->force_z += damping_force * nz;
                result2->force_x -= damping_force * nx;
                result2->force_z -= damping_force * nz;

                result1->hit_robot = true;
                result2->hit_robot = true;
                any_collision = true;
            }
        }
    }

    return any_collision;
}

void collision_clamp_positions(CollisionWorld* world, float* out_positions) {
    // Hard clamp robot positions to prevent deep penetration
    // This is a safety net for physics stability

    for (int i = 0; i < world->robot_count; i++) {
        if (!world->robots[i].active) continue;
        CollisionCircle* robot = &world->robots[i];

        float x = robot->x;
        float z = robot->z;

        // Clamp to field boundaries (with max penetration tolerance)
        float min_x = world->field.min_x + robot->radius - COLLISION_MAX_PENETRATION;
        float max_x = world->field.max_x - robot->radius + COLLISION_MAX_PENETRATION;
        float min_z = world->field.min_z + robot->radius - COLLISION_MAX_PENETRATION;
        float max_z = world->field.max_z - robot->radius + COLLISION_MAX_PENETRATION;

        if (x < min_x) x = world->field.min_x + robot->radius;
        if (x > max_x) x = world->field.max_x - robot->radius;
        if (z < min_z) z = world->field.min_z + robot->radius;
        if (z > max_z) z = world->field.max_z - robot->radius;

        // Clamp against cylinders
        for (int j = 0; j < world->cylinder_count; j++) {
            if (!world->cylinders[j].active) continue;
            CollisionCircle* cyl = &world->cylinders[j];

            float dx = x - cyl->x;
            float dz = z - cyl->z;
            float dist = sqrtf(dx * dx + dz * dz);
            float min_dist = robot->radius + cyl->radius - COLLISION_MAX_PENETRATION;

            if (dist < min_dist && dist > 0.0001f) {
                // Push robot out to minimum distance
                float target_dist = robot->radius + cyl->radius;
                float nx = dx / dist;
                float nz = dz / dist;
                x = cyl->x + nx * target_dist;
                z = cyl->z + nz * target_dist;
            }
        }

        // Clamp against other robots
        for (int j = 0; j < world->robot_count; j++) {
            if (i == j || !world->robots[j].active) continue;
            CollisionCircle* other = &world->robots[j];

            float dx = x - other->x;
            float dz = z - other->z;
            float dist = sqrtf(dx * dx + dz * dz);
            float min_dist = robot->radius + other->radius - COLLISION_MAX_PENETRATION;

            if (dist < min_dist && dist > 0.0001f) {
                // Push both robots apart equally
                float target_dist = robot->radius + other->radius;
                float overlap = target_dist - dist;
                float nx = dx / dist;
                float nz = dz / dist;
                x += nx * overlap * 0.5f;
                z += nz * overlap * 0.5f;
            }
        }

        out_positions[i * 2] = x;
        out_positions[i * 2 + 1] = z;
    }
}

bool collision_resolve(CollisionWorld* world, float* out_robot_positions) {
    bool any_collision = false;

    // Multiple iterations for stable resolution
    for (int iter = 0; iter < 4; iter++) {
        // Check robot-field collisions (walls)
        for (int i = 0; i < world->robot_count; i++) {
            if (!world->robots[i].active) continue;

            CollisionCircle* robot = &world->robots[i];
            if (collision_circle_field(&world->field, robot->x, robot->z, robot->radius)) {
                clamp_circle_to_field(&world->field, &robot->x, &robot->z, robot->radius);
                any_collision = true;
            }
        }

        // Check robot-cylinder collisions
        for (int i = 0; i < world->robot_count; i++) {
            if (!world->robots[i].active) continue;
            CollisionCircle* robot = &world->robots[i];

            for (int j = 0; j < world->cylinder_count; j++) {
                if (!world->cylinders[j].active) continue;
                CollisionCircle* cyl = &world->cylinders[j];

                if (collision_circle_circle(robot->x, robot->z, robot->radius,
                                           cyl->x, cyl->z, cyl->radius)) {
                    // Robot moves, cylinder stays (static obstacle)
                    separate_circles(&robot->x, &robot->z, robot->radius,
                                   cyl->x, cyl->z, cyl->radius, false);
                    any_collision = true;
                }
            }
        }

        // Check robot-robot collisions
        for (int i = 0; i < world->robot_count; i++) {
            if (!world->robots[i].active) continue;
            CollisionCircle* robot1 = &world->robots[i];

            for (int j = i + 1; j < world->robot_count; j++) {
                if (!world->robots[j].active) continue;
                CollisionCircle* robot2 = &world->robots[j];

                if (collision_circle_circle(robot1->x, robot1->z, robot1->radius,
                                           robot2->x, robot2->z, robot2->radius)) {
                    // Both robots move equally
                    float x1 = robot1->x, z1 = robot1->z;
                    float x2 = robot2->x, z2 = robot2->z;

                    // Separate robot1 from robot2
                    separate_circles(&x1, &z1, robot1->radius,
                                   x2, z2, robot2->radius, true);
                    // Separate robot2 from robot1 (with updated robot1 position)
                    separate_circles(&x2, &z2, robot2->radius,
                                   x1, z1, robot1->radius, true);

                    robot1->x = x1;
                    robot1->z = z1;
                    robot2->x = x2;
                    robot2->z = z2;

                    any_collision = true;
                }
            }
        }
    }

    // Copy final positions to output array
    if (out_robot_positions) {
        for (int i = 0; i < world->robot_count; i++) {
            out_robot_positions[i * 2] = world->robots[i].x;
            out_robot_positions[i * 2 + 1] = world->robots[i].z;
        }
    }

    return any_collision;
}
