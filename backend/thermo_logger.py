"""CSV logging for temperature sensor readings."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional


class ThermoLogger:
    """Handles CSV logging of temperature readings."""

    def __init__(self, data_dir: str | Path = "Data"):
        self.data_dir = Path(data_dir)
        self.csv_file = None
        self.csv_writer = None
        self.is_logging = False
        self.channels = 8

        # Create Data directory if it doesn't exist
        self.data_dir.mkdir(exist_ok=True)

    def start_logging(self) -> bool:
        """Start logging with a new CSV file for the current date."""
        if self.is_logging:
            logging.warning("Logging already active")
            return False

        try:
            # Create filename based on current date
            today = datetime.now().strftime("%Y-%m-%d")
            self.csv_file = self.data_dir / f"temperatures_{today}.csv"

            # Check if file already exists to determine if we need to write header
            file_exists = self.csv_file.exists()

            # Open file in append mode
            self.csv_file.open("a", newline="").close()  # Ensure file exists
            self.file_handle = open(str(self.csv_file), "a", newline="")
            
            # Prepare CSV header
            header = ["Timestamp"] + [f"CH{i+1}" for i in range(self.channels)]

            # Only write header if file is new
            if not file_exists:
                self.csv_writer = csv.writer(self.file_handle)
                self.csv_writer.writerow(header)
                print(f"[LOGGING] Created new log file: {self.csv_file}")
                logging.info(f"Created new log file: {self.csv_file}")
            else:
                self.csv_writer = csv.writer(self.file_handle)
                print(f"[LOGGING] Appending to existing log file: {self.csv_file}")
                logging.info(f"Appending to existing log file: {self.csv_file}")

            self.is_logging = True
            print(f"[LOGGING] Started logging to {self.csv_file}")
            logging.info(f"Started logging to {self.csv_file}")
            return True

        except Exception as e:
            print(f"[LOGGING ERROR] Error starting logging: {e}")
            logging.error(f"Error starting logging: {e}")
            self.is_logging = False
            return False

    def log_reading(self, readings: List[float]) -> None:
        """Log a temperature reading to CSV."""
        if not self.is_logging or not self.csv_writer:
            return

        try:
            timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            row = [timestamp] + readings
            self.csv_writer.writerow(row)
            self.file_handle.flush()  # Flush to ensure data is written
        except Exception as e:
            logging.error(f"Error logging reading: {e}")

    def stop_logging(self) -> None:
        """Stop logging and close the CSV file."""
        if not self.is_logging:
            return

        try:
            if self.file_handle:
                self.file_handle.close()
            self.is_logging = False
            logging.info("Stopped logging")
        except Exception as e:
            logging.error(f"Error stopping logging: {e}")

    def get_log_file_path(self) -> Optional[Path]:
        """Return the current log file path."""
        return self.csv_file if self.is_logging else None
