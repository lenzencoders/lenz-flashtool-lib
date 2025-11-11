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

    PKG_INFO_LENGTH = 0x05
    """int: Packet INFO constant structure length of 5 bytes

    Packet Structure:
        Request Packet:
        [DUMMY_DATA_SIZE][REG_ADDR][ CMD  ][DUMMY_DATA][CHECKSUM]
        [     1 byte    ][2 bytes ][1 byte][----------][ 1 byte ]

        Response Packet:
        [DUMMY_DATA_SIZE][REG_ADDR][CMD+CMD_VAL_ADD][DUMMY_DATA][CHECKSUM]
        [     1 byte    ][2 bytes ][     1 byte    ][----------][ 1 byte ]

    """

    RX_DATA_LENGTH_IRS = 0xFC
    """int: Data length for command:
        HEX_IRS_ENC_WRITE_READ_CMD: 0x0F
    """

    RX_DATA_LENGTH_CURRENT = 0x04
    """int: Data length for commands:
        HEX_READ_ENC2_CURRENT: 0x12
    """

    CMD_VAL_ADD = 0x10
    """int: Value added to CMD in the Response Packet

    Response:
        [DUMMY_DATA_SIZE][REG_ADDR][CMD+CMD_VAL_ADD][DUMMY_DATA][CHECKSUM]

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
            0x04 for BISS_MODE_DEFAULT_SPI
        - Defines all subsequent communications via SPI, AB (incremental), UART for channels 1 and 2 until changed
        - Address in packet doesn't matter

    Note:
        FlashTool mode is persistent until changed or power cycled
        Default: BISS_MODE_DEFAULT_SPI (0x04) - Channel 1: Without communication, Channel 2: SPI

    Packet Structure:
        Request: [01][REG_ADDR][0x01][CHANNEL_BYTE][CHECKSUM]
        Where CHANNEL_BYTE is 0x00, 0x01, 0x02 or 0x03

    Example:
        >>> :0100000100FE  Select FlashTool mode - BISS_MODE_SPI_SPI
    """

    CMD_SELECT_FLASHTOOL_CURRENT_SENSOR_MODE = 0x11
    """int: Command to select FlashTool current sensor mode.

    Black FlashTool has Current Sensor mode.
    Green FlashTool has NOT Current Sensor mode.

    Usage:
        - Sent before any channel-specific operations
        - Parameter:
            0x00 for CURRENT_SENSOR_MODE_DISABLE,
            0x01 for CURRENT_SENSOR_MODE_ENABLE
        - Defines all subsequent communications via SPI, AB (incremental), UART for channels 1 and 2 until changed
        - Address in packet doesn't matter

    Note:
        FlashTool current sensor mode is persistent until changed or power cycled
        Default: CURRENT_SENSOR_MODE_ENABLE (0x01)

    Packet Structure:
        Request: [01][REG_ADDR][0x11][CHANNEL_BYTE][CHECKSUM]
        Where CHANNEL_BYTE is 0x00 or 0x01

    Example:
        >>> :0100001101ed  Select current sensor mode - CURRENT_SENSOR_MODE_ENABLE
    """

    CMD_SELECT_CH1_MODE = 0x0E
    """ Command to select FlashTool channel 1 SPI mode.
    Works for BISS_MODE_SPI_SPI.

    Usage:
        - Sent before any channel-specific operations
        - Parameter:
            0x00 for CH1_LENZ_BISS,
            0x01 for CH1_LIR_SSI,
            0x02 for CH1_LIR_BISS_21B
        - Defines all subsequent communications via SPI for channel 1
        - Address in packet doesn't matter

    Note:
        FlashTool current sensor mode is persistent until changed or power cycled
        Default: CH1_LENZ_BISS (0x00)

    Packet Structure:
        Request: [01][REG_ADDR][0x0E][CHANNEL_BYTE][CHECKSUM]
        Where CHANNEL_BYTE is 0x00 or 0x01 or 0x02

    Example:
        >>> :0100000e01ed  Select channel 1 SPI mode - CH1_LENZ_BISS
    """

    HEX_READ_ENC2_CURRENT = 0x12
    """int: Command to read current from encoder on channel 2.

    Usage:
        - Single data frame
        - Requires encoder to be powered on
        - Returns one measurement frame in each response packet
        - Address in packet doesn't matter

    Packet Structure:
        Request: [DUMMY_DATA_SIZE][REG_ADDR][0x12][DUMMY_DATA][CHECKSUM]

        Where:

        - DUMMY_DATA_SIZE: 4 bytes

    Example Request Packet Structure:
        >>> 0400001200010203e4

    Response Format:
        Data frame contains:

        >>> [Header][DataFrame][Checksum]

        Where:

        - Header: `[0x04, 0x00, 0x00, 0x22]` (fixed pattern)
        - DataFrame: 1 measurement frame (4 bytes):

        >>> [ENC2_CURRENT_HIGH][ENC2_CURRENT_MID][ENC2_CURRENT_LOW]

        - Checksum: 1 byte (sum of first 8 bytes modulo ...)

    Example Response Packet Structure:
        >>> 04 00 00 22 [frame] [checksum]
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

    HEX_IRS_ENC_WRITE_READ_CMD = 0x0F
    """int: Command to write data to encoder registers.

    Usage:
        - Used for configuration and parameter setting

    Packet Structure:
        Request: [DATA_SIZE][REG_ADDR][0x0D][DATA_MSB][DATA_LSB][CHECKSUM]
        Response: None

    Example:
        >>>  :0100400D05AD
    """

    HEX_READ_INSTANT_ANGLE_ENC_SPI = 0x10
    """int: Command to read instant angle data from encoder via SPI.

    Usage:
        - Single data frame for encoder reading
        - Requires encoder to be powered on
        - Returns one measurement frame in each response packet

    Response Format:
        Data frame contains:

        >>> [Header][DataFrame][Checksum]

        Where:

        - Header: `[0x04, 0x00, 0x00, 0x20]` (fixed pattern)
        - DataFrame: 1 measurement frame (8 bytes):

        >>> [ENC2_LOW][ENC2_MID][ENC2_HIGH][ENC2_COUNTER]

        - Checksum: 1 byte (sum of first 12 bytes modulo ...)

    Data Interpretation:
        >>> Encoder Angle = (HIGH << 16) | (MID << 8) | LOW

        Counter = Single byte turn counter

    Example Packet Structure:
        >>> 04 00 00 20 [1 frame...] [checksum]
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

    CMD_REBOOT_TO_BL = 0xFF
    """int: Command to reboot to bootloader.

    Usage:
        - Used for entering bootloader
        - Address in packet doesn't matter

    Note:
        Need to use bootloader cmd to reboot to main fw.

    Packet Structure:
        - Request: [0x01][REG_ADDR][0xFF][DUMMY_DATA][CHECKSUM]

    Example:
        >>> :010000ff0000
    """


