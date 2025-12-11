#!/usr/bin/env python3
"""
Verify SMTC readings by computing temperature from measured mV (K-type ITS-90).

Reads a channel's millivolts via sm_tc, converts to °C using the published inverse
polynomial, and shows both the computed temperature and the board-reported °C.

Usage:
  python3 mv_to_temp_verify.py [channel]

Default channel: 1
"""

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
    2.508355e-02,
    7.860106e-08,
    -2.503131e-10,
    8.315270e-14,
    -1.228034e-17,
    9.804036e-22,
    -4.413030e-26,
    1.057734e-30,
    -1.052755e-35,
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
            print("Usage: python3 mv_to_temp_verify.py [channel]")
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
