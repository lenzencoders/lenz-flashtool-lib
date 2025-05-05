r'''
 _     _____ _   _ _____   _____ _   _  ____ ___  ____  _____ ____  ____
| |   | ____| \ | |__  /  | ____| \ | |/ ___/ _ \|  _ \| ____|  _ \/ ___|
| |   |  _| |  \| | / /   |  _| |  \| | |  | | | | | | |  _| | |_) \___ \
| |___| |___| |\  |/ /_   | |___| |\  | |__| |_| | |_| | |___|  _ < ___) |
|_____|_____|_| \_/____|  |_____|_| \_|\____\___/|____/|_____|_| \_|____/


Data Visualization Utilities Module

This module provides plotting functions for comparing datasets and visualizing their
properties. It supports both interactive display and file export capabilities.

Key Features:
- Single and dual dataset plotting with automatic max/min value annotation
- Configurable labels and display properties
- Flexible output options (display and/or file save)
- Support for custom directories and filenames

Dependencies:
- numpy (for calculations)
- matplotlib (for plotting functionality)
- os (for path operations)

Author:
    LENZ ENCODERS, 2020-2025
'''
import os
from typing import Optional, Union, Sequence
import numpy as np
import matplotlib.pyplot as plt


def plot(
    data: Union[Sequence[float], np.ndarray],
    filename: Optional[str] = None,
    directory: Optional[str] = None
) -> None:
    """
    Plots a single dataset with annotated max and min values.

    Args:
        data: Input data to visualize (list or numpy array of numerical values)
        filename: Name for the output file (including extension). If None, plot won't be saved.
        directory: Target directory for saving. If None, uses current working directory.

    Returns:
        None: Displays interactive plot and optionally saves to file.

    Example:
        >>> data = [1, 3, 2, 4, 3]
        >>> plot(data, 'trend.png', 'plots')  # Saves to 'plots/trend.png'
    """
    plt.ion()
    plt.figure()
    plt.plot(data)
    max_val = np.max(data)
    min_val = np.min(data)
    plt.text(0.02, 0.98, f'Max: {max_val:.2f}\nMin: {min_val:.2f}',
             transform=plt.gca().transAxes,
             verticalalignment='top',
             bbox={"boxstyle": 'round', "facecolor": 'white', "alpha": 0.8}
             )
    if filename and directory:
        full_path = os.path.join(directory, filename)
        plt.savefig(full_path)
    elif filename:
        plt.savefig(filename)
    plt.show()


def plot2(
    a: Union[Sequence[float], np.ndarray],
    b: Union[Sequence[float], np.ndarray],
    filename: Optional[str] = None,
    directory: Optional[str] = None,
    label1: str = 'After calibration',
    label2: str = 'Before calibration'
) -> None:
    """
    Plots two datasets for comparison with annotated statistics.

    Args:
        a: First dataset (list or numpy array)
        b: Second dataset (list or numpy array)
        filename: Output filename (including extension). None prevents saving.
        directory: Target directory. None uses current directory.
        label1: Legend label for first dataset
        label2: Legend label for second dataset

    Returns:
        None: Displays interactive comparison plot
    """
    plt.ion()
    plt.figure()
    plt.plot(a, label=label1)
    plt.plot(b, label=label2)
    plt.legend(loc='lower left')

    max_a = np.max(a)
    min_a = np.min(a)
    max_b = np.max(b)
    min_b = np.min(b)
    plt.text(0.02, 0.98, f'{label1}:\nMax: {max_a:.2f}\nMin: {min_a:.2f}\n\n'
             f'{label2}:\nMax: {max_b:.2f}\nMin: {min_b:.2f}',
             transform=plt.gca().transAxes,
             verticalalignment='top',
             bbox={"boxstyle": 'round', "facecolor": 'white', "alpha": 0.8}
             )
    if filename and directory:
        full_path = os.path.join(directory, filename)
        plt.savefig(full_path)
    elif filename:
        plt.savefig(filename)
    plt.show()
