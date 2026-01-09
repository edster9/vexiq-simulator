cmake_minimum_required(VERSION 3.16)
project(vexiq_sim CXX C)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_C_STANDARD 11)

# Compiler flags
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra")
set(CMAKE_CXX_FLAGS_DEBUG "-g -O0")
set(CMAKE_CXX_FLAGS_RELEASE "-O2")

# Find required packages
find_package(PkgConfig REQUIRED)
pkg_check_modules(SDL2 REQUIRED sdl2)
find_package(OpenGL REQUIRED)
find_package(GLEW REQUIRED)

# Source files
set(SOURCES
    src/main.cpp
    src/platform/platform.cpp
    src/math/vec3.cpp
    src/math/mat4.cpp
    src/render/camera.cpp
    src/render/shader.cpp
    src/render/floor.cpp
    src/render/glb_loader.cpp
    src/render/mesh.cpp
    src/render/mpd_loader.cpp
    src/render/text.cpp
    src/render/debug.cpp
    src/scene/scene.cpp
    src/physics/drivetrain.cpp
    src/ipc/subprocess.cpp
    src/ipc/gamepad.cpp
    src/ipc/python_bridge.cpp
)

# Executable
add_executable(vexiq_sim ${SOURCES})

# Include directories
target_include_directories(vexiq_sim PRIVATE
    ${CMAKE_SOURCE_DIR}/src
    ${SDL2_INCLUDE_DIRS}
    ${OPENGL_INCLUDE_DIRS}
    ${GLEW_INCLUDE_DIRS}
)

# Link libraries
target_link_libraries(vexiq_sim
    ${SDL2_LIBRARIES}
    ${OPENGL_LIBRARIES}
    GLEW::GLEW
    m
)
