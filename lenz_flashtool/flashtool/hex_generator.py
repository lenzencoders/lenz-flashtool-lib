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
- Automatic date extraction from file modification timestamps

Functions:
    extract_version_from_filename(filename: str) -> int
        Extracts version number from filename and converts to hex format.

    get_file_date(filepath: str) -> int
        Extracts year and month from file modification time in YYYYMM format.

    generate_hex_main_fw(firmware_file: str, bootloader_file: str,
                        firmware_date: int = None, bootloader_date: int = None) -> None
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
- datetime: File timestamp processing and date formatting
- .hex_utils.HexFileProcessor: Core HEX processing engine

Usage Examples:
    Basic HEX generation:
    >>> generate_hex_main_fw("firmware.hex", "bootloader.hex")

    With versioned files:
    >>> generate_hex_main_fw("firmware_FT_ver_1_2_3.hex", "bootloader_FT_ver_2_0_1.hex",
    ...                     firmware_date=202507, bootloader_date=202507)

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
    - File modification dates in YYYYMM format
    - Optional bootloader integration

Security and Validation:
- CRC32 integrity verification
- Version consistency checking
- Input file validation
- Memory-safe operations
- Pattern validation
- Date format validation

Author:
    LENZ ENCODERS, 2020-2025
'''
import re
import os
from datetime import datetime
from glob import glob
from .hex_utils import HexFileProcessor


def extract_version_from_filename(filename: str) -> int:
    """
    Extract version from filename and convert to 32-bit integer.
    Supports 'X.Y.Z' (dots) or 'X_Y_Z' (underscores) formats.
    
    Returns version as (major << 16) | (minor << 8) | patch
    """
    basename = os.path.basename(filename)
    
    # Try new format with dots: X.Y.Z
    match = re.search(r'(\d+)\.(\d+)\.(\d+)', basename)
    if not match:
        # Fallback to old format with underscores: X_Y_Z
        match = re.search(r'(\d+)_(\d+)_(\d+)', basename)
    
    if match:
        major = int(match.group(1))
        minor = int(match.group(2))
        patch = int(match.group(3))
        return (major << 16) | (minor << 8) | patch
    
    # Default version 1.0.0
    return 0x00000100


def get_file_date(filepath: str) -> int:
    """
    Extract year and month from file modification time and format as YYYYMM integer.

    Uses the file's last modification timestamp to determine the creation date.
    Returns the date in YYYYMM format (e.g., 202507 for July 2025).

    Args:
        filepath: Full path to the file to extract date from

    Returns:
        int: Date in YYYYMM format representing the file's modification year and month

    Raises:
        FileNotFoundError: If the specified file path does not exist
        OSError: If there are permission issues accessing the file

    Example:
        >>> get_file_date("/path/to/firmware.hex")
        202507
        >>> get_file_date("nonexistent_file.hex")  # Returns current date if file not found
        202412
    """
    if not os.path.exists(filepath):
        return int(datetime.now().strftime('%Y%m'))

    mod_time = os.path.getmtime(filepath)
    mod_date = datetime.fromtimestamp(mod_time)

    return int(mod_date.strftime('%Y%m'))


def generate_hex_main_fw(firmware_file: str, bootloader_file: str,
                         firmware_date: int = None, bootloader_date: int = None):
    """
    Generate a processed HEX file with CRC metadata for main firmware and optional bootloader.
    Automatically extracts versions from filenames (supports 'ver_X_Y_Z' or 'X.Y.Z' patterns).
    Output file will be named 'app_X.Y.Z.hex' using version from firmware filename (SemVer format).

    Args:
        firmware_file (str): Filename of main firmware HEX file (must exist)
        bootloader_file (str): Filename of bootloader HEX file (optional)

    Example:
        >>> generate_hex_main_fw("firmware_FT_1.0.11.hex", "bootloader_FT_1.0.3.hex")
        # Will create output file: app_1.0.11.hex
        
        >>> generate_hex_main_fw("firmware_FT_ver_1_0_2.hex", "bootloader_FT_ver_1_0_0.hex")
        # Will create output file: app_1.0.2.hex (backward compatible)
    """
    processor = HexFileProcessor()

    # Extract versions from filenames
    try:
        program_version = extract_version_from_filename(firmware_file)
        # Extract version string for output filename
        # Try new format first (X.Y.Z)
        version_match = re.search(r'(\d+)\.(\d+)\.(\d+)', firmware_file)
        if not version_match:
            # Fallback to old format (_ver_X_Y_Z)
            version_match = re.search(r'_ver_(\d+)_(\d+)_(\d+)', firmware_file)
        
        # Extract version numbers for output filename in SemVer format
        if version_match:
            major, minor, patch = version_match.group(1), version_match.group(2), version_match.group(3)
            version_str = f"app_{major}.{minor}.{patch}.hex"
        else:
            version_str = "app_1.0.0.hex"
    except ValueError:
        program_version = 0x00000100  # Default version 1.0.0
        version_str = "app_1.0.0.hex"  # Default output filename

    try:
        bootloader_version = extract_version_from_filename(bootloader_file) if bootloader_file else 0x00000100
    except ValueError:
        bootloader_version = 0x00000100  # Default version 1.0.0

    # Process files
    firmware_filepath = os.path.abspath(firmware_file)

    if firmware_date is None:
        firmware_date = get_file_date(firmware_filepath)

    if bootloader_file:
        bootloader_filepath = os.path.abspath(bootloader_file)
        if bootloader_date is None and os.path.exists(bootloader_filepath):
            bootloader_date = get_file_date(bootloader_filepath)
    else:
        bootloader_date = firmware_date

    processor.parse_hex_file(firmware_filepath)

    if bootloader_file:
        bootloader_filepath = os.path.abspath(bootloader_file)
        if os.path.exists(bootloader_filepath):
            processor.parse_hex_file(bootloader_filepath, is_bootloader=True)

    processed_hex = processor.split_with_crc(
        chunk_size=2048,
        metadata=True,
        program_version=program_version,
        bootloader_version=bootloader_version,
        program_date=firmware_date,
        bootloader_date=bootloader_date,
    )

    output_dir = os.path.dirname(firmware_filepath)
    output_file = os.path.join(output_dir, version_str)

    with open(output_file, "w") as f:
        f.write("\n".join(processed_hex))


def find_latest_fw_version(directory: str = None, pattern: str = "firmware_FT_*.hex") -> str:
    """
    Finds the firmware file with the latest version matching the specified pattern.
    Supports both 'X.Y.Z' (dots) and 'X_Y_Z' (underscores) version formats.

    Searches the specified directory for files following the version pattern and returns
    the path to the file with the highest version number (X.Y.Z).

    Args:
        directory (str, optional): Directory to search in. If None, uses the script's directory.
                                Defaults to None.
        pattern (str, optional): File pattern to match. Should contain '*' as wildcard.
                            Defaults to "firmware_FT_*.hex".

    Returns:
        str: Full path to the firmware file with the highest version number.

    Raises:
        FileNotFoundError: If no matching firmware files are found in the directory.

    Examples:
        >>> find_latest_fw_version("/firmware/")
        "/firmware/firmware_FT_1.0.11.hex"

        >>> find_latest_fw_version(pattern="bootloader_FT_*.hex")
        "/firmware/bootloader_FT_1.0.3.hex"
    """
    if directory is None:
        directory = os.path.dirname(os.path.abspath(__file__))

    full_pattern = os.path.join(directory, pattern)
    fw_files = glob(full_pattern)

    if not fw_files:
        raise FileNotFoundError(f"No firmware files matching '{pattern}' pattern found in {directory}")

    def extract_version(filename):
        """
        Extracts version tuple (X,Y,Z) from filename.
        Supports both 'X.Y.Z' (dots) and 'X_Y_Z' (underscores) formats.
        """
        basename = os.path.basename(filename)
        
        # Try new format with dots first: X.Y.Z
        match = re.search(r'(\d+)\.(\d+)\.(\d+)', basename)
        if match:
            return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        
        # Fallback to old format with underscores: X_Y_Z
        match = re.search(r'(\d+)_(\d+)_(\d+)', basename)
        if match:
            return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        
        # No version found
        return (0, 0, 0)

    # Sort by version tuple (major, minor, patch)
    sorted_files = sorted(fw_files, key=extract_version)
    latest_fw = sorted_files[-1]
    version = extract_version(latest_fw)

    if version == (0, 0, 0):
        print(f"Warning: Could not extract version from filename: {latest_fw}")
    else:
        print(f"Found firmware version {version[0]}.{version[1]}.{version[2]}: {latest_fw}")
    
    return latest_fw
