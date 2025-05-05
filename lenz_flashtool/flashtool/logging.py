r'''
 _     _____ _   _ _____   _____ _   _  ____ ___  ____  _____ ____  ____
| |   | ____| \ | |__  /  | ____| \ | |/ ___/ _ \|  _ \| ____|  _ \/ ___|
| |   |  _| |  \| | / /   |  _| |  \| | |  | | | | | | |  _| | |_) \___ \
| |___| |___| |\  |/ /_   | |___| |\  | |__| |_| | |_| | |___|  _ < ___) |
|_____|_____|_| \_/____|  |_____|_| \_|\____\___/|____/|_____|_| \_|____/


BiSS Flash Tool Logging Module

This module provides enhanced logging functionality with color formatting for the BiSS FlashTool system.
It includes a custom formatter for colored console output and a flexible logging initialization function.

Key Features:
- Color-coded log messages based on severity level
- Customizable logging formats for both console and file output
- Thread-safe logging configuration
- Optional file logging with different verbosity levels
- ANSI color support for terminal output

Components:
    MyFormatter:
        A custom logging formatter that applies color to messages based on their log level.
        Supports ERROR (red), DEBUG (gray), and INFO (blue) levels by default.

    init_logging():
        Configures and returns a logger with console and optional file output handlers.
        Allows separate log level control for each output stream.

Usage Example:
    >>> from lib_logging import init_logging
    >>> logger = init_logging("app.log")
    >>> logger.info("System initialized")
    >>> logger.error("Connection failed")

Color Scheme:
    ERROR   - Red
    DEBUG   - Gray
    INFO    - Blue
    WARNING - Default color (configurable)

Configuration Options:
    - Console log level (default: INFO)
    - File log level (default: DEBUG)
    - Custom log message formats
    - Optional timestamp formatting

Dependencies:
    - logging: Python standard logging module
    - sys: For stdout handling
    - typing: For type hints
    - ..utils.colors.TermColors: Color code definitions

Security Considerations:
    - File logging handles IOError/OSError gracefully
    - No sensitive data should be logged at INFO level or below

Author:
    LENZ ENCODERS, 2020-2025
'''

import logging
import sys
from typing import Optional
from ..utils.termcolors import TermColors


class MyFormatter(logging.Formatter):
    """
    Custom logging formatter that adds color to log messages based on the log level.

    Attributes:
        formats (dict): A mapping from log levels to their corresponding format strings.
        default_format (str): The default format string for log messages.
    """

    formats: dict = {
        logging.ERROR: f'{TermColors.Red}%(message)s{TermColors.ENDC}',
        logging.DEBUG: f'{TermColors.GRAY}%(message)s{TermColors.ENDC}',
        logging.INFO: f'{TermColors.Blue}%(message)s{TermColors.ENDC}',
        # Add more formats for other log levels if needed
    }

    def __init__(self, fmt: str = "%(asctime)s [%(funcName)s] %(levelname)s %(message)s", datefmt: str = None) -> None:
        """
        Initializes the formatter with a default format.

        Args:
            fmt (str): The default format string.
            datefmt (str): The date format string.
        """
        super().__init__(fmt=fmt, datefmt=datefmt, style='%')
        self.default_format: str = fmt

    def format(self, record: logging.LogRecord) -> str:
        """
        Formats the log record according to the log level, adding color where appropriate.

        Args:
            record (logging.LogRecord): The log record to format.

        Returns:
            str: The formatted log message.
        """
        log_fmt = self.formats.get(record.levelno, self.default_format)
        formatter = logging.Formatter(fmt=log_fmt, datefmt=self.datefmt, style='%')
        return formatter.format(record)


def init_logging(
    logfilename: Optional[str] = None,
    stdout_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    logger_name: str = "lenz_flashtool"
) -> logging.Logger:
    """
    Initializes the logging system with console and optional file handlers.

    This function sets up a logger with a stdout handler and, if a filename is provided,
    a file handler. Each handler has its own logging level and formatter.

    Args:
        logfilename (Optional[str]): The name of the file to log messages to. If None, no file logging occurs.
        stdout_level (int): The logging level for the stdout handler (default: INFO).
        file_level (int): The logging level for the file handler (default: DEBUG).
        logger_name (str): The name of the logger to configure (default: "lenz_flashtool").
            If None, the root logger is configured.

    Returns:
        logging.Logger: The configured logger instance.

    Raises:
        ValueError: If logging levels are invalid.
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(min(stdout_level, file_level))

    if logger.hasHandlers():
        logger.handlers.clear()

    # Console handler
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(stdout_level)
    stdout_formatter = MyFormatter()
    stdout_handler.setFormatter(stdout_formatter)
    logger.addHandler(stdout_handler)

    # File handler (optional)
    if logfilename:
        try:
            file_handler = logging.FileHandler(logfilename)
            file_handler.setLevel(file_level)
            file_formatter = logging.Formatter(
                "%(asctime)s %(processName)s %(name)s [%(funcName)s] %(levelname)s %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except (IOError, OSError) as e:
            logger.warning("Failed to create log file '%s': %s", logfilename, e)

    return logger
