r'''
 _     _____ _   _ _____   _____ _   _  ____ ___  ____  _____ ____  ____
| |   | ____| \ | |__  /  | ____| \ | |/ ___/ _ \|  _ \| ____|  _ \/ ___|
| |   |  _| |  \| | / /   |  _| |  \| | |  | | | | | | |  _| | |_) \___ \
| |___| |___| |\  |/ /_   | |___| |\  | |__| |_| | |_| | |___|  _ < ___) |
|_____|_____|_| \_/____|  |_____|_| \_|\____\___/|____/|_____|_| \_|____/


BiSS Flash Tool - HEX/DIF Data Transmission Module

This module provides functionality to read HEX/DIF files and transmit the data to a BiSS device.
It handles parsing, organizing data into pages/banks, and communication with the BiSS interface.

Key Features:
- Parses standard Intel HEX format files with LENZ-specific extensions
- Supports Differential Index Table (DIF) CSV files
- Organizes data into banks and pages according to BiSS specifications
- Implements CRC verification and retry mechanisms
- Provides progress tracking during data transmission

Modules:
    - os: Operating system interfaces
    - sys: System-specific parameters and functions
    - logging: Event logging system
    - time: Time access and conversions
    - numpy: Array processing for DIF files
    - colorama: Cross-platform colored terminal text
    - libs.lib_progress: Progress bar utilities
    - lib_flashtool: BiSS FlashTool interface library

Classes:
    - HexRecord: Represents a single record from a HEX file

Functions:
    - read_hex_file: Reads and parses a HEX file into HexRecord objects
    - parse_hex_file: Extracts data, CRC, and page numbers from HEX records
    - organize_data_into_pages: Structures data into pages/banks for transmission
    - send_data_to_device: Transmits organized data to the BiSS device
    - send_hex: Main function for HEX file transmission
    - send_dif: Main function for DIF file transmission

Usage:
    For HEX files:
        send_hex("input_file.hex")

    For DIF files:
        send_dif("input_file.csv")

Author:
    LENZ ENCODERS, 2020-2025
'''

from os import path
import sys
import logging
from typing import List, Tuple
import struct
import binascii
from csv import reader
import colorama  # for Windows
import numpy as np
from ..biss.registers import BiSSBank
colorama.init()  # for Windows

# Constants
START_PAGE = 1
END_PAGE = 60
FILL_BYTE = 'FF'

logger = logging.getLogger(__name__)


