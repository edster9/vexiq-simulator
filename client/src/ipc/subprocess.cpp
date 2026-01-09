/*
 * Subprocess management implementation
 * Cross-platform (Windows/POSIX) subprocess spawning with pipes
 */

#include "subprocess.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#ifdef _WIN32
// Windows implementation
#include <io.h>

bool subprocess_spawn(Subprocess* proc, const char* command, const char* working_dir) {
    memset(proc, 0, sizeof(Subprocess));

    SECURITY_ATTRIBUTES sa;
    sa.nLength = sizeof(SECURITY_ATTRIBUTES);
    sa.bInheritHandle = TRUE;
    sa.lpSecurityDescriptor = NULL;

    HANDLE stdin_read, stdin_write;
    HANDLE stdout_read, stdout_write;

    // Create pipes for stdin
    if (!CreatePipe(&stdin_read, &stdin_write, &sa, 0)) {
        fprintf(stderr, "CreatePipe stdin failed\n");
        return false;
    }
    SetHandleInformation(stdin_write, HANDLE_FLAG_INHERIT, 0);

    // Create pipes for stdout
    if (!CreatePipe(&stdout_read, &stdout_write, &sa, 0)) {
        fprintf(stderr, "CreatePipe stdout failed\n");
        CloseHandle(stdin_read);
        CloseHandle(stdin_write);
        return false;
    }
    SetHandleInformation(stdout_read, HANDLE_FLAG_INHERIT, 0);

    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    memset(&si, 0, sizeof(si));
    memset(&pi, 0, sizeof(pi));

    si.cb = sizeof(STARTUPINFOA);
    si.hStdInput = stdin_read;
    si.hStdOutput = stdout_write;
    si.hStdError = GetStdHandle(STD_ERROR_HANDLE);
    si.dwFlags |= STARTF_USESTDHANDLES;

    // Create the process
    char* cmd_copy = _strdup(command);  // CreateProcess may modify the string
    if (!CreateProcessA(
            NULL,
            cmd_copy,
            NULL,
            NULL,
            TRUE,
            0,
            NULL,
            working_dir,
            &si,
            &pi)) {
        fprintf(stderr, "CreateProcess failed: %lu\n", GetLastError());
        free(cmd_copy);
        CloseHandle(stdin_read);
        CloseHandle(stdin_write);
        CloseHandle(stdout_read);
        CloseHandle(stdout_write);
        return false;
    }
    free(cmd_copy);

    // Close handles we don't need
    CloseHandle(stdin_read);
    CloseHandle(stdout_write);

    proc->process = pi.hProcess;
    proc->thread = pi.hThread;
    proc->stdin_write = stdin_write;
    proc->stdout_read = stdout_read;
    proc->running = true;

    return true;
}

int subprocess_write(Subprocess* proc, const char* data, size_t len) {
    if (!proc->running) return -1;

    DWORD written;
    if (!WriteFile(proc->stdin_write, data, (DWORD)len, &written, NULL)) {
        return -1;
    }
    return (int)written;
}

bool subprocess_write_str(Subprocess* proc, const char* str) {
    size_t len = strlen(str);
    return subprocess_write(proc, str, len) == (int)len;
}

int subprocess_read(Subprocess* proc, char* buffer, size_t buffer_size) {
    if (!proc->running) return -1;

    DWORD available;
    if (!PeekNamedPipe(proc->stdout_read, NULL, 0, NULL, &available, NULL)) {
        return -1;
    }

    if (available == 0) return 0;

    DWORD to_read = (available < buffer_size) ? available : (DWORD)buffer_size;
    DWORD read_bytes;
    if (!ReadFile(proc->stdout_read, buffer, to_read, &read_bytes, NULL)) {
        return -1;
    }

    return (int)read_bytes;
}

bool subprocess_read_line(Subprocess* proc, char* buffer, size_t buffer_size) {
    if (!proc->running || buffer_size == 0) return false;

    size_t pos = 0;
    while (pos < buffer_size - 1) {
        DWORD read_bytes;
        char c;
        if (!ReadFile(proc->stdout_read, &c, 1, &read_bytes, NULL) || read_bytes == 0) {
            if (pos > 0) {
                buffer[pos] = '\0';
                return true;
            }
            return false;
        }

        if (c == '\n') {
            buffer[pos] = '\0';
            return true;
        }
        if (c != '\r') {
            buffer[pos++] = c;
        }
    }

    buffer[pos] = '\0';
    return true;
}

bool subprocess_is_running(Subprocess* proc) {
    if (!proc->running) return false;

    DWORD exit_code;
    if (GetExitCodeProcess(proc->process, &exit_code)) {
        if (exit_code != STILL_ACTIVE) {
            proc->running = false;
            return false;
        }
    }
    return true;
}

void subprocess_terminate(Subprocess* proc) {
    if (proc->running) {
        TerminateProcess(proc->process, 1);
        proc->running = false;
    }
}

void subprocess_destroy(Subprocess* proc) {
    subprocess_terminate(proc);
    if (proc->stdin_write) CloseHandle(proc->stdin_write);
    if (proc->stdout_read) CloseHandle(proc->stdout_read);
    if (proc->process) CloseHandle(proc->process);
    if (proc->thread) CloseHandle(proc->thread);
    memset(proc, 0, sizeof(Subprocess));
}