class UartBootloaderCmd(IntEnum):
    UART_COMMAND_STATE_STAY_BL = 0x00
    """int: Command to stay in bootloader.

    Need to be sent in 5s after FlashTool is powered on. 
    To try again to reset the power of FlashTool.

    Usage:
        - Request consist UART_SEQ_STAY_IN_BL as data
        - Address in packet doesn't matter
        - Response consist UART_SEQ_ANSWER_TO_STAY_IN_BL as data

    Packet Structure:
        Request: [DATA_SIZE][REG_ADDR][0x00][UART_SEQ_STAY_IN_BL][CHECKSUM]
        Response: [DATA_SIZE][REG_ADDR][0x10][UART_SEQ_ANSWER_TO_STAY_IN_BL][CHECKSUM]

    Examples:
        Requests:
            >>>  :040000000531f6b917
        Response:
            >>>  :0400001006b14ef9ee
    """

    UART_COMMAND_LOAD_2K = 0x01
    """int: Command to load 2048 bytes of fw to FlashTool.

    Usage:
        - Address in packet doesn't matter

    Packet Structure:
        Request: [DATA_SIZE][REG_ADDR][0x01][DATA][CHECKSUM]

    Example Packet Structure:
        >>> 40 00 00 01 [64 bytes...] [checksum]
    """

    UART_COMMAND_RUN_PROGRAM = 0x02
    """int: Command to run main firmware FlashTool.

    Usage:
        - Data and address in packet doesn't matter

    Packet Structure:
        Request: [DATA_SIZE][REG_ADDR][0x02][DUMMY_DATA][CHECKSUM]

    Examples:
        >>>  :0100000200fd
    """

    UART_COMMAND_CHECK_PROGRAM_CRC32 = 0x04
    """int: Command to calculate CRC32 of main firmware FlashTool and set memory flag.

    Usage:
        - Data and address in packet doesn't matter

    Packet Structure:
        Request: [DATA_SIZE][REG_ADDR][0x04][DUMMY_DATA][CHECKSUM]

    Examples:
        >>>  :0100000400fb
    """

    UART_COMMAND_WRITE_CURRENT_PAGE_CRC32 = 0x05
    """int: Command to write current page CRC32.

    Usage:
        - When UART_COMMAND_RUN_PROGRAM is used
        - Address in packet doesn't matter

    Packet Structure:
        Request: [DATA_SIZE][REG_ADDR][0x05][CRC32_DATA][CHECKSUM]

    Examples:
        >>>  :040000058068B36CF0
    """

    UART_COMMAND_READ_MEMORYSTATE = 0x06
    """int: Command to read memory state of FlashTool.

    Response MEMORY_STATE_DATA:
        - UART_MEMORYSTATE_IDLE = 0
        - UART_MEMORYSTATE_FLASH_FW_CRC_OK = 2
        - UART_MEMORYSTATE_FLASH_FW_CRC_FAULT = 3
        - UART_MEMORYSTATE_FW_CHECK_CRC32_FAULT = 4
        - UART_MEMORYSTATE_FW_CHECK_CRC32_OK = 5
        - UART_MEMORYSTATE_FLASH_FW_NULL = 12
        - UART_MEMORYSTATE_FLASH_BSY = 255

    Usage:
        - Data and address in packet doesn't matter

    Packet Structure:
        Request: [DATA_SIZE][REG_ADDR][0x06][DUMMY_DATA][CHECKSUM]
        Response: [DATA_SIZE][REG_ADDR][0x16][MEMORY_STATE_DATA][CHECKSUM]

    Examples:
        Request:
            >>>  :0100000600f9
        Response:
            >>>  :0100001602e7
    """

    UART_COMMAND_READ_PROGRAM_BOOTLOADER_VER = 0x07
    """int: Command to read fw and bootloader version of FlashTool.

    Response VERSION_DATA:
        - Bytes 0-3: Firmware version (4 bytes, big-endian format)
        - Bytes 4-7: Bootloader version (4 bytes, big-endian format)

    Each version is represented as 4-byte value in format:
        - Major version: byte 0
        - Minor version: byte 1
        - Patch version: byte 2
        - Build number: byte 3

    Usage:
        - Data and address in packet doesn't matter

    Packet Structure:
        Request: [DATA_SIZE][REG_ADDR][0x07][DUMMY_DATA][CHECKSUM]
        Response: [DATA_SIZE][REG_ADDR][0x17][VERSION_DATA][CHECKSUM]

    Examples:
        Request:
            >>>  :080000070000000000000000f1
        Response:
            >>>  :80000170001000700010002d6
            Firmware: 0x00010007, Bootloader: 0x00010002

    Note:
        - Version data is returned in big-endian byte order
        - Actual version interpretation depends on device-specific format
    """


class UartBootloaderSeq:
    UART_SEQ_STAY_IN_BL = [0x05, 0x31, 0xF6, 0xB9]

    UART_SEQ_ANSWER_TO_STAY_IN_BL = [0x06, 0xB1, 0x4E, 0xF9]


class UartBootloaderMemoryStates(IntEnum):
    UART_MEMORYSTATE_IDLE = 0x00

    UART_MEMORYSTATE_FLASH_FW_CRC_OK = 2

    UART_MEMORYSTATE_FLASH_FW_CRC_FAULT = 3

    UART_MEMORYSTATE_FW_CHECK_CRC32_FAULT = 4

    UART_MEMORYSTATE_FW_CHECK_CRC32_OK = 5

    UART_MEMORYSTATE_FLASH_FW_NULL = 12

    UART_MEMORYSTATE_FLASH_BSY = 255