class HexRecord:
    """Represents a single record from an Intel HEX format file with LENZ extensions.

    The LENZ extended HEX format includes additional record types for CRC and page information
    while maintaining compatibility with standard Intel HEX format.

    Attributes:
        byte_count (int): The number of data bytes in the record (0-255).
        address (int): The 16-bit starting address for the data (0x0000-0xFFFF).
        record_type (int): The type of the HEX record (0x00-0x05).
        data (bytearray): The actual data bytes contained in the record.

    LENZ Encrypted Record Types                         Common Record Types:
        0x00: Data record
        0x01: End of File record
        0x02: Unused                                    (Extended Segment Address record)
        0x03: CRC of the page data record               (Start Segment Address record)
        0x04: Page record in format (:02000004<page><64B blocks count>XX)
        0x05: Unused                                    (Start Linear Address record)
    """

    def __init__(self, byte_count: int, address: int, record_type: int, data: bytearray) -> None:
        """Initializes a new HexRecord instance.

        Args:
            byte_count: The count of data bytes in this record. Must be between 0 and 255.
            address: The starting memory address for this record's data. 16-bit value.
            record_type: The type of HEX record. Common values are 0x00-0x05.
            data: The actual data bytes contained in this record. Length must match byte_count.

        Raises:
            ValueError: If byte_count doesn't match data length or values are out of valid ranges.
        """
        if byte_count != len(data):
            raise ValueError(f"Byte count {byte_count} doesn't match data length {len(data)} {data}")
        if not 0 <= byte_count <= 255:
            raise ValueError(f"Byte count {byte_count} must be between 0 and 255")
        if not 0 <= address <= 0xFFFF:
            raise ValueError(f"Address {hex(address)} must be between 0x0000 and 0xFFFF")
        if not 0 <= record_type <= 5:
            raise ValueError(f"Record type {hex(record_type)} must be between 0x00 and 0x05")

        self.byte_count = byte_count
        self.address = address
        self.record_type = record_type
        self.data = data

    def __str__(self) -> str:
        """Returns a human-readable string representation of the HEX record.

        Returns:
            A formatted string showing all record fields in hexadecimal notation.
        """
        return (f"HexRecord(type=0x{self.record_type:02X}, "
                f"address=0x{self.address:04X}, "
                f"bytes={self.byte_count}, "
                f"data={bytes(self.data).hex().upper()})")

    def to_hex_line(self) -> str:
        """Converts the record back to Intel HEX format string.

        Calculates the checksum and formats all fields according to the HEX specification.

        Returns:
            A string in Intel HEX format (e.g., ':10010000214601360121470136007EFE09D2190140')

        Raises:
            ValueError: If the record contains invalid data that can't be properly formatted.
        """
        if not self.data and self.record_type != 0x01:  # EOF record can have 0 bytes
            raise ValueError("Data records must contain at least one byte of data")

        # Calculate checksum: sum of all bytes mod 256, then two's complement
        checksum = self.calculate_checksum()

        hex_line = (f":{self.byte_count:02X}{self.address:04X}{self.record_type:02X}"
                    f"{self.data.hex().upper()}{checksum:02X}")
        return hex_line

    def calculate_checksum(self) -> int:
        """Calculate hex record checksum"""
        checksum = self.byte_count
        checksum += (self.address >> 8) & 0xFF  # High byte of address
        checksum += self.address & 0xFF         # Low byte of address
        checksum += self.record_type
        checksum += sum(self.data)
        return (~checksum + 1) & 0xFF       # Two's complement

    @classmethod
    def create_extended_address(cls, page: int) -> 'HexRecord':
        """Factory method for extended address records."""
        upper_bits = (page >> 5) & 0xFF
        return cls(
            byte_count=2,
            address=0x0000,
            record_type=0x04,
            data=bytearray([0x08, upper_bits])  # 08 indicates address upper bits
        )

    @classmethod
    def create_crc_record(cls, crc_value: int) -> 'HexRecord':
        """Factory method for CRC32 records."""
        return cls(
            byte_count=4,
            address=0x0000,
            record_type=0x03,  # CRC record type
            data=bytearray(crc_value.to_bytes(4, 'big'))
        )

    @classmethod
    def from_line(cls, line: str) -> 'HexRecord':
        """Parse an Intel HEX line into a HexRecord object."""
        # if not line.startswith(':'):
        #     raise ValueError(f"Invalid HEX line: {line}")
        if line.startswith(':'):
            line = line[1:].strip()  # Remove ':' and trailing whitespace
        byte_count = int(line[0:2], 16)
        address = int(line[2:6], 16)
        record_type = int(line[6:8], 16)
        data_end = 8 + byte_count * 2
        data_hex = line[8:data_end]
        data = [int(data_hex[i:i+2], 16) for i in range(0, len(data_hex), 2)]
        checksum = int(line[data_end:data_end+2], 16)

        record = cls(byte_count, address, record_type, data)
        # Optional: Verify checksum
        if record.calculate_checksum() != checksum:
            raise ValueError(f"Checksum mismatch in line: {line}, calculated: {record.calculate_checksum()}")
        return record


