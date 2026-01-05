"""
Virtual Controller GUI (PyGame Version)
=======================================
A PyGame-based virtual VEX IQ controller for testing robot code.
Supports both mouse input and USB gamepad.
"""

import os

# Set SDL joystick device path for WSL2 compatibility
# This must be set before importing pygame
if os.path.exists('/dev/input/js0'):
    os.environ['SDL_JOYSTICK_DEVICE'] = '/dev/input/js0'

import pygame
import math
from typing import Callable, Optional
from dataclasses import dataclass


# Colors
BLACK = (20, 20, 20)
DARK_GRAY = (40, 40, 40)
MID_GRAY = (80, 80, 80)
LIGHT_GRAY = (120, 120, 120)
WHITE = (255, 255, 255)
BLUE = (74, 144, 217)
LIGHT_BLUE = (106, 176, 249)
GREEN = (76, 175, 80)
RED = (244, 67, 54)
ORANGE = (255, 152, 0)


@dataclass
class JoystickState:
    """State of a virtual joystick."""
    x: int = 0  # -100 to 100
    y: int = 0  # -100 to 100
    dragging: bool = False


class VirtualJoystick:
    """A virtual joystick widget."""

    def __init__(self, x: int, y: int, size: int = 150, label: str = ""):
        self.rect = pygame.Rect(x, y, size, size)
        self.size = size
        self.center_x = x + size // 2
        self.center_y = y + size // 2
        self.stick_radius = 25
        self.max_distance = (size // 2) - self.stick_radius - 10
        self.label = label

        self.state = JoystickState()

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle mouse events. Returns True if joystick was updated."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.state.dragging = True
                self._update_from_mouse(event.pos)
                return True

        elif event.type == pygame.MOUSEBUTTONUP:
            if self.state.dragging:
                self.state.dragging = False
                self.state.x = 0
                self.state.y = 0
                return True

        elif event.type == pygame.MOUSEMOTION:
            if self.state.dragging:
                self._update_from_mouse(event.pos)
                return True

        return False

    def _update_from_mouse(self, pos: tuple[int, int]):
        """Update joystick position from mouse position."""
        dx = pos[0] - self.center_x
        dy = pos[1] - self.center_y

        # Limit to max distance
        distance = math.sqrt(dx * dx + dy * dy)
        if distance > self.max_distance:
            dx = dx * self.max_distance / distance
            dy = dy * self.max_distance / distance

        # Convert to -100 to 100 range
        self.state.x = int((dx / self.max_distance) * 100)
        self.state.y = int((-dy / self.max_distance) * 100)  # Invert Y

    def set_from_gamepad(self, x: float, y: float):
        """Set joystick position from gamepad axis (-1 to 1)."""
        self.state.x = int(x * 100)
        self.state.y = int(-y * 100)  # Invert Y

    def draw(self, surface: pygame.Surface):
        """Draw the joystick."""
        # Background circle
        pygame.draw.circle(surface, DARK_GRAY, (self.center_x, self.center_y),
                          self.size // 2 - 5)
        pygame.draw.circle(surface, MID_GRAY, (self.center_x, self.center_y),
                          self.size // 2 - 5, 2)

        # Crosshairs
        pygame.draw.line(surface, MID_GRAY,
                        (self.center_x, self.rect.top + 10),
                        (self.center_x, self.rect.bottom - 10), 1)
        pygame.draw.line(surface, MID_GRAY,
                        (self.rect.left + 10, self.center_y),
                        (self.rect.right - 10, self.center_y), 1)

        # Calculate stick position
        stick_x = self.center_x + (self.state.x / 100) * self.max_distance
        stick_y = self.center_y - (self.state.y / 100) * self.max_distance

        # Draw stick
        color = LIGHT_BLUE if self.state.dragging else BLUE
        pygame.draw.circle(surface, color, (int(stick_x), int(stick_y)),
                          self.stick_radius)
        pygame.draw.circle(surface, WHITE, (int(stick_x), int(stick_y)),
                          self.stick_radius, 2)

        # Label
        font = pygame.font.Font(None, 24)
        label_surface = font.render(self.label, True, LIGHT_GRAY)
        label_rect = label_surface.get_rect(centerx=self.center_x,
                                            top=self.rect.bottom + 5)
        surface.blit(label_surface, label_rect)


class VirtualButton:
    """A virtual controller button."""

    def __init__(self, x: int, y: int, width: int = 70, height: int = 35,
                 label: str = ""):
        self.rect = pygame.Rect(x, y, width, height)
        self.label = label
        self.pressed = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle mouse events. Returns True if state changed."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.pressed = True
                return True

        elif event.type == pygame.MOUSEBUTTONUP:
            if self.pressed:
                self.pressed = False
                return True

        return False

    def draw(self, surface: pygame.Surface):
        """Draw the button."""
        color = BLUE if self.pressed else DARK_GRAY
        pygame.draw.rect(surface, color, self.rect, border_radius=5)
        pygame.draw.rect(surface, LIGHT_GRAY if self.pressed else MID_GRAY,
                        self.rect, 2, border_radius=5)

        font = pygame.font.Font(None, 22)
        label_surface = font.render(self.label, True, WHITE)
        label_rect = label_surface.get_rect(center=self.rect.center)
        surface.blit(label_surface, label_rect)


class MotorIndicator:
    """Visual indicator for motor state - compact version for 12 ports."""

    def __init__(self, x: int, y: int, port: int, label: str = "", size: int = 50):
        self.size = size
        self.port = port
        self.label = label or f"M{port}"
        self.x = x
        self.y = y

        self.velocity = 0.0
        self.spinning = False

    def set_position(self, x: int, y: int):
        """Update position (for dynamic layout)."""
        self.x = x
        self.y = y

    def set_state(self, velocity: float, spinning: bool):
        """Update motor state."""
        self.velocity = velocity
        self.spinning = spinning

    def draw(self, surface: pygame.Surface):
        """Draw the motor indicator."""
        center_x = self.x + self.size // 2
        center_y = self.y + self.size // 2

        # Motor body
        if self.spinning and self.velocity != 0:
            if self.velocity > 0:
                color = GREEN
            else:
                color = RED
        else:
            color = DARK_GRAY

        pygame.draw.circle(surface, color, (center_x, center_y),
                          self.size // 2 - 3)
        pygame.draw.circle(surface, MID_GRAY, (center_x, center_y),
                          self.size // 2 - 3, 2)

        # Port label
        font = pygame.font.Font(None, 22)
        port_surface = font.render(f"P{self.port}", True, WHITE)
        port_rect = port_surface.get_rect(center=(center_x, center_y - 6))
        surface.blit(port_surface, port_rect)

        # Velocity text inside circle
        vel_font = pygame.font.Font(None, 18)
        vel_text = f"{int(self.velocity)}%"
        vel_surface = vel_font.render(vel_text, True, WHITE)
        vel_rect = vel_surface.get_rect(center=(center_x, center_y + 10))
        surface.blit(vel_surface, vel_rect)

        # Label below
        label_font = pygame.font.Font(None, 16)
        label_surface = label_font.render(self.label, True, LIGHT_GRAY)
        label_rect = label_surface.get_rect(centerx=center_x,
                                            top=self.y + self.size + 2)
        surface.blit(label_surface, label_rect)


class PneumaticIndicator:
    """Visual indicator for pneumatic cylinder state."""

    def __init__(self, x: int, y: int, port: int, label: str = "", size: int = 50):
        self.size = size
        self.port = port
        self.label = label or f"Pneu{port}"
        self.x = x
        self.y = y

        self.extended = False
        self.pump_on = True

    def set_position(self, x: int, y: int):
        """Update position (for dynamic layout)."""
        self.x = x
        self.y = y

    def set_state(self, extended: bool, pump_on: bool):
        """Update pneumatic state."""
        self.extended = extended
        self.pump_on = pump_on

    def draw(self, surface: pygame.Surface):
        """Draw the pneumatic indicator."""
        center_x = self.x + self.size // 2
        center_y = self.y + self.size // 2

        # Cylinder body (rectangle)
        rect = pygame.Rect(self.x + 5, self.y + 10, self.size - 10, self.size - 20)

        # Color based on state
        if self.extended:
            color = BLUE  # Extended = blue
        else:
            color = DARK_GRAY  # Retracted = gray

        pygame.draw.rect(surface, color, rect, border_radius=5)
        pygame.draw.rect(surface, MID_GRAY, rect, 2, border_radius=5)

        # Piston indicator (small rectangle that moves)
        piston_y = self.y + 15 if self.extended else self.y + self.size - 25
        piston_rect = pygame.Rect(self.x + 10, piston_y, self.size - 20, 10)
        pygame.draw.rect(surface, LIGHT_GRAY, piston_rect)

        # Port label
        font = pygame.font.Font(None, 20)
        port_surface = font.render(f"P{self.port}", True, WHITE)
        port_rect = port_surface.get_rect(center=(center_x, center_y))
        surface.blit(port_surface, port_rect)

        # State text
        state_font = pygame.font.Font(None, 16)
        state_text = "EXT" if self.extended else "RET"
        state_color = BLUE if self.extended else LIGHT_GRAY
        state_surface = state_font.render(state_text, True, state_color)
        state_rect = state_surface.get_rect(centerx=center_x, top=self.y + self.size + 2)
        surface.blit(state_surface, state_rect)

        # Label below
        label_font = pygame.font.Font(None, 14)
        label_surface = label_font.render(self.label, True, LIGHT_GRAY)
        label_rect = label_surface.get_rect(centerx=center_x, top=self.y + self.size + 14)
        surface.blit(label_surface, label_rect)


class VirtualControllerGUI:
    """Main PyGame-based virtual controller GUI."""

    def __init__(self, title: str = "VEX IQ Virtual Controller", width: int = 1280,
                 height: int = 720):
        pygame.init()
        pygame.display.set_caption(title)

        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        self.clock = pygame.time.Clock()
        self.running = True

        # Controller reference
        self._controller = None

        # Initialize hardware gamepad
        pygame.joystick.init()
        self.gamepad = None
        if pygame.joystick.get_count() > 0:
            self.gamepad = pygame.joystick.Joystick(0)
            print(f"Gamepad detected: {self.gamepad.get_name()}")

        # Create UI elements
        self._create_ui()

        # Motor indicators
        self._motor_indicators: dict[int, MotorIndicator] = {}

        # Pneumatic indicators
        self._pneumatic_indicators: dict[int, PneumaticIndicator] = {}

        # Status message
        self.status = "Ready"

    def _create_ui(self):
        """Create all UI elements."""
        center_x = self.width // 2

        # Controller section (left half of screen)
        ctrl_center = self.width // 4

        # Joysticks - larger and more spread out
        js_size = 180
        js_y = 180
        self.left_joystick = VirtualJoystick(ctrl_center - js_size - 60, js_y, js_size, "LEFT (A/B)")
        self.right_joystick = VirtualJoystick(ctrl_center + 60, js_y, js_size, "RIGHT (C/D)")

        # Buttons - positioned around joysticks
        btn_y = 100
        self.btn_l_up = VirtualButton(ctrl_center - js_size - 40, btn_y, label="L-Up")
        self.btn_l_down = VirtualButton(ctrl_center - js_size - 40, btn_y + 45, label="L-Down")
        self.btn_r_up = VirtualButton(ctrl_center + js_size + 20, btn_y, label="R-Up")
        self.btn_r_down = VirtualButton(ctrl_center + js_size + 20, btn_y + 45, label="R-Down")

        # E and F buttons below joysticks
        btn_bottom_y = js_y + js_size + 60
        self.btn_e_up = VirtualButton(ctrl_center - 120, btn_bottom_y, label="E-Up")
        self.btn_e_down = VirtualButton(ctrl_center - 120, btn_bottom_y + 45, label="E-Down")
        self.btn_f_up = VirtualButton(ctrl_center + 50, btn_bottom_y, label="F-Up")
        self.btn_f_down = VirtualButton(ctrl_center + 50, btn_bottom_y + 45, label="F-Down")

        self.buttons = [
            self.btn_l_up, self.btn_l_down, self.btn_r_up, self.btn_r_down,
            self.btn_e_up, self.btn_e_down, self.btn_f_up, self.btn_f_down
        ]

    def add_motor_indicator(self, port: int, name: str = ""):
        """Add a motor indicator - positioned in right half of screen."""
        indicator = MotorIndicator(0, 0, port, name, size=55)
        self._motor_indicators[port] = indicator
        self._layout_motors()

    def _layout_motors(self):
        """Arrange motor indicators in a grid on the right side."""
        if not self._motor_indicators:
            return

        # Motor panel on right half of screen
        panel_x = self.width // 2 + 40
        panel_y = 120
        motor_size = 55
        spacing = 70  # space between motor centers
        cols = 6  # 6 motors per row (can fit 12 in 2 rows)

        sorted_ports = sorted(self._motor_indicators.keys())
        for i, port in enumerate(sorted_ports):
            row = i // cols
            col = i % cols
            x = panel_x + col * spacing
            y = panel_y + row * (motor_size + 35)
            self._motor_indicators[port].set_position(x, y)

    def update_motor(self, port: int, velocity: float, spinning: bool):
        """Update a motor's displayed state."""
        if port in self._motor_indicators:
            self._motor_indicators[port].set_state(velocity, spinning)

    def add_pneumatic_indicator(self, port: int, name: str = ""):
        """Add a pneumatic indicator - positioned below motors."""
        indicator = PneumaticIndicator(0, 0, port, name, size=55)
        self._pneumatic_indicators[port] = indicator
        self._layout_pneumatics()

    def _layout_pneumatics(self):
        """Arrange pneumatic indicators below motors on the right side."""
        if not self._pneumatic_indicators:
            return

        # Pneumatic panel on right half, below motors
        panel_x = self.width // 2 + 40
        panel_y = 320  # Below motors section
        pneu_size = 55
        spacing = 70
        cols = 6

        sorted_ports = sorted(self._pneumatic_indicators.keys())
        for i, port in enumerate(sorted_ports):
            row = i // cols
            col = i % cols
            x = panel_x + col * spacing
            y = panel_y + row * (pneu_size + 40)
            self._pneumatic_indicators[port].set_position(x, y)

    def update_pneumatic(self, port: int, extended: bool, pump_on: bool):
        """Update a pneumatic's displayed state."""
        if port in self._pneumatic_indicators:
            self._pneumatic_indicators[port].set_state(extended, pump_on)

    def set_controller(self, controller):
        """Connect to a VEX controller stub."""
        self._controller = controller

    def set_status(self, message: str):
        """Set status bar message."""
        self.status = message

    def _handle_gamepad(self):
        """Read hardware gamepad input.

        Xbox 360 to VEX IQ Controller Mapping:
        --------------------------------------
        Sticks (VEX IQ 2nd Gen axis naming):
          Left Stick Y  → Axis A (vertical)
          Left Stick X  → Axis B (horizontal)
          Right Stick X → Axis C (horizontal)
          Right Stick Y → Axis D (vertical)

        Buttons:
          LB (button 4)  → L-Up
          LT (axis 2)    → L-Down (trigger as button, threshold > 0.5)
          RB (button 5)  → R-Up
          RT (axis 5)    → R-Down (trigger as button, threshold > 0.5)
          Y  (button 3)  → E-Up
          X  (button 2)  → E-Down
          B  (button 1)  → F-Up
          A  (button 0)  → F-Down
        """
        if not self.gamepad:
            return

        try:
            # Read stick axes
            # Xbox 360: 0=left X, 1=left Y, 3=right X, 4=right Y
            # (axis 2 and 5 are triggers on Xbox 360)
            left_x = self.gamepad.get_axis(0)
            left_y = self.gamepad.get_axis(1)
            right_x = self.gamepad.get_axis(3) if self.gamepad.get_numaxes() > 3 else 0
            right_y = self.gamepad.get_axis(4) if self.gamepad.get_numaxes() > 4 else 0

            # Apply deadzone
            deadzone = 0.1
            if abs(left_x) < deadzone: left_x = 0
            if abs(left_y) < deadzone: left_y = 0
            if abs(right_x) < deadzone: right_x = 0
            if abs(right_y) < deadzone: right_y = 0

            # Update virtual joysticks
            self.left_joystick.set_from_gamepad(left_x, left_y)
            self.right_joystick.set_from_gamepad(right_x, right_y)

            # Update controller stub
            # VEX IQ 2nd Gen axis mapping:
            #   Axis A = Left stick Y (vertical)
            #   Axis B = Left stick X (horizontal)
            #   Axis C = Right stick X (horizontal)
            #   Axis D = Right stick Y (vertical)
            if self._controller:
                self._controller.axisA.set_position(int(-left_y * 100))
                self._controller.axisB.set_position(int(left_x * 100))
                self._controller.axisC.set_position(int(right_x * 100))
                self._controller.axisD.set_position(int(-right_y * 100))

            # Read triggers (axes 2 and 5 on Xbox 360)
            # Triggers go from -1 (released) to 1 (fully pressed) on some drivers,
            # or 0 to 1 on others. Use threshold of 0.5 for button activation.
            trigger_threshold = 0.5
            lt_value = self.gamepad.get_axis(2) if self.gamepad.get_numaxes() > 2 else -1
            rt_value = self.gamepad.get_axis(5) if self.gamepad.get_numaxes() > 5 else -1

            # Handle both -1 to 1 and 0 to 1 trigger ranges
            lt_pressed = lt_value > trigger_threshold
            rt_pressed = rt_value > trigger_threshold

            # Read buttons with Xbox 360 to VEX IQ mapping
            if self.gamepad.get_numbuttons() >= 6:
                # Shoulder buttons
                self.btn_l_up.pressed = self.gamepad.get_button(4)    # LB → L-Up
                self.btn_r_up.pressed = self.gamepad.get_button(5)    # RB → R-Up

                # Triggers as buttons
                self.btn_l_down.pressed = lt_pressed                   # LT → L-Down
                self.btn_r_down.pressed = rt_pressed                   # RT → R-Down

                # Face buttons
                self.btn_e_up.pressed = self.gamepad.get_button(3)    # Y → E-Up
                self.btn_e_down.pressed = self.gamepad.get_button(2)  # X → E-Down
                self.btn_f_up.pressed = self.gamepad.get_button(1)    # B → F-Up
                self.btn_f_down.pressed = self.gamepad.get_button(0)  # A → F-Down

        except pygame.error:
            pass

    def _update_controller_from_ui(self):
        """Update the VEX controller stub from UI state (mouse input)."""
        if not self._controller:
            return

        # Joysticks - VEX IQ 2nd Gen axis mapping:
        #   Axis A = Left stick Y, Axis B = Left stick X
        #   Axis C = Right stick X, Axis D = Right stick Y
        self._controller.axisA.set_position(self.left_joystick.state.y)
        self._controller.axisB.set_position(self.left_joystick.state.x)
        self._controller.axisC.set_position(self.right_joystick.state.x)
        self._controller.axisD.set_position(self.right_joystick.state.y)

        # Buttons
        self._controller.buttonLUp.set_pressed(self.btn_l_up.pressed)
        self._controller.buttonLDown.set_pressed(self.btn_l_down.pressed)
        self._controller.buttonRUp.set_pressed(self.btn_r_up.pressed)
        self._controller.buttonRDown.set_pressed(self.btn_r_down.pressed)
        self._controller.buttonEUp.set_pressed(self.btn_e_up.pressed)
        self._controller.buttonEDown.set_pressed(self.btn_e_down.pressed)
        self._controller.buttonFUp.set_pressed(self.btn_f_up.pressed)
        self._controller.buttonFDown.set_pressed(self.btn_f_down.pressed)

    def _draw(self):
        """Draw the entire GUI."""
        self.screen.fill(BLACK)

        # Draw divider line between controller and motor panels
        pygame.draw.line(self.screen, MID_GRAY,
                        (self.width // 2, 60),
                        (self.width // 2, self.height - 50), 1)

        # Left side title - Controller
        font_title = pygame.font.Font(None, 36)
        ctrl_title = font_title.render("Controller", True, WHITE)
        ctrl_rect = ctrl_title.get_rect(centerx=self.width // 4, top=30)
        self.screen.blit(ctrl_title, ctrl_rect)

        # Right side title - Robot Status
        motor_title = font_title.render("Robot Status", True, WHITE)
        motor_rect = motor_title.get_rect(centerx=self.width * 3 // 4, top=30)
        self.screen.blit(motor_title, motor_rect)

        # Subtitle for motors
        font_sub = pygame.font.Font(None, 24)
        sub_title = font_sub.render("Motor Ports (12 max)", True, LIGHT_GRAY)
        sub_rect = sub_title.get_rect(centerx=self.width * 3 // 4, top=65)
        self.screen.blit(sub_title, sub_rect)

        # Draw joysticks
        self.left_joystick.draw(self.screen)
        self.right_joystick.draw(self.screen)

        # Draw joystick values
        font = pygame.font.Font(None, 24)
        ctrl_center = self.width // 4
        js_size = 180

        left_text = f"A:{self.left_joystick.state.y:4d}  B:{self.left_joystick.state.x:4d}"
        right_text = f"C:{self.right_joystick.state.x:4d}  D:{self.right_joystick.state.y:4d}"

        left_surface = font.render(left_text, True, LIGHT_GRAY)
        right_surface = font.render(right_text, True, LIGHT_GRAY)

        self.screen.blit(left_surface, (ctrl_center - js_size - 20, 180 + js_size + 30))
        self.screen.blit(right_surface, (ctrl_center + 100, 180 + js_size + 30))

        # Draw buttons
        for btn in self.buttons:
            btn.draw(self.screen)

        # Draw motor indicators
        for indicator in self._motor_indicators.values():
            indicator.draw(self.screen)

        # If no motors, show placeholder
        if not self._motor_indicators:
            font = pygame.font.Font(None, 28)
            no_motors = font.render("No motors configured", True, MID_GRAY)
            no_rect = no_motors.get_rect(centerx=self.width * 3 // 4, centery=200)
            self.screen.blit(no_motors, no_rect)

        # Draw pneumatic section subtitle if we have pneumatics
        if self._pneumatic_indicators:
            pneu_sub = font_sub.render("Pneumatics", True, LIGHT_GRAY)
            pneu_rect = pneu_sub.get_rect(left=self.width // 2 + 40, top=295)
            self.screen.blit(pneu_sub, pneu_rect)

        # Draw pneumatic indicators
        for indicator in self._pneumatic_indicators.values():
            indicator.draw(self.screen)

        # Gamepad status (bottom left)
        font_small = pygame.font.Font(None, 22)
        if self.gamepad:
            gp_text = f"Gamepad: {self.gamepad.get_name()}"
            gp_color = GREEN
        else:
            gp_text = "No gamepad detected (using mouse)"
            gp_color = ORANGE
        gp_surface = font_small.render(gp_text, True, gp_color)
        self.screen.blit(gp_surface, (20, self.height - 25))

        # Status (bottom right)
        status_surface = font_small.render(self.status, True, LIGHT_GRAY)
        status_rect = status_surface.get_rect(right=self.width - 20,
                                              bottom=self.height - 10)
        self.screen.blit(status_surface, status_rect)

        pygame.display.flip()

    def update(self):
        """Process one frame. Call this from the main loop."""
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            # Handle joystick events
            self.left_joystick.handle_event(event)
            self.right_joystick.handle_event(event)

            # Handle button events
            for btn in self.buttons:
                btn.handle_event(event)

        # Handle hardware gamepad
        self._handle_gamepad()

        # Update controller stub
        self._update_controller_from_ui()

        # Draw
        self._draw()

        # Cap framerate
        self.clock.tick(60)

    def run(self):
        """Run the main loop (blocking)."""
        while self.running:
            self.update()

        pygame.quit()


# Test standalone
if __name__ == "__main__":
    gui = VirtualControllerGUI()

    # Add test motors (simulating all 12 ports)
    gui.add_motor_indicator(1, "Left 1")
    gui.add_motor_indicator(2, "Right 1")
    gui.add_motor_indicator(3, "Arm")
    gui.add_motor_indicator(4, "Claw")

    # Simulate motor updates
    frame = 0
    while gui.running:
        gui.update()
        frame += 1
        if frame % 2 == 0:  # Update every 2 frames for smoother display
            # Simulate motor response to joystick (split arcade)
            drive = gui.left_joystick.state.y
            turn = gui.right_joystick.state.x
            left_vel = drive + turn
            right_vel = drive - turn

            # Clamp to -100 to 100
            left_vel = max(-100, min(100, left_vel))
            right_vel = max(-100, min(100, right_vel))

            gui.update_motor(1, left_vel, left_vel != 0)
            gui.update_motor(2, right_vel, right_vel != 0)
            gui.update_motor(3, 0, False)
            gui.update_motor(4, 0, False)
