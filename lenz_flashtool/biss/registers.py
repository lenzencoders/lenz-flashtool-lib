r'''
 _     _____ _   _ _____   _____ _   _  ____ ___  ____  _____ ____  ____
| |   | ____| \ | |__  /  | ____| \ | |/ ___/ _ \|  _ \| ____|  _ \/ ___|
| |   |  _| |  \| | / /   |  _| |  \| | |  | | | | | | |  _| | |_) \___ \
| |___| |___| |\  |/ /_   | |___| |\  | |__| |_| | |_| | |___|  _ < ___) |
|_____|_____|_| \_/____|  |_____|_| \_|\____\___/|____/|_____|_| \_|____/


BiSS Encoder Register Definitions Module

This module defines the register mappings and banking system for BiSS C encoder devices used
with the LENZ FlashTool. It provides an enumeration (`BiSSBank`) of register indices and constants
for accessing programmable and fixed-address registers, as well as managing the paged banking system for extended configuration.

Register Organization:
- Programmable Registers (Indices 0-63): Used for device configuration, including nonce, CRC, serial number,
  production date, and security keys.
- Fixed-Address Registers (Indices 64-127): Contain device information (e.g., serial number, device ID)
  and runtime data (e.g., encoder data, status flags).

Banking System:
- Supports a paged banking system with a service bank (index 2) and user banks (indices 5-37).
- Each bank contains 64 bytes of data, with a bank select register (`BSEL_REG_INDEX`) to switch banks.
- Fixed-address registers (64-127) are accessible regardless of the selected bank.

Usage Notes:
- Registers are 32-bit unless otherwise specified and stored in big-endian format (highest-value byte at the lowest address).
- Some registers (e.g., configuration registers) require unlock sequences before writing.
- The `BiSSBank` enum provides indices for accessing registers and constants for bank management.

Key Constants:
- Programmable Registers: Nonce, CRC32, serial number, production date, device ID, and key registers.
- Fixed-Address Registers: Command, encoder data, harmonic measurements, status flags, version information,
  and device/manufacturer IDs.
- Banking: Service bank, user banks, and bank/page sizes for firmware updates and data transfers.

Author:
    LENZ ENCODERS, 2020-2025
'''
from enum import IntEnum


class BiSSBank(IntEnum):
    """
    Enumeration of BiSS C encoder register indices and banking constants.

    Defines indices for programmable registers (0-63), fixed-address registers (64-127),
    and constants for the banking system. Each constant represents either a register index
    or a size/bank definition used for device configuration, operation, and data access.
    """

    NONCE_REG_INDEX = 0
    """int: Index for the nonce register while programming."""

    CRC32_REG_INDEX = 12
    """int: Index for the CRC32 register for data integrity checks while programming."""

    SERIALNUM_REG_INDEX = 16
    """int: Index for the serial number programming register."""

    PRODDATE_REG_INDEX = 20
    """int: Index for the production date programming register."""

    CRC_ARRAY_REG_INDEX = 24
    """int: CRC array programming register index."""

    PAGENUM_REG_INDEX = 24
    """int: Page number programming register index."""

    SERIALNUM_CRC_REG_INDEX = 25  # Serial number CRC programming register index
    """int: Serial number CRC programming register index."""

    KEY_CRC_REG_INDEX = 26  # Key CRC programming register index
    """int: Key CRC programming register index."""

    DEVID_CRC_REG_INDEX = 27  # Device ID CRC programming register index
    """int: Device ID CRC programming register index."""

    KEY_REG_INDEX = 28  # Key programming register index
    """int: Key programming register index."""

    DEVID_L_REG_INDEX = 54  # Lower part of device ID programming register index
    """int: Lower part of device ID programming register index."""

    DEVID_H_REG_INDEX = 58  # Higher part of device ID programming register index
    """int: Higher part of device ID programming register index."""

    # ==== Fixed addresses registers indexes

    FIXED_ADDRESSES_START_INDEX = 64
    """int: Start index of fixed address registers."""

    BSEL_REG_INDEX = 64  # Bank select register index
    """int: Bank select register index."""

    DEV_SN_REG_INDEX = 68  # Device serial number index
    """int: Device serial number index."""

    DEV_SN_SIZE = 4  # Device serial number size in bytes
    """int: Device serial number size in bytes."""

    # ==== Free Registers start:
    CMD_REG_INDEX = 72  # Command register index - 2 bytes
    """int: Command register index - 2 bytes."""

    ENC_DATA_REG_INDEX = 74  # Encoder data: Calibration state, temperature, Vcc, Signal Mod,
    """int: Encoder data register index (calibration state, temperature, Vcc, Signal Mod)."""

    FIRSTHARMAMP_REG_INDEX = 80  # First harmonic amplitude register index
    """int: First harmonic amplitude register index."""

    FIRSTHARMANGLE_REG_INDEX = 82  # First harmonic angle register index
    """int: First harmonic angle register index."""

    REV_RES_REG_INDEX = 84  # 0x54  # rev and resolution
    """int: Revolution and resolution register index."""

    SHIFT_REG_INDEX = 85  # 0x55  # 3 bytes 0x55 0x56 0x57 # shift (0x80 to 0x55 for 180°)
    """int: Shift register index (3 bytes for 180° shift)."""

    CMD_STATE_FLAG_REG_INDEX = 97  # Command state flag register index
    """int: Command state flag register index."""

    STATE_FLAG_REG_INDEX = 98  # State flag register index
    """int: State flag register index."""

    BOOTLOADER_VER_REG_INDEX = 108
    """int: Bootloader version register index."""

    BOOTLOADER_VER_SIZE = 4
    """int: Bootloader version size in bytes."""

    PROGVER_REG_INDEX = 112  # Program version register index
    """int: Program version register index."""

    PROGVER_REG_SIZE = 4
    """int: Program version size in bytes."""

    MFG_REG_INDEX = 116
    """int: Manufacturing date register index."""

    MFG_REG_SIZE = 4
    """int: Manufacturer date register size in bytes."""

    # ==== Free Registers end.

    DEV_ID_H_REG_INDEX = 120  # Device ID
    """int: Device ID (high part) register index."""

    DEV_ID_H_SIZE = 4
    """int: Device ID (high part) size in bytes."""

    DEV_ID_L_REG_INDEX = 124
    """int: Device ID (low part) register index."""

    DEV_ID_L_SIZE = 2
    """int: Device ID (low part) size in bytes."""

    MFR_ID_REG_INDEX = 126  # Manufacturer ID
    """int: Manufacturer ID register index."""

    MFG_ID_SIZE = 2
    """int: Manufacturer ID size in bytes."""

    # BiSS banking definitions
    BISS_BANK_SERV = 2  # Service bank index
    """int: Service bank index."""

    BISS_USERBANK_START = 5  # Start index of user banks
    """int: Start index of user banks."""

    BISS_USERBANK_END = 37  # End index of user banks
    """int: End index of user banks."""

    BANKS_PER_PAGE = 32  # Number of banks per page
    """int: Number of banks per page."""

    REGISTER_PLUS_BSEL_SIZE = 65  # Size of each bank in bytes (64) plus BSEL reg size (1) (data + bank number)
    """int: Size of each bank in bytes (64) plus BSEL reg size (1) (data + bank number)."""

    REGISTER_PLUS_FIXED_BANK_SIZE = 128  # Register bank (64) and Fixed Addresses (64) size
    """int: Register bank (64) and Fixed Addresses (64) size."""

    FIXED_BANK_SIZE = 64
    """int: Fixed bank size in bytes."""