def read_hex_file(filepath: str) -> List[HexRecord]:
    """Reads and parses an Intel HEX file into HexRecord objects.

    Args:
        filepath: Path to the HEX file to read

    Returns:
        List of HexRecord objects representing the file contents

    Raises:
        SystemExit: If file not found or parsing errors occur
    """
    if not path.exists(filepath):
        print(f"File not found: {filepath}")
        sys.exit(1)

    hex_records = []
    try:
        with open(filepath, mode='r',  encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if line:  # Skip empty lines
                    record = HexRecord.from_line(line)
                    hex_records.append(record)
    except (ValueError, IndexError) as e:
        print(f"Error parsing HEX file {filepath}: {e}")
        sys.exit(1)
    except OSError as err:
        print(f"OS error: {err}")
        sys.exit(1)

    return hex_records


def calculate_checksum(hex_data: str) -> int:
    """Calculate Intel HEX-style checksum for a hex string.

    Args:
        hex_data: Hex string without leading ':' or ending checksum

    Returns:
        Checksum byte (0-255)

    Example:
        >>> calculate_checksum("10010000214601360121470136007EFE09D21901")
        64
    """
    bytes_data = bytearray.fromhex(hex_data)
    return (- ((sum(bytes_data)) % 256)) % 256


def parse_hex_file(file_path: str) -> Tuple[List[int], List[int], List[HexRecord]]:
    """
    Parses the provided HEX file and extracts necessary data, including CRC and page number.

    Args:
        file_path (str): The path to the input HEX file.

    Returns:
        tuple: A tuple containing:
            - List[int]: CRC values extracted from the HEX file.
            - int: The page number extracted from the HEX file.
            - bytearray: The extracted data from the HEX file.

    Raises:
        ValueError: If the page number or CRC is not found in the HEX file.
    """
    try:
        records = read_hex_file(file_path)
    except Exception as e:
        raise ValueError(f"Error reading HEX file: {e}") from e

    crc_values = []    # 0x03 records
    page_numbers = []  # 0x04 records
    data_records = []  # 0x00 records

    for record in records:
        if record.record_type == 0x00:  # Data record
            # Create new record with bank information
            data_with_bank = bytearray(record.data)
            next_bank = ((record.address % 0x00A0) % 0x20) + (BiSSBank.BISS_USERBANK_START + 1)  # starting 6th bank
            data_with_bank.append(next_bank)

            modified_record = HexRecord(
                byte_count=record.byte_count + 1,
                address=record.address,
                record_type=record.record_type,
                data=data_with_bank
            )
            data_records.append(modified_record)
        elif record.record_type == 0x03:  # CRC record
            crc_values.append(int.from_bytes(record.data, 'big'))
        elif record.record_type == 0x04:  # Page record
            page_numbers.append(record.data[0])

    if not page_numbers:
        raise ValueError("Page number not found in HEX file")
    if not crc_values:
        raise ValueError("CRC not found in HEX file")

    return crc_values, page_numbers, data_records


def organize_data_into_pages(data_records: List[HexRecord]) -> List[List[bytes]]:
    """Organizes data records into pages according to bank configuration.

    Args:
        data_records: List of data records to organize

    Returns:
        Nested list structure where:
        - Outer list represents pages
        - Inner lists contain bank data (bytes) for each page
    """
    pages = []
    current_page = []
    current_bank_data = bytearray()

    for record in data_records:
        current_bank_data.extend(record.data)

        while len(current_bank_data) >= BiSSBank.REGISTER_PLUS_BSEL_SIZE:
            bank = current_bank_data[:BiSSBank.REGISTER_PLUS_BSEL_SIZE]
            current_bank_data = current_bank_data[BiSSBank.REGISTER_PLUS_BSEL_SIZE:]

            if len(current_page) >= BiSSBank.BANKS_PER_PAGE:
                pages.append(current_page)
                current_page = []
            current_page.append(bank)

    if current_page:
        pages.append(current_page)

    return pages


def reverse_endian(byte_list: list, word_size: int = 4) -> list:
    """
    Reverse the endianness of the given byte list based on the word size.

    Args:
        byte_list (List[int]): The list of bytes to reverse.
        word_size (int, optional): The word size in bytes (e.g., 1, 2, or 4). Defaults to 4.

    Returns:
        List[int]: A new list of bytes with the endianness reversed.
    """
    if word_size != 0:
        reversed_bytes = []
        for i in range(0, len(byte_list), word_size):
            reversed_bytes.extend(byte_list[i:i + word_size][::-1])
        return reversed_bytes
    return byte_list


def get_nonce(filename: str) -> list:
    """
    Retrieve the nonce values from a binary file.

    Args:
        filename (str): The base filename (without extension) of the nonce file.

    Returns:
        List[int]: A list of 32-bit unsigned integers representing the nonces.
    """
    nonce_filepath = f"{filename}_nonce.bin"
    with open(nonce_filepath, "rb") as f:
        file_content = f.read()
    # Iterate over the file content in chunks of 4 bytes
    return [struct.unpack(">I", file_content[i:i + 4])[0]
            for i in range(0, len(file_content), 4)]


def dif_to_biss_hex(dif_table: np.ndarray, filename: str, start_page: int = 22) -> None:
    """ TODO rewrite using HexRecord class
    Convert a difference table to a LENZ HEX file format and write it to a file.

    This function generates a HEX file from a numpy array (`DifTable`) containing
    difference data, formatting it according to Intel HEX standards. It pads the input
    data to a minimum length of 64 bytes, organizes it into 64-byte data records,
    calculates CRC values, and writes the result to the specified file.
    The resulting HEX file is ready to upload to LENZ BiSS devices.

    Args:
        DifTable (np.ndarray): A numpy array of integers representing difference data.
            Must be convertible to 8-bit signed integers (np.byte).
        filename (str): The path to the output HEX file where the data will be written.

    Returns:
        None: The function writes directly to the file and does not return a value.

    HEX File Structure:
        :02000004<page><64B blocks count>XX  (Page number and 64B blocks count)
        :<len><addr>00<data>XX  (Multiple data records)
        :04000003<CRC>XX  (CRC32 record)
        :00000001FF  (EOF marker)
    """
    PAGENUMBER_RECORD_TYPE = '04'
    DATA_RECORD_TYPE = '00'
    CRC_RECORD_TYPE = '03'
    EOF_RECORD = ":00000001FF"
    BLOCK_SIZE = 64

    if not isinstance(dif_table, np.ndarray):
        raise TypeError("Input must be numpy array")

    # logger.info('Encrypting calibration data with ciph')
    # Convert to numpy array and pad if needed
    dif_data = np.array(dif_table, dtype=np.byte)
    if len(dif_data) < BLOCK_SIZE:
        dif_data = np.append(dif_data, np.zeros(BLOCK_SIZE - len(dif_data), dtype=np.byte))
    l_dif = len(dif_data)
    logger.info('Converting %s dif to HEX (padded to %s bytes)', len(dif_table), l_dif)

    # Prepare header page record
    start_block = start_page << 5
    page_record = f'020000{PAGENUMBER_RECORD_TYPE}{start_page:02X}{((l_dif // BLOCK_SIZE) - 1):02X}'

    # Generate HEX data output
    hexdataout = [f':{page_record}{calculate_checksum(page_record):02X}']

    for block_num, i in enumerate(range(0, l_dif, BLOCK_SIZE)):
        block = dif_data[i:i + BLOCK_SIZE]
        address = start_block + block_num
        data_hex = block.tobytes().hex().upper()

        # Build record
        data_record = f"{BLOCK_SIZE:02X}{address >> 8:02X}{address & 0xFF:02X}{DATA_RECORD_TYPE}{data_hex}"
        hexdataout.append(f":{data_record}{calculate_checksum(data_record):02X}")

    # Add CRC32 record
    crc_record = f"040000{CRC_RECORD_TYPE}{binascii.crc32(dif_data):08X}"
    hexdataout.append(f":{crc_record}{calculate_checksum(crc_record):02X}")

    # Add EOF
    hexdataout.append(EOF_RECORD)

    try:
        with open(filename, "w") as output:
            for row in hexdataout:
                output.write(row.upper() + '\n')
    except IOError as e:
        raise IOError(f"Failed to write to {filename}: {e}")
    logger.info('Output hex: %s', filename)


def dec2hex(nr: int) -> str:
    """
    Converts an integer to a hexadecimal string of even length.

    Converts the given integer to its hexadecimal string representation,
    ensuring that the result has an even number of characters by prepending a '0' if necessary.

    Args:
        nr (int): The integer to convert to hexadecimal.

    Returns:
        str: The hexadecimal string representation of 'nr' with even length.

    Examples:
        >>> dec2hex(15)
        '0f'
        >>> dec2hex(255)
        'ff'
        >>> dec2hex(4095)
        '0fff'
    """
    h = format(int(nr), 'x')
    return '0' + h if len(h) % 2 else h


def dec2hex4(nr: int) -> str:
    """
    Converts an integer to a hexadecimal string of at least 4 characters, padding with zeros as necessary.

    The function ensures the resulting hexadecimal string has a minimum length of 4 characters by
    prepending zeros. If the hex string is longer than 4 characters, it may add additional zeros
    based on the length modulo operation.

    Args:
        nr (int): The integer to convert to hexadecimal.

    Returns:
        str: The hexadecimal string representation of 'nr', padded to at least 4 characters.

    Examples:
        >>> dec2hex4(15)
        '000f'
        >>> dec2hex4(255)
        '00ff'
        >>> dec2hex4(4095)
        '0fff'
        >>> dec2hex4(65535)
        'ffff'
    """
    h = format(int(nr), 'x')
    return '0' * (4 - len(h) % 5) + h


def dec2dec4(nr: int) -> str:
    """
    Converts an integer to a decimal string of at least 4 digits, padding with zeros as necessary.

    The function ensures the resulting decimal string has a minimum length of 4 digits by
    prepending zeros. If the number is greater than 9999, it prepends a '0'.

    Args:
        nr (int): The integer to convert to a decimal string.

    Returns:
        str: The decimal string representation of 'nr', padded to at least 4 digits.

    Examples:
        >>> dec2dec4(15)
        '0015'
        >>> dec2dec4(123)
        '0123'
        >>> dec2dec4(12345)
        '012345'
    """
    h = format(int(nr), '')
    if nr > 9999:
        return '0' + h
    return '0' * (4 - len(h) % 5) + h


def bytes_to_hex_str(byte_array: bytes) -> str:
    """
    Converts a bytes object to a hexadecimal string representation.

    Each byte in the input bytes object is converted to its two-digit uppercase hexadecimal equivalent.
    The resulting string is a concatenation of these hexadecimal values.

    Args:
        byte_array (bytes): The bytes object to convert.

    Returns:
        str: A string containing the hexadecimal representation of the input bytes.

    Example:
        >>> data = b'\\x01\\x02\\x0A\\xFF'
        >>> hex_str = bytes_to_hex_str(data)
        >>> print(hex_str)
        '01020AFF'
    """
    return ''.join(f'{byte:02X}' for byte in byte_array)


def generate_hex_line(address: int, command: int, data: list) -> str:
    """
    Generate a formatted hex line for communication with a device.

    Args:
        address (int): The 16-bit address field.
        command (int): The command byte.
        data (List[int]): A list of data bytes to include in the hex line.

    Returns:
        str: The formatted hex line string, including the starting ':' and checksum.
    """
    size = len(data)
    size_hex = f"{size:02X}"
    address_hex = f"{address:04X}"
    command_hex = f"{command:02X}"
    data_hex = bytes_to_hex_str(data)
    hex_line = f":{size_hex}{address_hex}{command_hex}{data_hex}"
    crc = calculate_checksum(hex_line[1:])  # Exclude the starting ":"
    crc_hex = f"{crc:02X}"
    hex_line_with_crc = hex_line + crc_hex
    return hex_line_with_crc


def generate_byte_line(address: int, command: int, data: list) -> bytes:
    """
    Generate a byte array for sending commands to a device.

    Args:
        address (int): The starting address for the command.
        command (int): The command code.
        data (List[int]): A list of data bytes to include in the command.

    Returns:
        bytes: A byte array representing the command, ready to be sent over a serial port.
    """
    size = len(data)
    size_hex = f"{size:02X}"
    address_hex = f"{address:04X}"
    command_hex = f"{command:02X}"
    # logger.debug(f"Using {data} to generate hex line")
    data_hex = bytes_to_hex_str(data)
    hex_line = f":{size_hex}{address_hex}{command_hex}{data_hex}"
    crc = calculate_checksum(hex_line[1:])  # Exclude the starting ":"
    crc_hex = f"{crc:02X}"
    hex_line_with_crc = hex_line + crc_hex
    # logger.debug(f"Hex line with crc - {hex_line_with_crc}")
    return bytes.fromhex(hex_line_with_crc[1:])


def _pad_and_recalculate_checksum(row_data: str) -> str:
    """
    Pads an Intel HEX data row to 16 bytes and recalculates its checksum.

    Args:
        row_data (str): An Intel HEX data row string without ':'.

    Returns:
        str: The modified data row, padded to 16 bytes with an updated checksum.

    """
    data_length = int(row_data[:2], 16)     # :10... - length
    if data_length < 16:
        padding_needed = 16 - data_length   # Calculate padding
        address = row_data[2:6]
        data_field = row_data[8:-2] + FILL_BYTE * padding_needed
        checksum = 0x10 + int(address[:2], 16) + int(address[2:], 16) + sum(bytearray.fromhex(data_field))
        checksum = (-checksum) & 0xFF
        row_data = f"10{address}00{data_field}{checksum:02X}"
    return row_data


def _create_dummy_data_row(address: str, fill: str = FILL_BYTE) -> str:
    """
    Creates a dummy Intel HEX data row filled with a specified byte.

    The address is incremented by 16 bytes to create the next sequential address.

    Args:
        address (str): The starting address for the row, as a 4-character hex string.
        fill (str, optional): The fill byte in hex format (default is 'FF').

    Returns:
        Complete Intel HEX record string (without ':') with:
        - Length: 16 bytes (0x10)
        - Type: 00 (data)
        - Data: 16 bytes of fill value
        - Valid checksum
    """
    address = int(address, 16) + 16  # Increment address
    dummy_data_row = f"10{address:04X}00{fill * 16}"
    checksum = 0x10 + (address >> 8) + (address & 0xFF)
    checksum = (-checksum) & 0xFF
    return dummy_data_row + f"{checksum:02X}"


def _prep_data_rows(df: List[str], section_id: int, base_offset: int,
                    prep_bytes: List[bytes]) -> List[str]:
    """
    Prepares data rows for HEX file processing with encryption.

    Args:
        df: List of HEX file rows
        section_id: Section identifier for the data block
        base_offset: Base address offset for the section
        prep_bytes: List of bytes for XOR processing

    Returns:
        List of processed HEX records ready for output
    """
    hexdataout = []
    temp_data = []
    flashend = False
    row = 2
    len_df = len(df)
    start_adr = int(df[row-1][2:6], 16)
    block_num = (int(df[row-1][2:6], 16) - start_adr) // 64

    # Create header record
    data = [2, 0, 0, 4, section_id, 63]
    data.append((-sum(data)) % 256)
    temp_hex = [dec2hex(x) for x in data]
    hexdataout.append(":" + "".join(temp_hex))

    # Process data blocks
    while not flashend:
        if row + 5 < len_df:
            temp_hexr = []
            if all(int(df[row+i][6:8]) == 0 for i in range(-1, 3)):
                for i in range(-1, 3):
                    temp_hexr.append(df[row+i][8:-2])
                temp_hexr = "".join(temp_hexr)
                temp_data.append(temp_hexr)
                block_num = (int(df[row-1][2:6], 16) - start_adr) // 64
                temp_hexrb = bytes.fromhex(temp_hexr)
                temp_proc = bytes(a ^ b for a, b in zip(temp_hexrb, prep_bytes[block_num]))
                temp_hexc = f"40{dec2hex4(block_num + base_offset)}00{temp_proc.hex()}"
                crc = sum(int(temp_hexc[i:i+2], 16) for i in range(0, len(temp_hexc), 2))
                temp_hexc += dec2hex((-crc) & 0xFF)
                hexdataout.append(":" + temp_hexc)
                row += 4
        else:
            flashend = True
        if block_num == 255:
            flashend = True

    # Process remaining data
    temp_hex = []
    if block_num < 255:
        for i in range(-1, 4):
            if int(df[row+i][6:8]) == 0:
                temp_hex.append(df[row+i][8:-2])
            else:
                temp_hex = "".join(temp_hex)

                temp_data.append(temp_hex)
                block_num = (int(df[row-1][2:6], 16) - start_adr) // 64
                temp_hexrb = bytes.fromhex(temp_hex)
                temp_proc = bytes(a ^ b for a, b in zip(temp_hexrb, prep_bytes[block_num]))
                temp_hexc = f"40{dec2hex4(block_num + base_offset)}00{temp_proc.hex()}"
                crc = sum(int(temp_hexc[i:i+2], 16) for i in range(0, len(temp_hexc), 2))
                temp_hexc += dec2hex((-crc) & 0xFF)
                hexdataout.append(":" + temp_hexc)
                break

    # Add CRC32 footer
    temp_data = "".join(temp_data)
    temp_hex = '04000003' + dec2hex(binascii.crc32(binascii.a2b_hex(temp_data)))
    crc = int(temp_hex[0:2], 16)
    for i in range(2, len(temp_hex), 2):
        crc = crc + int(temp_hex[i:i+2], 16)
    temp_hex = temp_hex + dec2hex((-crc) % 256)
    hexdataout.append(":" + temp_hex)

    # Update header with final block count
    data = [2, 0, 0, 4, section_id, (int(hexdataout[-2][5:7], 16) - int(hexdataout[1][5:7], 16)) % 256]
    data.append((-sum(data)) % 256)
    hexdataout[0] = ":" + "".join(dec2hex(x) for x in data)
    return hexdataout


def _readhex(filepath: str) -> list[str]:
    """TODO get rid of this function, replace with read_hex_file()
    Reads an Intel HEX file and returns a list of hex record strings.

    Opens the specified HEX file, reads its contents, and extracts the hex record strings
    (excluding the initial colon ':' in each line). Each line is expected to be an Intel HEX
    record starting with ':'.

    Args:
        filepath (str): The path to the HEX file.

    Returns:
        List[str]: A list of hex record strings from the file.

    Raises:
        SystemExit: If the file does not exist or cannot be opened.

    Example:
        >>> records = readhex('difftable.hex')
        >>> print(records[0])
        '-73'
    """
    try:
        if not path.exists(filepath):
            print("File not found!")
            sys.exit(1)
    except OSError as err:
        print(f'OS error! {err}')
        sys.exit(1)
    with open(filepath, mode='r',  encoding='utf-8') as file:
        filereader = reader(file, delimiter=':')
        dataframe = [row[1] for row in filereader if len(row) > 1]
    return dataframe


def prep_hex(filepath: str) -> None:
    """
    Main function to prepare HEX file for firmware update.

    Args:
        filepath: Path to input HEX file

    Returns:
        None (writes output to <filename>_op.hex)

    Raises:
        FileNotFoundError: If input file doesn't exist
        IOError: If there are file access issues
    """
    try:
        inputhexfile = _readhex(filepath)
    except FileNotFoundError:
        sys.stderr.write(f"Error: File '{filepath}' not found.\n")
        sys.exit(1)
    except IOError as e:
        sys.stderr.write(f"IO error: {e}\n")
        sys.exit(1)

    print("Input hexfile:", filepath)
    filename, _ = path.splitext(filepath)
    # TODO move hashes to the function args
    hashes = [(24, 6144, 'actis')]
    hash_bytes = []
    for section_id, count, desc in hashes:
        base_offset = section_id << 5
        with open(f'lenz_hash_{desc}.bin', "rb") as f:
            for _ in range(base_offset, base_offset + ((count >> 6) or 1)):
                hash_bytes.append(f.read(64))
    hexdata = []
    fullhexdataout = []
    hexdata_parts = (len(inputhexfile) - 4) // 128 + 1
    rawhexdata = []

    for i in range(hexdata_parts):
        hexdatarow = []
        hexdatarow.append(inputhexfile[0])
        for j in range(i * 128, (i + 1) * 128):
            if j + 4 > len(inputhexfile):
                break
            row_data = inputhexfile[j + 1]
            hexdatarow.append(_pad_and_recalculate_checksum(row_data))
            rawhexdata.append(row_data[8:-2])
        if i == hexdata_parts - 1:
            while len(hexdatarow) < 129:
                hexdatarow.append(_create_dummy_data_row(hexdatarow[-1][2:6]))

        hexdatarow.append(inputhexfile[len(inputhexfile)-2])
        hexdatarow.append(inputhexfile[len(inputhexfile)-1])
        hexdata.append(hexdatarow)

    for part in range(hexdata_parts):
        df = hexdata[part]
        section_id = int(df[0][10:12], 16) << 5 | int(df[1][2:6], 16) >> 11
        base_offset = section_id << 5
        hexdataout = _prep_data_rows(df, section_id, base_offset, hash_bytes[part << 5:])
        fullhexdataout.append(hexdataout)

    fullhexdataout[-1].append(":00000001FF")

    output_filepath = f"{filename}_op.hex"
    try:
        with open(output_filepath, "w") as output:
            print("Output:", output_filepath)
            for hexdataout in fullhexdataout:
                for cell in hexdataout:
                    output.write(cell.upper() + '\n')
        # print("\n")
    except Exception as e:
        sys.stderr.write(f"Error writing output file: {e}\n")
        sys.exit(1)
