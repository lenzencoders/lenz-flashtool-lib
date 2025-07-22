r'''
 _     _____ _   _ _____   _____ _   _  ____ ___  ____  _____ ____  ____
| |   | ____| \ | |__  /  | ____| \ | |/ ___/ _ \|  _ \| ____|  _ \/ ___|
| |   |  _| |  \| | / /   |  _| |  \| | |  | | | | | | |  _| | |_) \___ \
| |___| |___| |\  |/ /_   | |___| |\  | |__| |_| | |_| | |___|  _ < ___) |
|_____|_____|_| \_/____|  |_____|_| \_|\____\___/|____/|_____|_| \_|____/


FlashTool HEX Generator Module

This module provides advanced processing of Intel HEX files for firmware programming,
with automatic version detection and CRC metadata generation.

Key Features:
- HEX file processing with automatic CRC32 generation
- Smart version extraction from filenames (supports multiple patterns)
- Bootloader integration with version synchronization
- 2048-byte page optimization for flash programming
- Metadata injection (versions, timestamps, CRCs)
- Cross-platform path handling
- Latest version detection in directory

Enhanced Functionality:
- Automatic version detection from filenames
- Flexible pattern matching for versioned files
- Default version fallback (1.0.0) when pattern not found
- Absolute path support for files in any location
- Validation of input files

Functions:
    generate_hex_main_fw(firmware_file: str, bootloader_file: str) -> None
        Processes firmware and bootloader HEX files, generates output with:
        - Combined firmware+bootloader (optional)
        - Extracted version metadata
        - 2048-byte page structure
        - CRC32 checksums
        - Output named 'app_ver_X_Y_Z.hex'

    find_latest_fw_version(directory: str = None, pattern: str = "app_ver_*_*_*.hex") -> str
        Finds the firmware file with the latest version matching specified pattern
        - Supports custom version patterns
        - Automatic version number comparison
        - Returns full path to latest version

Dependencies:
- os: Cross-platform path operations
- re: Regular expressions for version extraction
- glob: File pattern matching
- .hex_utils.HexFileProcessor: Core HEX processing engine

Usage Examples:
    Basic HEX generation:
    >>> generate_hex_main_fw("firmware.hex", "bootloader.hex")

    With versioned files:
    >>> generate_hex_main_fw("firmware_FT_ver_1_2_3.hex", "bootloader_FT_ver_2_0_1.hex")

    Find latest firmware:
    >>> find_latest_fw_version("/firmware/")
    "/firmware/app_ver_2_1_0.hex"

    Custom pattern matching:
    >>> find_latest_fw_version(pattern="fw_v*.*.*.hex")

Output:
    Generates versioned HEX files containing:
    - Processed firmware data in 2048-byte pages
    - Embedded CRC32 for each page
    - Extracted version information
    - Optional bootloader integration

Security and Validation:
- CRC32 integrity verification
- Version consistency checking
- Input file validation
- Memory-safe operations
- Pattern validation

Author:
    LENZ ENCODERS, 2020-2025
'''
import re
import os
from glob import glob
from .hex_utils import HexFileProcessor


def extract_version_from_filename(filename: str) -> int:
    """
    Extract version number from filename in format *_ver_X_Y_Z.*
    and convert it to 0x00XXYYZZ hex format.

    Args:
        filename: Filename containing version (e.g., "firmware_FT_ver_1_0_2.hex")

    Returns:
        int: Version in 0x00XXYYZZ format (e.g., 0x00010002 for 1.0.2)

    Raises:
        ValueError: If version pattern not found in filename
    """
    # Find version pattern in filename
    match = re.search(r'_ver_(\d+)_(\d+)_(\d+)', filename)
    if not match:
        raise ValueError(f"Version not found in filename: {filename}")

    major, minor, patch = map(int, match.groups())

    # Pack into 0x00MMmmpp format (MM=major, mm=minor, pp=patch)
    return (major << 16) | (minor << 8) | patch


