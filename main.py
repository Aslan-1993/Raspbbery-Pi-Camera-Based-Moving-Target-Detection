"""
Object Tracking System - Software Documentation
===============================================

This script runs on a Raspberry Pi and integrates:
- Picamera2 for live video capture
- OpenCV for color-based object detection
- Servo motors for pan/tilt movement
- LCD1602 for status display
- ADC over I2C for light sensing
- GPIO outputs for external device control
- Telegram integration for notifications
- Threading for parallel camera capture, LCD updates, and speech

Main features:
- Captures live frames from the camera
- Applies HSV-based color filtering
- Detects the largest object in the frame
- Moves pan/tilt servos to keep the object near the center
- Reads ambient light from an ADC channel
- Updates LCD and voice status messages asynchronously
- Saves sample frames during tracking
- Allows HSV tuning through OpenCV trackbars

Important:
- This code depends on custom/local modules:
    - custom_servo.py
    - Telegram_Bot.py
    - LCD1602.py
- It is intended to run on Raspberry Pi hardware with the required peripherals connected.
"""

import cv2                          # OpenCV library for image processing and GUI windows
from picamera2 import Picamera2     # Raspberry Pi camera interface
import smbus                        # I2C communication library
import RPi.GPIO as GPIO             # Raspberry Pi GPIO control
import time                         # Time utilities for delays and timestamps
import numpy as np                  # Numerical operations and array handling
import sys                          # System-specific parameters and path handling
from threading import Thread        # Base thread class
import threading                    # Threading utilities

# Add local Python module directory so custom modules can be imported
sys.path.append('/home/Python')

from custom_servo import Servo      # Custom servo control class
from Telegram_Bot import Telegram   # Custom Telegram notification class
import LCD1602                      # LCD1602 display control module
import os                           # Operating system commands


# -------------------------------------------------------------------
# Hardware Initialization
# -------------------------------------------------------------------

# Create camera object used for frame capture
picam2 = Picamera2()

# Create servo objects for horizontal and vertical movement
pan = Servo(pin=13)
tilt = Servo(pin=12)

# Initial angles for the pan and tilt servos
pan_angle = 0
tilt_angle = 0

# Move servos to their initial positions
pan.set_angle(pan_angle)
tilt.set_angle(tilt_angle)

# Initialize LCD1602 at I2C address 0x27 with backlight enabled
LCD1602.init(0x27, 1)

# Use BCM numbering for GPIO pins
GPIO.setmode(GPIO.BCM)

# GPIO pins used as outputs for external devices
RELAY_PIN = 27
RELAY_PIN2 = 26

# Configure relay pins as outputs
GPIO.setup(RELAY_PIN, GPIO.OUT)
GPIO.setup(RELAY_PIN2, GPIO.OUT)

# Initialize I2C bus number 1
bus = smbus.SMBus(1)

# I2C address of ADS7830 ADC
ADC_ADDRESS = 0x4b


# -------------------------------------------------------------------
# Camera Configuration
# -------------------------------------------------------------------

# Display width and height used for camera preview
dispW = 400
dispH = 400

# Set preview resolution
picam2.preview_configuration.main.size = (dispW, dispH)

# Set preview pixel format
picam2.preview_configuration.main.format = "RGB888"

# Set desired frame rate
picam2.preview_configuration.controls.FrameRate = 60

# Align configuration and apply it
picam2.preview_configuration.align()
picam2.configure("preview")

# Start the camera stream
picam2.start()


# -------------------------------------------------------------------
# Display / Overlay Settings
# -------------------------------------------------------------------

# FPS variable for calculating smoothed frame rate
fps = 0

# Position of FPS text on displayed frame
pos = (10, 30)

# OpenCV font settings
font = cv2.FONT_HERSHEY_SIMPLEX
height = 0.5
weight = 1
myColor = (0, 0, 255)


