#!/usr/bin/env python3
"""Monitor GPIO button pin states in real-time to diagnose phantom presses."""

import RPi.GPIO as GPIO
import time
from datetime import datetime

# Button pin mapping (same as thermologger.py)
BUTTON_PINS = {
    1: 16,
    2: 13,
    3: 15,
    4: 31
}

def setup_pins():
    """Configure GPIO pins."""
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    
    for button_num, pin in BUTTON_PINS.items():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        initial_state = GPIO.input(pin)
        print(f"Button {button_num} on pin {pin}: initial state={initial_state} (0=LOW, 1=HIGH)")

def monitor_pins(poll_interval=0.1):
    """Monitor pin states continuously and report changes."""
    print(f"\nMonitoring button pins (polling every {poll_interval*1000:.0f}ms)...")
    print("Press Ctrl+C to stop\n")
    
    # Track last known state for each pin
    last_states = {pin: GPIO.input(pin) for pin in BUTTON_PINS.values()}
    
    try:
        while True:
            current_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            
            # Check each pin
            for button_num, pin in BUTTON_PINS.items():
                current_state = GPIO.input(pin)
                
                # Report state changes
                if current_state != last_states[pin]:
                    state_name = "HIGH (pressed)" if current_state == 1 else "LOW (unpressed)"
                    print(f"[{current_time}] Button {button_num} (pin {pin}): {last_states[pin]} -> {current_state} ({state_name})")
                    last_states[pin] = current_state
            
            time.sleep(poll_interval)
    
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")
        print("\nFinal pin states:")
        for button_num, pin in BUTTON_PINS.items():
            state = GPIO.input(pin)
            state_name = "HIGH (pressed)" if state == 1 else "LOW (unpressed)"
            print(f"  Button {button_num} (pin {pin}): {state} ({state_name})")

def main():
    """Main entry point."""
    print("=" * 60)
    print("GPIO Button Pin Monitor")
    print("=" * 60)
    print()
    
    setup_pins()
    
    print("\nConfiguration:")
    print("  - GPIO mode: BOARD")
    print("  - Pull-down resistors: ENABLED")
    print("  - Expected: LOW (0) when unpressed, HIGH (1) when pressed")
    
    monitor_pins()
    
    GPIO.cleanup()
    print("GPIO cleanup complete")

if __name__ == "__main__":
    main()
