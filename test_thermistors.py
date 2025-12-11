#!/usr/bin/env python3
"""
Test script for reading on-board thermistor/RTD temperatures from SMTC card.

Tests all 8 thermistor channels with formatted table output.
Run on Raspberry Pi with: python3 test_thermistors.py
"""

import sys
import time
from datetime import datetime

try:
    import sm_tc
except ImportError as e:
    print(f"ERROR: Could not import SMtc library: {e}")
    print("Make sure to install the sm_tc library:")
    print("  cd smtc/python && sudo pip3 install --upgrade .")
    sys.exit(1)


def main():
    """Test thermistor temperature reading."""
    try:
        # Initialize SMTC card
        # Stack level 0 = address 0x16, I2C bus 1
        card = sm_tc.SMtc(stack=0, i2c=1)
        print("✓ SMTC card initialized successfully")
        print()
        
        # Display header
        print(f"{'Time':<10} | {'CH1':>6} | {'CH2':>6} | {'CH3':>6} | {'CH4':>6} | {'CH5':>6} | {'CH6':>6} | {'CH7':>6} | {'CH8':>6}")
        print("-" * 90)
        
        # Read thermistors continuously
        iteration = 0
        while True:
            try:
                timestamp = datetime.now().strftime("%H:%M:%S")
                temps = []
                
                # Read all 8 thermistor channels
                for channel in range(1, 9):
                    try:
                        temp = card.get_thermistor_temp(channel)
                        temps.append(f"{temp:6.1f}")
                    except Exception as e:
                        print(f"ERROR reading channel {channel}: {e}")
                        temps.append("  ERR ")
                
                # Print formatted row
                row = f"{timestamp:<10} | " + " | ".join(temps)
                print(row)
                
                iteration += 1
                time.sleep(1)
                
                # Optional: Exit after N iterations for testing
                # if iteration >= 5:
                #     break
                    
            except KeyboardInterrupt:
                print("\n\nShutdown requested by user")
                break
            except Exception as e:
                print(f"\nERROR during read: {e}")
                print("Troubleshooting:")
                print("  - Check I2C connection with: i2cdetect -y 1")
                print("  - Verify SMTC card is present at address 0x16")
                print("  - Check thermistor channels are properly connected")
                break
    
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        print("\nTroubleshooting:")
        print("  - Ensure running as root: sudo python3 test_thermistors.py")
        print("  - Verify I2C is enabled: raspi-config > Interface Options > I2C")
        print("  - Check SMTC library is installed: pip3 list | grep sm-tc")
        print("  - Verify stack level: SMTC(stack=0) for I2C address 0x16")
        print("    If card is at different address (0x17-0x1E), use stack 1-6")
        sys.exit(1)


if __name__ == "__main__":
    main()
