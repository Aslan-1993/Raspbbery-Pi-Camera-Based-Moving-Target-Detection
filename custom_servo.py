import pigpio  # Library for controlling Raspberry Pi GPIO with accurate timing


class Servo:
    """
    A class for controlling a servo motor using PWM through the pigpio library.

    This class allows:
    - Initializing a servo on a selected GPIO pin
    - Limiting movement to a defined angle range
    - Setting the servo angle
    - Reading the current angle
    - Mapping angle values to PWM duty values
    """

    # PWM value limits used for servo movement
    MAX_PW = 1250  # PWM duty value corresponding approximately to +90 degrees
    MIN_PW = 250   # PWM duty value corresponding approximately to -90 degrees

    # PWM frequency for standard servo motors
    _freq = 50     # 50 Hz = 20 ms period

    def __init__(self, pin, min_angle=-90, max_angle=90):
        """
        Initialize the servo object.

        Parameters
        ----------
        pin : int
            GPIO pin connected to the servo signal wire.

        min_angle : int, optional
            Minimum allowed angle for the servo. Default is -90.

        max_angle : int, optional
            Maximum allowed angle for the servo. Default is +90.
        """

        # Create pigpio interface object
        self.pi = pigpio.pi()

        # Store the GPIO pin number
        self.pin = pin

        # Set PWM frequency for the selected pin
        self.pi.set_PWM_frequency(self.pin, self._freq)

        # Set PWM range for finer resolution
        self.pi.set_PWM_range(self.pin, 10000)

        # Store current servo angle
        self.angle = 0

        # Store servo motion limits
        self.max_angle = max_angle
        self.min_angle = min_angle

        # Start with 0 duty cycle so the servo is not driven immediately
        self.pi.set_PWM_dutycycle(self.pin, 0)

    def set_angle(self, angle):
        """
        Set the servo to a requested angle.

        Parameters
        ----------
        angle : int or float
            Desired servo angle.

        Notes
        -----
        The input angle is clamped between min_angle and max_angle.
        Then it is mapped into a PWM duty value and sent to the GPIO pin.
        """

        # Limit the requested angle so it stays within allowed range
        if angle > self.max_angle:
            angle = self.max_angle
        elif angle < self.min_angle:
            angle = self.min_angle

        # Save the final angle
        self.angle = angle

        # Convert angle to PWM duty value
        duty = self.map(angle, -90, 90, self.MIN_PW, self.MAX_PW)

        # Send PWM duty cycle to servo pin
        self.pi.set_PWM_dutycycle(self.pin, duty)

    def get_angle(self):
        """
        Return the current stored angle of the servo.

        Returns
        -------
        int or float
            Current servo angle.
        """
        return self.angle

    def map(self, x, in_min, in_max, out_min, out_max):
        """
        Map a number from one range to another.

        Parameters
        ----------
        x : float
            Input value to convert.

        in_min : float
            Minimum value of the input range.

        in_max : float
            Maximum value of the input range.

        out_min : float
            Minimum value of the output range.

        out_max : float
            Maximum value of the output range.

        Returns
        -------
        float
            Converted value in the output range.
        """
        return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min