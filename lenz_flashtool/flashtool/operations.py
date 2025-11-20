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
from .hex_utils import organize_data_into_pages, get_nonce, parse_hex_file, dif_to_biss_hex, generate_hex_line, read_hex_file_irs
from ..biss.registers import BiSSBank
from .uart import UartCmd

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
    sleep(0.5)

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
    ft.biss_read_flags()
    sleep(0.2)
    logger.info('Sending \'run\' command...')
    ft.biss_write_command("run")
    sleep(0.4)
    ft.biss_read_flags()
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


def send_hex_irs_enc(filename: str) -> bool:
    """
    Download and flash a hex file to the IRS encoder with verification.

    This function handles the complete firmware update process for the IRS encoder,
    including bootloader entry, hex file transmission, CRC verification, and
    returning to normal operation mode. The process includes retry logic for
    robust operation.

    Process Flow:
    1. Establish connection with encoder in bootloader mode
    2. Read and parse the hex file
    3. Transmit data pages with appropriate command handling
    4. Verify each page using CRC checks
    5. Exit bootloader and return to firmware mode
    6. Implement 3-attempt retry logic for fault tolerance

    Args:
        filename (str): Path to the hex file to be uploaded to the encoder.
                       The file should be in Intel HEX format.

    Returns:
        bool: True if the entire upload process completes successfully,
              False if any critical step fails.

    Example:
        >>> success = send_hex_irs_enc("firmware_v1.2.hex")
        >>> if success:
        ...     print("Firmware update completed successfully")
        ... else:
        ...     print("Firmware update failed")
    """
    ft = FlashTool()
    connected = ft.enter_bl_irs()
    if not connected:
        logger.error("Failed to connect to IRS encoder!")
        ft.close()
        return False

    try:
        df = read_hex_file_irs(filename)
        flashend = False
        row = 0
        logger.info(f'Uploading {filename} to the encoder.')
        Page = 1

        try:
            for attempt in range(3):
                while not flashend:
                    tx_row = bytes.fromhex(df[row])
                    row += 1

                    if (tx_row[3] == 4) | (tx_row[3] == 0):
                        tx_data = bytes.fromhex(generate_hex_line(
                            address=0x0000,
                            command=UartCmd.HEX_IRS_ENC_WRITE_READ_CMD,
                            data=list(tx_row),
                        )[1:])
                        ft._write_to_port(tx_data)
                        sleep(0.1)

                    elif (tx_row[3] == 3):
                        tx_data = bytes.fromhex(generate_hex_line(
                            address=0x0000,
                            command=UartCmd.HEX_IRS_ENC_WRITE_READ_CMD,
                            data=list(tx_row),
                        )[1:])
                        ft._write_to_port(tx_data)
                        sleep(0.1)

                        enc_upl_answ = ft.port_read(len(tx_data) - 1)
                        enc_upl_answ_hex = enc_upl_answ.tobytes().hex().upper()
                        logger.debug(f"Enc upl answer: {enc_upl_answ_hex}")

                        CRC_hex = df[row - 1][8:16].upper()
                        CRC_enc_raw = enc_upl_answ_hex[8:16]
                        CRC_enc = "".join([CRC_enc_raw[i:i+2] for i in range(6, -1, -2)])
                        logger.debug(f"HEX CRC: {CRC_hex}, Encoder data CRC: {CRC_enc}")

                        if CRC_enc == CRC_hex:
                            logger.info(f"Page {Page}: Verify OK!")
                        else:
                            logger.error(f"Page {Page}: Verify FAILED! HEX file CRC: {CRC_hex}. Encoder CRC: {CRC_enc}")
                            raise ValueError("Uploading file error!")

                        Page += 1

                    elif (tx_row[3] == 1):
                        flashend = True
        except Exception as e:
            logger.info(f"Attempt {attempt + 1} failed: "
                        f"{str(e)}")
            if attempt == 2:
                raise
            sleep(0.1)

        if not ft.enter_fw_irs():
            logger.error("Failed to exit bootloader mode!")
            ft.close()
            return False

        logger.info("Hex file uploaded successfully!")
        ft.close()
        return True

    except Exception as e:
        logger.error(f"An exception occurred while uploading hex file: {e}")
        ft.close()
        return False
