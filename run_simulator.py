#!/usr/bin/env python3
"""
Run the VEX IQ Simulator
========================
Quick launcher for the simulator.

Usage:
    python run_simulator.py                    # Auto-detect .iqpython file
    python run_simulator.py myrobot.iqpython   # Specify file
"""

import sys
from pathlib import Path

# Add simulator to path
sys.path.insert(0, str(Path(__file__).parent / "simulator"))

from harness import main

if __name__ == "__main__":
    main()
