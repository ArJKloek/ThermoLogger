#!/usr/bin/env python3
"""
Print mV readings for all 8 thermocouple channels in a single row, updated every second.
Usage: python3 test_mv_all_channels.py
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
    header = ['Time'] + [f"CH{i}" for i in range(1, ch_count + 1)]
    print(" | ".join(f"{h:>8}" for h in header))
    print('-' * (11 * (ch_count + 1)))

    try:
        while True:
            now = datetime.now().strftime('%H:%M:%S')
            row = [now]
            for ch in range(1, ch_count + 1):
                try:
                    mv = card.get_mv(ch)
                    row.append(f"{mv:8.3f}")
                except Exception as e:
                    row.append("   ERR  ")
            print(" | ".join(row))
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDone")


if __name__ == "__main__":
    main()
