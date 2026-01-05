"""
VEX IQ Simulator
================
A local simulator for testing VEX IQ robot code without hardware.

Uses Ursina for 3D rendering and will use PyBullet for physics.
"""

from .vex_stub import *
from .iqpython_parser import parse_iqpython, describe_robot, RobotConfig

# Main entry point is now simulator.main (Ursina-based)
# Old pygame-based modules (virtual_controller, harness) are deprecated
