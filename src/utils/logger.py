"""Structured logging setup for audit trail and debugging."""
import logging
import json
from logging import LogRecord
from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional context."""

    def add_fields(self, log_record: dict, record: LogRecord, message_dict: dict) -> None:
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)

        # Add timestamp in ISO format
        log_record['timestamp'] = self.formatTime(record, self.datefmt)

        # Add log level
        log_record['level'] = record.levelname

        # Add module and function information
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno


def setup_logging(level: str = "INFO"):
    """
    Setup structured JSON logging for audit trail.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(level)

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create console handler with JSON formatter
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # Use JSON formatter for structured logging
    formatter = CustomJsonFormatter()
    console_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(console_handler)

    return logger


# Get or create logger
def get_logger(name: str) -> logging.Logger:
    """Get logger instance."""
    return logging.getLogger(name)
