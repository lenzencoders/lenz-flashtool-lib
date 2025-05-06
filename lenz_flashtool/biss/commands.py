r'''
 _     _____ _   _ _____   _____ _   _  ____ ___  ____  _____ ____  ____
| |   | ____| \ | |__  /  | ____| \ | |/ ___/ _ \|  _ \| ____|  _ \/ ___|
| |   |  _| |  \| | / /   |  _| |  \| | |  | | | | | | |  _| | |_) \___ \
| |___| |___| |\  |/ /_   | |___| |\  | |__| |_| | |_| | |___|  _ < ___) |
|_____|_____|_| \_/____|  |_____|_| \_|\____\___/|____/|_____|_| \_|____/


BiSS Encoder Commands Interface Module

This module provides constants and functions for interacting with BiSS encoder devices,
specifically focused on command interpretation and error flag decoding.

Key Components:
- ERROR_FLAGS: Dictionary mapping bit positions to error flag descriptions
- BISS_COMMANDSTATE: Dictionary mapping state integers to command state descriptions
- biss_commands: Dictionary of supported BiSS commands with opcodes and descriptions

Functions:
- interpret_biss_commandstate(): Decodes integer state values into human-readable strings
- interpret_error_flags(): Converts bitmask error values into list of active error flags

Usage Examples:
    >>> interpret_biss_commandstate(5)
    ['BISS_COMMANDSTATE_OTP_SERDATE_CRC_OK']

    >>> interpret_error_flags(0x105)  # Bits 0 and 8 set
    ['FLAGS_FW_CRC32_CHECK_FAIL', 'FLAGS_KEY_NULL']

Error Flag Notes:
- Error flags use bitmask representation where each bit corresponds to a specific error
- Multiple flags can be active simultaneously
- Flag descriptions indicate various hardware and firmware conditions

Command State Notes:
- Represents the current operational state of the BiSS encoder
- Includes states for firmware updates, CRC checks, and device initialization

Command Reference:
- The biss_commands dictionary provides complete command documentation including:
  - Hexadecimal opcodes
  - Detailed functional descriptions
  - Permanent vs temporary operation indicators
  - Configuration vs operational commands

Security Considerations:
- Several commands perform permanent OTP (One-Time Programmable) operations
- Flash memory operations require explicit unlock sequences
- Device contains secure elements for key storage and validation

Author:
    LENZ ENCODERS, 2020-2025
'''
ERROR_FLAGS = {
    0: "FLAGS_FW_CRC32_CHECK_FAIL",
    1: "FLAGS_FLASH_FW_ERROR",
    2: "FLAGS_STARTUP_ERROR",
    3: "FLAGS_BL_CRC32_CHECK_FAIL",
    4: "FLAGS_STAY_IN_BL",
    5: "FLAGS_OTP_SERIAL_DATE_ERROR",
    6: "FLAGS_OTP_DEVID_ERROR",
    7: "FLAGS_DEVID_NULL",
    8: "FLAGS_FLASH_KEY_ERROR",
    9: "FLAGS_KEY_NULL",
    10: "FLAGS_RDP_AA",
    11: "FLAGS_BISS_ERR",
    12: "FLAGS_BISS_WARN",
}

BISS_COMMANDSTATE = {
    0: "BISS_COMMANDSTATE_IDLE",
    2: "BISS_COMMANDSTATE_FLASH_FW_CRC_OK",
    3: "BISS_COMMANDSTATE_FLASH_FW_CRC_FAULT",
    4: "BISS_COMMANDSTATE_FW_CHECK_CRC32_FAULT",
    5: "BISS_COMMANDSTATE_OTP_SERDATE_CRC_OK",
    6: "BISS_COMMANDSTATE_OTP_SERDATE_CRC_FAULT",
    7: "BISS_COMMANDSTATE_FLASH_KEY_CRC_OK",
    8: "BISS_COMMANDSTATE_FLASH_KEY_CRC_FAULT",
    9: "BISS_COMMANDSTATE_FLASH_KEY_NULL",
    10: "BISS_COMMANDSTATE_OTP_DEVID_CRC_OK",
    11: "BISS_COMMANDSTATE_OTP_DEVID_CRC_FAULT",
    12: "BISS_COMMANDSTATE_FLASH_FW_NULL",
    240: "BISS_COMMANDSTATE_BSY_START",
    255: "BISS_COMMANDSTATE_FLASH_BSY"
}

