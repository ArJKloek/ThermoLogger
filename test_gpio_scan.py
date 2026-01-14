#!/usr/bin/env python3
"""
Scan and display the state of all GPIO pins on Raspberry Pi.
Shows which pins are HIGH (3.3V) or LOW (0V).
"""

import time

try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False
    print("ERROR: RPi.GPIO not available")
    print("Install with: sudo apt-get install python3-rpi.gpio")
    exit(1)

# All valid BCM GPIO pins on Raspberry Pi (most models)
# GPIO 0-27 are standard, 28-31 vary by model
ALL_GPIO_PINS = [
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
    16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27
]

def scan_gpio_pins():
    """Scan all GPIO pins and display their state."""
    GPIO.setmode(GPIO.BCM)
    
    print("=" * 70)
    print("GPIO Pin Scanner - Raspberry Pi")
    print("=" * 70)
    print("\nScanning all GPIO pins...")
    print("\nFormat: BCM GPIO# | State | Voltage")
    print("-" * 70)
    
    results = []
    
    for pin in ALL_GPIO_PINS:
        try:
            # Try to set up pin as input with pull-up
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            state = GPIO.input(pin)
            voltage = "3.3V" if state == GPIO.HIGH else "0.0V"
            status = "HIGH" if state == GPIO.HIGH else "LOW "
            results.append((pin, status, voltage, "OK"))
            
        except Exception as e:
            results.append((pin, "---", "---", f"Error: {str(e)[:20]}"))
    
    # Display results in a nice table
    for pin, status, voltage, note in results:
        if "Error" not in note:
            print(f"GPIO {pin:2d}      | {status} | {voltage}     | {note}")
        else:
            print(f"GPIO {pin:2d}      | {status} | {voltage}     | {note}")
    
    print("-" * 70)
    print("\nSummary:")
    high_count = sum(1 for _, status, _, note in results if status == "HIGH" and "Error" not in note)
    low_count = sum(1 for _, status, _, note in results if status == "LOW " and "Error" not in note)
    error_count = sum(1 for _, _, _, note in results if "Error" in note)
    
    print(f"  HIGH pins (3.3V): {high_count}")
    print(f"  LOW pins (0V):    {low_count}")
    print(f"  Errors/Unavail:   {error_count}")
    
    return results

def monitor_specific_pins(pins, duration=10):
    """Monitor specific GPIO pins for changes over time."""
    GPIO.setmode(GPIO.BCM)
    
    print(f"\n{'=' * 70}")
    print(f"Monitoring GPIO pins: {pins}")
    print(f"Duration: {duration} seconds")
    print(f"{'=' * 70}\n")
    
    # Setup pins
    for pin in pins:
        try:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        except Exception as e:
            print(f"Error setting up GPIO {pin}: {e}")
            return
    
    # Get initial states
    last_states = {pin: GPIO.input(pin) for pin in pins}
    
    print("Initial states:")
    for pin, state in last_states.items():
        voltage = "3.3V" if state else "0.0V"
        print(f"  GPIO {pin}: {'HIGH' if state else 'LOW'} ({voltage})")
    
    print("\nMonitoring for changes... (press Ctrl+C to stop)")
    print("-" * 70)
    
    start_time = time.time()
    
    try:
        while time.time() - start_time < duration:
            for pin in pins:
                current_state = GPIO.input(pin)
                if current_state != last_states[pin]:
                    timestamp = time.strftime("%H:%M:%S")
                    old_v = "3.3V" if last_states[pin] else "0.0V"
                    new_v = "3.3V" if current_state else "0.0V"
                    print(f"[{timestamp}] GPIO {pin}: {old_v} → {new_v}")
                    last_states[pin] = current_state
            
            time.sleep(0.01)  # 10ms polling
        
        print(f"\n{'-' * 70}")
        print(f"Monitoring complete after {duration} seconds")
        
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")
    
    print("\nFinal states:")
    for pin in pins:
        state = GPIO.input(pin)
        voltage = "3.3V" if state else "0.0V"
        print(f"  GPIO {pin}: {'HIGH' if state else 'LOW'} ({voltage})")

def main():
    """Main function."""
    if not HAS_GPIO:
        return
    
    try:
        # First, scan all pins
        results = scan_gpio_pins()
        
        # Ask user if they want to monitor specific pins
        print("\n" + "=" * 70)
        print("Options:")
        print("  1. Monitor specific pins for changes (e.g., button testing)")
        print("  2. Exit")
        print("=" * 70)
        
        try:
            choice = input("\nEnter choice (1 or 2): ").strip()
            
            if choice == "1":
                pins_input = input("Enter GPIO pin numbers to monitor (comma-separated, e.g., 0,1,2): ").strip()
                pins = [int(p.strip()) for p in pins_input.split(",")]
                duration = input("Monitor duration in seconds (default 10): ").strip()
                duration = int(duration) if duration else 10
                
                monitor_specific_pins(pins, duration)
        
        except (ValueError, KeyboardInterrupt):
            print("\nInvalid input or interrupted")
    
    finally:
        GPIO.cleanup()
        print("\n[GPIO] Cleanup complete")

if __name__ == "__main__":
    main()
