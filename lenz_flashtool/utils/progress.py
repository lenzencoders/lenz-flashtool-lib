
r'''
 _     _____ _   _ _____   _____ _   _  ____ ___  ____  _____ ____  ____
| |   | ____| \ | |__  /  | ____| \ | |/ ___/ _ \|  _ \| ____|  _ \/ ___|
| |   |  _| |  \| | / /   |  _| |  \| | |  | | | | | | |  _| | |_) \___ \
| |___| |___| |\  |/ /_   | |___| |\  | |__| |_| | |_| | |___|  _ < ___) |
|_____|_____|_| \_/____|  |_____|_| \_|\____\___/|____/|_____|_| \_|____/

Progress Bar Utility Script

This script provides utilities for displaying a progress bar in the terminal with customizable color options.
It includes functions to translate color names to ANSI codes and to display a dynamic progress bar that updates
as a process completes.

Functions:
    - get_ansi_color_code(color_name): Translates a color name into an ANSI color code.
    - percent_complete(step, total_steps, bar_width=60, title="", print_perc=True, color='green'): Displays a
      progress bar in the terminal to indicate the percentage of completion.

Usage:
    This script is intended to be imported as a module in other Python scripts where a visual representation
    of progress is desired. The `percent_complete` function can be called to display and update a progress bar.

Example:
    In a Python script:

    ```python
    import lib_progress

    for i in range(101):
        lib_progress.percent_complete(i, 100, title="Processing", color="cyan")
        time.sleep(0.1)  # Simulating a task
    ```

(c) LENZ ENCODERS, 2020-2024
'''
import sys
from .termcolors import TermColors


def _get_ansi_color_code(color_name):
    """
    Translates a color name into an ANSI color code using TermColors class.

    Args:
        color_name (str): The name of the color (e.g., "red", "green", "blue", etc.).

    Returns:
        str: The ANSI color code corresponding to the color name. If the color name is not recognized,
             it defaults to white (TermColors.White).

    Available colors:
        - "grey"/"gray" (TermColors.DarkGray)
        - "black" (TermColors.Black)
        - "red" (TermColors.Red)
        - "green" (TermColors.Green)
        - "yellow" (TermColors.Yellow)
        - "blue" (TermColors.Blue)
        - "magenta" (TermColors.Magenta)
        - "violet" (TermColors.LightMagenta)
        - "cyan" (TermColors.Cyan)
        - "white" (TermColors.White)
        - "reset" (TermColors.ENDC)
    """
    color_mapping = {
        "grey": TermColors.DarkGray,
        "gray": TermColors.DarkGray,
        "black": TermColors.Black,
        "red": TermColors.Red,
        "green": TermColors.Green,
        "yellow": TermColors.Yellow,
        "blue": TermColors.Blue,
        "magenta": TermColors.Magenta,
        "violet": TermColors.LightMagenta,
        "cyan": TermColors.Cyan,
        "white": TermColors.White,
        "reset": TermColors.ENDC
    }
    return color_mapping.get(color_name.lower(), TermColors.White)  # Default to white


def percent_complete(step, total_steps, bar_width=60, title="", print_perc=True, color='green'):
    """
    Displays a progress bar in the terminal to indicate the percentage of completion.

    Args:
        step (int): The current step or iteration.
        total_steps (int): The total number of steps or iterations.
        bar_width (int, optional): The width of the progress bar in characters. Defaults to 60.
        title (str, optional): An optional title to display alongside the progress bar. Defaults to "".
        print_perc (bool, optional): Whether to print the percentage complete. Defaults to True.
        color (str, optional): The name of the color for the progress bar. Defaults to "green".

    Returns:
        None

    Author: https://stackoverflow.com/a/70586588
    """
    # UTF-8 left blocks: 1, 1/8, 1/4, 3/8, 1/2, 5/8, 3/4, 7/8
    utf_8s = ["█", "▏", "▎", "▍", "▌", "▋", "▊", "█"]
    perc = 100 * float(step) / float(total_steps)
    max_ticks = bar_width * 8
    num_ticks = int(round(perc / 100 * max_ticks))
    full_ticks = num_ticks / 8      # Number of full blocks
    part_ticks = num_ticks % 8      # Size of partial block (array index)
    disp = progbar = ""                 # Blank out variables
    progbar += utf_8s[0] * int(full_ticks)  # Add full blocks into Progress Bar
    # If part_ticks is zero, then no partial block, else append part char
    if part_ticks > 0:
        progbar += utf_8s[part_ticks]
    # Pad Progress Bar with fill character
    progbar += "▒" * int((max_ticks/8 - float(num_ticks)/8.0))
    if len(title) > 0:
        disp = title + ": "         # Optional title to progress display
    # Print progress bar in color: https://stackoverflow.com/a/21786287/6929343
    disp += _get_ansi_color_code(color)  # Color
    disp += progbar                     # Progress bar to progress display
    disp += TermColors.ENDC                # Color Reset
    if print_perc:
        # If requested, append percentage complete to progress display
        perc = min(perc, 100.0)          # Fix "100.04 %" rounding error
        disp += f" {perc:6.2f} %"
    # Output to terminal repetitively over the same line using '\r'.
    sys.stdout.write("\r" + disp)
    sys.stdout.flush()
