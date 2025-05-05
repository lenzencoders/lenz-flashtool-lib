r'''
 _     _____ _   _ _____   _____ _   _  ____ ___  ____  _____ ____  ____
| |   | ____| \ | |__  /  | ____| \ | |/ ___/ _ \|  _ \| ____|  _ \/ ___|
| |   |  _| |  \| | / /   |  _| |  \| | |  | | | | | | |  _| | |_) \___ \
| |___| |___| |\  |/ /_   | |___| |\  | |__| |_| | |_| | |___|  _ < ___) |
|_____|_____|_| \_/____|  |_____|_| \_|\____\___/|____/|_____|_| \_|____/


UART commands for the LENZ FlashTool device.


Author:
    LENZ ENCODERS, 2020-2025
'''
from enum import IntEnum


class UartCmd(IntEnum):
    """Enumeration of UART commands for communication with the FlashTool system.

    This class defines all the hexadecimal command codes used for controlling power,
    channel selection, and data communication with the FlashTool hardware.
    """

    CMD_POWER_OFF = 0x0B
    """int: Command to power off encoder on channel 2.

    Usage:
        - Sent to deactivate power to the encoder connected to channel 2
        - Typically used during maintenance or reconfiguration
        - Expects no additional parameters
        - Data and address in packet doesn't matter

    Packet Structure:
        Request: [DUMMY_DATA_SIZE][REG_ADDR][0x0B][DUMMY_DATA][CHECKSUM]
        Response: None

    Examples:
        >>>  :0100400BFFB5
        >>>  :0400400B111111116D

    """

    CMD_POWER_ON = 0x0C
    """int: Command to power on the encoder on channel 2.

    Usage:
        - Sent to activate power to the encoder connected to channel 2
        - Should be followed by a stabilization delay (0.1s) before communication
        - Expects no additional parameters
        - Data and address in packet doesn't matter

    Packet Structure:
        Request: [DUMMY_DATA_SIZE][REG_ADDR][0x0C][DUMMY_DATA][CHECKSUM]
        Response: None

    Examples:
        >>>  :0100400C0AA9
        >>>  :0300400CAABBCC80
    """

    CMD_CH1_POWER_OFF = 0x08
    """int: Command to power off encoder on channel 1.

    Usage:
        - Sent to deactivate power to the secondary encoder (channel 1)
        - Useful for power management in dual-encoder systems
        - Typically used during maintenance or reconfiguration
        - Expects no additional parameters

    Packet Structure:
        Request: [DUMMY_DATA_SIZE][REG_ADDR][0x08][DUMMY_DATA][CHECKSUM]
        Response: None

    Examples:
        >>>  :01004008DDDA
        >>>  :04000008DDAADDAAE6
    """

    CMD_CH1_POWER_ON = 0x09
    """int: Command to power on the encoder on channel 1.

    Usage:
        - Sent to activate power to the secondary encoder (channel 1)
        - Should be preceded by channel selection if needed
        - Requires stabilization time (0.1s) before encoder communication
        - Expects no additional parameters

    Packet Structure:
        Request: [DUMMY_DATA_SIZE][REG_ADDR][0x09][DUMMY_DATA][CHECKSUM]
        Response: None

    Examples:
        >>>  :0100000903F3
        >>>  :0300A009A0A0A173
    """

    CMD_SELECT_SPI_CH = 0X0A
    """int: Command to select SPI communication channel.

    Usage:
        - Sent before any channel-specific operations
        - Parameter: 0x00 for channel 1, 0x01 for channel 2
        - Affects all subsequent SPI communications until changed

    Note:
        Channel selection is persistent until changed or power cycled
        Default: Channel 2 (0x01)

    Packet Structure:
        Request: [01][REG_ADDR][0x0A][CHANNEL_BYTE][CHECKSUM]
        Where CHANNEL_BYTE is 0x00 or 0x01

    Example:
        >>> :0100400A00F4  Select channel 1
    """

    CMD_SELECT_FLASHTOOL_MODE = 0x01
    """int: Command to select FlashTool mode for communication.

    Usage:
        - Sent before any channel-specific operations
        - Parameter:
            0x00 for BISS_MODE_SPI_SPI,
            0x01 for BISS_MODE_AB_UART,
            0x02 for BISS_MODE_SPI_UART_IRS,
            0x03 for BISS_MODE_AB_SPI
        - Defines all subsequent communications via SPI, AB (incremental), UART for channels 1 and 2 until changed
        - Address in packet doesn't matter

    Note:
        FlashTool mode is persistent until changed or power cycled
        Default: BISS_MODE_SPI_SPI (0x00)

    Packet Structure:
        Request: [01][REG_ADDR][0x01][CHANNEL_BYTE][CHECKSUM]
        Where CHANNEL_BYTE is 0x00, 0x01, 0x02 or 0x03

    Example:
        >>> :0100000100FE  Select FlashTool mode - BISS_MODE_SPI_SPI
    """

    CMD_NVRST = 0x83      # Command to reset the FlashTool
    """int: Command to perform a non-volatile reset of the FlashTool.

    Usage:
        - Clears any temporary settings
        - Requires stabilization time (0.1s) before encoder communication
        - Data and address in packet doesn't matter

    Packet Structure:
        Request: [DUMMY_DATA_SIZE][REG_ADDR][0x83][DUMMY_DATA][CHECKSUM]
        Response: None

    Examples:
        >>>  :01004083221A
        >>>  :0400408311111111F5
    """

    # Data Communication Commands
    HEX_WRITE_CMD = 0x0D
    """int: Command to write data to encoder registers.

    Usage:
        - Used for configuration and parameter setting

    Packet Structure:
        Request: [DATA_SIZE][REG_ADDR][0x0D][DATA_MSB][DATA_LSB][CHECKSUM]
        Response: None

    Example:
        >>>  :0100400D05AD
    """

    HEX_READ_ANGLE_TWO_ENC_SPI = 0x80
    """int: Command to read angle data from two encoders via SPI.

    Usage:
        - Continuous streaming mode for dual-encoder reading
        - Requires both encoders to be powered on
        - Returns multiple measurement frames in each response packet

    Response Format:
        Each 245-byte packet contains:

        >>> [Header][FrameCount][Reserved][DataFrames...][Checksum]

        Where:

        - Header: `[0xF0, 0x00, 0x00, 0x90]` (fixed pattern)
        - FrameCount: Number of valid data frames (typically 30)
        - DataFrames: 30 measurement frames (8 bytes each):

        >>> [ENC1_LOW][ENC1_MID][ENC1_HIGH][ENC1_COUNTER]
        >>> [ENC2_LOW][ENC2_MID][ENC2_HIGH][ENC2_COUNTER]

        - Checksum: 1 byte (sum of first 244 bytes modulo 256)

    Data Interpretation:
        >>> Encoder Angle = (HIGH << 16) | (MID << 8) | LOW

        Counter = Single byte turn counter

    Example Packet Structure:
        >>> F0 00 00 90 [30 frames...] [checksum]
    """

    HEX_READ_ANGLE_TWO_ENC_AB_UART = 0x79
    """int: Command to read angle data via AB (incremental) interface over UART.

    Usage:
        - Alternative to SPI angle reading
        - Provides quadrature-encoded equivalent output
        - Faster update rate than SPI in some implementations
    """

    HEX_READ_ANGLE_TWO_ENC_AB_SPI = 0x78
    """int: Command to read angle data via AB (incremental) interface over SPI.

    Usage:
        - SPI angle reading
        - Provides quadrature-encoded equivalent output

    Note:
        channel 1 - AB
        channel 2 - SPI
    """

    HEX_READ_CMD = 0x82
    """int: Generic read command for encoder data.

    Usage:
        - Followed by register address and dummy data with size equal to required read data size
        - Can read various status and configuration registers
        - Response length depends on target register

    Packet Structure:
        - Request: [DUMMY_DATA_SIZE][REG_ADDR][0x82][DUMMY_DATA][CHECKSUM]
        - Response: [DATA_SIZE][REG_ADDR][0x92][DATA][CHECKSUM]

    Examples:
        Read Example:
            >>>  :01004082013C
        Response:
            >>>  0x10040920528

        Another example writing 3 to BSEL register (changing BiSS Bank to 3):

        Requests:
            >>>  :0100400D03AF  Writing 3 to register 0x40
            >>>  :01004082013C  Reading register 0x40
        Response:
            >>>  0x1004092032A  Register 0x40 keeps 0x03
    """
