r'''
 _     _____ _   _ _____   _____ _   _  ____ ___  ____  _____ ____  ____
| |   | ____| \ | |__  /  | ____| \ | |/ ___/ _ \|  _ \| ____|  _ \/ ___|
| |   |  _| |  \| | / /   |  _| |  \| | |  | | | | | | |  _| | |_) \___ \
| |___| |___| |\  |/ /_   | |___| |\  | |__| |_| | |_| | |___|  _ < ___) |
|_____|_____|_| \_/____|  |_____|_| \_|\____\___/|____/|_____|_| \_|____/


BiSSIOMixin — BiSS C register read/write, command dispatch, and calibration helpers.

Author:
    LENZ ENCODERS, 2020-2026
'''

import sys
import time
import logging
from enum import IntEnum
from typing import Iterable, Optional, List, Union, Tuple, Any
import numpy as np
from ..biss import (
    biss_commands, interpret_biss_commandstate, interpret_error_flags,
    BiSSBank,
)
from ..biss.encoder_state import ENCODER_STATE_FIELDS
from .uart import UartCmd
from .errors import FlashToolError, UARTErrorType, UARTErrorCode, BiSSFaultState
from .hex_utils import (
    calculate_checksum,
    generate_byte_line,
    generate_hex_line,
    reverse_endian, bytes_to_hex_str
)
from ..utils.progress import percent_complete

logger = logging.getLogger(__name__)


