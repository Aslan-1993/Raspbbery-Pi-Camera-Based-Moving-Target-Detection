# Camera-Based Moving Target Detection, Tracking, and Wireless Reporting System

An academic Raspberry Pi and OpenCV project for real-time moving target detection, tracking, and wireless reporting.

## Overview
This project presents the design and implementation of an academic prototype for camera-based moving target detection and tracking. The system uses a Raspberry Pi 4 and a Raspberry Pi Camera Module to detect a color-defined target, track it in real time using pan/tilt servo motors, provide local feedback through an LCD and voice output, and send wireless notifications through Telegram.

The project was developed as a final B.Sc. project in Electrical and Electronics Engineering.

## Key Features
- Real-time target detection using OpenCV
- Color-based image processing in HSV space
- Automatic target tracking with pan/tilt servo motors
- LCD status display for local feedback
- Voice status indication
- Telegram alert message when a target is detected
- Light-level sensing using an ADS7830 ADC and photoresistor
- Dual operating modes:
  - **Train Mode** – used to tune and learn the target color
  - **Track Mode** – used for autonomous real-time tracking

## System Architecture
The system is built around a Raspberry Pi 4 Model B as the main processing and control unit. Video frames captured by the Raspberry Pi Camera Module are processed in Python using OpenCV. Once a target is detected, the system calculates the position error relative to the frame center and adjusts two servo motors to keep the target centered.

Additional output modules include:
- LCD1602 I2C display
- Voice/audio indication
- Telegram wireless reporting
- Illumination indicator for low-light conditions

## Hardware Components
- Raspberry Pi 4 Model B
- Raspberry Pi Camera Module V2
- 2x SG90 Servo Motors
- LCD1602 with I2C interface
- ADS7830 ADC
- Photoresistor
- Relay modules
- Audio output module / speaker
- LED illumination indicator
- 18650 battery-based power source

## Software Stack
- Python 3
- OpenCV
- NumPy
- requests
- pigpio
- smbus / smbus2
- Picamera2
- RPi.GPIO