# -------------------------------------------------------------------
# HSV Detection Parameters
# -------------------------------------------------------------------

# Initial lower and upper HSV bounds for color thresholding
hueLow = 25
hueHigh = 65
satLow = 154
satHigh = 255
valLow = 88
valHigh = 241

# Trackbar flag:
# 0 = calibration/training mode
# 1 = tracking mode
track = 0

# Counter used to limit one-time notification behavior
myCount = 0

# LCD state flag used to avoid repeated updates
lcd = 3

# Timestamps for rate-limiting speech and LCD updates
last_speech_time = 0
last_lcd_update = 0


# -------------------------------------------------------------------
# Trackbar Callback Functions
# Each callback updates one HSV boundary or the tracking mode.
# -------------------------------------------------------------------

def onTrack1(val):
    """Update lower hue threshold from trackbar."""
    global hueLow
    hueLow = val


def onTrack2(val):
    """Update upper hue threshold from trackbar."""
    global hueHigh
    hueHigh = val


def onTrack3(val):
    """Update lower saturation threshold from trackbar."""
    global satLow
    satLow = val


def onTrack4(val):
    """Update upper saturation threshold from trackbar."""
    global satHigh
    satHigh = val


def onTrack5(val):
    """Update lower value (brightness) threshold from trackbar."""
    global valLow
    valLow = val


def onTrack6(val):
    """Update upper value (brightness) threshold from trackbar."""
    global valHigh
    valHigh = val


def onTrack7(val):
    """Update tracking mode from trackbar."""
    global track
    track = val


# Create a GUI window for displaying the camera and mask
cv2.namedWindow('Camera and Mask')

# Create sliders for interactive HSV tuning and mode switching
cv2.createTrackbar('Hue Low', 'Camera and Mask', hueLow, 360, onTrack1)
cv2.createTrackbar('Hue High', 'Camera and Mask', hueHigh, 360, onTrack2)
cv2.createTrackbar('Sat Low', 'Camera and Mask', satLow, 255, onTrack3)
cv2.createTrackbar('Sat High', 'Camera and Mask', satHigh, 255, onTrack4)
cv2.createTrackbar('Val Low', 'Camera and Mask', valLow, 255, onTrack5)
cv2.createTrackbar('Val High', 'Camera and Mask', valHigh, 255, onTrack6)
cv2.createTrackbar('Train-0 Track-1', 'Camera and Mask', track, 1, onTrack7)


def say_target_in_thread(status):
    """
    Speak a status message asynchronously.

    Parameters
    ----------
    status : int
        Status code selecting which message to speak.
        1 = tracking message
        2 = centered/completed message
        3 = searching message

    Notes
    -----
    Runs speech in a separate thread so the main loop does not block.
    """
    def say_target():
        if status == 1:
            os.system("espeak 'Tracking target'")
        if status == 2:
            os.system("espeak 'target destroyed'")
        if status == 3:
            os.system("espeak 'searching target'")

    thread = threading.Thread(target=say_target)
    thread.start()


def update_lcd_in_thread(message):
    """
    Update the LCD text asynchronously.

    Parameters
    ----------
    message : str
        Text to display on the LCD first row.

    Notes
    -----
    The LCD is cleared before writing the new message.
    This is done in a separate thread to reduce blocking.
    """
    def update_lcd():
        LCD1602.clear()
        LCD1602.write(0, 0, message)

    thread = threading.Thread(target=update_lcd)
    thread.start()


class TelegramMessageThread(Thread):
    """
    Thread used to send a Telegram notification without blocking the main loop.
    """

    def _init_(self):
        Thread._init_(self)

    def run(self):
        """Send a Telegram message using the custom Telegram class."""
        Telegram().send_message()