class BiSSIOMixin:
    """Mixin providing BiSS register I/O, command dispatch, status reads, and calibration helpers."""

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
            self._check_write_response(0.005)
            logger.debug("Sending BiSS %s command (%s)", command, hex(command_code))
            time.sleep(0.01)
        else:
            logger.error("Unknown command: '%s'", command)
            raise FlashToolError(f"Unknown command: '{command}'.")

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
            frame = generate_byte_line(BiSSBank.BSEL_REG_INDEX, UartCmd.HEX_WRITE_CMD, [bank_num])
            logger.debug(f"{frame.hex(' ')}")
            self._write_to_port(generate_byte_line(BiSSBank.BSEL_REG_INDEX, UartCmd.HEX_WRITE_CMD, [bank_num]))
            self._check_write_response(0.005)
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
            self._check_write_response()
        except (ValueError, TypeError) as e:
            logger.error("Validation error in biss_write: %s", str(e))
            raise

    def biss_write_word(self, addr: int, word: Union[int, List[int], bytearray, np.ndarray]) -> None:
        """
        Writes one or more 8, 16, or 32-bit words to BiSS registers starting at the specified address.

        Converts the provided word(s) to bytes, handles endianness, and writes them to the BiSS encoder.
        Supports:
        - Single integers or lists of integers
        - bytearray
        - numpy arrays (np.int8, np.int16, np.int32, np.uint8, np.uint16, np.uint32)

        Args:
            addr: The starting BiSS register address (0-127).
            word: A single integer, list of integers, bytearray, or numpy array to write.

        Raises:
            ValueError: If the address is out of range, the word list is empty, a word is negative,
            or a word exceeds the 32-bit limit.
            TypeError: If any word is not an integer.
            FlashToolError: If a hardware communication error occurs.

        Example:
            >>> ft = FlashTool()
            >>> ft.biss_write_word(0x10, 0xABCD)  # Write a 16-bit word
            >>> ft.biss_write_word(0x20, [0x01, 0x02])  # Write two 8-bit words
            >>> ft.biss_write_word(0x30, np.array([0x1234, 0x5678], dtype=np.int16))
            >>> ft.biss_write_word(0x40, bytearray([0x01, 0x02, 0x03]))
        """
        try:
            if not 0 <= addr <= 127:
                raise ValueError(f"Address {addr} out of range (0-127)")

            if isinstance(word, (np.int8, np.int16, np.int32, np.uint8, np.uint16, np.uint32)):
                words = [int(word)]
                word_size = word.itemsize

            elif isinstance(word, int):
                words = [word]
                max_word = word
                if max_word > 0xFFFFFFFF:
                    raise ValueError(f"Word value {max_word} exceeds 32-bit limit")
                word_size = 4 if max_word > 0xFFFF else (2 if max_word > 0xFF else 1)

            elif isinstance(word, np.ndarray):
                if word.ndim != 1:
                    raise ValueError(f"Numpy array must be 1-dimensional (got {word.ndim}D)")

                supported_dtypes = [
                    np.int8, np.int16, np.int32, np.uint8, np.uint16, np.uint32,
                    'int8', 'int16', 'int32', 'uint8', 'uint16', 'uint32'
                ]

                if word.dtype not in supported_dtypes:
                    raise ValueError(f"Unsupported numpy dtype: {word.dtype}. "
                                     f"Supported: int8, int16, int32, uint8, uint16, uint32")

                words = word.tolist()
                word_size = word.itemsize

                if word.dtype in [np.uint8, 'uint8'] and any(w > 0xFF for w in words):
                    raise ValueError("uint8 values must be <= 0xFF")
                elif word.dtype in [np.uint16, 'uint16'] and any(w > 0xFFFF for w in words):
                    raise ValueError("uint16 values must be <= 0xFFFF")
                elif word.dtype in [np.uint32, 'uint32'] and any(w > 0xFFFFFFFF for w in words):
                    raise ValueError("uint32 values must be <= 0xFFFFFFFF")

            elif isinstance(word, bytearray):
                words = list(word)
                word_size = 1

            elif isinstance(word, list):
                words = word
                if not words:
                    raise ValueError("Empty word list provided")

                for i, w in enumerate(words):
                    if not isinstance(w, int):
                        raise TypeError(f"Word {i} is not an integer (got {type(w)})")
                    if w < 0:
                        raise ValueError(f"Word {i} is negative ({w})")

                max_word = max(words)
                if max_word > 0xFFFFFFFF:
                    raise ValueError(f"Word value {max_word} exceeds 32-bit limit")
                word_size = 4 if max_word > 0xFFFF else (2 if max_word > 0xFF else 1)

            else:
                raise TypeError(f"Unsupported type: {type(word)}. "
                                f"Supported: int, list[int], bytearray, np.ndarray")

            if not isinstance(word, (np.ndarray, np.integer)):
                max_val_in_list = max(words) if words else 0
                if word_size == 1 and max_val_in_list > 0xFF:
                    raise ValueError(f"Word size determined as 1-byte, but value {max_val_in_list} > 0xFF")
                elif word_size == 2 and max_val_in_list > 0xFFFF:
                    raise ValueError(f"Word size determined as 2-byte, but value {max_val_in_list} > 0xFFFF")
                elif word_size == 4 and max_val_in_list > 0xFFFFFFFF:
                    raise ValueError(f"Word size determined as 4-byte, but value {max_val_in_list} > 0xFFFFFFFF")

            byte_list = []

            if isinstance(word, np.ndarray):
                byte_list = list(word.tobytes())
            elif isinstance(word, bytearray):
                byte_list = list(word)
            else:
                for w in words:
                    try:
                        byte_list.extend(w.to_bytes(word_size, byteorder='big', signed=(w < 0)))
                    except OverflowError as e:
                        raise ValueError(f"Word {w} doesn't fit in {word_size} byte(s)") from e

            reversed_bytes = reverse_endian(byte_list, word_size)

            if isinstance(word, np.ndarray):
                logger.debug("Sending numpy array %s (dtype: %s, shape: %s) to address %s",
                             word, word.dtype, word.shape, addr)
            else:
                logger.debug("Sending word %s with starting index %s", word, addr)

            self._write_to_port(generate_byte_line(addr, UartCmd.HEX_WRITE_CMD, reversed_bytes))
            self._check_write_response(0.005)
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
        self._write_to_port(generate_byte_line(BiSSBank.STATE_FLAG_REG_INDEX, UartCmd.HEX_READ_CMD, list(range(2))))
        biss_data = self._read_biss_response(expected_length=2, timeout=1.0)
        state_flags = np.frombuffer(biss_data[4:-1], dtype=np.uint8).copy()
        logger.debug(f"State flags: {state_flags}")
        return state_flags

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
        register_count = BiSSBank.REGISTER_PLUS_FIXED_BANK_SIZE
        self._write_to_port(generate_byte_line(0, UartCmd.HEX_READ_CMD, list(range(register_count))))
        biss_data = self._read_biss_response(expected_length=register_count, timeout=1.0)
        registers = np.frombuffer(biss_data[4:-1], dtype=np.uint8).copy()

        logger.info("BiSS registers:")
        logger.info(registers[:64])
        logger.info(registers[64:])

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
            self._write_to_port(generate_byte_line(BiSSBank.FIXED_ADDRESSES_START_INDEX, UartCmd.HEX_READ_CMD, list(range(BiSSBank.FIXED_BANK_SIZE))))
            biss_data = self._read_biss_response(expected_length=BiSSBank.FIXED_BANK_SIZE, timeout=1.0)
            enc_ver_answ_uint8 = np.frombuffer(biss_data[4:-1], dtype=np.uint8).copy()
            cor = BiSSBank.FIXED_ADDRESSES_START_INDEX
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
            program_val = endict['Program   ']
            program_bytes = [f"{int(program_val[i:i+2], 16):02d}" for i in range(0, 8, 2)]
            program_bytes_reversed = program_bytes[::-1]
            program_formatted = '.'.join(program_bytes_reversed)
            bootloader_val = endict['Bootloader']
            bootloader_bytes = [f"{int(bootloader_val[i:i+2], 16):02d}" for i in range(0, 8, 2)]
            bootloader_bytes_reversed = bootloader_bytes[::-1]
            bootloader_formatted = '.'.join(bootloader_bytes_reversed)
            logger.info(f"Program: {program_formatted}, " +
                        f"Bootloader: {bootloader_formatted}")
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
            biss_data = self._read_biss_response(expected_length=BiSSBank.FIXED_BANK_SIZE,timeout=1.0)
            enc_ver_answ_uint8 = np.frombuffer(biss_data[4:-1], dtype=np.uint8).copy()
            enc_ver_answ = bytes_to_hex_str(enc_ver_answ_uint8)
            enc_ver_dict = {'HSI':  enc_ver_answ_uint8[BiSSBank.FIRSTHARMAMP_REG_INDEX-BiSSBank.FIXED_ADDRESSES_START_INDEX]}
            logger.info('======= ENCODER DATA ========')
            logger.debug('Raw encoder answer: %s', enc_ver_answ)
            for name, val in enc_ver_dict.items():
                logger.info(f'{str(name)}: \t {str(val)}')
            logger.info('=============================')
            return (enc_ver_dict["HSI"])
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

    def biss_read_calibration_temp_vcc(self, iterations: Optional[int] = None) -> None:
        """
        Reads and prints encoder calibration state, signal modulation, temperature, and VCC.

        Retrieves calibration data, including calibration state, signal modulation, temperature,
        and supply voltage, and prints them in a loop with a 1-second interval.

        Args:
            iterations: Number of read cycles. ``None`` (default) loops until SIGINT
                is received (handled by :meth:`enable_signal_handling`) or the
                process is otherwise terminated. Pass an int for a bounded read.

        Returns:
            None

        Example:
            >>> ft = FlashTool()
            >>> ft.biss_read_calibration_temp_vcc()
            CalState: 32, SignalMod: [3671, 4362], EncTemp = 27 °C, Vcc = 4.98 V
            ...
        """
        degree_sign = "\N{DEGREE SIGN}"
        count = 0
        while iterations is None or count < iterations:
            read_data = self.biss_addr_read(BiSSBank.ENC_DATA_REG_INDEX, 18).view('uint16')
            print(f"CalState: {read_data[0]}, SignalMod: {read_data[[7, 8]]}, ",
                  f"EncTemp = {int(read_data[1]) - 64} {degree_sign}C, Vcc = {read_data[2] / 1000} V")
            count += 1
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
            self._write_to_port(generate_byte_line(BiSSBank.CMD_STATE_FLAG_REG_INDEX, UartCmd.HEX_READ_CMD, list(range(1))))
            biss_data = self._read_biss_response(expected_length=1, timeout=1.0)
            command_state = np.frombuffer(biss_data[4:-1], dtype=np.uint8).copy()
            logger.debug(f"Command state: {command_state}")
            return command_state
        except FlashToolError as e:
            logger.error("ERROR: Can't read command state! %s", e)
            return None

    def _read_biss_response(self, expected_length: int, timeout: float = 1.0) -> bytes:
        """Read and validate one length-prefixed HEX_READ_CMD response.

        Frame format: [payload_len][addr_hi][addr_lo][cmd][payload...][crc].
        A four-byte payload is used by the firmware for diagnostic error frames.
        """
        header = self._read_exact(1, timeout=timeout)
        response_len = header[0]
        if response_len > 128:
            raise FlashToolError(f"Invalid BiSS response length: {response_len}")

        # Fixed part after the length byte: address(2), command(1), payload, CRC(1).
        expected_total_len = response_len + 5
        rest = self._read_exact(expected_total_len - 1, timeout=timeout)
        response = header + rest

        logger.debug(
            "BiSS response: requested=%d, declared=%d, received=%d, raw=%s",
            expected_length,
            response_len,
            len(response),
            response.hex(" "),
        )

        calculated_crc = calculate_checksum(response[:-1].hex())
        if calculated_crc != response[-1]:
            raise FlashToolError(
                f"Checksum error in BiSS response: calculated 0x{calculated_crc:02X}, "
                f"received 0x{response[-1]:02X}"
            )

        if response[3] == FlashToolError.UART_CMD_ERROR_FRAME:
            self._raise_error_frame(response)

        if response_len != expected_length:
            raise FlashToolError(
                f"requested {expected_length} bytes, "
                f"device declared {response_len} bytes, "
                f"raw={response.hex(' ')}"
            )

        return response

    def _check_write_response(self, timeout: float = 0.05) -> None:
        """
        Check whether the device returned an error frame after a HEX_WRITE_CMD.

        Per the UART protocol, a successful ``HEX_WRITE_CMD`` (``0x0D``) produces
        **no response** — the device silently applies the write. However, on
        failure the device does send a diagnostic frame with the same layout as
        a read response::

            [len=4][addr_hi][addr_lo][0xE0]
            [offender_cmd][error_type][error_code][fault_state][crc]

        Args:
            timeout: Maximum time to wait for a potential error frame, in seconds.
                Defaults to ``0.05`` — enough for the device to start replying,
                small enough not to slow down normal writes.

        Returns:
            None: the method returns silently when no error frame is received.

        Raises:
            FlashToolError: If the device reports an error. The exception carries
                ``error_type``, ``error_code`` and ``fault_state`` decoded from
                the frame, plus a human-readable description.

        Example:
            >>> ft.biss_set_bank(164)   # device replies with BISS_FAULT_WRITE
            Traceback (most recent call last):
                ...
            FlashToolError: BiSS error: error_type=0x01 (ERROR_TYPE_BISS),
                error_code=0x04 (UART_ERROR_BISS_WRITE_FAULT: BiSS write fault),
                fault_state=0x02 (BISS_FAULT_WRITE: BiSS write fault)
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and self._port.in_waiting < 1:
            time.sleep(0.001)

        if self._port.in_waiting < 1:
            return

        header = self._read_exact(1, timeout=max(timeout, 0.1))
        response_len = header[0]

        expected_total = response_len + 5
        rest = self._read_exact(expected_total - 1, timeout=max(timeout, 0.1))
        data = header + rest

        calculated_crc = calculate_checksum(data[:-1].hex())
        if calculated_crc != data[-1]:
            raise FlashToolError(
                f"Checksum error in write response: "
                f"calculated 0x{calculated_crc:02X}, received 0x{data[-1]:02X}"
            )

        if data[3] == FlashToolError.UART_CMD_ERROR_FRAME:
            logger.debug(
                "Error frame after WRITE_REG: offender=0x%02X, type=0x%02X, "
                "code=0x%02X, fault=0x%02X",
                data[4], data[5], data[6], data[7],
            )
            self._raise_error_frame(data)

        logger.warning(
            "Unexpected RX after WRITE_REG: "
            "len=%d, cmd=0x%02X, raw=%s",
            response_len,
            data[3] if len(data) > 3 else 0,
            data.hex(" "),
        )

        raise FlashToolError(
            f"Unexpected response after HEX_WRITE_CMD: {data.hex(' ')}"
        )

    def _raise_error_frame(self, data: bytes) -> None:
        """Decode and raise a firmware diagnostic error frame.

        Frame:
            [len=4][addr_hi][addr_lo][0xE0]
            [offender_cmd][error_type][error_code][fault_state][crc]
        """
        if len(data) != 9 or data[0] != 4:
            raise FlashToolError(
                f"Invalid error frame length: declared={data[0] if data else 'N/A'}, "
                f"received={len(data)}, raw={data.hex(' ')}"
            )

        if data[3] != FlashToolError.UART_CMD_ERROR_FRAME:
            raise FlashToolError(
                f"Invalid error frame command: 0x{data[3]:02X}"
            )
        
        offender_cmd = data[4]
        error_type   = data[5]
        error_code   = data[6]
        fault_state  = data[7]

        raise FlashToolError(
            "",
            offender_cmd=offender_cmd,
            error_type=UARTErrorType(error_type),
            error_code=UARTErrorCode(error_code),
            fault_state=BiSSFaultState(fault_state),
        )

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
        if not 0 <= bissbank <= 255:
            raise ValueError("bissbank must be in range 0..255")
        if not 0 <= addr <= 127:
            raise ValueError("addr must be in range 0..127")
        if not 1 <= length <= 128:
            raise ValueError("length must be in range 1..128")

        self.biss_set_bank(bissbank)
        self._write_to_port(generate_byte_line(addr, UartCmd.HEX_READ_CMD, list(range(length))))
        biss_data = self._read_biss_response(expected_length=length, timeout=1.0)
        register_data = np.frombuffer(biss_data[4:-1], dtype=np.uint8).copy()
        logger.info("Registers in bank %s at address %s:\n%s", bissbank, addr, register_data)
        return register_data

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
        if not isinstance(addr, int) or not 0 <= addr <= 127:
            raise ValueError("addr must be an integer in range 0..127")
        if not isinstance(length, int) or not 1 <= length <= 128:
            raise ValueError("length must be an integer in range 1..128")

        self._write_to_port(generate_byte_line(addr, UartCmd.HEX_READ_CMD, list(range(length))))
        biss_data = self._read_biss_response(expected_length=length, timeout=1.0)
        register_data = np.frombuffer(biss_data[4:-1], dtype=np.uint8).copy()
        logger.debug("Registers at %s:\n%s", addr, register_data)
        return register_data

    def read_encoder_flag(
        self,
        flag_name: Optional[str] = None,
        start_bit: Optional[int] = None,
        num_bits: int = 1,
    ) -> Union[IntEnum, int]:
        """
        Reads a bitfield from the EncoderState register (BiSSBank.ENC_DATA_REG_INDEX, 0x4A).

        Two modes:
            - Named:  pass ``flag_name`` to resolve the field via ``ENCODER_STATE_FIELDS``
              and get back the corresponding ``IntEnum`` member.
            - Raw:    pass ``start_bit`` (and optionally ``num_bits``) to get back a
              plain integer for fields not modeled as an enum.

        Args:
            flag_name: Name of a field defined in
                :data:`lenz_flashtool.biss.encoder_state.ENCODER_STATE_FIELDS`
                (e.g. ``'AmplitudeCalibration'``).
            start_bit: LSB position of the field within the 16-bit register (0-15).
                Required when ``flag_name`` is ``None``.
            num_bits: Width of the field in bits. Only used in raw mode.

        Returns:
            ``IntEnum`` member when ``flag_name`` is given, otherwise the raw
            integer value of the extracted bits.

        Raises:
            ValueError: If ``flag_name`` is unknown, neither argument is provided,
                or the extracted raw value is not a defined member of the target
                enum (indicates firmware/library drift).
            FlashToolError: Propagated from the underlying BiSS read.

        Examples:
            >>> ft.read_encoder_flag('AmplitudeCalibration')
            <AmplitudeCalibration.DONE: 3>
            >>> ft.read_encoder_flag(start_bit=11, num_bits=2)
            0
        """
        if flag_name is not None:
            try:
                enum_cls, start_bit, num_bits = ENCODER_STATE_FIELDS[flag_name]
            except KeyError:
                raise ValueError(
                    f"Unknown flag: {flag_name!r}. "
                    f"Available: {list(ENCODER_STATE_FIELDS)}"
                )
        else:
            if start_bit is None:
                raise ValueError("Must provide either flag_name or start_bit")
            enum_cls = None

        raw = self.biss_addr_read(BiSSBank.ENC_DATA_REG_INDEX, 2)
        value = int(raw[0]) | (int(raw[1]) << 8)
        mask = (1 << num_bits) - 1
        field_val = (value >> start_bit) & mask

        if enum_cls is not None:
            return enum_cls(field_val)
        return field_val

    def wait_for_flag(
        self,
        flag_name: str,
        target_state: Union[int, IntEnum, Iterable[Union[int, IntEnum]]],
        timeout: float = 30.0,
        interval: float = 0.2,
    ) -> IntEnum:
        """
        Polls the EncoderState register until ``flag_name`` reaches an accepted state.

        Transient :class:`FlashToolError` exceptions raised during polling are
        logged at DEBUG level and retried on the next interval — BiSS reads can
        briefly fail while the encoder is busy with long operations (flashing,
        calibration).

        Args:
            flag_name: Name of the field to poll (key in ``ENCODER_STATE_FIELDS``).
            target_state: Single acceptable state or an iterable of acceptable
                states. Each may be an ``IntEnum`` member or a plain ``int``.
            timeout: Maximum total wait time, in seconds.
            interval: Delay between polls, in seconds.

        Returns:
            The ``IntEnum`` state that satisfied the predicate.

        Raises:
            TimeoutError: If no accepted state is observed within ``timeout``.

        Example:
            >>> from lenz_flashtool import AmplitudeCalibration
            >>> ft.wait_for_flag(
            ...     'AmplitudeCalibration',
            ...     [AmplitudeCalibration.DONE, AmplitudeCalibration.IDLE],
            ...     timeout=30.0,
            ...     interval=0.5,
            ... )
        """
        if isinstance(target_state, (int, IntEnum)):
            targets = {int(target_state)}
        else:
            targets = {int(s) for s in target_state}

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                state = self.read_encoder_flag(flag_name)
            except FlashToolError as e:
                logger.debug("Transient error reading %s: %s; retrying.", flag_name, e)
            else:
                if int(state) in targets:
                    logger.info("%s reached target state: %s", flag_name, state)
                    return state
            time.sleep(interval)

        raise TimeoutError(
            f"Timeout ({timeout}s) waiting for {flag_name} "
            f"to reach one of {sorted(targets)}"
        )

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
        logger.debug(f"Crc flag: {crc_flag}")
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
            if state_flags is None:
                logger.error("Failed to read state flags: No data received")
                raise FlashToolError("No state flags data received from encoder")
            logger.debug("State flags raw data: %s", state_flags)
            flags = (np.uint16(state_flags[1]) << 8) | state_flags[0]
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
        try:
            ans, _ = self.read_data_enc1_AB_enc2_SPI(0.01, False)
            if not ans.any() or len(ans) < 1:
                logger.error("No valid data received from encoder")
                return

            raw_value = int(ans[0])
            resolution = 2**24
            total_degrees = raw_value * 360.0 / resolution

            degrees = int(total_degrees)
            remaining = total_degrees - degrees
            minutes = int(remaining * 60)
            seconds = round((remaining * 60 - minutes) * 60, 2)

            output = (f"[{raw_value}]: \t"
                      f"{degrees:>3}{degree_sign} "
                      f"{minutes:02d}' "
                      f"{seconds:05.2f}\"")

            sys.stdout.write("\r" + output + " " * 10)
            logger.debug(output)

        except ValueError as e:
            logger.error(f"Invalid encoder data: {e}")
        except Exception as e:
            logger.error(f"Error reading angle: {e}")

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
        self.biss_write_word(BiSSBank.SHIFT_REG_INDEX, shift_angle)  # TODO add validation
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
                    # time.sleep(0.01)

                # Send each bank in the page
                for bank_idx, bank_data in enumerate(page_data):
                    bank_num = bank_idx + BiSSBank.BISS_USERBANK_START
                    if bank_num == 5:  # Set bank 5 explicitly
                        self.biss_set_bank(bank_num)
                    # time.sleep(0.05)

                    if pbar:
                        percent_complete(bank_idx, BiSSBank.BANKS_PER_PAGE - 1, title=f"Sending Page {page_idx}")
                    hex_line = generate_hex_line(0, UartCmd.HEX_WRITE_CMD, bank_data)
                    self.hex_line_send(hex_line)
                    self._check_write_response(0.005)

                time.sleep(0.3)
                if difmode:
                    self.biss_write_command('savediftable')
                else:
                    self.biss_write_command('load2k')

                time.sleep(1.25)

                if not self.biss_read_flags_flashCRC()[0]:
                    success = True
                    logger.debug("Page %s sent successfully", page_idx)
                else:
                    retry_count += 1
                    logger.error("Page %s CRC mismatch! Retry %s/%s", page_idx, retry_count, max_retries)
                    if retry_count == max_retries:
                        logger.critical("Failed to send page %s after %s attempts", page_idx, max_retries)
                        raise FlashToolError(f"Failed to send page {page_idx} after {max_retries} attempts")

        logger.info(" Done uploading!")
