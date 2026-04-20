"""Logging utilities for pdf2md."""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class Logger:
    """Custom logger for pdf2md with both standard logging and loguru support."""

    _instance: Optional["Logger"] = None
    _initialized: bool = False

    def __new__(cls) -> "Logger":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not self._initialized:
            self._setup_logger()
            Logger._initialized = True

    def _setup_logger(self) -> None:
        """Setup the logger configuration."""
        # Use standard logging for compatibility
        self.logger = logging.getLogger("pdf2md")
        self.logger.setLevel(logging.DEBUG)

        # Create logs directory if it doesn't exist
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)

        # Create log file with date (one file per day)
        date_str = datetime.now().strftime("%Y%m%d")
        log_file = self.logs_dir / f"pdf2md_{date_str}.log"

        # Formatter with class, line number, and full timestamp
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # File handler for detailed logging
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Console handler with simpler format
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        self.log_file = log_file
        self.info(f"Logging initialized. Log file: {log_file}")

    def info(self, msg: str, *args, **kwargs) -> None:
        """Log an info message."""
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        """Log a warning message."""
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        """Log an error message."""
        self.logger.error(msg, *args, **kwargs)

    def debug(self, msg: str, *args, **kwargs) -> None:
        """Log a debug message."""
        self.logger.debug(msg, *args, **kwargs)

    def set_level(self, level: str) -> None:
        """Set the logging level.

        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.logger.setLevel(getattr(logging, level.upper()))

    def get_log_file(self) -> Optional[Path]:
        """Get the current log file path.

        Returns:
            Path to the log file, or None if not available.
        """
        return getattr(self, "log_file", None)

    def get_logs_dir(self) -> Path:
        """Get the logs directory path.

        Returns:
            Path to the logs directory.
        """
        return self.logs_dir


# Global logger instance
logger = Logger()


def get_logger() -> Logger:
    """Get the global logger instance.

    Returns:
        The Logger singleton instance.
    """
    return logger