def process_frame(frame):
    """
    Process one video frame.

    Steps performed
    ---------------
    1. Convert BGR image to HSV
    2. Apply color threshold using current HSV bounds
    3. Reduce noise with dilation and erosion
    4. Find contours in the binary mask
    5. Select the largest contour if available
    6. Draw a bounding rectangle around the detected object
    7. If tracking mode is active, compute position error relative to image center
    8. Adjust servo angles accordingly
    9. Update LCD / speech state messages

    Parameters
    ----------
    frame : numpy.ndarray
        Current camera frame in BGR format.

    Returns
    -------
    tuple
        (processed_frame, mask)
        processed_frame : frame with overlays
        mask : binary mask used for detection
    """
    global pan_angle, tilt_angle, track, myCount, contours, lcd, last_speech_time, last_lcd_update

    # Convert frame from BGR color space to HSV
    frameHSV = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Build lower and upper arrays for thresholding
    lowerBound = np.array([hueLow, satLow, valLow])
    upperBound = np.array([hueHigh, satHigh, valHigh])

    # Create binary mask for pixels inside the selected HSV range
    myMask = cv2.inRange(frameHSV, lowerBound, upperBound)

    # Use morphological operations to reduce isolated noise
    kernel = np.ones((3, 3), np.uint8)
    myMask = cv2.dilate(myMask, kernel, iterations=1)
    myMask = cv2.erode(myMask, kernel, iterations=1)

    # Find external contours in the mask
    contours, _ = cv2.findContours(myMask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        # Select the largest detected contour
        largest_contour = max(contours, key=cv2.contourArea)

        # Compute bounding rectangle of the contour
        x, y, w, h = cv2.boundingRect(largest_contour)

        # Draw rectangle around detected object
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)

        if track == 1:
            # Begin one-time Telegram notification on first detection
            if myCount == 0:
                TelegramMessageThread().start()
                myCount = 1

            # Compute object center error relative to frame center
            tilt_error = (y + h / 2) - dispH / 2
            pan_error = (x + w / 2) - dispW / 2

            # Update tilt angle if object is far enough from center vertically
            if abs(tilt_error) > 10:
                tilt_angle = max(min(tilt_angle + tilt_error / 25, 4), -90)
                tilt.set_angle(tilt_angle)

            # Update pan angle if object is far enough from center horizontally
            if abs(pan_error) > 10:
                pan_angle = max(min(pan_angle - pan_error / 25, 90), -90)
                pan.set_angle(pan_angle)

            # If object is close to image center, update status
            if abs(pan_error) < 10 and abs(tilt_error) < 10 and lcd != 1:
                current_time = time.time()
                if current_time - last_lcd_update > 2:
                    update_lcd_in_thread("Target destroyed")
                    say_target_in_thread(2)
                    last_lcd_update = current_time
                    last_speech_time = current_time
                    lcd = 1

            # If object is still off-center, update tracking status
            if abs(pan_error) > 10 and abs(tilt_error) > 10 and lcd != 0:
                current_time = time.time()
                if current_time - last_lcd_update > 2:
                    update_lcd_in_thread("Tracking target")
                    say_target_in_thread(1)
                    last_lcd_update = current_time
                    last_speech_time = current_time
                    lcd = 0

        if track == 0:
            # Clear LCD in calibration mode
            LCD1602.clear()

    else:
        # No contours found
        if track == 1:
            if lcd == 3 or lcd == 1 or lcd == 0:
                current_time = time.time()
                if current_time - last_lcd_update > 5:
                    update_lcd_in_thread("Searching target")
                    say_target_in_thread(3)
                    last_lcd_update = current_time
                    last_speech_time = current_time

        # Reset one-time detection counter when target disappears
        myCount = 0

    return frame, myMask


class FrameCaptureThread(Thread):
    """
    Background thread for continuous camera frame capture.

    Attributes
    ----------
    frame : numpy.ndarray or None
        Most recent frame captured from the camera.
    running : bool
        Controls the capture loop.
    """

    def _init_(self):
        Thread._init_(self)
        self.frame = None
        self.running = True

    def run(self):
        """Continuously grab frames from Picamera2 while running is True."""
        global picam2
        while self.running:
            self.frame = picam2.capture_array()

    def stop(self):
        """Request the capture loop to stop."""
        self.running = False


