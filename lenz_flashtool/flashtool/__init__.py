"""

LENZ BiSS Protocol Implementation

Provides BiSS encoder protocol standarts and utilities.

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

from .uart import UartCmd
from .core import FlashTool
from .logging import init_logging
from .hex_utils import get_nonce, generate_hex_line, calculate_checksum, _readhex
from .errors import FlashToolError
from .operations import biss_send_dif, biss_send_hex
__all__ = [
    'UartCmd',
    'FlashTool',
    'init_logging',
    'generate_hex_line',
    'calculate_checksum',
    'get_nonce',
    'FlashToolError',
    '_readhex',
    'biss_send_dif',
    'biss_send_hex'
]
