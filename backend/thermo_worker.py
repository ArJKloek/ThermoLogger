from __future__ import annotations

import math
import random
import time
from typing import List

from PyQt5.QtCore import QThread, pyqtSignal

try:
    from perlin_noise import PerlinNoise
    HAS_PERLIN = True
except ImportError:
    HAS_PERLIN = False


class DummySMtc:
    """Synthetic thermocouple reader using Perlin noise for realistic temperature variation."""

    def __init__(self, channels: int = 8):
        self.channels = channels
        self.time_scale = 0.001  # Very slow time scale for extremely smooth variation
        if HAS_PERLIN:
            # Create independent Perlin noise generators for each channel with more octaves for smoothness
            self.noise_generators = [PerlinNoise(octaves=1, seed=ch) for ch in range(channels)]
        else:
            self.noise_generators = None

    def get_temp(self, channel: int) -> float:
        """Return a realistic temperature value using Perlin noise."""
        if channel < 1 or channel > self.channels:
            return float("nan")
        
        ch_idx = channel - 1
        base_temp = 20.0 + ch_idx * 2.0  # Slight offset per channel
        
        if HAS_PERLIN and self.noise_generators:
            # Use Perlin noise for smooth, realistic variations
            noise_val = self.noise_generators[ch_idx](time.time() * self.time_scale)
            temp = base_temp + 10.0 * noise_val
        else:
            # Fallback to very smooth sine wave if perlin_noise not installed
            phase = ch_idx * 0.6
            temp = base_temp + 2.5 * math.sin(time.time() / 15.0 + phase)
        
        return round(temp, 1)
    
    def get_mv(self, channel: int) -> float:
        """Return a dummy voltage value (not used in dummy mode)."""
        return 0.0
    
    def check_unplugged_channels(self) -> List[int]:
        """Check for unplugged channels (returns empty list for dummy mode)."""
        return []


class ThermoThread(QThread):
    """Background reader that emits temperature readings periodically."""

    reading_ready = pyqtSignal(list)
    source_changed = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, interval_sec: float = 1.0, channels: int = 8, settings_manager=None, parent=None):
        super().__init__(parent)
        self.interval_sec = max(0.1, float(interval_sec))
        self.channels = channels
        self.settings_manager = settings_manager
        self._stop = False
        self._startup_error = ""
        self.device = None
        self.source = "unknown"
        self.unplugged_channels = []  # List of channels with 0.00 mV (unplugged)
        self._init_device()

    def _init_device(self) -> None:
        """Try to use real hardware; fall back to the dummy generator."""
        try:
            import sm_tc

            self.device = sm_tc.SMtc(0)
            self.source = "hardware"
            
            # Configure thermocouple types from settings if available
            if self.settings_manager:
                # Mapping from settings letter to sm_tc constants
                tc_type_map = {
                    'B': 0,  # _TC_TYPE_B
                    'E': 1,  # _TC_TYPE_E
                    'J': 2,  # _TC_TYPE_J
                    'K': 3,  # _TC_TYPE_K
                    'N': 4,  # _TC_TYPE_N
                    'R': 5,  # _TC_TYPE_R
                    'S': 6,  # _TC_TYPE_S
                    'T': 7   # _TC_TYPE_T
                }
                
                for channel in range(self.channels):
                    tc_type_letter = self.settings_manager.get_channel_type(channel)
                    if tc_type_letter in tc_type_map:
                        tc_type_code = tc_type_map[tc_type_letter]
                        try:
                            self.device.set_sensor_type(channel + 1, tc_type_code)
                            print(f"[HARDWARE] Set CH{channel + 1} to Type {tc_type_letter}")
                        except Exception as e:
                            print(f"[HARDWARE] Failed to set CH{channel + 1} type: {e}")
            
            # Check for unplugged channels (0.00 mV voltage)
            print("[HARDWARE] Checking for unplugged channels...")
            self.unplugged_channels = []
            for ch in range(1, self.channels + 1):
                try:
                    mv = self.device.get_mv(ch)
                    if mv == 0.0:
                        self.unplugged_channels.append(ch)
                        print(f"[HARDWARE] CH{ch} unplugged (0.00 mV)")
                except Exception as e:
                    print(f"[HARDWARE] Error checking CH{ch}: {e}")
            
            if self.unplugged_channels:
                unplugged_str = ", ".join([f"CH{ch}" for ch in self.unplugged_channels])
                print(f"[HARDWARE] Unplugged channels: {unplugged_str}")
            
        except Exception as exc:  # pragma: no cover - depends on hardware
            self.device = DummySMtc(self.channels)
            self.source = "dummy"
            self._startup_error = str(exc)

    def run(self) -> None:  # pragma: no cover - involves timing and threads
        if self._startup_error:
            self.error.emit(f"Falling back to dummy: {self._startup_error}")
        
        self.source_changed.emit(self.source)
        
        # Only show noise source info if we're using dummy data
        if self.source == "dummy":
            noise_source = "Perlin noise" if HAS_PERLIN else "sine wave (fallback)"
            self.error.emit(f"Using {noise_source} for dummy data")

        while not self._stop:
            readings: List[float] = []
            for idx in range(self.channels):
                try:
                    temp = self.device.get_temp(idx + 1)
                    readings.append(temp)
                except Exception as exc:
                    self.error.emit(str(exc))
                    readings.append(float("nan"))
            self.reading_ready.emit(readings)
            self.msleep(int(self.interval_sec * 1000))

    def stop(self, timeout_ms: int = 1000) -> None:
        self._stop = True
        self.wait(timeout_ms)
