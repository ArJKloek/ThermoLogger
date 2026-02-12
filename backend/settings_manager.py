"""Settings manager for ThermoLogger configuration."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List

from backend.error_logger import ErrorLogger


class SettingsManager:
    """Manages application settings including thermocouple types."""

    THERMOCOUPLE_TYPES = ['K', 'J', 'T', 'E', 'N', 'S', 'R', 'B']
    DEFAULT_TYPE = 'K'

    def __init__(self, settings_file: str | Path = "settings.json"):
        self.settings_file = Path(settings_file)
        self.channel_types: List[str] = [self.DEFAULT_TYPE] * 8
        self.channel_enabled: List[bool] = [True] * 8  # All channels enabled by default
        self.show_preview: bool = True  # Show e-paper preview by default
        self.load_settings()

    def load_settings(self) -> bool:
        """Load settings from JSON file."""
        if not self.settings_file.exists():
            msg = f"Settings file not found at {self.settings_file}, using defaults"
            logging.info(msg)
            ErrorLogger.log_info(f"[SETTINGS] {msg}")
            print(f"[SETTINGS] No settings file found, using defaults")
            return False

        try:
            with open(self.settings_file, 'r') as f:
                data = json.load(f)
                self.channel_types = data.get('channel_types', [self.DEFAULT_TYPE] * 8)
                self.channel_enabled = data.get('channel_enabled', [True] * 8)
                self.show_preview = data.get('show_preview', True)
                
                # Ensure we have exactly 8 channels
                while len(self.channel_types) < 8:
                    self.channel_types.append(self.DEFAULT_TYPE)
                self.channel_types = self.channel_types[:8]
                
                while len(self.channel_enabled) < 8:
                    self.channel_enabled.append(True)
                self.channel_enabled = self.channel_enabled[:8]
                
                msg = f"Settings loaded from {self.settings_file}"
                logging.info(msg)
                ErrorLogger.log_info(f"[SETTINGS] {msg}")
                print(f"[SETTINGS] Loaded from {self.settings_file}")
                print(f"[SETTINGS] Channel types: {self.channel_types}")
                print(f"[SETTINGS] Channel enabled: {self.channel_enabled}")
                return True
        except Exception as e:
            error_msg = f"Error loading settings: {e}"
            logging.error(error_msg)
            ErrorLogger.log_error(f"[SETTINGS] {error_msg}", e)
            print(f"[SETTINGS ERROR] Failed to load: {e}")
            return False

    def save_settings(self) -> bool:
        """Save settings to JSON file."""
        try:
            data = {
                'channel_types': self.channel_types,
                'channel_enabled': self.channel_enabled,
                'show_preview': self.show_preview
            }
            with open(self.settings_file, 'w') as f:
                json.dump(data, f, indent=2)
            msg = f"Settings saved to {self.settings_file}"
            logging.info(msg)
            ErrorLogger.log_info(f"[SETTINGS] {msg}")
            print(f"[SETTINGS] Saved to {self.settings_file}")
            print(f"[SETTINGS] Channel types: {self.channel_types}")
            print(f"[SETTINGS] Channel enabled: {self.channel_enabled}")
            return True
        except Exception as e:
            error_msg = f"Error saving settings: {e}"
            logging.error(error_msg)
            ErrorLogger.log_error(f"[SETTINGS] {error_msg}", e)
            print(f"[SETTINGS ERROR] Failed to save: {e}")
            return False

    def get_channel_type(self, channel: int) -> str:
        """Get thermocouple type for a specific channel (0-7)."""
        if 0 <= channel < 8:
            return self.channel_types[channel]
        return self.DEFAULT_TYPE

    def set_channel_type(self, channel: int, tc_type: str) -> bool:
        """Set thermocouple type for a specific channel (0-7)."""
        if 0 <= channel < 8 and tc_type in self.THERMOCOUPLE_TYPES:
            self.channel_types[channel] = tc_type
            return True
        return False

    def get_all_channel_types(self) -> List[str]:
        """Get all channel thermocouple types."""
        return self.channel_types.copy()

    def is_channel_enabled(self, channel: int) -> bool:
        """Check if a channel is enabled (0-7)."""
        if 0 <= channel < 8:
            return self.channel_enabled[channel]
        return False

    def set_channel_enabled(self, channel: int, enabled: bool) -> bool:
        """Enable or disable a channel (0-7)."""
        if 0 <= channel < 8:
            self.channel_enabled[channel] = enabled
            return True
        return False

    def get_enabled_channels(self) -> List[int]:
        """Get list of enabled channel numbers (0-7)."""
        return [i for i in range(8) if self.channel_enabled[i]]

    def set_all_channel_types(self, types: List[str]) -> bool:
        """Set all channel thermocouple types."""
        if len(types) != 8:
            return False
        if not all(t in self.THERMOCOUPLE_TYPES for t in types):
            return False
        self.channel_types = types.copy()
        return True