def read_adc(channel):
    """
    Read one channel from the ADS7830 ADC.

    Parameters
    ----------
    channel : int
        ADC input channel number, expected range 0..7.

    Returns
    -------
    int
        ADC reading from 0 to 255, or -1 if the channel is invalid.
    """
    if channel < 0 or channel > 7:
        return -1

    # Build command byte for channel selection
    command = 0x8b | (channel << 4)

    # Send command to ADC
    bus.write_byte(ADC_ADDRESS, command)

    # Read converted value
    adc_value = bus.read_byte(ADC_ADDRESS)

    return adc_value


def main_loop():
    """
    Main program loop.

    Responsibilities
    ----------------
    - Start camera capture thread
    - Read ambient light from ADC
    - Capture the latest frame
    - Flip and process the frame
    - Display original image and mask side by side
    - Draw center crosshair and FPS text
    - Save selected frames periodically while tracking
    - Exit cleanly when ESC is pressed or window is closed
    """
    global fps

    # Start background frame capture
    frame_capture = FrameCaptureThread()
    frame_capture.start()

    # Timestamp used for spaced frame saving
    last_saved_time = time.time()

    # Counter limits number of saved frames
    frame_counter = 1

    while True:
        tStart = time.time()

        # Get the latest frame from the capture thread
        frame = frame_capture.frame

        # Read light level from ADC channel 0
        light_level = read_adc(0)

        # Example logic using ambient light reading
        if light_level < 110:
            GPIO.output(RELAY_PIN2, GPIO.HIGH)
        else:
            GPIO.output(RELAY_PIN2, GPIO.LOW)

        # Skip iteration if no frame is yet available
        if frame is None:
            continue

        # Flip image vertically and horizontally
        frame = cv2.flip(frame, -1)

        # Process frame and generate mask
        frame, myMask = process_frame(frame)

        # Convert grayscale mask to BGR so it can be concatenated with the frame
        myMask = cv2.cvtColor(myMask, cv2.COLOR_GRAY2BGR)

        # Display original frame and mask side by side
        combined_frame = cv2.hconcat([frame, myMask])

        # Draw a center cross marker
        centerX, centerY = dispW // 2, dispH // 2
        cv2.line(combined_frame, (centerX - 10, centerY), (centerX + 10, centerY), (0, 255, 0), 1)
        cv2.line(combined_frame, (centerX, centerY - 10), (centerX, centerY + 10), (0, 255, 0), 1)

        # Draw FPS value
        cv2.putText(combined_frame, str(int(fps)) + ' FPS', pos, font, height, myColor, weight)

        # Show the output window
        cv2.imshow("Camera and Mask", combined_frame)

        # Save up to 3 frames at 5-second intervals while tracking
        if track == 1 and contours and frame_counter < 4:
            current_time = time.time()
            if current_time - last_saved_time >= 5:
                frame_name = f"/home/aslan/Python/frame_save/frame_{frame_counter}.jpg"
                cv2.imwrite(frame_name, frame)
                print(f"Frame saved: {frame_name}")
                last_saved_time = current_time
                frame_counter += 1

        # Exit if ESC is pressed or the window is closed
        if cv2.waitKey(1) == 27 or cv2.getWindowProperty("Camera and Mask", cv2.WND_PROP_VISIBLE) < 1:
            LCD1602.clear()
            break

        # Compute smoothed FPS
        tEnd = time.time()
        loopTime = tEnd - tStart
        fps = 0.9 * fps + 0.1 * (1 / loopTime)

    # Stop the capture thread and close display windows
    frame_capture.stop()
    cv2.destroyAllWindows()


# Run the main loop only when this file is executed directly
if _name_ == "_main_":
    main_loop()