biss_commands = {
    'non': (0x0000, "No operation command. Device remains in current state with no action taken."),
    'load2k': (0x0107, "Load 2 KB of data from registers into device memory. Used for firmware updates."),
    'staybl': (0x020E, "Force device to stay in bootloader mode. Prevents automatic transition to application mode "
               "for extended maintenance operations."),
    'run': (0x0309, "Exit bootloader mode and execute the main application program. Initiates normal encoder operation."),
    'zeroing': (0x041C, "Perform encoder zeroing procedure. Resets position counter to zero at current mechanical position."),
    'set_dir_cw': (0x051B, "Configure encoder direction sensing for clockwise rotation. "
                   "Position values will increase when rotating clockwise."),
    'set_dir_ccw': (0x0612, "Configure encoder direction sensing for counterclockwise rotation. Position values will increase "
                    "when rotating counterclockwise."),
    'saveflash': (0x0838, "Commit current configuration parameters to flash memory. All settings will persist after "
                  "power cycle."),
    'ampcalibrate': (0x0A36, "Initiate amplitude calibration routine. Automatically adjusts signal amplitudes."),
    'cleardiflut': (0x0B31, "Clear differential lookup table (DifLUT). Resets all offset compensation values to default state."),
    'setfastbiss': (0x0C24, "Enable high-speed BiSS communication mode. Increases data transmission rate at the cost of "
                            "potential reduced noise immunity."),
    'setdefbiss': (0x0D23, "Revert to standard BiSS communication mode. Provides robust communication with standard "
                           "timing parameters."),
    'reboot': (0x0F2D, "Perform device reboot."),
    'reboot2bl': (0x1070, "Reboot device directly into bootloader mode. Enables firmware update and configuration procedures "
                  "without external hardware intervention"),
    'loadseriald': (0x1177, "Write serial number and manufacturing date to OTP memory. This operation is permanent and "
                    "cannot be reversed."),
    'loaddevid': (0x146C, "Program DevID into OTP memory. This operation is permanent and cannot be reversed."),
    'loadkey': (0x1379, "Store key in secure flash memory. Used for secure communication and firmware validation."),
    'savediftable': (0x156B, "Save differential compensation table to memory. Preserves signal integrity calibration across "
                     "power cycles."),
    'unlockflash': (0x1662, "Enable write access to protected flash memory regions. Required before performing configuration "
                    "changes."),
    'unlocksetup': (0x1D53, 'Disable configuration write protection. Allows modification of sensitive device parameters.'),
    'enarccal': (0x1E5A, 'Enable arc-based calibration mode. Prepares device for angular position calibration procedures.'),
    'clearcalflash': (0x1F5D, 'Erase all high-speed oscillator (HSI) and differential calibration data from flash.'),
}


def interpret_biss_commandstate(state_int: int) -> list:
    """
    Interpret a given integer as a BiSS command state.

    Args:
        state_int (int): An integer representing the current command state.

    Returns:
        List[str]: A list containing the description of the current command state.
                   If the state is not recognized, returns ["Unknown state"].
    """
    state_description = BISS_COMMANDSTATE.get(state_int, "Unknown state")
    return [state_description]


def interpret_error_flags(error_int: int) -> list:
    """
    Interpret a given integer as a set of error flags.

    Args:
        error_int (int): An integer where each bit represents a different error flag.

    Returns:
        List[str]: A list of active error flags based on the set bits in the input integer.
                   If no flags are set, returns ["No error flags set"].
    """
    error_int = int(error_int)
    active_flags = [
        flag_name for bit_pos, flag_name in ERROR_FLAGS.items()
        if error_int & (1 << bit_pos)
    ]
    return active_flags or ["No error flags set"]
