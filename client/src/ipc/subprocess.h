/*
 * Subprocess management for Python IPC
 * Cross-platform subprocess spawning with pipe communication
 */

#ifndef SUBPROCESS_H
#define SUBPROCESS_H

#include <stdbool.h>
#include <stddef.h>

#ifdef _WIN32
#include <windows.h>
#else
#include <sys/types.h>
#endif

typedef struct Subprocess {
    bool running;

#ifdef _WIN32
    HANDLE process;
    HANDLE thread;
    HANDLE stdin_write;
    HANDLE stdout_read;
#else
    pid_t pid;
    int stdin_fd;   // Write to child's stdin
    int stdout_fd;  // Read from child's stdout
#endif
} Subprocess;

// Spawn a subprocess with piped stdin/stdout
// command: full command to execute (e.g., "python3 ipc_bridge.py")
// working_dir: working directory for the subprocess (can be NULL)
bool subprocess_spawn(Subprocess* proc, const char* command, const char* working_dir);

// Write data to subprocess stdin
// Returns number of bytes written, or -1 on error
int subprocess_write(Subprocess* proc, const char* data, size_t len);

// Write a null-terminated string to subprocess stdin
bool subprocess_write_str(Subprocess* proc, const char* str);

// Read available data from subprocess stdout (non-blocking)
// Returns number of bytes read, 0 if no data available, -1 on error
int subprocess_read(Subprocess* proc, char* buffer, size_t buffer_size);

// Read a line from subprocess stdout (blocks until newline or EOF)
// Returns true if a line was read, false on error/EOF
bool subprocess_read_line(Subprocess* proc, char* buffer, size_t buffer_size);

// Check if subprocess is still running
bool subprocess_is_running(Subprocess* proc);

// Terminate subprocess
void subprocess_terminate(Subprocess* proc);

// Cleanup subprocess resources
void subprocess_destroy(Subprocess* proc);

#endif // SUBPROCESS_H
