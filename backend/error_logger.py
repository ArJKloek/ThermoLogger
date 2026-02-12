"""Comprehensive error and event logging for ThermoLogger."""

import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler


class ErrorLogger:
    """Centralized error logging system for the entire application."""

    _instance = None
    _logger = None

    def __new__(cls):
        """Singleton pattern to ensure only one instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, log_dir: str | Path = "Data/logs", max_bytes: int = 5 * 1024 * 1024):
        """Initialize the error logger.
        
        Args:
            log_dir: Directory to store log files
            max_bytes: Maximum size of log file before rotation (default 5MB)
        """
        if self._initialized:
            return

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.max_bytes = max_bytes
        self._setup_logging()
        self._initialized = True

    def _setup_logging(self):
        """Set up logging configuration with both file and console handlers."""
        # Create main logger - store in class variable, not instance
        logger = logging.getLogger("ThermoLogger")
        logger.setLevel(logging.DEBUG)

        # Remove any existing handlers
        logger.handlers.clear()

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # File handler with rotation
        log_file = self.log_dir / "thermologger.log"
        try:
            file_handler = RotatingFileHandler(
                str(log_file),
                maxBytes=self.max_bytes,
                backupCount=5
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not create file handler for logging: {e}", file=sys.stderr)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Set class variable
        ErrorLogger._logger = logger

    @classmethod
    def get_logger(cls) -> logging.Logger:
        """Get the logger instance."""
        if cls._logger is None:
            # Create singleton instance to initialize logging
            try:
                instance = cls()
            except Exception as e:
                print(f"FATAL: Could not initialize ErrorLogger: {e}", file=sys.stderr)
                # Return a minimal fallback logger
                return logging.getLogger("ThermoLogger_Fallback")
        
        if cls._logger is None:
            print(f"FATAL: Logger still None after initialization", file=sys.stderr)
            # Return a minimal fallback logger
            return logging.getLogger("ThermoLogger_Fallback")
            
        return cls._logger

    @staticmethod
    def log_debug(message: str, **kwargs):
        """Log debug message."""
        logger = ErrorLogger.get_logger()
        logger.debug(message, **kwargs)

    @staticmethod
    def log_info(message: str, **kwargs):
        """Log info message."""
        logger = ErrorLogger.get_logger()
        logger.info(message, **kwargs)

    @staticmethod
    def log_warning(message: str, **kwargs):
        """Log warning message."""
        logger = ErrorLogger.get_logger()
        logger.warning(message, **kwargs)

    @staticmethod
    def log_error(message: str, exception: Exception = None, **kwargs):
        """Log error message with optional exception details."""
        logger = ErrorLogger.get_logger()
        if exception:
            logger.error(message, exc_info=True, **kwargs)
        else:
            logger.error(message, **kwargs)

    @staticmethod
    def log_critical(message: str, exception: Exception = None, **kwargs):
        """Log critical message with optional exception details."""
        logger = ErrorLogger.get_logger()
        if exception:
            logger.critical(message, exc_info=True, **kwargs)
        else:
            logger.critical(message, **kwargs)

    @staticmethod
    def log_hardware_event(channel: int, status: str, details: str = ""):
        """Log hardware-related events (channel connect/disconnect)."""
        logger = ErrorLogger.get_logger()
        message = f"[HARDWARE] Channel {channel}: {status}"
        if details:
            message += f" - {details}"
        logger.info(message)

    @staticmethod
    def log_reading_error(channel: int, error: str):
        """Log temperature reading errors."""
        logger = ErrorLogger.get_logger()
        logger.warning(f"[READING] Channel {channel} failed: {error}")

    @staticmethod
    def log_gpio_event(button_num: int, event: str, details: str = ""):
        """Log GPIO button events."""
        logger = ErrorLogger.get_logger()
        message = f"[GPIO] Button {button_num}: {event}"
        if details:
            message += f" - {details}"
        logger.info(message)

    @staticmethod
    def log_communication_error(message: str, exception: Exception = None):
        """Log communication errors with device."""
        logger = ErrorLogger.get_logger()
        if exception:
            logger.error(f"[COMM] {message}", exc_info=True)
        else:
            logger.error(f"[COMM] {message}")
