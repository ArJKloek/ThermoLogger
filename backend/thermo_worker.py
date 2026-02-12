from __future__ import annotations

import math
import random
import time
from typing import List

from PyQt5.QtCore import QThread, pyqtSignal

from backend.error_logger import ErrorLogger

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
    unplugged_changed = pyqtSignal(list)  # Emits updated unplugged channels list
    check_complete = pyqtSignal()  # Emits when thermocouple check completes (regardless of changes)

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
        self._check_counter = 0  # Counter for periodic unplugged checks
        self._check_interval = 10  # Check every 10 readings (~10 seconds)
        self._init_device()

    def _init_device(self) -> None:
        """Try to use real hardware; fall back to the dummy generator."""
        try:
            import sm_tc

            self.device = sm_tc.SMtc(0)
            self.source = "hardware"
            ErrorLogger.log_info("Initialized hardware SMtc device")
            
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
                            ErrorLogger.log_info(f"Set CH{channel + 1} to Type {tc_type_letter}")
                        except Exception as e:
                            ErrorLogger.log_error(f"Failed to set CH{channel + 1} type", e)
            
            # Check for unplugged channels (0.00 mV voltage)
            ErrorLogger.log_info("Checking for unplugged channels...")
            self.unplugged_channels = []
            for ch in range(1, self.channels + 1):
                try:
                    mv = self.device.get_mv(ch)
                    if mv == 0.0:
                        self.unplugged_channels.append(ch)
                        ErrorLogger.log_hardware_event(ch, "unplugged", "0.00 mV")
                except Exception as e:
                    ErrorLogger.log_error(f"Error checking CH{ch} voltage", e)
            
            if self.unplugged_channels:
                unplugged_str = ", ".join([f"CH{ch}" for ch in self.unplugged_channels])
                ErrorLogger.log_info(f"Unplugged channels detected: {unplugged_str}")
            
        except Exception as exc:  # pragma: no cover - depends on hardware
            self.device = DummySMtc(self.channels)
            self.source = "dummy"
            self._startup_error = str(exc)
            ErrorLogger.log_warning(f"Hardware initialization failed, falling back to dummy mode: {exc}", exc)

    def _check_unplugged_status(self) -> None:
        """Check voltage on all channels and update unplugged list if changed."""
        if self.source != "hardware":
            return
        
        try:
            current_unplugged = []
            for ch in range(1, self.channels + 1):
                try:
                    mv = self.device.get_mv(ch)
                    if mv == 0.0:
                        current_unplugged.append(ch)
                except Exception as e:
                    ErrorLogger.log_error(f"Error checking voltage on CH{ch}", e)
            
            # Check if the unplugged list changed
            if set(current_unplugged) != set(self.unplugged_channels):
                # Find newly connected channels
                newly_connected = set(self.unplugged_channels) - set(current_unplugged)
                # Find newly disconnected channels
                newly_disconnected = set(current_unplugged) - set(self.unplugged_channels)
                
                if newly_connected:
                    connected_str = ", ".join([f"CH{ch}" for ch in sorted(newly_connected)])
                    ErrorLogger.log_hardware_event(list(newly_connected)[0], "connected", connected_str)
                
                if newly_disconnected:
                    disconnected_str = ", ".join([f"CH{ch}" for ch in sorted(newly_disconnected)])
                    ErrorLogger.log_hardware_event(list(newly_disconnected)[0], "disconnected", disconnected_str)
                
                # Update the list and emit signal
                self.unplugged_channels = current_unplugged
                self.unplugged_changed.emit(self.unplugged_channels)
        except Exception as e:
            ErrorLogger.log_error("Error checking unplugged status", e)
        finally:
            # Always emit check_complete, even if nothing changed
            self.check_complete.emit()

    def run(self) -> None:  # pragma: no cover - involves timing and threads
        if self._startup_error:
            error_msg = f"Falling back to dummy: {self._startup_error}"
            self.error.emit(error_msg)
            ErrorLogger.log_warning(error_msg)
        
        self.source_changed.emit(self.source)
        ErrorLogger.log_info(f"Temperature reading thread started, source: {self.source}")
        
        # Only show noise source info if we're using dummy data
        if self.source == "dummy":
            noise_source = "Perlin noise" if HAS_PERLIN else "sine wave (fallback)"
            msg = f"Using {noise_source} for dummy data"
            self.error.emit(msg)
            ErrorLogger.log_info(msg)

        while not self._stop:
            readings: List[float] = []
            for idx in range(self.channels):
                try:
                    temp = self.device.get_temp(idx + 1)
                    readings.append(temp)
                except Exception as exc:
                    error_msg = str(exc)
                    self.error.emit(error_msg)
                    ErrorLogger.log_reading_error(idx + 1, error_msg)
                    readings.append(float("nan"))
            self.reading_ready.emit(readings)
            
            # Periodically check for unplugged channel changes
            self._check_counter += 1
            if self._check_counter >= self._check_interval:
                self._check_counter = 0
                self._check_unplugged_status()
            
            self.msleep(int(self.interval_sec * 1000))

    def stop(self, timeout_ms: int = 1000) -> None:
        self._stop = True
        self.wait(timeout_ms)
