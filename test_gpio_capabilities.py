#!/usr/bin/env python3
"""
Test script to detect which GPIO pins can be used and which have errors.
Specifically tests pull-up/pull-down configurations.
"""

import RPi.GPIO as GPIO
import time

# All GPIO pins in BOARD numbering (physical pin numbers)
# Valid pins are typically: 3, 5, 7, 8, 10, 11, 12, 13, 15, 16, 18, 19, 21, 22, 23, 24, 26, 29, 31, 32, 33, 35, 36, 37, 38, 40
ALL_BOARD_PINS = list(range(1, 41))  # Test pins 1-40

def test_pin_setup(pin, pull_mode_name, pull_mode):
    """Test if a pin can be set up with a specific pull mode."""
    try:
        GPIO.setup(pin, GPIO.IN, pull_up_down=pull_mode)
        # Try to read the pin
        state = GPIO.input(pin)
        # Cleanup this pin
        GPIO.cleanup(pin)
        return True, state
    except Exception as e:
        error_msg = str(e)
        # Extract just the important part of the error
        if "invalid" in error_msg.lower():
            return False, "Invalid pin"
        elif "direction" in error_msg.lower():
            return False, "Direction error"
        elif "permission" in error_msg.lower():
            return False, "Permission error"
        else:
            return False, error_msg[:30]

def scan_all_pins():
    """Scan all GPIO pins and test their capabilities."""
    print("=" * 80)
    print("GPIO Pin Capability Scanner - Raspberry Pi")
    print("=" * 80)
    print("\nTesting all pins with BOARD numbering (physical pins)...")
    print("\nFormat: Pin# | Pull-UP | Pull-DOWN | No-Pull | Notes")
    print("-" * 80)
    
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    
    usable_pins = []
    
    for pin in ALL_BOARD_PINS:
        # Test with pull-up
        success_up, result_up = test_pin_setup(pin, "PUD_UP", GPIO.PUD_UP)
        
        # Test with pull-down
        success_down, result_down = test_pin_setup(pin, "PUD_DOWN", GPIO.PUD_DOWN)
        
        # Test with no pull
        success_off, result_off = test_pin_setup(pin, "PUD_OFF", GPIO.PUD_OFF)
        
        # Format results
        up_str = "✓ OK" if success_up else f"✗ {result_up}"
        down_str = "✓ OK" if success_down else f"✗ {result_down}"
        off_str = "✓ OK" if success_off else f"✗ {result_off}"
        
        # Determine if pin is usable
        if success_up or success_down or success_off:
            usable_pins.append((pin, success_up, success_down, success_off))
            note = "USABLE"
        else:
            note = "NOT USABLE / POWER/GND"
        
        print(f"Pin {pin:2d}  | {up_str:20s} | {down_str:20s} | {off_str:20s} | {note}")
    
    # Summary
    print("-" * 80)
    print("\n" + "=" * 80)
    print("SUMMARY - USABLE GPIO PINS:")
    print("=" * 80)
    print("\nPins that work with PULL-UP (recommended for buttons to GND):")
    pullup_pins = [pin for pin, up, down, off in usable_pins if up]
    print(f"  {pullup_pins}")
    
    print("\nPins that work with PULL-DOWN (for buttons to 3.3V):")
    pulldown_pins = [pin for pin, up, down, off in usable_pins if down]
    print(f"  {pulldown_pins}")
    
    print("\nPins that work WITHOUT pull resistors:")
    nopull_pins = [pin for pin, up, down, off in usable_pins if off]
    print(f"  {nopull_pins}")
    
    print("\n" + "=" * 80)
    print("RECOMMENDATION FOR YOUR 4 BUTTONS:")
    print("=" * 80)
    
    # Suggest 4 good pins for buttons
    suggested_pins = []
    common_button_pins = [10, 12, 16, 18, 22, 24, 26, 32, 36, 38, 40]
    
    for pin in common_button_pins:
        if pin in pullup_pins:
            suggested_pins.append(pin)
        if len(suggested_pins) >= 4:
            break
    
    if len(suggested_pins) >= 4:
        print(f"\nSuggested pins for 4 buttons (with pull-up): {suggested_pins[:4]}")
        print("\nExample code:")
        print("```python")
        print("GPIO.setmode(GPIO.BOARD)")
        for i, pin in enumerate(suggested_pins[:4], 1):
            print(f"GPIO.setup({pin}, GPIO.IN, pull_up_down=GPIO.PUD_UP)")
            print(f"GPIO.add_event_detect({pin}, GPIO.FALLING, callback=lambda ch: button_callback(ch, {i}), bouncetime=200)")
        print("```")
    else:
        print("\nNot enough suitable pins found. Use pins from the pull-up list above.")
    
    return usable_pins

def test_specific_pins(pins):
    """Test specific pins in detail."""
    print("\n" + "=" * 80)
    print(f"DETAILED TEST FOR PINS: {pins}")
    print("=" * 80)
    
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    
    for pin in pins:
        print(f"\nTesting Pin {pin}:")
        print("-" * 40)
        
        # Test pull-up
        print(f"  Testing with PULL-UP...", end=" ")
        success, result = test_pin_setup(pin, "PUD_UP", GPIO.PUD_UP)
        if success:
            print(f"✓ OK (initial state: {'HIGH' if result else 'LOW'})")
        else:
            print(f"✗ FAILED: {result}")
        
        # Test pull-down
        print(f"  Testing with PULL-DOWN...", end=" ")
        success, result = test_pin_setup(pin, "PUD_DOWN", GPIO.PUD_DOWN)
        if success:
            print(f"✓ OK (initial state: {'HIGH' if result else 'LOW'})")
        else:
            print(f"✗ FAILED: {result}")
        
        # Test no pull
        print(f"  Testing with NO-PULL...", end=" ")
        success, result = test_pin_setup(pin, "PUD_OFF", GPIO.PUD_OFF)
        if success:
            print(f"✓ OK (initial state: {'HIGH' if result else 'LOW'})")
        else:
            print(f"✗ FAILED: {result}")

def main():
    """Main function."""
    try:
        # First, scan all pins
        usable_pins = scan_all_pins()
        
        # Ask if user wants to test specific pins
        print("\n" + "=" * 80)
        print("Would you like to test specific pins in detail?")
        choice = input("Enter pin numbers (comma-separated) or press Enter to exit: ").strip()
        
        if choice:
            pins = [int(p.strip()) for p in choice.split(",")]
            test_specific_pins(pins)
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        GPIO.cleanup()
        print("\n[GPIO] Cleanup complete")

if __name__ == "__main__":
    main()
