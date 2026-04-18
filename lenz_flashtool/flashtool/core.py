r'''
 _     _____ _   _ _____   _____ _   _  ____ ___  ____  _____ ____  ____
| |   | ____| \ | |__  /  | ____| \ | |/ ___/ _ \|  _ \| ____|  _ \/ ___|
| |   |  _| |  \| | / /   |  _| |  \| | |  | | | | | | |  _| | |_) \___ \
| |___| |___| |\  |/ /_   | |___| |\  | |__| |_| | |_| | |___|  _ < ___) |
|_____|_____|_| \_/____|  |_____|_| \_|\____\___/|____/|_____|_| \_|____/


FlashTool core library module for BiSS C Firmware Update and Calibration.

This library provides functions for interfacing with BiSS C encoders using LENZ FlashTool, performing firmware updates,
and executing calibration routines.

Author:
    LENZ ENCODERS, 2020-2026
'''

import os
import sys
import logging
import signal
from typing import Callable, Dict, Optional, Any, Tuple, Type
from types import TracebackType
import serial
import serial.tools.list_ports

from .serial_io import SerialIOMixin
from .encoder_control import EncoderControlMixin
from .biss_io import BiSSIOMixin
from .data_streaming import DataStreamingMixin
from .bootloader import BootloaderMixin
from .errors import FlashToolError

logger = logging.getLogger(__name__)


