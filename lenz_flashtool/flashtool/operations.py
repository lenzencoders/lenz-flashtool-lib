r'''
 _     _____ _   _ _____   _____ _   _  ____ ___  ____  _____ ____  ____
| |   | ____| \ | |__  /  | ____| \ | |/ ___/ _ \|  _ \| ____|  _ \/ ___|
| |   |  _| |  \| | / /   |  _| |  \| | |  | | | | | | |  _| | |_) \___ \
| |___| |___| |\  |/ /_   | |___| |\  | |__| |_| | |_| | |___|  _ < ___) |
|_____|_____|_| \_/____|  |_____|_| \_|\____\___/|____/|_____|_| \_|____/


BiSS Flash Programming Module

This module provides functionality for programming BiSS encoder devices with firmware (HEX)
and differential lookup tables (DIF) via a flash programming interface.

Key Features:
- HEX file transmission to BiSS devices
- DIF table conversion and transmission
- Secure programming with validation
- Progress tracking support
- Error handling and status flag checking

Functions:
    send_hex(file_path: str, nonce: Optional[int] = None, pbar: Optional[Any] = None) -> None
        Transmits a HEX firmware file to a BiSS device with optional security nonce and progress tracking.

    send_dif(file_path: str, pbar: Optional[Any] = None) -> None
        Converts and transmits a DIF table CSV file to a BiSS device with progress tracking.

Dependencies:
- os: File path operations
- logging: Event logging
- time: Delay operations
- numpy: CSV data processing (for DIF tables)
- typing: Type hints
- .core.FlashTool: Core flash programming interface
- .hex_utils: HEX file parsing and conversion utilities
- ..biss.registers: BiSS register definitions

Usage Example:
    >>> from biss_flash import send_hex, send_dif
    >>> # Program firmware
    >>> send_hex("firmware_v1.2.hex")
    >>> # Program DIF table
    >>> send_dif("calibration_table.csv")

Security Notes:
- Uses nonce for secure programming sessions
- Verifies CRCs for data integrity
- Checks device flags after programming

Author:
    LENZ ENCODERS, 2020-2025
'''
from os import path
import logging
from time import sleep
from typing import Optional, Any
import numpy as np
from .core import FlashTool
from .hex_utils import organize_data_into_pages, get_nonce, parse_hex_file, dif_to_biss_hex
from ..biss.registers import BiSSBank

logger = logging.getLogger(__name__)

START_PAGE = 1
END_PAGE = 60


def biss_send_hex(file_path: str, nonce: Optional[int] = None, pbar: Optional[Any] = None) -> None:
    """Main function for transmitting HEX files to BiSS device.

    Args:
        file_path: Path to input HEX file
        nonce: Optional security nonce value
        pbar: Optional progress bar object
    """
    ft = FlashTool()
    filename, _ = path.splitext(file_path)
    logger.info("Input enchexfile: %s", file_path)
    ft.biss_write_command("reboot2bl")
    sleep(0.2)

    crc_values, page_numbers, data_records = parse_hex_file(file_path)
    pages = organize_data_into_pages(data_records)

    if not nonce:
        nonce = get_nonce(filename)
    logger.info("Nonce: %s", nonce)

    ft.biss_set_bank(BiSSBank.BISS_BANK_SERV)
    ft.biss_set_bank(BiSSBank.BISS_BANK_SERV)

    ft.biss_write_word(BiSSBank.NONCE_REG_INDEX, nonce)
    ft.biss_write_word(BiSSBank.CRC32_REG_INDEX, crc_values[0])
    ft.biss_write_word(BiSSBank.PAGENUM_REG_INDEX, page_numbers[0])
    # print(page_numbers[0])
    # ft.biss_read_registers(BISS_BANK_SERV)
    # print('=====')
    ft.send_data_to_device(pages, crc_values, page_numbers, START_PAGE, END_PAGE, pbar)
    ft.read_flags()
    sleep(0.2)
    logger.info('Sending \'run\' command...')
    ft.biss_write_command("run")
    sleep(0.4)
    ft.read_flags()
    ft.close()


def biss_send_dif(file_path: str, pbar: Optional[Any] = None) -> None:
    """Main function for transmitting DIF tables to BiSS device.

    Args:
        file_path: Path to input DIF CSV file
        pbar: Optional progress bar object
    """

    ft = FlashTool()
    # fullcal_data = pd.read_csv(file_path)  # lib_FullCal_diftable.csv

    fullcal_data = np.loadtxt(file_path, delimiter=',', dtype=np.int8, skiprows=1)
    logger.info("Input dif: %s", file_path)

    diftable_hex_filename = f'{path.splitext(path.basename(file_path))[0]}.hex'
    dif_to_biss_hex(fullcal_data, diftable_hex_filename)

    ft.biss_write_command("reboot2bl")
    sleep(0.3)

    crc_values, page_numbers, data_records = parse_hex_file(diftable_hex_filename)
    pages = organize_data_into_pages(data_records)

    ft.biss_set_bank(BiSSBank.BISS_BANK_SERV)
    ft.biss_set_bank(BiSSBank.BISS_BANK_SERV)

    ft.biss_write_word(BiSSBank.CRC32_REG_INDEX, crc_values[0])
    ft.biss_write_word(BiSSBank.PAGENUM_REG_INDEX, page_numbers[0])

    ft.send_data_to_device(pages, crc_values, page_numbers, START_PAGE, END_PAGE, pbar=pbar, difmode=True)

    sleep(0.5)
    ft.close()
