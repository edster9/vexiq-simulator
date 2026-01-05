"""
Minimal Ursina test to verify rendering works.
"""

from ursina import *

app = Ursina()

# Set background
window.color = color.dark_gray

# Simple floor - use flat cube instead of plane (plane ignores color)
# Use built-in color instead of color.rgb()
floor = Entity(
    model='cube',
    color=color.dark_gray,
    scale=(6, 0.01, 6),
    y=-0.005
)

# Simple robot cube
robot = Entity(
    model='cube',
    color=color.red,
    scale=(0.5, 0.3, 0.5),
    position=(0, 0.15, 0)
)

# Grid lines - use built-in color
for i in range(7):
    offset = -3 + i
    Entity(model='cube', scale=(6, 0.01, 0.03), position=(0, 0.01, offset), color=color.gray)
    Entity(model='cube', scale=(0.03, 0.01, 6), position=(offset, 0.01, 0), color=color.gray)

# UI Panel at bottom (25% of screen)
panel_bg = Entity(
    parent=camera.ui,
    model='quad',
    color=color.black,
    scale=(2, 0.25),
    position=(0, -0.375, 0)
)

# Divider line
divider = Entity(
    parent=camera.ui,
    model='quad',
    color=color.gray,
    scale=(2, 0.003),
    position=(0, -0.25, 0)
)

# UI Text
title = Text(text='CONTROLLER', parent=camera.ui, y=-0.28, x=-0.25, scale=1)
ports_title = Text(text='PORTS', parent=camera.ui, y=-0.28, x=0.25, scale=1)

# Simple joystick indicator (circle) - use built-in colors
js_bg = Entity(
    parent=camera.ui,
    model='circle',
    color=color.dark_gray,
    scale=0.07,
    position=(-0.3, -0.38, 0)
)
js_stick = Entity(
    parent=camera.ui,
    model='circle',
    color=color.azure,
    scale=0.025,
    position=(-0.3, -0.38, 0)
)

# Status text
status = Text(text='Test UI - Move mouse to verify interaction', parent=camera.ui, y=-0.47, scale=0.7)

# Camera setup
camera.position = (0, 9, -6)
camera.rotation_x = 50
camera.fov = 60

app.run()
