#!/usr/bin/env python3
"""
Display thermocouple temperature (board reading) vs on-board thermistor temperature for all 8 channels.
Shows how the thermistor (cold-junction reference) compares to the thermocouple reading on each channel.

Usage: python3 test_thermistor_vs_board_temp.py
"""

import sys
import time
from datetime import datetime

try:
    import sm_tc
except ImportError as e:
    print(f"ERROR: Could not import sm_tc: {e}")
    print("Install with: cd smtc/python && sudo pip3 install --upgrade --force-reinstall . --break-system-packages")
    sys.exit(1)


def main():
    try:
        card = sm_tc.SMtc(stack=0, i2c=1)
    except Exception as e:
        print(f"FATAL: cannot init SMtc: {e}")
        sys.exit(1)

    ch_count = 8
    
    # Build header with alternating columns for each channel
    header = ['Time']
    for ch in range(1, ch_count + 1):
        header.append(f"CH{ch}-Board")
        header.append(f"CH{ch}-Therm")
    
    print(" | ".join(f"{h:>10}" for h in header))
    print('-' * (13 + (ch_count * 22)))

    try:
        while True:
            now = datetime.now().strftime('%H:%M:%S')
            row = [now]
            
            for ch in range(1, ch_count + 1):
                try:
                    board_c = card.get_temp(ch)
                    therm_c = card.get_thermistor_temp(ch)
                    row.append(f"{board_c:10.2f}")
                    row.append(f"{therm_c:10.2f}")
                except Exception as e:
                    row.append("      ERR")
                    row.append("      ERR")
            
            print(" | ".join(row))
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDone")


if __name__ == "__main__":
    main()