class FlashTool(SerialIOMixin, BiSSIOMixin, EncoderControlMixin,
                DataStreamingMixin, BootloaderMixin):
    """
    Main interface for interacting with BiSS C encoders via FlashTool device, connected to a serial port.
    FlashTool device has 2 channels for encoder connection. Commands perform on channel 2 if not mentioned.

    This class provides methods for:
    - Establishing serial communication with FlashTool device
    - Sending commands and data to the encoder
    - Reading encoder status and data
    - Performing firmware updates
    - Executing calibration routines

    The class implements the singleton pattern to ensure only one connection exists.

    Typical usage:
        >>> with FlashTool() as ft:
        ...     ft.biss_read_snum()  # Read serial number of the encoder (on channel 2)
        ...     ft.encoder_power_cycle()  # Perform power cycle on channel 2
        ...     ft.biss_write_command('reboot2bl')  # Reboot to bootloader
    """

    _instance = None
    _original_signal_handlers: Dict[int, Any] = {}

    def __new__(cls, *args, **kwargs) -> 'FlashTool':
        """
        Creates or returns the singleton instance of the FlashTool class.

        Ensures that only one instance of FlashTool exists to manage the connection
        to the BiSS C encoder via the LENZ FlashTool device.

        Args:
            *args: Variable positional arguments passed to the constructor.
            **kwargs: Variable keyword arguments passed to the constructor.

        Returns:
            FlashTool: The singleton instance of the FlashTool class.
        """
        if cls._instance is None:
            cls._instance = super(FlashTool, cls).__new__(cls)
            cls._instance._cleanup_handlers = []  # List[Callable]
        return cls._instance

    def __init__(self, port_description_prefixes: Tuple[str, ...] = ('XR21V',), baud_rate: int = 12000000) -> None:
        """
        Initializes the FlashTool instance by establishing a serial connection to the LENZ FlashTool device.

        Detects and connects to the appropriate serial port based on the provided port description prefixes.
        Configures the serial port with the specified baud rate and buffer sizes.
        Implements singleton behavior by skipping reinitialization if already initialized.

        Platform-specific behavior:
        - Windows: Uses exact prefix matching on port descriptions and configures buffer sizes
        - Linux: Uses enhanced detection including VID:PID matching and configures basic serial parameters
        - Other OS: Raises FlashToolError for unsupported operating systems

        Args:
            port_description_prefixes: Tuple of strings representing prefixes for port descriptions
            to match (e.g., 'XR21V'). Defaults to ('XR21V',).
            baud_rate: The baud rate for the serial connection. Defaults to 12,000,000.

        Raises:
            FlashToolError: If no matching serial port is found or if the port is already in use.

        Example:
            >>> ft = FlashTool(port_description_prefixes=('XR21V',), baud_rate=12000000)
            >>> ft.is_initialized
            True
        """
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._initialized = True
        self._port = None
        self._port_name = None

        ports = serial.tools.list_ports.comports(include_links=False)
        if os.name == 'nt':
            for porti in ports:
                if porti.description.startswith(port_description_prefixes):
                    self._port_name = porti.device
                    try:
                        self._port = serial.Serial(porti.device, baud_rate, timeout=1)
                        self._port.set_buffer_size(rx_size=16777216, tx_size=16384)
                        logger.debug('LENZ FlashTool %s - Connected!', self._port_name)
                        break
                    except serial.SerialException as e:
                        raise FlashToolError(f'LENZ FlashTool: {self._port_name} is being used!') from e
            else:
                logger.error('Error: LENZ FlashTool not found!')
                logger.debug('Program expectedly closed.')
                raise FlashToolError('LENZ FlashTool not found!')
        elif os.name == 'posix':
            found_port = self._find_linux_port_enhanced(ports, port_description_prefixes)
            if found_port:
                self._port_name = found_port
                try:
                    self._port = serial.Serial(self._port_name, baud_rate, timeout=1)

                    self._port.bytesize = serial.EIGHTBITS
                    self._port.parity = serial.PARITY_NONE
                    self._port.stopbits = serial.STOPBITS_ONE

                    self._port.timeout = 1
                    self._port.write_timeout = 1
                    self._port.xonxoff = False
                    self._port.rtscts = False
                    try:
                        if hasattr(self._port, 'set_buffer_sizes'):
                            logger.debug("Has atribute")
                            self._port.set_buffer_sizes(rx_size=4096, tx_size=4096)
                    except Exception as e:
                        logger.debug(f"Buffer size adjustment not supported: {e}")
                        logger.debug('LENZ FlashTool %s - Connected!', self._port_name)
                except serial.SerialException as e:
                    raise FlashToolError(f'LENZ FlashTool: {self._port_name} is being used!') from e
            else:
                logger.error('Error: LENZ FlashTool not found!')
                logger.debug('Available ports: %s', [f"{p.device}: {p.description} (HWID: {p.hwid})" for p in ports])
                raise FlashToolError('LENZ FlashTool not found!')
        else:
            logger.error('Error: Unsupported operating system!')
            raise FlashToolError('Unsupported operating system!')
        self._port.flushInput()

    def __enter__(self) -> 'FlashTool':
        """
        Enters the context manager, returning the initialized FlashTool instance.

        The serial connection is already established during initialization,
        so this method simply returns the instance for use within a `with` block.

        Returns:
            FlashTool: The initialized FlashTool instance.

        Example:
            >>> with FlashTool() as ft:
            ...     ft.biss_read_snum()
        """
        # Connection is already established in __init__
        return self

    def __exit__(
            self,
            exc_type: Optional[Type[BaseException]],
            exc_val: Optional[BaseException],
            exc_tb: Optional[TracebackType]
            ) -> bool:
        """
        Exits the context manager, closing the serial connection and performing cleanup.

        Calls the `close` method to release resources, including the serial port and
        registered cleanup handlers. Restores original signal handlers and resets the singleton instance.

        Args:
            exc_type: The type of the exception raised, if any.
            exc_val: The exception instance raised, if any.
            exc_tb: The traceback of the exception, if any.

        Returns:
            bool: False, indicating that exceptions are not suppressed and will be re-raised.

        Example:
            >>> with FlashTool() as ft:
            ...     raise ValueError("Test error")
            ... # Automatically calls close() and re-raises the exception
        """
        self.close()
        # Return False to re-raise any exceptions
        return False

    def register_cleanup(self, handler: Callable[[], None]) -> 'FlashTool':
        """
        Registers a cleanup function to be executed during `close` or on SIGINT.

        Allows scripts to define custom cleanup operations, such as resetting hardware states
        or closing additional resources, which are called when the FlashTool connection is closed.

        Args:
            handler: A callable with no arguments that performs cleanup operations.

        Returns:
            FlashTool: The FlashTool instance for method chaining.

        Example:
            >>> def custom_cleanup():
            ...     elmo.motor_off()
            ...     print("Cleaning up resources. Stopping motor.")
            >>> ft = FlashTool().register_cleanup(custom_cleanup)
        """
        self._cleanup_handlers.append(handler)
        return self

    def enable_signal_handling(self, signals: Tuple[int, ...] = (signal.SIGINT,)) -> 'FlashTool':
        """
        Enables signal handling for the specified signals to ensure proper cleanup.

        Registers signal handlers to call the `close` method when the specified signals are received,
        preserving the original handlers for restoration during cleanup.

        Args:
            signals: Tuple of signal numbers to handle (e.g., signal.SIGINT). Defaults to (signal.SIGINT,).

        Returns:
            FlashTool: The FlashTool instance for method chaining.

        Example:
            >>> ft = FlashTool().enable_signal_handling((signal.SIGINT, signal.SIGTERM))
        """
        for sig in signals:
            self._original_signal_handlers[sig] = signal.getsignal(sig)
            signal.signal(sig, self._signal_handler)
        return self

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """
        Handles received signals by performing cleanup and exiting the program.

        Logs the received signal, calls the `close` method to release resources,
        and terminates the program with a status code of 1.

        Args:
            signum: The signal number received (e.g., signal.SIGINT).
            frame: The current stack frame at the time of the signal.

        Raises:
            SystemExit: Always raises to terminate the program after cleanup.
        """
        logger.info("Signal %s received, cleaning up...", signum)
        self.close()
        sys.exit(1)

    def _default_cleanup(self) -> None:
        """
        Performs default cleanup operations, such as closing the serial port.

        Closes the serial port if it is open, logging the operation and any errors that occur during closure.

        Returns:
            None

        Example:
            >>> ft = FlashTool()
            >>> ft._default_cleanup()  # Closes the serial port
        """
        if self._port is not None and self._port.is_open:
            try:
                self._port.close()
                logger.debug("Serial port %s closed", self._port_name)
            except Exception as e:
                logger.warning("Error closing port: %s", e)

    def close(self):
        """
        Closes the serial port connection and performs cleanup.

        Executes all registered cleanup handlers, closes the serial port, restores original signal handlers,
        and resets the singleton instance. Logs the closure of the connection.

        Returns:
            None

        Example:
            >>> ft = FlashTool()
            >>> ft.close()
            INFO: FlashTool: COM3 closed.
        """
        for handler in reversed(self._cleanup_handlers):
            try:
                handler()
            except Exception as e:
                logger.warning("Cleanup error in %s: %s", handler.__name__, str(e))

        # Perform default cleanup
        self._default_cleanup()

        # Restore original signal handlers
        for sig, handler in self._original_signal_handlers.items():
            try:
                signal.signal(sig, handler)
            except Exception as e:
                logger.warning("Error restoring signal handler: %s", e)

        # Reset singleton instance
        FlashTool._instance = None
        self._initialized = False
        logger.info('FlashTool: %s closed.', self._port_name)
