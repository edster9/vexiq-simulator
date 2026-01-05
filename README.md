# VEX IQ Python Simulator

A local simulator for testing VEX IQ 2nd Generation robot code without physical hardware. Supports USB gamepad input and provides real-time visualization of motors and pneumatics.

## Features

- **Load VEXcode IQ Projects**: Parse and execute `.iqpython` files directly
- **Virtual Controller**: On-screen joysticks and buttons with mouse support
- **USB Gamepad Support**: Xbox 360/One controller mapping to VEX IQ controller
- **Motor Visualization**: Real-time display of motor velocity and direction for all 12 ports
- **Pneumatic Indicators**: Visual feedback for pneumatic cylinder states
- **Drive Mode Support**: All 6 VEXcode IQ drive modes (split, splitRight, tank, arcadeL, arcadeR, none)

## Requirements

- Python 3.10+
- pygame

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/vexiq-simulator.git
cd vexiq-simulator

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Running the Simulator

```bash
# Run with a specific .iqpython file
python simulator/harness.py your_robot.iqpython

# Or run without arguments to auto-detect .iqpython files
python simulator/harness.py
```

### Controller Mapping (Xbox 360 to VEX IQ)

| Xbox Button | VEX IQ Button | Typical Use |
|-------------|---------------|-------------|
| Left Stick Y | Axis A | Drive forward/back |
| Left Stick X | Axis B | (varies by mode) |
| Right Stick X | Axis C | Turn left/right |
| Right Stick Y | Axis D | (varies by mode) |
| Y | E-Up | Arm up |
| X | E-Down | Arm down |
| LB | L-Up | Secondary arm up |
| LT | L-Down | Secondary arm down |
| RB | R-Up | Claw open |
| RT | R-Down | Claw close |
| B | F-Up | Auxiliary 1 |
| A | F-Down | Auxiliary 2 |

### VEX IQ Drive Modes

| Mode | Name | Left Motor | Right Motor |
|------|------|------------|-------------|
| 1 | split | axisA + axisC | axisA - axisC |
| 2 | splitRight | axisD + axisB | axisD - axisB |
| 3 | tank | axisA | axisD |
| 4 | none | (disabled) | (disabled) |
| 5 | arcadeL | axisA + axisB | axisA - axisB |
| 6 | arcadeR | axisD + axisC | axisD - axisC |

## Project Structure

```
vexiq-simulator/
├── simulator/
│   ├── harness.py           # Main entry point
│   ├── vex_stub.py          # VEX IQ API stub implementation
│   ├── virtual_controller.py # PyGame GUI
│   └── iqpython_parser.py   # .iqpython file parser
├── docs/
│   └── WSL2_GAMEPAD_SETUP.md # Detailed WSL2 gamepad guide
├── requirements.txt
├── LICENSE
├── README.md
└── *.iqpython               # Your robot code (not tracked in git)
```

## Getting .iqpython Files

1. Open [VEXcode IQ](https://codeiq.vex.com/) in your browser
2. Create or open your robot project
3. Click **File > Save to your device**
4. Save the `.iqpython` file to this project directory
5. Run the simulator with your file

## WSL2 Gamepad Support

If running in WSL2, USB gamepads require additional setup:

```powershell
# Windows PowerShell (Admin)
usbipd list                              # Find your controller's BUSID
usbipd bind --busid <BUSID>              # Share device (one-time)
usbipd attach --wsl --busid <BUSID>      # Attach to WSL
```

**Note:** The default WSL2 kernel lacks joystick drivers. You'll need to build a custom kernel.

See **[WSL2 Gamepad Setup Guide](docs/WSL2_GAMEPAD_SETUP.md)** for complete instructions including:
- Installing usbipd-win
- Building a custom WSL2 kernel with Xbox controller support
- Troubleshooting common issues

## Supported VEX IQ API

The simulator supports a subset of the VEX IQ Python API:

- **Motor**: `spin()`, `stop()`, `set_velocity()`, `set_stopping()`
- **MotorGroup**: Same as Motor, applied to multiple motors
- **Controller**: All axes (A, B, C, D) and buttons (L, R, E, F Up/Down)
- **Pneumatic**: `extend()`, `retract()`, `pump_on()`, `pump_off()`
- **Brain**: `screen.print()`, `screen.clear_screen()`, `timer`
- **Inertial**: `calibrate()`, `is_calibrating()`
- **SmartDrive/Drivetrain**: Basic configuration parsing

## Limitations

- No physics simulation (motors respond instantly)
- No sensor simulation (distance, color, etc.)
- No autonomous path visualization
- Simplified timing (uses system sleep)

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This project is not affiliated with, endorsed by, or sponsored by VEX Robotics, Inc. or Innovation First International, Inc.

**VEX**, **VEX IQ**, **VEXcode**, and related trademarks are the property of Innovation First International, Inc. and/or VEX Robotics, Inc.

This simulator is an independent, unofficial tool created for educational purposes to help students learn and test VEX IQ robot code without requiring physical hardware. For official VEX IQ documentation and tools, please visit [vexrobotics.com](https://www.vexrobotics.com/).