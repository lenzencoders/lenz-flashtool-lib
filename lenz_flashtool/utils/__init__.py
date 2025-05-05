"""

Utils for plotting, coloring output and progress bar.

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

from .plot import plot, plot2
from .termcolors import TermColors
from .progress import percent_complete

__all__ = [
    'plot',
    'plot2',
    'TermColors',
    'percent_complete'

]