#else
// POSIX implementation (Linux, macOS)
#include <unistd.h>
#include <sys/wait.h>
#include <signal.h>
#include <fcntl.h>
#include <errno.h>

bool subprocess_spawn(Subprocess* proc, const char* command, const char* working_dir) {
    memset(proc, 0, sizeof(Subprocess));

    int stdin_pipe[2];   // [0] = read end (child), [1] = write end (parent)
    int stdout_pipe[2];  // [0] = read end (parent), [1] = write end (child)

    if (pipe(stdin_pipe) == -1) {
        perror("pipe stdin");
        return false;
    }

    if (pipe(stdout_pipe) == -1) {
        perror("pipe stdout");
        close(stdin_pipe[0]);
        close(stdin_pipe[1]);
        return false;
    }

    pid_t pid = fork();
    if (pid == -1) {
        perror("fork");
        close(stdin_pipe[0]);
        close(stdin_pipe[1]);
        close(stdout_pipe[0]);
        close(stdout_pipe[1]);
        return false;
    }

    if (pid == 0) {
        // Child process
        close(stdin_pipe[1]);   // Close write end of stdin pipe
        close(stdout_pipe[0]);  // Close read end of stdout pipe

        dup2(stdin_pipe[0], STDIN_FILENO);
        dup2(stdout_pipe[1], STDOUT_FILENO);

        close(stdin_pipe[0]);
        close(stdout_pipe[1]);

        if (working_dir) {
            if (chdir(working_dir) == -1) {
                perror("chdir");
                _exit(1);
            }
        }

        // Execute command via shell
        execl("/bin/sh", "sh", "-c", command, NULL);
        perror("execl");
        _exit(1);
    }

    // Parent process
    close(stdin_pipe[0]);   // Close read end of stdin pipe
    close(stdout_pipe[1]);  // Close write end of stdout pipe

    // Set stdout to non-blocking for subprocess_read
    int flags = fcntl(stdout_pipe[0], F_GETFL, 0);
    fcntl(stdout_pipe[0], F_SETFL, flags | O_NONBLOCK);

    proc->pid = pid;
    proc->stdin_fd = stdin_pipe[1];
    proc->stdout_fd = stdout_pipe[0];
    proc->running = true;

    return true;
}

int subprocess_write(Subprocess* proc, const char* data, size_t len) {
    if (!proc->running) return -1;
    ssize_t written = write(proc->stdin_fd, data, len);
    return (int)written;
}

bool subprocess_write_str(Subprocess* proc, const char* str) {
    size_t len = strlen(str);
    return subprocess_write(proc, str, len) == (int)len;
}

int subprocess_read(Subprocess* proc, char* buffer, size_t buffer_size) {
    if (!proc->running) return -1;

    ssize_t bytes = read(proc->stdout_fd, buffer, buffer_size);
    if (bytes == -1) {
        if (errno == EAGAIN || errno == EWOULDBLOCK) {
            return 0;  // No data available
        }
        return -1;
    }
    return (int)bytes;
}

bool subprocess_read_line(Subprocess* proc, char* buffer, size_t buffer_size) {
    if (!proc->running || buffer_size == 0) return false;

    // Temporarily set to blocking for line read
    int flags = fcntl(proc->stdout_fd, F_GETFL, 0);
    fcntl(proc->stdout_fd, F_SETFL, flags & ~O_NONBLOCK);

    size_t pos = 0;
    while (pos < buffer_size - 1) {
        char c;
        ssize_t bytes = read(proc->stdout_fd, &c, 1);
        if (bytes <= 0) {
            // Restore non-blocking
            fcntl(proc->stdout_fd, F_SETFL, flags);
            if (pos > 0) {
                buffer[pos] = '\0';
                return true;
            }
            return false;
        }

        if (c == '\n') {
            buffer[pos] = '\0';
            fcntl(proc->stdout_fd, F_SETFL, flags);
            return true;
        }
        if (c != '\r') {
            buffer[pos++] = c;
        }
    }

    buffer[pos] = '\0';
    fcntl(proc->stdout_fd, F_SETFL, flags);
    return true;
}

bool subprocess_is_running(Subprocess* proc) {
    if (!proc->running) return false;

    int status;
    pid_t result = waitpid(proc->pid, &status, WNOHANG);
    if (result == proc->pid) {
        proc->running = false;
        return false;
    }
    return true;
}

void subprocess_terminate(Subprocess* proc) {
    if (proc->running) {
        kill(proc->pid, SIGTERM);
        usleep(100000);  // 100ms grace period
        kill(proc->pid, SIGKILL);
        waitpid(proc->pid, NULL, 0);
        proc->running = false;
    }
}

void subprocess_destroy(Subprocess* proc) {
    subprocess_terminate(proc);
    if (proc->stdin_fd > 0) close(proc->stdin_fd);
    if (proc->stdout_fd > 0) close(proc->stdout_fd);
    memset(proc, 0, sizeof(Subprocess));
}

#endif
