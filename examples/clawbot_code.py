# Clawbot IQ - Sample VEXcode Python
# This demonstrates device declarations for the Clawbot

from vex import *

# Brain and Inertial sensor
brain = Brain()
brain_inertial = Inertial()

# Drive motors
left_motor = Motor(Ports.PORT1, GearSetting.RATIO_18_1, False)
right_motor = Motor(Ports.PORT6, GearSetting.RATIO_18_1, True)

# Arm and claw motors
arm_motor = Motor(Ports.PORT4, GearSetting.RATIO_36_1, False)
claw_motor = Motor(Ports.PORT10, GearSetting.RATIO_18_1, False)

# Motor groups for drivetrain
left_motors = MotorGroup(left_motor)
right_motors = MotorGroup(right_motor)

# Sensors
bumper_sensor = BumperSwitch(Ports.PORT7)
color_sensor = ColorSensor(Ports.PORT2)
distance_sensor = DistanceSensor(Ports.PORT9)

# Drivetrain configuration
# Parameters: left, right, wheel_travel, track_width, wheelbase, units, ratio
drivetrain = SmartDrive(left_motors, right_motors, brain_inertial, 200, 295, 40, MM, 1)


def main():
    # Autonomous code here
    drivetrain.drive_for(FORWARD, 300, MM)
    arm_motor.spin_for(FORWARD, 90, DEGREES)
    claw_motor.spin_for(FORWARD, 45, DEGREES)


# Run the main function
main()
