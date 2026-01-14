#!/usr/bin/env python3
"""
Simple test script to detect button press on GPIO 0 (BCM pin 0).
Press Ctrl+C to exit.
"""

import time

try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False
    print("WARNING: RPi.GPIO not available. Install with: sudo apt-get install python3-rpi.gpio")
    print("Running in simulation mode - press Enter to simulate button press.")

# GPIO pin configuration
BUTTON_PIN = 0  # BCM GPIO 0

def setup_gpio():
    """Initialize GPIO for button input."""
    if not HAS_GPIO:
        return
    
    # Use BCM pin numbering
    GPIO.setmode(GPIO.BCM)
    
    # Set up GPIO pin as input with pull-up resistor
    # Button should connect GPIO pin to ground when pressed
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    print(f"[GPIO] Pin {BUTTON_PIN} configured as input with pull-up")
    print("[GPIO] Button should connect to ground when pressed")

def button_callback(channel):
    """Callback function when button is pressed."""
    print(f"[BUTTON] Button pressed on GPIO {channel}! (Interrupt detected)")

def main():
    """Main test loop."""
    print("=" * 60)
    print("Button Test - GPIO 0")
    print("=" * 60)
    
    if HAS_GPIO:
        setup_gpio()
        
        # Option 1: Use interrupt detection (recommended)
        print("\n[MODE] Using interrupt detection (falling edge)")
        print("[INFO] Press the button connected to GPIO 0...")
        print("[INFO] Press Ctrl+C to exit\n")
        
        # Add event detection for falling edge (button press)
        # bounce_time prevents multiple triggers from switch bounce
        GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING, 
                            callback=button_callback, 
                            bouncetime=200)
        
        try:
            # Keep program running
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n[EXIT] Exiting...")
        finally:
            GPIO.cleanup()
            print("[GPIO] Cleanup complete")
    
    else:
        # Simulation mode when GPIO not available
        print("\n[SIMULATION] Press Enter to simulate button press, 'q' to quit")
        try:
            while True:
                user_input = input()
                if user_input.lower() == 'q':
                    break
                print(f"[BUTTON] Simulated button press on GPIO {BUTTON_PIN}!")
        except KeyboardInterrupt:
            print("\n[EXIT] Exiting...")

def test_polling_mode():
    """Alternative: polling mode for button detection."""
    if not HAS_GPIO:
        print("GPIO not available for polling test")
        return
    
    setup_gpio()
    
    print("\n[MODE] Using polling mode")
    print("[INFO] Press the button connected to GPIO 0...")
    print("[INFO] Press Ctrl+C to exit\n")
    
    button_state = GPIO.input(BUTTON_PIN)
    
    try:
        while True:
            current_state = GPIO.input(BUTTON_PIN)
            
            # Detect falling edge (button pressed)
            if button_state == GPIO.HIGH and current_state == GPIO.LOW:
                print(f"[BUTTON] Button pressed on GPIO {BUTTON_PIN}!")
            
            # Detect rising edge (button released)
            elif button_state == GPIO.LOW and current_state == GPIO.HIGH:
                print(f"[BUTTON] Button released on GPIO {BUTTON_PIN}")
            
            button_state = current_state
            time.sleep(0.01)  # 10ms polling interval
            
    except KeyboardInterrupt:
        print("\n[EXIT] Exiting...")
    finally:
        GPIO.cleanup()
        print("[GPIO] Cleanup complete")

if __name__ == "__main__":
    # Use interrupt mode (recommended)
    main()
    
    # Uncomment below to test polling mode instead
    # test_polling_mode()