def generate_hex_main_fw(firmware_file: str, bootloader_file: str):
    """
    Generate a processed HEX file with CRC metadata for main firmware and optional bootloader.
    Automatically extracts versions from filenames if they contain '_ver_X_Y_Z' pattern.
    Output file will be named 'app_ver_X_Y_Z.hex' using version from firmware filename.

    Args:
        firmware_file (str): Filename of main firmware HEX file (must exist)
        bootloader_file (str): Filename of bootloader HEX file (optional)

    Example:
        >>> generate_hex_main_fw("firmware_FT_ver_1_0_2.hex", "bootloader_FT_ver_1_0_0.hex")
        # Will create output file: app_ver_1_0_2.hex
    """
    processor = HexFileProcessor()

    # Extract versions from filenames
    try:
        program_version = extract_version_from_filename(firmware_file)
        # Extract version string for output filename
        version_match = re.search(r'_ver_(\d+)_(\d+)_(\d+)', firmware_file)
        version_str = f"app_ver_{version_match.group(1)}_{version_match.group(2)}_{version_match.group(3)}.hex"
    except ValueError:
        program_version = 0x00000100  # Default version 1.0.0
        version_str = "app_ver_1_0_0.hex"  # Default output filename

    try:
        bootloader_version = extract_version_from_filename(bootloader_file) if bootloader_file else 0x00000100
    except ValueError:
        bootloader_version = 0x00000100  # Default version 1.0.0

    # Process files
    firmware_file_path = os.path.abspath(firmware_file)
    processor.parse_hex_file(firmware_file_path)

    if bootloader_file:
        bootloader_file_path = os.path.abspath(bootloader_file)
        if os.path.exists(bootloader_file_path):
            processor.parse_hex_file(bootloader_file_path, is_bootloader=True)

    processed_hex = processor.split_with_crc(
        chunk_size=2048,
        metadata=True,
        program_version=program_version,
        bootloader_version=bootloader_version
    )

    output_dir = os.path.dirname(firmware_file_path)
    output_file = os.path.join(output_dir, version_str)

    with open(output_file, "w") as f:
        f.write("\n".join(processed_hex))


def find_latest_fw_version(directory: str = None, pattern: str = "app_ver_*_*_*.hex") -> str:
    """
    Finds the firmware file with the latest version matching the specified pattern.

    Searches the specified directory for files following the version pattern and returns
    the path to the file with the highest version number (X.Y.Z).

    Args:
        directory (str, optional): Directory to search in. If None, uses the script's directory.
                                Defaults to None.
        pattern (str, optional): File pattern to match with wildcards for version numbers.
                            Should contain '*' where version numbers appear.
                            Defaults to "app_ver_*_*_*.hex".

    Returns:
        str: Full path to the firmware file with the highest version number.

    Raises:
        FileNotFoundError: If no matching firmware files are found in the directory.
        ValueError: If the pattern doesn't contain enough wildcards for version numbers.

    Examples:
        >>> find_latest_fw_version("/firmware/")
        "/firmware/app_ver_2_1_0.hex"

        >>> find_latest_fw_version(pattern="fw_v*.*.*.hex")
        "C:/project/fw_v3.2.1.hex"
    """
    if directory is None:
        directory = os.path.dirname(os.path.abspath(__file__))

    # Validate the pattern has enough wildcards for version components
    if pattern.count('*') < 3:
        raise ValueError("Pattern must contain at least 3 wildcards for version components (major.minor.patch)")

    full_pattern = os.path.join(directory, pattern)
    fw_files = glob(full_pattern)

    if not fw_files:
        raise FileNotFoundError(f"No firmware files matching '{pattern}' pattern found in {directory}")

    def extract_version(filename):
        """
        Extracts version tuple (X,Y,Z) from filename based on the pattern.

        Converts the pattern to a regex by replacing wildcards with capture groups.
        """
        # Convert glob pattern to regex
        regex_pattern = re.escape(pattern)
        regex_pattern = regex_pattern.replace(r'\*', r'(\d+)')  # Replace escaped * with digit capture
        match = re.search(regex_pattern, os.path.basename(filename))
        if match and len(match.groups()) >= 3:
            return tuple(map(int, match.groups()[:3]))  # Take first 3 groups as version
        return (0, 0, 0)

    sorted_files = sorted(fw_files, key=extract_version)
    latest_fw = sorted_files[-1]
    version = extract_version(latest_fw)

    print(f"Found firmware version {version[0]}.{version[1]}.{version[2]}: {latest_fw}")
    return latest_fw
