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
#

from .commands import (
    BISS_COMMANDSTATE,
    ERROR_FLAGS,
    biss_commands,
    interpret_biss_commandstate,
    interpret_error_flags
)
from .crc import biss_crc6_calc
from .registers import (
    BiSSBank,
)

__all__ = [
    'BISS_COMMANDSTATE',
    'ERROR_FLAGS',
    'biss_commands',
    'interpret_biss_commandstate',
    'interpret_error_flags',

    'biss_crc6_calc',

    'BiSSBank'
]
