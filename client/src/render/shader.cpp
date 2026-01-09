#include "shader.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static GLuint compile_shader(GLenum type, const char* source) {
    GLuint shader = glCreateShader(type);
    glShaderSource(shader, 1, &source, NULL);
    glCompileShader(shader);

    GLint success;
    glGetShaderiv(shader, GL_COMPILE_STATUS, &success);
    if (!success) {
        char log[512];
        glGetShaderInfoLog(shader, sizeof(log), NULL, log);
        fprintf(stderr, "Shader compilation failed:\n%s\n", log);
        glDeleteShader(shader);
        return 0;
    }

    return shader;
}

bool shader_create(Shader* s, const char* vertex_src, const char* fragment_src) {
    memset(s, 0, sizeof(Shader));

    GLuint vert = compile_shader(GL_VERTEX_SHADER, vertex_src);
    if (!vert) return false;

    GLuint frag = compile_shader(GL_FRAGMENT_SHADER, fragment_src);
    if (!frag) {
        glDeleteShader(vert);
        return false;
    }

    GLuint program = glCreateProgram();
    glAttachShader(program, vert);
    glAttachShader(program, frag);
    glLinkProgram(program);

    GLint success;
    glGetProgramiv(program, GL_LINK_STATUS, &success);
    if (!success) {
        char log[512];
        glGetProgramInfoLog(program, sizeof(log), NULL, log);
        fprintf(stderr, "Shader linking failed:\n%s\n", log);
        glDeleteProgram(program);
        glDeleteShader(vert);
        glDeleteShader(frag);
        return false;
    }

    glDeleteShader(vert);
    glDeleteShader(frag);

    s->program = program;
    s->valid = true;
    return true;
}

static char* read_file(const char* path) {
    FILE* f = fopen(path, "rb");
    if (!f) {
        fprintf(stderr, "Failed to open file: %s\n", path);
        return NULL;
    }

    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);

    char* buffer = (char*)malloc(size + 1);
    if (!buffer) {
        fclose(f);
        return NULL;
    }

    (void)fread(buffer, 1, size, f);
    buffer[size] = '\0';
    fclose(f);

    return buffer;
}

bool shader_load(Shader* s, const char* vertex_path, const char* fragment_path) {
    char* vert_src = read_file(vertex_path);
    if (!vert_src) return false;

    char* frag_src = read_file(fragment_path);
    if (!frag_src) {
        free(vert_src);
        return false;
    }

    bool result = shader_create(s, vert_src, frag_src);

    free(vert_src);
    free(frag_src);
    return result;
}

void shader_destroy(Shader* s) {
    if (s->valid) {
        glDeleteProgram(s->program);
        s->program = 0;
        s->valid = false;
    }
}

void shader_use(Shader* s) {
    glUseProgram(s->program);
}

void shader_set_mat4(Shader* s, const char* name, Mat4* m) {
    GLint loc = glGetUniformLocation(s->program, name);
    glUniformMatrix4fv(loc, 1, GL_FALSE, m->m);
}

void shader_set_vec3(Shader* s, const char* name, Vec3 v) {
    GLint loc = glGetUniformLocation(s->program, name);
    glUniform3f(loc, v.x, v.y, v.z);
}

void shader_set_float(Shader* s, const char* name, float f) {
    GLint loc = glGetUniformLocation(s->program, name);
    glUniform1f(loc, f);
}

void shader_set_int(Shader* s, const char* name, int i) {
    GLint loc = glGetUniformLocation(s->program, name);
    glUniform1i(loc, i);
}
