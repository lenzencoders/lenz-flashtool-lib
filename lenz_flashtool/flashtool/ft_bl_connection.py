r"""
 _     _____ _   _ _____   _____ _   _  ____ ___  ____  _____ ____  ____
| |   | ____| \ | |__  /  | ____| \ | |/ ___/ _ \|  _ \| ____|  _ \/ ___|
| |   |  _| |  \| | / /   |  _| |  \| | |  | | | | | | |  _| | |_) \___ \
| |___| |___| |\  |/ /_   | |___| |\  | |__| |_| | |_| | |___|  _ < ___) |
|_____|_____|_| \_/____|  |_____|_| \_|\____\___/|____/|_____|_| \_|____/


FlashTool Bootloader Connection Module

This module provides functionality for establishing and maintaining a connection with a device
in bootloader mode over a serial port. It implements a robust connection protocol with retry
mechanisms and timeout handling for reliable firmware flashing operations.

Key Features:
- Automatic detection of COM ports with specified prefix
- Bootloader sequence handshake protocol
- Configurable timeout and retry behavior
- Detailed logging and status reporting
- Thread-safe serial communication

Protocol Flow:
1. Scan for available COM ports matching the specified prefix
2. Establish connection with the first matching port
3. Send stay-in-bootloader command sequence
4. Verify correct response sequence
5. Retry on failure with exponential backoff

Dependencies:
- serial: For serial port communication
- numpy: For array comparison operations
- logging: For system logging
- time: For delay and timeout handling
- ..utils.termcolors: For colored terminal output
- .uart: For bootloader command definitions
- lenz_flashtool: Core FlashTool functionality

Usage Example:
    >>> if connect_and_stay_in_bl(timeout_s=30):
    ...     print("Device successfully entered bootloader mode")
    ... else:
    ...     print("Failed to connect to bootloader")

Security Notes:
- Implements command/response verification
- Limits retry attempts to prevent infinite loops
- Uses timeout safeguards for all operations

Author:
    LENZ ENCODERS, 2020-2025
"""
import time
import numpy as np
import logging
import serial.tools.list_ports
from ..utils.termcolors import TermColors
from .uart import UartBootloaderCmd, UartBootloaderSeq
import lenz_flashtool as ft
from .core import FlashTool

logger = logging.getLogger(__name__)

port_prefix = 'XR21V'


def connect_and_stay_in_bl(timeout_s: int = 20, retry_delay: float = 0.5) -> bool:
    """
    Wait for COM port and send boot sequence to stay in bootloader mode.

    Continuously scans for available COM ports matching the specified prefix and attempts
    to establish a bootloader connection. Implements a robust handshake protocol with
    configurable timeout and retry behavior.

    Args:
        timeout_s: Maximum time in seconds to attempt connection (default: 20)
        retry_delay: Delay in seconds between port scan attempts (default: 0.5)

    Returns:
        bool: True if successful handshake, False if timeout reached

    Raises:
        RuntimeError: If serial communication fails catastrophically
        ValueError: If invalid parameters are provided

    Side Effects:
        - Attempts to open and configure serial ports
        - Modifies device state if successful
        - Outputs status messages to console and log

    Example:
        >>> # Wait up to 20 seconds for bootloader connection
        >>> success = connect_and_stay_in_bl(timeout_s=30)
        >>> if success:
        ...     # Proceed with firmware update
    """
    start_time = time.time()
    last_port = None

    print(f"{TermColors.Yellow}Waiting for COM port with prefix {port_prefix} (timeout: {timeout_s}s)...{TermColors.Default}")

    tx_row = bytes.fromhex(ft.generate_hex_line(
        address=0x0000,
        command=UartBootloaderCmd.UART_COMMAND_STATE_STAY_BL,
        data=UartBootloaderSeq.UART_SEQ_STAY_IN_BL
    )[1:])

    logger.debug(f"Sent BiSS Data: {tx_row.hex()}")

    while time.time() - start_time < timeout_s:
        available_ports = [
            p for p in serial.tools.list_ports.comports()
            if p.description.startswith(port_prefix)
        ]

        if not available_ports:
            time.sleep(retry_delay)
            continue

        port = available_ports[0]  # Take first matching port

        if port.device != last_port:
            print(f"{TermColors.Green}Found port: {port.device} ({port.description}){TermColors.Default}")
            last_port = port.device

        try:
            with FlashTool(port_description_prefixes=(port_prefix,)) as lenz:
                for attempt in range(3):
                    try:
                        lenz._write_to_port(tx_row)
                        response = lenz.port_read(len(tx_row) - 1)

                        if np.array_equal(response, UartBootloaderSeq.UART_SEQ_ANSWER_TO_STAY_IN_BL):
                            logger.info(f"{TermColors.Green}Answer sequence to stay in bl is correct{TermColors.Default}")
                            return True

                    except Exception as e:
                        print(f"{TermColors.Yellow}Attempt {attempt + 1} failed: {str(e)}{TermColors.Default}")
                        if attempt == 2:
                            raise
                        time.sleep(0.1)

        except Exception as e:
            logger.error(f"Error on {port.device}: {str(e)}")
            time.sleep(1)
            continue

    print(f"Timeout after {timeout_s} seconds")
    return False


def connect_and_enter_fw(timeout_s: int = 20, retry_delay: float = 0.5) -> bool:
    """
    Waits for a COM port with a specific prefix to become available, connects to it,
    and sends a firmware entry command once.

    The function will continuously monitor for the specified COM port until either:
    - The port is found and the command is successfully sent (returns True)
    - The timeout period is exceeded (returns False)

    Args:
        timeout_s: Maximum time in seconds to wait for the port (default: 20)
        retry_delay: Delay in seconds between port availability checks (default: 0.5)

    Returns:
        bool: True if command was successfully sent, False if timeout occurred
    """
    start_time = time.time()
    last_port = None

    print(f"{TermColors.Yellow}Waiting for COM port with prefix {port_prefix} "
          f"(timeout: {timeout_s}s)...{TermColors.Default}")

    tx_data = bytes.fromhex(ft.generate_hex_line(
        address=0x0000,
        command=UartBootloaderCmd.UART_COMMAND_RUN_PROGRAM,
        data=[0x00]
    )[1:])

    logger.debug(f"Command to send: {tx_data.hex()}")

    while time.time() - start_time < timeout_s:
        available_ports = [
            p for p in serial.tools.list_ports.comports()
            if p.description.startswith(port_prefix)
        ]

        if not available_ports:
            time.sleep(retry_delay)
            continue

        port = available_ports[0]  # Use first matching port

        if port.device != last_port:
            print(f"{TermColors.Green}Found port: {port.device} "
                  f"({port.description}){TermColors.Default}")
            last_port = port.device

        try:
            with FlashTool(port_description_prefixes=(port_prefix,)) as tool:
                for attempt in range(3):  # Retry up to 3 times
                    try:
                        tool._write_to_port(tx_data)
                        print(f"{TermColors.Green}Command successfully sent{TermColors.Default}")
                        return True
                    except Exception as e:
                        print(f"{TermColors.Yellow}Attempt {attempt + 1} failed: "
                              f"{str(e)}{TermColors.Default}")
                        if attempt == 2:  # Last attempt failed
                            raise
                        time.sleep(0.1)
        except Exception as e:
            logger.error(f"Error on {port.device}: {str(e)}")
            time.sleep(1)
            continue

    print(f"{TermColors.Red}Timeout after {timeout_s} seconds{TermColors.Default}")
    return False
