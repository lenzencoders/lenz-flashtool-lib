"""

LENZ Encoder Signal Processing Library

This library provides a comprehensive suite of signal processing functions for high-precision
LENZ encoder systems, designed to enhance the accuracy of position measurements in applications
such as motor control, robotics, and industrial automation. It includes advanced algorithms for
differential signal computation, harmonic analysis, noise filtering, and calibration table
generation, with specialized support for motor-driven systems to suppress harmonic errors.

Key Features:

- Differential signal computation between paired encoder signals for error analysis.
- Advanced filtering techniques, including bidirectional moving average and custom smoothing filters.
- Harmonic analysis using Fast Fourier Transform (FFT) to identify and quantify periodic errors.
- Generation of difference compensation tables for systematic error correction.
- Motor harmonic suppression for enhanced accuracy in motor-driven encoder systems.
- Support for 24-bit encoder data with proper handling of wrap-around effects.

Notes:

- The library assumes 24-bit encoder data (0 to 2^24 - 1) but can be adapted for other resolutions.
- Functions are designed for static use, requiring no instantiation of `LenzEncoderProcessor`.
- Calibration routines (`lenz_cal`, `lenz_cal_motor_harm`) are optimized for high-precision
  applications but may require tuning of parameters like `coarse_red` and `motor_harm` for
  specific use cases.
- The `diff_table_gen_motor_harm` function includes motor harmonic suppression, which is critical
  for motor-driven systems but requires a valid `motor_harm` value.

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

# Core functions
from .processing import LenzEncoderProcessor

__all__ = [
    'LenzEncoderProcessor'
]
