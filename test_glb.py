#!/usr/bin/env python3
"""Test loading GLB model in Ursina."""

from ursina import *

app = Ursina()

# Load the Brain GLB model
brain = Entity(
    model='models/electronics/glb/228-2540.glb',
    scale=0.01,  # STEP files are in mm, scale down
    position=(0, 0, 0),
    color=color.dark_gray,  # Apply color directly
)

# Add ground plane for reference
ground = Entity(
    model='plane',
    scale=10,
    color=color.light_gray,
    y=-0.5,
)

# Shader for GLB materials
from ursina.shaders import lit_with_shadows_shader
brain.shader = lit_with_shadows_shader

# Lighting - this exact setup worked before
sun = DirectionalLight()
sun.look_at(Vec3(1, -1, 1))

# Camera controls
EditorCamera()

# Instructions
Text(
    text='Mouse: Rotate | Scroll: Zoom | WASD: Move',
    position=(-0.85, 0.45),
    scale=1.5,
)

app.run()
