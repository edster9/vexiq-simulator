"""
VEX IQ Simulator - Python Components
=====================================
Provides Python robot harness for the C++ SDL rendering client.

Components:
- vex_stub: VEX IQ API stubs for running robot code
- iqpython_parser: Parser for .iqpython project files
- ipc_bridge: IPC bridge between C++ client and Python harness
"""

from .vex_stub import *
from .iqpython_parser import parse_iqpython, describe_robot, RobotConfig
