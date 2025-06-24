"""

FlashTool library for BiSS C Firmware Update and Calibration.

This library provides functions for interfacing with BiSS C encoders using LENZ FlashTool, performing firmware updates,
and executing calibration routines.

Author:
    LENZ ENCODERS, 2020-2025
"""

#
# r'''
#  _     _____ _   _ _____   _____ _   _  ____ ___  ____  _____ ____  ____
# | |   | ____| \ | |__  /  | ____| \ | |/ ___/ _ \|  _ \| ____|  _ \/ ___|
# | |   |  _| |  \| | / /   |  _| |  \| | |  | | | | | | |  _| | |_) \___ \
# | |___| |___| |\  |/ /_   | |___| |\  | |__| |_| | |_| | |___|  _ < ___) |
# |_____|_____|_| \_/____|  |_____|_| \_|\____\___/|____/|_____|_| \_|____/
# '''

from .utils import plot, plot2, TermColors
from .biss import (
    ERROR_FLAGS, BISS_COMMANDSTATE, biss_commands, BiSSBank
    )
from .flashtool import (
    UartCmd,
    FlashTool,
    FlashToolError,
    generate_hex_line,
    init_logging,
    get_nonce,
    _readhex,
    biss_send_hex,
    biss_send_dif,
    calculate_checksum,
    dif2hex,
    prep_hex
)
from .testing import MockFlashTool
from .encproc import LenzEncoderProcessor

__all__ = [
    # Constants
    'ERROR_FLAGS',
    'BISS_COMMANDSTATE',
    'biss_commands',
    'BiSSBank',

    # Command constants
    'UartCmd',

    # Core classes
    'FlashTool',
    'FlashToolError',
    'MockFlashTool',
    'LenzEncoderProcessor',

    # Utility functions and classes
    'generate_hex_line',
    'init_logging',
    'get_nonce',
    'calculate_checksum',
    '_readhex',
    'biss_send_dif',
    'biss_send_hex',
    'plot',
    'plot2',
    'TermColors',
    'dif2hex',
    'prep_hex'
]

__version__ = "0.1.2"
__author__ = "LENZ ENCODERS"
