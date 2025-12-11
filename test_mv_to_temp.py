#!/usr/bin/env python3
"""Quick check: convert channel mV to °C using ITS-90 inverse poly (K-type)."""

import sys
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

    ch = 1
    if len(sys.argv) > 1:
        try:
            ch = int(sys.argv[1])
        except ValueError:
            print("Usage: python3 test_mv_to_temp.py [channel]")
            sys.exit(1)

    print(f"Reading channel {ch} (press Ctrl+C to stop)...")
    print(f"{'Time':<10} | {'mV':>8} | {'Calc °C':>8} | {'Board °C':>9}")
    print('-' * 45)

    try:
        while True:
            mv = card.get_mv(ch)
            calc_c = sm_tc.k_type_mv_to_c(mv)
            board_c = card.get_temp(ch)
            now = datetime.now().strftime('%H:%M:%S')
            print(f"{now:<10} | {mv:8.3f} | {calc_c:8.2f} | {board_c:9.2f}")
    except KeyboardInterrupt:
        print("\nDone")


if __name__ == "__main__":
    main()
