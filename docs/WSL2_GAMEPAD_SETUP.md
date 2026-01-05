# WSL2 Gamepad Setup Guide

This guide explains how to use a USB gamepad (Xbox 360/One controller) with the VEX IQ Simulator running in WSL2.

## Overview

WSL2 doesn't natively support USB devices. To use a gamepad, you need to:

1. Install usbipd-win on Windows to share USB devices
2. Build a custom WSL2 kernel with joystick drivers
3. Attach the gamepad to WSL2

## Prerequisites

- Windows 10 (build 19041+) or Windows 11
- WSL2 with Ubuntu or similar distro
- Administrator access on Windows
- Xbox 360 or Xbox One controller (wired or wireless with adapter)

## Step 1: Install usbipd-win on Windows

Open PowerShell as Administrator and run:

```powershell
winget install usbipd
```

Or download from: https://github.com/dorssel/usbipd-win/releases

## Step 2: Install USB/IP Tools in WSL2

In your WSL2 terminal:

```bash
sudo apt update
sudo apt install linux-tools-generic hwdata
sudo update-alternatives --install /usr/local/bin/usbip usbip /usr/lib/linux-tools/*-generic/usbip 20
```

## Step 3: Build Custom WSL2 Kernel (Required for Joystick Support)

The default WSL2 kernel doesn't include joystick drivers. You need to build a custom kernel.

### 3.1 Install Build Dependencies

```bash
sudo apt update
sudo apt install build-essential flex bison libssl-dev libelf-dev \
    libncurses-dev autoconf libudev-dev libtool dwarves
```

### 3.2 Clone and Configure Kernel

```bash
# Clone the WSL2 kernel source
cd ~
git clone --depth 1 https://github.com/microsoft/WSL2-Linux-Kernel.git wsl-kernel
cd wsl-kernel

# Copy the current config
cp Microsoft/config-wsl .config

# Enable joystick modules
cat >> .config << 'EOF'
CONFIG_INPUT_JOYSTICK=y
CONFIG_INPUT_JOYDEV=y
CONFIG_JOYSTICK_XPAD=y
CONFIG_JOYSTICK_XPAD_FF=y
CONFIG_JOYSTICK_XPAD_LEDS=y
CONFIG_HID_MICROSOFT=y
CONFIG_INPUT_FF_MEMLESS=y
EOF

# Update config
make olddefconfig
```

### 3.3 Build the Kernel

```bash
# Build (uses all CPU cores, takes 10-30 minutes)
make -j$(nproc)

# Copy kernel to Windows
cp arch/x86/boot/bzImage /mnt/c/Users/YOUR_USERNAME/wsl-kernel
```

Replace `YOUR_USERNAME` with your Windows username.

### 3.4 Configure WSL to Use Custom Kernel

Create or edit `C:\Users\YOUR_USERNAME\.wslconfig`:

```ini
[wsl2]
kernel=C:\\Users\\YOUR_USERNAME\\wsl-kernel
```

### 3.5 Restart WSL

In PowerShell:

```powershell
wsl --shutdown
```

Then reopen your WSL terminal.

## Step 4: Using usbipd to Share the Gamepad

### 4.1 List USB Devices (Windows PowerShell as Admin)

```powershell
usbipd list
```

Look for your Xbox controller. Example output:

```
BUSID  VID:PID    DEVICE                          STATE
1-9    045e:028e  Xbox 360 Controller for Windows Not shared
```

### 4.2 Bind the Device (One-time Setup)

```powershell
usbipd bind --busid 1-9
```

Replace `1-9` with your controller's BUSID.

### 4.3 Attach to WSL

```powershell
usbipd attach --wsl --busid 1-9
```

### 4.4 Verify in WSL

```bash
# Check if joystick device exists
ls -la /dev/input/js*

# Should show something like:
# crw-rw-r-- 1 root input 13, 0 Jan  4 12:00 /dev/input/js0
```

## Step 5: Add User to Input Group

```bash
sudo usermod -aG input $USER
```

Log out and back in for this to take effect.

## Step 6: Test the Gamepad

```bash
# Install joystick tools
sudo apt install joystick

# Test the gamepad
jstest /dev/input/js0
```

Move the sticks and press buttons - you should see values change.

## Troubleshooting

### "Device not found" after attach

The Windows Xbox driver may be holding the device. Try:

1. Close any games or Xbox Game Bar
2. Disconnect and reconnect the controller
3. Run `usbipd attach` again

### Joystick device not appearing

1. Verify kernel has joystick support:

   ```bash
   zcat /proc/config.gz | grep JOYSTICK
   ```

   Should show `CONFIG_INPUT_JOYDEV=y`

2. Check dmesg for errors:
   ```bash
   dmesg | grep -i xbox
   ```

### Permission denied on /dev/input/js0

Make sure you're in the input group:

```bash
groups $USER
```

If `input` is not listed, run the usermod command and log out/in.

### Simulator doesn't detect gamepad

The simulator needs the `SDL_JOYSTICK_DEVICE` environment variable. This is set automatically in the code, but you can also set it manually:

```bash
export SDL_JOYSTICK_DEVICE=/dev/input/js0
python simulator/harness.py your_robot.iqpython
```

## Quick Reference Commands

```powershell
# Windows PowerShell (Admin)
usbipd list                           # List USB devices
usbipd bind --busid <ID>              # Share device (one-time)
usbipd attach --wsl --busid <ID>      # Attach to WSL
usbipd detach --busid <ID>            # Detach from WSL
usbipd list | findstr -i "xbox game controller pad joystick 045e"
```

```bash
# WSL2
ls /dev/input/js*                     # Check for joystick
jstest /dev/input/js0                 # Test joystick
dmesg | tail -20                      # Check kernel messages
```

## Automating Attachment

You can create a script to quickly attach the gamepad:

**Windows (attach-gamepad.ps1):**

```powershell
usbipd attach --wsl --busid 1-9
```

Run this each time you start a WSL session and want to use the gamepad.
