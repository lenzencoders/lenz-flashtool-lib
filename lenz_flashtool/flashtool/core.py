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
    LENZ ENCODERS, 2020-2025
'''

import time
import os
import sys
import logging
import signal
from typing import Callable, Dict, Optional, List, Union, Any, Type, Tuple
from types import TracebackType
import serial
import serial.tools.list_ports
import numpy as np
from ..biss import (
    biss_commands, interpret_biss_commandstate, interpret_error_flags,
    BiSSBank
)
from .uart import UartCmd
from .errors import FlashToolError
from .hex_utils import (
    calculate_checksum,
    generate_byte_line,
    generate_hex_line,
    reverse_endian, bytes_to_hex_str
)
from ..utils.progress import percent_complete

logger = logging.getLogger(__name__)


class FlashTool:
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
        self.__port = None
        self.__port_name = None

        ports = serial.tools.list_ports.comports(include_links=False)
        if os.name == 'nt':
            for porti in ports:
                if porti.description.startswith(port_description_prefixes):
                    self.__port_name = porti.device
                    try:
                        self.__port = serial.Serial(porti.device, baud_rate, timeout=1)
                        self.__port.set_buffer_size(rx_size=16777216, tx_size=16384)
                        logger.debug('LENZ FlashTool %s - Connected!', self.__port_name)
                        break
                    except serial.SerialException as e:
                        raise FlashToolError(f'LENZ FlashTool: {self.__port_name} is being used!') from e
            else:
                logger.error('Error: LENZ FlashTool not found!')
                logger.debug('Program expectedly closed.')
                raise FlashToolError('LENZ FlashTool not found!')
        self.__port.flushInput()

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
        if self.__port is not None and self.__port.is_open:
            try:
                self.__port.close()
                logger.debug("Serial port %s closed", self.__port_name)
            except Exception as e:
                logger.warning("Error closing port: %s", e)

    def _wait_for_data(self, size: int, timeout: float = 1.0) -> bool:
        """
        Waits for the specified amount of data to be available in the serial input buffer.

        Polls the serial port until the required number of bytes is available
        or the timeout expires, checking every 10 milliseconds.

        Args:
            size: The number of bytes to wait for.
            timeout: Maximum time to wait in seconds. Defaults to 1.0.

        Returns:
            bool: True if the required data is available before the timeout, False otherwise.

        Example:
            >>> ft = FlashTool()
            >>> ft._wait_for_data(10, timeout=2.0)
            True
        """
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            if self.__port.in_waiting >= size:
                return True
            time.sleep(0.01)
        return False

    def _write_to_port(self, data: bytes) -> None:
        """
        Writes data to the serial port with unified error handling.

        Handles all serial port write operations, logging errors and raising exceptions for communication failures.

        Args:
            data: The bytes to write to the serial port.

        Raises:
            FlashToolError: If a serial communication error or unexpected failure occurs.

        Example:
            >>> ft = FlashTool()
            >>> ft._write_to_port(b'\\x01\\x00@\\x0b\\xff\\xb5')  # Power off encoder on channel 2
        """
        try:
            self.__port.write(data)
        except (serial.SerialException, OSError) as e:
            logger.error("Port write failed: %s", e)
            raise FlashToolError(f"Hardware communication failed: {e}") from e
        except Exception as e:
            logger.critical("Unexpected port write error: %s", e)
            raise FlashToolError("Critical write operation failure") from e

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
        logger.info('FlashTool: %s closed.', self.__port_name)

    def port_read(self, length: int) -> np.ndarray:
        """
        Reads data from the serial port and validates it with a checksum check.

        Waits for the specified number of data bytes plus a checksum byte, reads the data,
        and verifies the checksum. Logs the received data and checksum status, returning the data as a NumPy array.

        Args:
            length: The number of data bytes to read (excluding the checksum byte).

        Returns:
            np.ndarray: A NumPy array of uint8 values containing the received data (excluding header and checksum).

        Raises:
            FlashToolError: If the data is not received within the timeout period or if checksum validation fails.

        Example:
            >>> ft = FlashTool()
            >>> data = ft.port_read(10)
            >>> print(data)
            array([0x01, 0x02, ..., 0x0A], dtype=uint8)
        """
        if self._wait_for_data(length + 1, timeout=1.0):
            biss_data = self.__port.read(length + 5)  # len, addr, addr, cmd, checksum
            biss_value = int.from_bytes(biss_data, byteorder='big', signed=False)
            calculated_crc = calculate_checksum(biss_data[0:-1].hex())
            if calculated_crc == biss_data[-1]:
                crc_res = "OK"
                logger.debug(f"Received BiSS Data: {biss_value:#010x}, checksum calculated {calculated_crc}, \
                            in data {biss_data[-1]}, res = {crc_res}")
            else:
                crc_res = "FALSE"
                logger.error(f"Received BiSS Data: {biss_value:#010x}, checksum calculated {calculated_crc}, \
                            in data {biss_data[-1]}, res = {crc_res}")
            logger.info("BiSS received data:")
            data_array = np.array(list(biss_data[4:-1]), 'uint8')
            logger.info(data_array)
            return data_array
            # logger.info(np.array(list(biss_data[0:64]), 'uint8'))
            # logger.info(np.array(list(biss_data[64:-1]), 'uint8'))
        raise FlashToolError('Timeout waiting for register data.')

    def biss_cmd_reboot2bl(self):
        """
        Sends the BiSS command to reboot the device into bootloader mode.

        Issues the 'reboot2bl' command to the BiSS encoder, initiating a reboot into bootloader
        mode for firmware updates. Note: This method is deprecated and should be replaced with `biss_write_command('reboot2bl')`.

        Returns:
            None

        Example:
            >>> ft = FlashTool()
            >>> ft.biss_cmd_reboot2bl()
            WARNING: Deprecated method. Use biss_write_command('reboot2bl') instead.
        """
        logger.debug("Sending reboot to bootloader command")
        command_code: int = biss_commands['reboot2bl'][0]
        command_list: list[int] = [command_code & 0xFF, (command_code >> 8) & 0xFF]
        self.biss_write_word(BiSSBank.CMD_REG_INDEX, command_list)
        time.sleep(0.5)

    def biss_write_command(self, command: str):
        """
        Sends a specific BiSS command to the encoder.

        Issues a command from the `biss_commands` dictionary to the BiSS encoder, such as rebooting,
        setting direction, or initiating calibration. Commands are written to the command register.

        Args:
            command: The command key from `biss_commands`. Supported commands include:

                - 'non': No operation command. Device remains in current state with no action taken.
                - 'load2k': Load 2 KB of data from registers into device memory. Used for firmware updates.
                - 'staybl': Force device to stay in bootloader mode.
                - 'run': Exit bootloader mode and execute the main application program. Initiates normal encoder operation.
                - 'zeroing': Perform encoder zeroing procedure. Resets position counter to zero at current mechanical position.
                - 'set_dir_cw': Configure encoder direction sensing for clockwise rotation.
                - 'set_dir_ccw': Configure encoder direction sensing for counterclockwise rotation.
                - 'saveflash': Commit current configuration parameters to flash memory.
                - 'ampcalibrate': Initiate amplitude calibration routine. Automatically adjusts signal amplitudes.
                - 'cleardiflut': Clear differential lookup table (DifLUT). Resets all offset compensation values to default state.
                - 'set_fast_biss': Enable high-speed BiSS communication mode.
                - 'set_default_biss': Revert to standard BiSS communication mode.
                - 'reboot': Perform device reboot.
                - 'reboot2bl': Reboot device directly into bootloader mode.
                - 'loadseriald': Write serial number and manufacturing date to OTP memory.
                - 'loaddevid': Program DevID into OTP memory.
                - 'loadkey': Store key in secure flash memory.
                - 'savediftable': Save differential compensation table to memory.
                - 'unlockflash': Enable write access to protected flash memory regions.
                - 'unlocksetup': Disable configuration write protection.
                - 'enarccal': Enable arc-based calibration mode.
                - 'clearcalflash': Erase all high-speed oscillator (HSI) and differential calibration data from flash.

        Raises:
            FlashToolError: If the specified command is not found in `biss_commands`.

        Example:
            >>> ft = FlashTool()
            >>> ft.biss_write_command('reboot2bl')
        """
        if command in biss_commands:
            command_code: int = biss_commands[command][0]
            command_list: list[int] = [command_code & 0xFF, (command_code >> 8) & 0xFF]
            self._write_to_port(generate_byte_line(BiSSBank.CMD_REG_INDEX, UartCmd.HEX_WRITE_CMD, command_list))
            logger.debug("Sending BiSS %s command (%s)", command, hex(command_code))
            time.sleep(0.01)
        else:
            logger.error("Unknown command: '%s'", command)
            raise logger(f"Unknown command: '{command}'.")

    def hex_line_send(self, hex_line: str) -> bytes:
        """
        Sends a hex-formatted line to the FlashTool device.

        Converts the provided hex line (starting with ':') to bytes and transmits it to the FlashTool device via the serial port.

        Args:
            hex_line: A string representing a hex line, including the leading ':'.

        Returns:
            bytes: The transmitted bytes.

        Example:
            >>> ft = FlashTool()
            >>> ft.hex_line_send(':0100400C0AA9')
            b'\\x01\\x00@\\x0c\\n\\xa9'
        """
        # logger.debug(f'Uploading {hex_line} to the FlashTool.')
        tx_row = bytes.fromhex(hex_line[1:])
        # logger.debug(tx_row)
        self._write_to_port(tx_row)
        return tx_row

    def biss_set_bank(self, bank_num: int) -> None:
        """
        Sets the active BiSS bank for subsequent read/write operations.

        Selects the specified bank number for BiSS register operations, ensuring it is within the valid range (0-255).

        Args:
            bank_num: The BiSS bank number to select.

        Raises:
            ValueError: If the bank number is out of the valid range (0-255).
            TypeError: If the bank number is not an integer.

        Example:
            >>> ft = FlashTool()
            >>> ft.biss_set_bank(1)
        """
        try:
            if not 0 <= bank_num <= 255:
                raise ValueError(f"Bank {bank_num} out of range (0-255)")
            logger.debug('Setting bank %s', bank_num)
            self._write_to_port(generate_byte_line(BiSSBank.BSEL_REG_INDEX, UartCmd.HEX_WRITE_CMD, [bank_num]))
        except (ValueError, TypeError) as e:
            logger.error("Validation error in biss_set_bank: %s", str(e))
            raise

    def biss_write(self, addr: int, data: int) -> None:
        """
        Writes a single byte to a BiSS register at the specified address.

        Sends a single 8-bit value to the specified BiSS register address.
        Note: This method is deprecated and may be removed in future versions.

        Args:
            addr: The BiSS register address (0-127).
            data: The 8-bit integer value to write.

        Raises:
            ValueError: If the address is out of range (0-127) or if the data is negative.
            TypeError: If the data is not an integer.

        Example:
            >>> ft = FlashTool()
            >>> ft.biss_write(0x10, 0xFF)
            WARNING: Deprecated method. Consider using biss_write_word instead.
        """
        # TODO unused function?
        try:
            if not 0 <= addr <= 127:
                raise ValueError(f"Address {addr} out of range (0-127)")

            if not isinstance(data, int):
                raise TypeError(f"Data {data} is not an integer (got {type(data)})")
            if data < 0:
                raise ValueError(f"Data {data} is negative")
            self._write_to_port(generate_byte_line(addr, UartCmd.HEX_WRITE_CMD, [data]))
        except (ValueError, TypeError) as e:
            logger.error("Validation error in biss_write: %s", str(e))
            raise

    def biss_write_word(self, addr: int, word: Union[int, List[int]]) -> None:
        """
        Writes one or more 8, 16, or 32-bit words to BiSS registers starting at the specified address.

        Converts the provided word(s) to bytes, handles endianness, and writes them to the BiSS encoder.
        Supports single integers or lists of integers, automatically determining the word
        size (8, 16, or 32 bits) based on the maximum value.

        Args:
            addr: The starting BiSS register address (0-127).
            word: A single integer or a list of integers to write.

        Raises:
            ValueError: If the address is out of range, the word list is empty, a word is negative,
            or a word exceeds the 32-bit limit.
            TypeError: If any word is not an integer.
            FlashToolError: If a hardware communication error occurs.

        Example:
            >>> ft = FlashTool()
            >>> ft.biss_write_word(0x10, 0xABCD)  # Write a 16-bit word
            >>> ft.biss_write_word(0x20, [0x01, 0x02])  # Write two 8-bit words
        """
        try:
            if not 0 <= addr <= 127:
                raise ValueError(f"Address {addr} out of range (0-127)")

            words = [word] if isinstance(word, int) else word
            if not words:
                raise ValueError("Empty word list provided")

            for i, w in enumerate(words):
                if not isinstance(w, int):
                    raise TypeError(f"Word {i} is not an integer (got {type(w)})")
                if w < 0:
                    raise ValueError(f"Word {i} is negative ({w})")

            # Determine word size
            max_word = max(words)
            if max_word > 0xFFFFFFFF:
                raise ValueError(f"Word value {max_word} exceeds 32-bit limit")
            word_size = 4 if max_word > 0xFFFF else (2 if max_word > 0xFF else 1)

            # Convert to bytes
            try:
                byte_list = []
                for w in words:
                    byte_list.extend(w.to_bytes(word_size, byteorder='big'))
                reversed_bytes = reverse_endian(byte_list, word_size)
            except OverflowError as e:
                raise ValueError(f"Word size mismatch: {e}") from e
            logger.debug("Sending word %s with starting index %s", word, addr)

            self._write_to_port(generate_byte_line(addr, UartCmd.HEX_WRITE_CMD, reversed_bytes))

        except (ValueError, TypeError) as e:
            logger.error("Validation error in biss_write_word: %s", str(e))
            raise

    def biss_read_state_flags(self) -> np.ndarray:
        """
        Reads the state flags from the BiSS encoder.

        Sends a read command to retrieve the state flags, validates the response
        with a checksum check, and returns the flags as a NumPy array.

        Returns:
            np.ndarray: A NumPy array of uint8 values containing the state flags.

        Raises:
            FlashToolError: If the checksum validation fails or no data is received within the timeout.

        Example:
            >>> ft = FlashTool()
            >>> flags = ft.biss_read_state_flags()
            >>> print(flags)
            array([0x01, 0x00], dtype=uint8)
        """
        self._write_to_port(generate_byte_line(BiSSBank.STATE_FLAG_REG_INDEX, UartCmd.HEX_READ_CMD, [1, 2]))
        time.sleep(0.01)

        if self.__port.in_waiting >= 1:
            biss_data = self.__port.read(7)
            biss_value = int.from_bytes(biss_data, byteorder='big', signed=False)
            if (calculate_checksum(biss_data[0:-1].hex())) == (biss_data[-1]):
                crc_res = "OK"
            else:
                crc_res = "FALSE"
                logger.error(f"Received BiSS Data: {biss_value:#010x}, \
                              checksum calculated {calculate_checksum(biss_data[0:-1].hex())}, \
                              in data {(biss_data[-1])}, \tres = {crc_res}")
                raise FlashToolError('checksum validation failed for state flags.')
            logger.debug("Received BiSS Data: %s", np.array(list(biss_data[:-1]), 'uint8'))
            logger.debug(f"Received BiSS Data: {biss_value:#010x}, \
                          checksum calculated {calculate_checksum(biss_data[0:-1].hex())}, \
                          in data {(biss_data[-1])}, \tres = {crc_res}")
            return (np.array(list(biss_data[4:-1]), 'uint8'))
        raise FlashToolError('No answer from encoder.')

    def biss_read_registers(self, bissbank: int) -> None:
        """
        Reads all registers from the specified BiSS bank and logs the results.

        Selects the specified bank, sends a read command for all registers,
        validates the response with a checksum check, and logs the received data as NumPy arrays.
        Does not return the data, only logs it for debugging purposes.

        Args:
            bissbank: The BiSS bank number to read from (0-255).

        Raises:
            FlashToolError: If the read operation times out or a communication error occurs.

        Example:
            >>> ft = FlashTool()
            >>> ft.biss_read_registers(1)
            INFO: BiSS registers:
            ...
        """
        self.biss_set_bank(bissbank)
        self.__port.flushInput()
        self._write_to_port(
                            generate_byte_line(0, UartCmd.HEX_READ_CMD,
                                               [item for item in list(range(BiSSBank.REGISTER_PLUS_FIXED_BANK_SIZE))]))
        time.sleep(0.1)

        if self.__port.in_waiting >= 4:
            biss_data = self.__port.read(BiSSBank.REGISTER_PLUS_FIXED_BANK_SIZE + 5)  # len, addr, addr, cmd, crc
            biss_value = int.from_bytes(biss_data, byteorder='big', signed=False)
            if (calculate_checksum(biss_data[0:-1].hex())) == (biss_data[-1]):
                crc_res = "OK"
            else:
                crc_res = "FALSE"
                logger.error(f"Received BiSS Data: {biss_value:#010x}, \
                            checksum calculated {calculate_checksum(biss_data[0:-1].hex())}, \
                            in data {(biss_data[-1])}, \tres = {crc_res}")
            logger.info("BiSS registers:")
            logger.info(np.array(list(biss_data[4:68]), 'uint8'))
            logger.info(np.array(list(biss_data[68:-1]), 'uint8'))

    def encoder_power_off(self) -> None:
        """
        Powers off the encoder on channel 2.

        Sends a POWER_OFF command to the BiSS encoder connected to channel 2 of the FlashTool device.

        Returns:
            None

        Example:
            >>> ft = FlashTool()
            >>> ft.encoder_power_off()
        """
        logger.debug('Sending POWER_OFF command to the encoder')
        tx_row = bytes.fromhex(generate_hex_line(0, UartCmd.CMD_POWER_OFF, [0])[1:])
        # logger.debug(tx_row)
        self._write_to_port(tx_row)

    def encoder_power_on(self) -> None:
        """
        Powers on the encoder on channel 2.

        Sends a POWER_ON command to the BiSS encoder connected to channel 2 of the FlashTool device.

        Returns:
            None

        Example:
            >>> ft = FlashTool()
            >>> ft.encoder_power_on()
        """
        logger.debug('Sending POWER_ON command to the encoder')
        tx_row = bytes.fromhex(generate_hex_line(0, UartCmd.CMD_POWER_ON, [0])[1:])
        # logger.debug(tx_row)
        self._write_to_port(tx_row)

    def encoder_ch1_power_off(self) -> None:
        """
        Powers off the encoder on channel 1.

        Sends a POWER_OFF command to the BiSS encoder connected to channel 1 of the FlashTool device.

        Returns:
            None

        Example:
            >>> ft = FlashTool()
            >>> ft.encoder_ch1_power_off()
        """
        logger.debug('Sending POWER_OFF command to the encoder')
        tx_row = bytes.fromhex(generate_hex_line(0, UartCmd.CMD_CH1_POWER_OFF, [0])[1:])
        # logger.debug(tx_row)
        self._write_to_port(tx_row)

    def encoder_ch1_power_on(self) -> None:
        """
        Powers on the encoder on channel 1.

        Sends a POWER_ON command to the BiSS encoder connected to channel 1 of the FlashTool device.

        Returns:
            None

        Example:
            >>> ft = FlashTool()
            >>> ft.encoder_ch1_power_on()
        """
        logger.debug('Sending POWER_ON command to the encoder')
        tx_row = bytes.fromhex(generate_hex_line(0, UartCmd.CMD_CH1_POWER_ON, [0])[1:])
        # logger.debug(tx_row)
        self._write_to_port(tx_row)

    def encoder_power_cycle(self) -> None:
        """
        Performs a power cycle on the encoder on channel 2.

        Powers off the encoder, waits 0.1 seconds, powers it back on, and waits another 0.1 seconds to ensure stabilization.

        Returns:
            None

        Example:
            >>> ft = FlashTool()
            >>> ft.encoder_power_cycle()
        """
        self.encoder_power_off()
        time.sleep(0.1)
        self.encoder_power_on()
        time.sleep(0.1)
        logger.debug('Performed power cycle to the encoder.')

    def encoder_ch1_power_cycle(self) -> None:
        """
        Performs a power cycle on the encoder on channel 1.

        Powers off the encoder, waits 0.1 seconds, powers it back on, and waits another 0.1 seconds to ensure stabilization.

        Returns:
            None

        Example:
            >>> ft = FlashTool()
            >>> ft.encoder_ch1_power_cycle()
        """
        self.encoder_ch1_power_off()
        time.sleep(0.1)
        self.encoder_ch1_power_on()
        time.sleep(0.1)
        logger.debug('Performed power cycle to the encoder.')

    def flashtool_rst(self) -> None:
        """
        Resets the FlashTool device.

        Sends a RESET command to the FlashTool, reinitializing its internal state.

        Returns:
            None

        Example:
            >>> ft = FlashTool()
            >>> ft.flashtool_rst()
        """
        logger.info('Sending RESET command to FlashTool')
        tx_row = bytes.fromhex(generate_hex_line(0, UartCmd.CMD_NVRST, [0])[1:])
        # logger.debug(tx_row)
        self._write_to_port(tx_row)

    def select_SPI_channel(self, channel: np.uint8) -> None:
        """
        Select SPI communication channel.

        Sends a SELECT CHANNEL command to the FlashTool.

        There are two channels:
            0 --> channel 1;
            1 --> channel 2.

        Args:
            channel (uint8): The channel number (must be 0 or 1).

        Returns:
            None

        Raises:
            ValueError: If the mode is not 0 or 1.

        Example:
            >>> ft = FlashTool()
            >>> ft.select_SPI_channel(0)
        """
        channel = np.uint8(channel)
        valid_channels = {np.uint8(0), np.uint8(1)}
        if channel not in valid_channels:
            raise ValueError(f"Invalid mode: {channel}. Must be one of the {valid_channels} (0: channel 1, 1: \
                             channel 2).")

        channel_descriptions = {
            0: "CHANNEL 1",
            1: "CHANNEL 2"
        }
        logger.info(f"Selected Channel: {channel} - {channel_descriptions[channel]}")

        tx_row = bytes.fromhex(generate_hex_line(0, UartCmd.CMD_SELECT_SPI_CH, [channel])[1:])
        # logger.debug(tx_row)
        self.__port.reset_output_buffer()
        self.__port.write(tx_row)
        self.__port.flush()

    def select_FlashTool_mode(self, mode: np.uint8):
        """
        Select FlashTool mode.

        Sends a SELECT Flashtool mode command to the FlashTool.

        There are three modes:
            0 --> BISS_MODE_SPI_SPI.
            1 --> BISS_MODE_AB_UART.
            2 --> BISS_MODE_SPI_UART_IRS.
            3 --> BISS_MODE_AB_SPI.

        Args:
            mode (uint8): The mode number (must be 0, 1, 2, 3).

        Returns:
            None

        Raises:
            ValueError: If the mode is not 0, 1, 2, 3.

        Example:
            >>> ft = FlashTool()
            >>> ft.select_FlashTool_mode(0)
        """
        mode = np.uint8(mode)
        valid_modes = {np.uint8(0), np.uint8(1), np.uint8(2), np.uint8(3)}
        if mode not in valid_modes:
            raise ValueError(f"Invalid mode: {mode}. Must be one of the {valid_modes} (0: BISS_MODE_SPI_SPI, 1: \
                             BISS_MODE_AB_UART, 2: BISS_MODE_SPI_UART_IRS, 3: BISS_MODE_AB_SPI).")

        mode_descriptions = {
            0: "BISS_MODE_SPI_SPI",
            1: "BISS_MODE_AB_UART",
            2: "BISS_MODE_SPI_UART_IRS",
            3: "BISS_MODE_AB_SPI"
        }
        logger.info(f"Selected FlashTool mode: {mode} - {mode_descriptions[mode]}")

        tx_row = bytes.fromhex(generate_hex_line(0, UartCmd.CMD_SELECT_FLASHTOOL_MODE, [mode])[1:])
        # logger.debug(tx_row)
        self.__port.reset_output_buffer()
        self.__port.write(tx_row)
        self.__port.flush()

    def read_data(self, read_time: float) -> np.ndarray:
        """
        Reads encoder data via SPI over USB for a specified duration.

        Sends a command to read data, collects incoming packets, validates them with checksums,
        and extracts encoder values. Prints progress indicators during reading.

        Args:
            read_time: The duration in seconds to read data.

        Returns:
            np.ndarray: A NumPy array of int32 values containing the encoder readings.

        Raises:
            ValueError: If a checksum or command error occurs in the received data.

        Example:
            >>> ft = FlashTool()
            >>> data = ft.read_data(2.0)
            Read USB data for 2.0 seconds: ..... OK!
            >>> print(data)
            array([12345, 12346, ...], dtype=int32)
        """
        print('Read USB data for ', read_time, ' seconds: ', end='')
        size = int(read_time * 500)
        size_l = int(size) % 256
        size_m = int(size / 256) % 256
        self.__port.flushInput()
        start_time = time.time()
        self._write_to_port(bytearray([1, size_m, size_l, 129, 0, int((126 - size_m - size_l) % 256)]))
        ok = 1
        dot_time = start_time + 0.2
        new_line_time = start_time + 10
        gu = []
        cou = []
        encoder = []
        while time.time() < start_time + read_time + 1:
            if self.__port.inWaiting() > 250:
                rx_data = np.array(list(self.__port.read(245)), 'int32')
                crc_hex = - sum(rx_data[0:244]) % 256
                if (rx_data[0] == 240) & (rx_data[3] == 145):
                    if crc_hex == rx_data[244]:
                        cou.extend(rx_data[7:244:4])
                        encoder.extend(rx_data[6:244:4]*65536 + rx_data[5:244:4]*256 + rx_data[4:244:4])
                    else:
                        print('HEX CheckSum ERROR!')
                        ok = 0
                        break
                else:
                    print('HEX Command ERROR!')
                    ok = 0
                    break
                if (rx_data[1] == 0) & (rx_data[2] == 0):
                    gu = np.array(gu, 'int32')
                    encoder = np.array(encoder, 'int32')
                    break
            else:
                time.sleep(0.001)
            if time.time() > new_line_time:
                new_line_time = new_line_time + 10
                print('\n', end='')

            elif time.time() > dot_time:
                dot_time = dot_time + 0.5
                print('.', end='')
        if ok:
            print(' OK!')
        return encoder

    def read_data_enc1_enc2_SPI(self, read_time: float, status: bool = True) -> Tuple[List[int], List[int]]:
        """
        Reads data from two encoders via SPI over USB for a specified duration.

        Sends a command to read data from both encoders, processes incoming packets, validates checksums,
        and extracts encoder values for both channels. Optionally prints progress indicators.

        Args:
            read_time: The duration in seconds to read data.
            status: If True, prints progress indicators (dots and status messages). Defaults to True.

        Returns:
            Tuple[List[int], List[int]]: Two lists containing the readings from encoder 1 and encoder 2, respectively.

        Raises:
            ValueError: If a checksum or command error occurs in the received data.

        Example:
            >>> ft = FlashTool()
            >>> enc1, enc2 = ft.read_data_enc1_enc2_SPI(2.0)
            Read USB data for 2.0 seconds: ..... OK!
            >>> print(enc1[:5], enc2[:5])
            [12345, 12346, ...], [54321, 54322, ...]
        """
        status and print('Read USB data for ', read_time, ' seconds: ', end='')
        logger.debug('Reading USB encoder 1 and encoder 2 data for %s seconds.', read_time)
        size = int(read_time * 1000)
        size_l = int(size) % 256
        size_m = int(size / 256) % 256
        b1 = size_l.to_bytes(1, 'big')
        b2 = size_m.to_bytes(1, 'big')
        address = b''.join([b2, b1])
        addr = int.from_bytes(address, 'big')
        tx_row = bytes.fromhex(generate_hex_line(addr, UartCmd.HEX_READ_ANGLE_TWO_ENC_SPI, [0])[1:])
        logger.debug("Reading CMD: %s", generate_hex_line(addr, UartCmd.HEX_READ_ANGLE_TWO_ENC_SPI, [0])[1:])
        self.__port.flushInput()
        start_time = time.time()
        self._write_to_port(tx_row)
        ok = 1
        dot_time = start_time + 0.2
        new_line_time = start_time + 10
        # gu = []
        cou1 = []
        cou2 = []
        # Encoder1_multiturn = list()
        # Encoder2_multiturn = list()
        encoder1 = []
        encoder2 = []
        while time.time() < start_time + read_time + 1:
            if self.__port.inWaiting() > 250:
                rx_data = np.array(list(self.__port.read(245)), 'int32')
                crc_hex = - sum(rx_data[0:244]) % 256
                if (rx_data[0] == 240) & (rx_data[3] == 144):
                    if crc_hex == rx_data[244]:
                        cou1.extend(rx_data[7:244:8])
                        encoder1.extend(rx_data[6:244:8]*65536 + rx_data[5:244:8]*256 + rx_data[4:244:8])
                        # Encoder_multiturn.extend(rx_data[6:244:6])
                        cou2.extend(rx_data[11:244:8])
                        encoder2.extend(rx_data[10:244:8]*65536 + rx_data[9:244:8]*256 + rx_data[8:244:8])
                    else:
                        print('HEX CheckSum ERROR!')
                        ok = 0
                        break
                else:
                    print('HEX Command ERROR!')
                    ok = 0
                    break
                if (rx_data[1] == 0) & (rx_data[2] == 0):
                    # gu = np.array(gu, 'int32')
                    # Encoder = np.array(Encoder, 'int32')
                    break
            else:
                time.sleep(0.001)
            if time.time() > new_line_time:
                new_line_time = new_line_time + 10
                status and print('\n', end='')

            elif time.time() > dot_time:
                dot_time = dot_time + 0.5
                status and print('.', end='')
        if ok:
            status and print(' OK!')
        return encoder1, encoder2

    def read_data_enc1_AB_enc2_SPI(self, read_time: float, status: bool = True) -> tuple[np.ndarray, np.ndarray]:
        """
        Read data from Encoder SPI (SIB, IRS) and AB over USB for a specified duration.

        Sends a command to read data from both encoders, processes incoming packets, validates checksums,
        and extracts encoder values for both channels. Optionally prints progress indicators.

        Data frame: 6 bytes
        0 byte  1 byte  2 byte  3 byte  4 byte   5 byte
        Enc2    *256    *65536  Cou     Enc1     *256

        Returns:
            tuple[np.ndarray, np.ndarray]: Two np.ndarrays containing:
                - Encoder2 data.
                - Encoder1 data.
        Raises:
            ValueError: If a checksum or command error occurs in the received data.
        """
        status and print('Read USB data for ', read_time, ' seconds: ', end='')
        size = int(read_time * 500)
        size_l = int(size) % 256
        size_m = int(size / 256) % 256
        b1 = size_l.to_bytes(1, 'big')
        b2 = size_m.to_bytes(1, 'big')
        address = b''.join([b2, b1])
        addr = int.from_bytes(address, 'big')
        tx_row = bytes.fromhex(generate_hex_line(addr, UartCmd.HEX_READ_ANGLE_TWO_ENC_AB_SPI, [0])[1:])

        self.__port.reset_output_buffer()
        self.__port.write(tx_row)
        self.__port.flush()

        Encoder2 = []
        Encoder1 = []
        # Cou = list()
        ok = 1
        start_time = time.time()
        dot_time = start_time + 0.2
        new_line_time = start_time + 10

        try:
            while time.time() < start_time + read_time + 1:
                if self.__port.inWaiting() > 250:
                    rx_data = np.array(list(self.__port.read(245)), 'int32')
                    CRC_HEX = - sum(rx_data[0:244]) % 256
                    if (rx_data[0] == 240) & (rx_data[3] == UartCmd.HEX_READ_ANGLE_TWO_ENC_AB_SPI + 0x10):
                        if (CRC_HEX == rx_data[244]):
                            # Cou.extend(rx_data[7:244:6])
                            Encoder2.extend(rx_data[6:244:6]*65536 + rx_data[5:244:6]*256 + rx_data[4:244:6])
                            Encoder1.extend(rx_data[9:244:6]*256 + rx_data[8:244:6])
                        else:
                            ok = 0
                            raise ValueError("HEX Command ERROR!")
                    else:
                        ok = 0
                        raise ValueError("HEX CheckSum ERROR!")

                    if (rx_data[1] == 0) & (rx_data[2] == 0):
                        raise ValueError("Recieved Data Size ERROR!")
                else:
                    time.sleep(0.001)

                if time.time() > new_line_time:
                    new_line_time = new_line_time + 10
                    status and print('\n', end='')
                elif time.time() > dot_time:
                    dot_time = dot_time + 0.5
                    status and print('.', end='')
            if ok:
                status and print(' OK!')
            return np.array(Encoder2, dtype='int32'), np.array(Encoder1, dtype='int32')

        except ValueError as e:
            logger.error(str(e))
            return np.array([], dtype='int32'), np.array([], dtype='int32')

    def biss_read_snum(self) -> Optional[Tuple[str, str, str, str]]:
        """
        Reads the serial number and metadata from the BiSS encoder.

        Sends a read command to retrieve encoder metadata, including bootloader version,
        serial number, manufacturing date, and program version. Parses and logs the data, returning it as a tuple.

        Returns:
            Optional[Tuple[str, str, str, str]]: A tuple containing the bootloader version, serial number,
            manufacturing date, and program version as hex strings, or None if the read fails.

        Raises:
            FlashToolError: If the read operation times out or a communication error occurs.

        Example:
            >>> ft = FlashTool()
            >>> data = ft.biss_read_snum()
            >>> print(data)
            ('0100', '12345678', '20230101', '0200')
        """
        try:
            self._write_to_port(generate_byte_line(BiSSBank.FIXED_ADDRESSES_START_INDEX, UartCmd.HEX_READ_CMD, list(range(64))))
            time.sleep(0.1)
            cor = BiSSBank.FIXED_ADDRESSES_START_INDEX
            enc_ver_answ_uint8 = self.port_read(BiSSBank.FIXED_BANK_SIZE)
            ans = bytes_to_hex_str(enc_ver_answ_uint8)
            # *2 in indexes is for bytes,
            endict = {'Bootloader':  ans[(BiSSBank.BOOTLOADER_VER_REG_INDEX-cor)*2:
                                         (BiSSBank.BOOTLOADER_VER_REG_INDEX-cor+BiSSBank.BOOTLOADER_VER_SIZE)*2],
                      'Serial No ':  ans[(BiSSBank.DEV_SN_REG_INDEX-cor)*2:
                                         (BiSSBank.DEV_SN_REG_INDEX-cor+BiSSBank.DEV_SN_SIZE)*2],
                      'Mfg. Date ':  ans[(BiSSBank.MFG_REG_INDEX-cor)*2:
                                         (BiSSBank.MFG_REG_INDEX-cor+BiSSBank.MFG_REG_SIZE)*2],
                      'Program   ':  ans[(BiSSBank.PROGVER_REG_INDEX-cor)*2:
                                         (BiSSBank.PROGVER_REG_INDEX-cor+BiSSBank.PROGVER_REG_SIZE)*2],
                      'Dev ID_H  ':  ans[(BiSSBank.DEV_ID_H_REG_INDEX-cor)*2:
                                         (BiSSBank.DEV_ID_H_REG_INDEX-cor+BiSSBank.DEV_ID_H_SIZE)*2],
                      'Dev ID_L  ':  ans[(BiSSBank.DEV_ID_L_REG_INDEX-cor)*2:
                                         (BiSSBank.DEV_ID_L_REG_INDEX-cor+BiSSBank.DEV_ID_L_SIZE)*2]}
            logger.info('======= ENCODER DATA ========')
            for name, val in endict.items():
                logger.info(f'{str(name)}: \t {str(val)}')
            logger.info('=============================')
            try:
                logger.info(f"DEVID: {bytes.fromhex(endict['Dev ID_H  '] + endict['Dev ID_L  ']).decode('ascii')}, " +
                            f"Serial No: {bytes.fromhex(endict['Serial No '][0:4]).decode('ascii')}" +
                            f"{endict['Serial No '][4:8]}, " +
                            f"Mfg date: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(int(endict['Mfg. Date '], 16)))} "
                            + "(UTC)")
            except UnicodeDecodeError:
                pass
            logger.debug('Raw encoder answer: %s', ans)
            return (
                endict["Bootloader"],
                endict["Serial No "],
                endict["Mfg. Date "],
                endict["Program   "],
            )
        except FlashToolError as e:
            logger.error("ERROR: Can't read registers data! %s", e)
            return None

    def biss_read_HSI(self) -> Optional[Tuple[str]]:
        """
        Reads the HSI (Harmonic Signal Indicator) data from the BiSS encoder.

        Sends a read command to retrieve encoder metadata, including the HSI value, and logs the result.
        Returns the HSI value as a single-element tuple.

        Returns:
            Optional[Tuple[str]]: A tuple containing the HSI value as a string, or None if the read fails.

        Raises:
            FlashToolError: If the read operation times out or a communication error occurs.

        Example:
            >>> ft = FlashTool()
            >>> hsi = ft.biss_read_HSI()
            >>> print(hsi)
            ('1A',)
        """
        try:
            self._write_to_port(generate_byte_line(BiSSBank.FIXED_ADDRESSES_START_INDEX, UartCmd.HEX_READ_CMD, list(range(64))))
            time.sleep(0.1)
            enc_ver_answ_uint8 = self.port_read(BiSSBank.FIXED_BANK_SIZE)
            enc_ver_answ = bytes_to_hex_str(enc_ver_answ_uint8[4:])
            enc_ver_dict = {'HSI':  enc_ver_answ_uint8[BiSSBank.FIRSTHARMAMP_REG_INDEX-BiSSBank.FIXED_ADDRESSES_START_INDEX]}
            logger.info('======= ENCODER DATA ========')
            logger.debug('Raw encoder answer: %s', enc_ver_answ)
            for name, val in enc_ver_dict.items():
                logger.info(f'{str(name)}: \t {str(val)}')
            logger.info('=============================')
            return (
                enc_ver_dict["HSI"]
            )
        except FlashToolError as e:
            logger.error("ERROR: Can't read registers data! %s", e)
            return None

    def biss_read_progver(self) -> None:
        """
        Reads and logs the encoder's program version.

        Retrieves the program version from the BiSS encoder and logs it in a formatted string (e.g., "1.1.0.4").

        Returns:
            None

        Example:
            >>> ft = FlashTool()
            >>> ft.biss_read_progver()
            INFO: Encoder's program version: 1.1.0.4
        """
        logger.info("Encoder's program version: " + ".".join(
                    f"{num:X}" for num in self.biss_addr_read(BiSSBank.PROGVER_REG_INDEX, 4)[::-1]))

    def biss_read_calibration_temp_vcc(self) -> None:
        """
        Continuously reads and prints encoder calibration state, signal modulation, temperature, and VCC.

        Retrieves calibration data, including calibration state, signal modulation, temperature,
        and supply voltage, and prints them in a loop with a 1-second interval.

        Returns:
            None

        Example:
            >>> ft = FlashTool()
            >>> ft.biss_read_calibration_temp_vcc()
            CalState: 32, SignalMod: [3671, 4362], EncTemp = 27 °C, Vcc = 4.98 V
            ...
        """
        degree_sign = "\N{DEGREE SIGN}"
        while True:
            read_data = self.biss_addr_read(BiSSBank.ENC_DATA_REG_INDEX, 18).view('uint16').byteswap()
            print(f"CalState: {read_data[0]}, SignalMod: {read_data[[7, 8]]}, ",
                  f"EncTemp = {int(read_data[1] >> 8) - 64} {degree_sign}C, Vcc = {read_data[2] / 1000} V")
            time.sleep(1)

    def biss_read_command_state(self) -> Optional[np.ndarray]:
        """
        Reads the command state from the BiSS encoder.

        Sends a read command to retrieve the command state,
        validates the response with a checksum check, and returns the state as a NumPy array.

        Returns:
            Optional[np.ndarray]: A NumPy array of uint8 values containing the command state, or None if the read fails.

        Raises:
            FlashToolError: If the checksum validation fails or no data is received within the timeout.

        Example:
            >>> ft = FlashTool()
            >>> state = ft.biss_read_command_state()
            >>> print(state)
            array([0x01], dtype=uint8)
        """
        try:
            self._write_to_port(generate_byte_line(BiSSBank.CMD_STATE_FLAG_REG_INDEX, UartCmd.HEX_READ_CMD, [1]))
            time.sleep(0.01)
            if self.__port.in_waiting >= 1:
                biss_data = self.__port.read(6)
                biss_value = int.from_bytes(biss_data, byteorder='big', signed=False)
                if (calculate_checksum(biss_data[0:-1].hex())) == (biss_data[-1]):
                    crc_res = "OK"
                else:
                    crc_res = "FALSE"
                    logger.error(f"Received BiSS Data: {biss_value:#010x}, \
                                checksum calculated {calculate_checksum(biss_data[0:-1].hex())}, \
                                in data {(biss_data[-1])}, \tres = {crc_res}")
                    # raise FlashToolError('checksum validation failed for command state.')
                logger.debug(np.array(list(biss_data[:-1]), 'uint8'))
                return (np.array(list(biss_data[4:-1]), 'uint8'))
        except FlashToolError as e:
            logger.error("ERROR: Can't read command state! %s", e)
            return None

    def biss_addr_readb(self, bissbank: int, addr: int, length: int) -> np.ndarray:
        """
        Reads a specific range of registers from the specified BiSS bank.

        Selects the specified bank, sends a read command for the given address and length,
        and returns the data as a NumPy array after checksum validation.

        Args:
            bissbank: The BiSS bank number to read from (0-255).
            addr: The starting BiSS register address (0-127).
            length: The number of registers to read.

        Returns:
            np.ndarray: A NumPy array of uint8 values containing the register data.

        Raises:
            FlashToolError: If the read operation times out or a checksum error occurs.
            ValueError: If the address or bank number is out of range.

        Example:
            >>> ft = FlashTool()
            >>> data = ft.biss_addr_readb(1, 0x10, 4)
            >>> print(data)
            array([0x01, 0x02, 0x03, 0x04], dtype=uint8)
        """
        self.biss_set_bank(bissbank)
        self.__port.flushInput()
        self._write_to_port(generate_byte_line(addr, UartCmd.HEX_READ_CMD, list(range(length))))
        time.sleep(0.01)

        if self._wait_for_data(length + 1, timeout=1.0):
            biss_data = self.__port.read(length + 5)  # len, addr, addr, cmd, crc
            biss_value = int.from_bytes(biss_data, byteorder='big', signed=False)
            calculated_crc = calculate_checksum(biss_data[0:-1].hex())
            if calculated_crc == biss_data[-1]:
                crc_res = "OK"
                logger.debug(f"Received BiSS Data: {biss_value:#010x}, checksum calculated {calculated_crc}, \
                             in data {biss_data[-1]}, res = {crc_res}")
            else:
                crc_res = "FALSE"
                logger.error(f"Received BiSS Data: {biss_value:#010x}, checksum calculated {calculated_crc}, \
                             in data {biss_data[-1]}, res = {crc_res}")
            logger.debug("BiSS Bank %s registers at %s:", bissbank, addr)
            logger.debug(np.array(list(biss_data[4:-1]), 'uint8'))
            return np.array(list(biss_data[4:-1]), 'uint8')
            # logger.info(np.array(list(biss_data[0:64]), 'uint8'))
            # logger.info(np.array(list(biss_data[64:-1]), 'uint8'))
        raise FlashToolError('Timeout waiting for register data.')

    def biss_addr_read(self, addr: int, length: int) -> np.ndarray:
        """
        Reads a specific range of registers from the current BiSS bank.

        Sends a read command for the given address and length, and returns the data as a NumPy array after checksum validation.

        Args:
            addr: The starting BiSS register address (0-127).
            length: The number of registers to read.

        Returns:
            np.ndarray: A NumPy array of uint8 values containing the register data.

        Raises:
            FlashToolError: If the read operation times out or a checksum error occurs.
            ValueError: If the address is out of range.

        Example:
            >>> ft = FlashTool()
            >>> data = ft.biss_addr_read(0x10, 4)
            >>> print(data)
            array([0x01, 0x02, 0x03, 0x04], dtype=uint8)
        """
        self.__port.flushInput()
        self._write_to_port(generate_byte_line(addr, UartCmd.HEX_READ_CMD, list(range(length))))
        time.sleep(0.01)

        if self._wait_for_data(length + 1, timeout=1.0):
            biss_data = self.__port.read(length + 5)  # len, addr, addr, cmd, crc
            biss_value = int.from_bytes(biss_data, byteorder='big', signed=False)
            calculated_crc = calculate_checksum(biss_data[0:-1].hex())
            if calculated_crc == biss_data[-1]:
                crc_res = "OK"
                # logger.debug(f"Received BiSS Data: {biss_value:#010x}, checksum calculated {calculated_crc}, \
                #              in data {biss_data[-1]}, res = {crc_res}")
            else:
                crc_res = "FALSE"
                logger.error(f"Received BiSS Data: {biss_value:#010x}, checksum calculated {calculated_crc}, \
                             in data {biss_data[-1]}, res = {crc_res}")
                raise FlashToolError('checksum error.')
            logger.debug("Registers at %s:", addr)
            logger.debug(np.array(list(biss_data[4:-1]), 'uint8'))
            return np.array(list(biss_data[4:-1]), 'uint8')
            # logger.info(np.array(list(biss_data[0:64]), 'uint8'))
            # logger.info(np.array(list(biss_data[64:-1]), 'uint8'))
        raise FlashToolError('Timeout waiting for register data.')

    def biss_read_flags_flashCRC(self) -> int:
        """
        Reads the flash CRC error flag from the BiSS encoder.

        Retrieves the state flags and extracts the flash CRC error flag (bit 1).

        Returns:
            int: The flash CRC flag value (0 or 1).

        Raises:
            FlashToolError: If the read operation fails or CRC validation fails.

        Example:
            >>> ft = FlashTool()
            >>> crc_flag = ft.biss_read_flags_flashCRC()
            >>> print(crc_flag)
            0
        """
        state_flags = self.biss_read_state_flags()
        error_flags_flash_pos = 1  # TODO use ERROR_FLAGS here
        crc_flag = state_flags >> error_flags_flash_pos & 1
        return crc_flag

    def biss_read_flags(self) -> Tuple[list[str], list[str]]:
        """
        Reads and interprets state flags and command state from the BiSS encoder.

        Retrieves state flags and command state, interprets them using helper functions,
        and logs the results. Returns the interpreted error flags and command state descriptions.

        Returns:
            Tuple[List[str], List[str]]: A tuple containing:
                - A list of active error flag descriptions.
                - A list containing the command state description.

        Raises:
            FlashToolError: If reading state flags or command state fails.

        Example:
            >>> ft = FlashTool()
            >>> flags, cmd_state = ft.biss_read_flags()
            >>> print(flags, cmd_state)
            ['FLASH_CRC_ERROR'], ['IDLE']
        """
        try:
            state_flags = self.biss_read_state_flags()
            logger.debug("State flags raw data: %s", state_flags)
            flags = (state_flags[1] << 8) | state_flags[0]
            interpreted_flags = interpret_error_flags(flags)
            logger.info("Interpreted error flags: %s", interpreted_flags)
            command_state = self.biss_read_command_state()[0]
            logger.debug("Command state raw data: %s", command_state)
            interpreted_command_state = interpret_biss_commandstate(command_state)
            logger.info("Interpreted command state: %s", interpreted_command_state)

            return interpreted_flags, interpreted_command_state

        except FlashToolError as e:
            logger.error("Failed to read flags: %s", e)
            raise

    def biss_read_angle_once(self) -> None:
        """
        Reads the encoder angle once and prints it in degrees, minutes, and seconds.

        Retrieves a single angle reading from encoder 2, converts it to degrees, and prints the formatted output.

        Returns:
            None

        Example:
            >>> ft = FlashTool()
            >>> ft.biss_read_angle_once()
            [2119664]:    45° 30' 15"
        """
        degree_sign = "\N{DEGREE SIGN}"
        _, ans = self.read_data_enc1_enc2_SPI(0.01, False)
        res = 2**24
        ang = int(ans[0]) * 360 / res
        degrs = int(ang)
        mins = int((ang - degrs) * 60)
        secs = int((ang - degrs - (mins / 60)) * 3600)
        sys.stdout.write("\r" + f'[{ans[0]}]: \t {str(degrs):>3}{degree_sign} {str(mins):2}\' {str(secs):2}\"' + '\t\t')
        logger.debug(f'[{ans[0]}]: \t {str(degrs):>3}{degree_sign} {str(mins):2}\' {str(secs):2}\"')

    def biss_zeroing(self) -> None:
        """
        Performs a zeroing calibration on the BiSS encoder.

        Resets the FlashTool, power cycles the encoder, unlocks setup and flash,
        issues the zeroing command, saves to flash, and power cycles again.

        Returns:
            None

        Example:
            >>> ft = FlashTool()
            >>> ft.biss_zeroing()
        """
        self.flashtool_rst()
        self.encoder_power_cycle()

        self.biss_write_command('unlocksetup')
        self.biss_write_command('unlockflash')
        self.biss_write_command('zeroing')
        self.biss_write_command('saveflash')
        time.sleep(0.2)
        self.encoder_power_cycle()

    def biss_set_dir_cw(self) -> None:
        """
        Sets the encoder direction to clockwise.

        Resets the FlashTool, power cycles the encoder, unlocks setup and flash,
        issues the clockwise direction command, saves to flash, and power cycles again.

        Returns:
            None

        Example:
            >>> ft = FlashTool()
            >>> ft.biss_set_dir_cw()
        """
        self.flashtool_rst()
        self.encoder_power_cycle()

        self.biss_write_command('unlocksetup')
        self.biss_write_command('unlockflash')
        self.biss_write_command('set_dir_cw')
        self.biss_write_command('saveflash')
        time.sleep(0.2)
        self.encoder_power_cycle()

    def biss_set_dir_ccw(self) -> None:
        """
        Sets the encoder direction to counterclockwise.

        Resets the FlashTool, power cycles the encoder, unlocks setup and flash,
        issues the counterclockwise direction command, saves to flash, and power cycles again.

        Returns:
            None

        Example:
            >>> ft = FlashTool()
            >>> ft.biss_set_dir_ccw()
        """
        self.flashtool_rst()
        self.encoder_power_cycle()

        self.biss_write_command('unlocksetup')
        self.biss_write_command('unlockflash')
        self.biss_write_command('set_dir_ccw')
        self.biss_write_command('saveflash')
        time.sleep(0.2)
        self.encoder_power_cycle()

    def biss_set_shift(self, shift_angle: int) -> None:
        """
        Sets the encoder shift angle and verifies the operation.

        Reads the current angle, unlocks setup and flash, writes the shift angle,
        saves to flash, power cycles the encoder, and verifies the new shift angle.

        Args:
            shift_angle: The shift angle value to set.

        Returns:
            None

        Example:
            >>> ft = FlashTool()
            >>> ft.biss_set_shift(1000)
            [12345]:     45° 30' 15" # TODO
            [1000]:      0°  0'  0"
        """
        if not isinstance(shift_angle, int):
            raise ValueError(f"Shift angle must be an integer, got {type(shift_angle)}")
        if not 0 <= shift_angle <= 255:  # TODO CHECK
            raise ValueError(f"Shift angle must be in range [0, {2**24 - 1}], got {shift_angle}")

        self.biss_read_angle_once()
        self.biss_write_command('unlocksetup')
        self.biss_write_command('unlockflash')
        self.biss_write_word(BiSSBank.SHIFT_REG_INDEX, 5, shift_angle)  # TODO add validation
        self.biss_write_command('saveflash')
        time.sleep(0.1)
        print(self.biss_addr_read(BiSSBank.SHIFT_REG_INDEX, 1))

        self.encoder_power_cycle()
        print(self.biss_addr_read(BiSSBank.SHIFT_REG_INDEX, 1))
        self.biss_read_angle_once()

    def send_data_to_device(self,
                            pages: List[List[bytes]],
                            crc_values: List[int],
                            page_numbers: List[int],
                            start_page: int,
                            end_page: int,
                            pbar: Optional[Any] = None,
                            difmode: bool = False
                            ) -> None:
        """
        Transmits organized data pages to the BiSS encoder with CRC verification.

        Sends pages of data to the encoder, writing CRC and page numbers as needed,
        and verifies each page with a flash CRC check. Supports a progress bar and differential mode for specific use cases.

        Args:
            pages: A list of pages, where each page is a list of byte arrays.
            crc_values: A list of CRC checksums for each page.
            page_numbers: A list of page numbers corresponding to each page.
            start_page: The index of the first page to transmit.
            end_page: The index of the last page to transmit.
            pbar: An optional progress bar object for tracking transmission progress.
            difmode: If True, uses differential table transmission mode. Defaults to False.

        Raises:
            SystemExit: If transmission fails after the maximum number of retries.
            FlashToolError: If a hardware communication error occurs.

        Example:
            >>> ft = FlashTool()
            >>> pages = [[b'\\x01\\x02', b'\\x03\\x04'], [b'\\x05\\x06', b'\\x07\\x08']]
            >>> crc_values = [0x1234, 0x5678]
            >>> page_numbers = [1, 2]
            >>> ft.send_data_to_device(pages, crc_values, page_numbers, 0, 1)
            INFO: Done uploading!
        """
        max_retries = 3

        for page_idx, (page_data, crc, page_num) in enumerate(zip(pages, crc_values, page_numbers), start=start_page):
            if page_idx > end_page:
                break

            retry_count = 0
            success = False

            while retry_count < max_retries and not success:
                # Write CRC and page number for pages after the first
                if page_idx > 1:
                    self.biss_set_bank(BiSSBank.BISS_BANK_SERV)
                    self.biss_write_word(BiSSBank.CRC32_REG_INDEX, crc)
                    self.biss_write_word(BiSSBank.PAGENUM_REG_INDEX, page_num)
                    time.sleep(0.02)
                    # self.biss_read_registers(BISS_BANK_SERV)

                # Send each bank in the page
                for bank_idx, bank_data in enumerate(page_data):
                    bank_num = bank_idx + BiSSBank.BISS_USERBANK_START
                    if bank_num == 5:  # Set bank 5 explicitly
                        self.biss_set_bank(bank_num)
                    time.sleep(0.02)

                    if pbar:
                        percent_complete(bank_idx, BiSSBank.BANKS_PER_PAGE - 1, title=f"Sending Page {page_idx}")
                    # print('HEX-LINE', generate_hex_line(0, HEX_WRITE_CMD, bank_data))
                    hex_line = generate_hex_line(0, UartCmd.HEX_WRITE_CMD, bank_data)
                    self.hex_line_send(hex_line)

                time.sleep(0.3)
                if difmode:
                    self.biss_write_command('savediftable')
                else:
                    self.biss_write_command('load2k')

                time.sleep(0.25)

                if not self.biss_read_flags_flashCRC()[0]:
                    success = True
                    logger.debug("Page %s sent successfully", page_idx)
                else:
                    retry_count += 1
                    logger.error("Page %s CRC mismatch! Retry %s/%s", page_idx, retry_count, max_retries)
                    # self.power_cycle()
                    # self.biss_cmd_reboot2bl()
                    if retry_count == max_retries:
                        logger.critical("Failed to send page %s after %s attempts", page_idx, max_retries)
                        sys.exit(1)

        logger.info(" Done uploading!")
