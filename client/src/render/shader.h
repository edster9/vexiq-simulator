#ifndef SHADER_H
#define SHADER_H

#include <stdbool.h>
#include <GL/glew.h>
#include "../math/mat4.h"
#include "../math/vec3.h"

typedef struct Shader {
    GLuint program;
    bool valid;
} Shader;

// Create shader from source strings
bool shader_create(Shader* s, const char* vertex_src, const char* fragment_src);

// Create shader from files
bool shader_load(Shader* s, const char* vertex_path, const char* fragment_path);

// Cleanup
void shader_destroy(Shader* s);

// Use shader
void shader_use(Shader* s);

// Uniform setters
void shader_set_mat4(Shader* s, const char* name, Mat4* m);
void shader_set_vec3(Shader* s, const char* name, Vec3 v);
void shader_set_float(Shader* s, const char* name, float f);
void shader_set_int(Shader* s, const char* name, int i);

#endif // SHADER_H
