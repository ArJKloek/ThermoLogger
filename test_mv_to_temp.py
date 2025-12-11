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

# ITS-90 inverse polynomial coefficients for K-type (µV -> °C)
_K_INV_COEFF_NEG = [
    0.0,
    2.5173462e-02,
    -1.1662878e-06,
    -1.0833638e-09,
    -8.9773540e-13,
    -3.7342377e-16,
    -8.6632643e-20,
    -1.0450598e-23,
    -5.1920577e-29,
]

_K_INV_COEFF_MID = [
    0.0,
    5.0835500e-01,
    7.8601060e-08,
    -2.5031310e-10,
    8.3152700e-14,
    -1.2280340e-17,
    9.8040360e-22,
    -4.4130300e-26,
    1.0577340e-30,
    -1.0527550e-35,
]

_K_INV_COEFF_HIGH = [
    -1.318058e+02,
    4.830222e-02,
    -1.646031e-06,
    5.464731e-11,
    -9.650715e-16,
    8.802193e-21,
    -3.110810e-26,
]


def _poly_eval(coeffs, x):
    """Evaluate polynomial via Horner's method."""
    acc = 0.0
    for c in reversed(coeffs):
        acc = acc * x + c
    return acc


def k_type_uv_to_c(uV):
    """Convert K-type thermocouple voltage (µV) to temperature (°C) using ITS-90."""
    if uV < -5891 or uV > 54886:
        raise ValueError('Voltage out of K-type range [-5891..54886] µV')
    if uV < 0:
        coeffs = _K_INV_COEFF_NEG
    elif uV <= 20644:
        coeffs = _K_INV_COEFF_MID
    else:
        coeffs = _K_INV_COEFF_HIGH
    return _poly_eval(coeffs, uV)


def k_type_mv_to_c(mV):
    """Convert K-type thermocouple voltage (mV) to temperature (°C) using ITS-90."""
    return k_type_uv_to_c(mV * 1000.0)


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
            calc_c = k_type_mv_to_c(mv)
            board_c = card.get_temp(ch)
            now = datetime.now().strftime('%H:%M:%S')
            print(f"{now:<10} | {mv:8.3f} | {calc_c:8.2f} | {board_c:9.2f}")
    except KeyboardInterrupt:
        print("\nDone")


if __name__ == "__main__":
    main()
