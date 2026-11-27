r'''
 _     _____ _   _ _____   _____ _   _  ____ ___  ____  _____ ____  ____
| |   | ____| \ | |__  /  | ____| \ | |/ ___/ _ \|  _ \| ____|  _ \/ ___|
| |   |  _| |  \| | / /   |  _| |  \| | |  | | | | | | |  _| | |_) \___ \
| |___| |___| |\  |/ /_   | |___| |\  | |__| |_| | |_| | |___|  _ < ___) |
|_____|_____|_| \_/____|  |_____|_| \_|\____\___/|____/|_____|_| \_|____/


SerialIOMixin — Low-level serial port I/O for FlashTool.

Author:
    LENZ ENCODERS, 2020-2026
'''

import time
import logging
import numpy as np
import serial
from .errors import FlashToolError
from .hex_utils import calculate_checksum

logger = logging.getLogger(__name__)


class SerialIOMixin:
    """Mixin providing low-level serial port read/write and port-discovery helpers."""

    def _find_linux_port_enhanced(self, ports, port_description_prefixes):
        """
        Enhanced Linux port detection for FlashTool devices.

        Searches for available serial ports that match the specified criteria,
        with priority given to XR21V1410 devices.

        Args:
            ports: List of serial port objects obtained from serial.tools.list_ports.comports()
            port_description_prefixes: Tuple of string prefixes to match against port descriptions
                                    (e.g., ('XR21V',) for XR21V1410 devices)

        Returns:
            str or None: Device path (e.g., '/dev/ttyUSB0') if a matching port is found,
                        None if no compatible device is detected.

        Search Patterns (in order of priority):
            1. VID:PID matching - Looks for '04e2:1410' in hardware ID (most reliable)
            2. Description matching - Checks if port description contains any of the prefixes
            3. Manufacturer matching - Checks if manufacturer field contains any of the prefixes
            4. Product matching - Checks if product field contains any of the prefixes

        Example:
            >>> ports = serial.tools.list_ports.comports()
            >>> device = self._find_linux_port_enhanced(ports, ('XR21V',))
            >>> print(device)
            '/dev/ttyUSB0'
        """

        search_patterns = [
            # VID:PID (04e2:1410 for XR21V1410)
            lambda p: '04e2:1410' in p.hwid.lower(),
            lambda p: p.description and any(prefix in p.description for prefix in port_description_prefixes),
            lambda p: p.manufacturer and any(prefix in p.manufacturer for prefix in port_description_prefixes),
            lambda p: p.product and any(prefix in p.product for prefix in port_description_prefixes),
        ]

        for port in ports:
            for pattern in search_patterns:
                try:
                    if pattern(port):
                        logger.debug(f"Found port: {port.device} - {port.description} (HWID: {port.hwid})")
                        return port.device
                except Exception as e:
                    logger.debug(f"Error checking pattern on port {port.device}: {e}")
                    continue
        return None

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
            if self._port.in_waiting >= size:
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
            self._port.reset_input_buffer()
            self._port.reset_output_buffer()
            self._port.write(data)
            self._port.flush()
        except (serial.SerialException, OSError) as e:
            logger.error("Port write failed: %s", e)
            raise FlashToolError(f"Hardware communication failed: {e}") from e
        except Exception as e:
            logger.critical("Unexpected port write error: %s", e)
            raise FlashToolError("Critical write operation failure") from e

    def port_read(self, length: int) -> np.ndarray:
        """
        Reads a BiSS frame from the serial port, validates its checksum, and returns the payload.

        The method blocks until the expected number of bytes arrives (or a timeout occurs).
        A complete BiSS frame consists of:

        * 1 byte  - length
        * 2 bytes - address (repeated)
        * 1 byte  - command
        * ``length`` bytes - payload data
        * 1 byte  - checksum

        The checksum is verified with :func:`calculate_checksum` over **all bytes except the
        checksum itself**.  If verification succeeds the payload (the ``length`` data bytes)
        is returned as a ``uint8`` NumPy array.  On failure a ``FlashToolError`` is raised.

        Args:
            length: Number of **payload** bytes expected (excludes the 5 technical bytes:
                    length, address*2, command, checksum).

        Returns:
            np.ndarray: 1-D array of ``dtype=uint8`` containing only the payload data.

        Raises:
            FlashToolError:
                * If no data arrives within the internal timeout (currently 1 s).
                * If the received checksum does not match the calculated one.

        Example:
            >>> ft = FlashTool()
            >>> data = ft.port_read(10)
            >>> print(data)
            array([0x01, 0x02, ..., 0x0A], dtype=uint8)
        """
        if self._wait_for_data(length + 1, timeout=1.0):
            biss_data = self._port.read(length + 5)  # len, addr, addr, cmd, checksum
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
            logger.debug("BiSS received data:")
            data_array = np.array(list(biss_data[4:-1]), 'uint8')
            logger.debug(data_array)
            return data_array
        raise FlashToolError('Timeout waiting for register data.')

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
        tx_row = bytes.fromhex(hex_line[1:])
        self._write_to_port(tx_row)
        return tx_row
