r'''
 _     _____ _   _ _____   _____ _   _  ____ ___  ____  _____ ____  ____
| |   | ____| \ | |__  /  | ____| \ | |/ ___/ _ \|  _ \| ____|  _ \/ ___|
| |   |  _| |  \| | / /   |  _| |  \| | |  | | | | | | |  _| | |_) \___ \
| |___| |___| |\  |/ /_   | |___| |\  | |__| |_| | |_| | |___|  _ < ___) |
|_____|_____|_| \_/____|  |_____|_| \_|\____\___/|____/|_____|_| \_|____/


EncoderControlMixin — Encoder power, reset, and mode selection.

Author:
    LENZ ENCODERS, 2020-2026
'''


import time
import logging
from typing import Literal
from .uart import UartCmd
from .hex_utils import generate_hex_line

logger = logging.getLogger(__name__)


class EncoderControlMixin:
    """Mixin providing encoder power control, FlashTool reset, and mode/channel selection."""

    def encoder_power_off(self) -> None:
        """
        Powers off the encoder on channel 2.

        Sends a POWER_OFF command to the BiSS encoder connected to channel 2 of the FlashTool device.

        Returns:
            None

        Example:
            >>> ft = FlashTool()
            >>> ft.encoder_power_off()
        """
        logger.debug('Sending POWER_OFF command to the encoder')
        tx_row = bytes.fromhex(generate_hex_line(0, UartCmd.CMD_POWER_OFF, [0])[1:])
        self._write_to_port(tx_row)

    def encoder_power_on(self) -> None:
        """
        Powers on the encoder on channel 2.

        Sends a POWER_ON command to the BiSS encoder connected to channel 2 of the FlashTool device.

        Returns:
            None

        Example:
            >>> ft = FlashTool()
            >>> ft.encoder_power_on()
        """
        logger.debug('Sending POWER_ON command to the encoder')
        tx_row = bytes.fromhex(generate_hex_line(0, UartCmd.CMD_POWER_ON, [0])[1:])
        self._write_to_port(tx_row)

    def encoder_ch1_power_off(self) -> None:
        """
        Powers off the encoder on channel 1.

        Sends a POWER_OFF command to the BiSS encoder connected to channel 1 of the FlashTool device.

        Returns:
            None

        Example:
            >>> ft = FlashTool()
            >>> ft.encoder_ch1_power_off()
        """
        logger.debug('Sending POWER_OFF command to the encoder')
        tx_row = bytes.fromhex(generate_hex_line(0, UartCmd.CMD_CH1_POWER_OFF, [0])[1:])
        self._write_to_port(tx_row)

    def encoder_ch1_power_on(self) -> None:
        """
        Powers on the encoder on channel 1.

        Sends a POWER_ON command to the BiSS encoder connected to channel 1 of the FlashTool device.

        Returns:
            None

        Example:
            >>> ft = FlashTool()
            >>> ft.encoder_ch1_power_on()
        """
        logger.debug('Sending POWER_ON command to the encoder')
        tx_row = bytes.fromhex(generate_hex_line(0, UartCmd.CMD_CH1_POWER_ON, [0])[1:])
        logger.debug(tx_row.hex())
        self._write_to_port(tx_row)

    def encoder_power_cycle(self) -> None:
        """
        Performs a power cycle on the encoder on channel 2.

        Powers off the encoder, waits 0.1 seconds, powers it back on, and waits another 0.1 seconds to ensure stabilization.

        Returns:
            None

        Example:
            >>> ft = FlashTool()
            >>> ft.encoder_power_cycle()
        """
        self.encoder_power_off()
        time.sleep(0.1)
        self.encoder_power_on()
        time.sleep(0.1)
        logger.debug('Performed power cycle to the encoder.')

    def encoder_ch1_power_cycle(self) -> None:
        """
        Performs a power cycle on the encoder on channel 1.

        Powers off the encoder, waits 0.1 seconds, powers it back on, and waits another 0.1 seconds to ensure stabilization.

        Returns:
            None

        Example:
            >>> ft = FlashTool()
            >>> ft.encoder_ch1_power_cycle()
        """
        self.encoder_ch1_power_off()
        time.sleep(0.1)
        self.encoder_ch1_power_on()
        time.sleep(0.1)
        logger.debug('Performed power cycle to the encoder.')

    def flashtool_rst(self) -> None:
        """
        Resets the FlashTool device.

        Sends a RESET command to the FlashTool, reinitializing its internal state.

        Returns:
            None

        Example:
            >>> ft = FlashTool()
            >>> ft.flashtool_rst()
        """
        logger.info('Sending RESET command to FlashTool')
        tx_row = bytes.fromhex(generate_hex_line(0, UartCmd.CMD_NVRST, [0])[1:])
        self._write_to_port(tx_row)
        time.sleep(0.01)

    def select_spi_channel(self, channel: Literal["channel1", "channel2"]) -> None:
        """
        Select SPI communication channel.

        Sends a SELECT CHANNEL command to the FlashTool.

        There are two channels:
            channel1;
            channel2.

        Args:
            channel: "channel1" or "channel2".

        Returns:
            None

        Raises:
            ValueError: If the mode is not channel1 or channel2.

        Example:
            >>> ft = FlashTool()
            >>> ft.select_SPI_channel('channel1')
        """
        channel_mapping = {
            "channel1": (0, "CHANNEL 1"),
            "channel2": (1, "CHANNEL 2")
        }

        if channel not in channel_mapping:
            raise ValueError(f'Invalid channel: "{channel}". Must be "channel1" or "channel2".')

        channel_num, channel_desc = channel_mapping[channel]
        logger.info(f"Selected Channel: {channel_num} - {channel_desc}")

        tx_row = bytes.fromhex(generate_hex_line(0, UartCmd.CMD_SELECT_SPI_CH, [channel_num])[1:])
        self._port.reset_output_buffer()
        self._port.write(tx_row)
        self._port.flush()

    def select_flashtool_mode(self, mode: Literal["spi_spi", "ab_uart", "spi_uart_irs", "ab_spi", "default_spi"]) -> None:
        """
        Select FlashTool communication mode.

        Sends a SELECT FLASHTOOL MODE command to configure the communication protocol
        for both channels of the FlashTool.

        Available modes:
            "spi_spi"      - Channel 1: SPI, Channel 2: SPI
            "ab_uart"      - Channel 1: AB signal, Channel 2: UART
            "spi_uart_irs" - Channel 1: SPI, Channel 2: UART for IRS encoders
            "ab_spi"       - Channel 1: AB signal, Channel 2: SPI
            "default_spi"  - Default mode: Channel 1: None, Channel 2: SPI

        Args:
            mode: Communication mode as descriptive string:
                - "spi_spi"      (0: BISS_MODE_SPI_SPI)
                - "ab_uart"      (1: BISS_MODE_AB_UART)
                - "spi_uart_irs" (2: BISS_MODE_SPI_UART_IRS)
                - "ab_spi"       (3: BISS_MODE_AB_SPI)
                - "default_spi"  (4: BISS_MODE_DEFAULT_SPI)

        Returns:
            None

        Raises:
            ValueError: If invalid mode string provided

        Example:
            >>> ft = FlashTool()
            >>> ft.select_flashtool_mode("spi_spi")  # Sets SPI on both channels
            >>> ft.select_flashtool_mode("spi_uart_irs")  # Sets SPI + UART for IRS
        """
        mode_mapping = {
            "spi_spi": (0, "BISS_MODE_SPI_SPI"),
            "ab_uart": (1, "BISS_MODE_AB_UART"),
            "spi_uart_irs": (2, "BISS_MODE_SPI_UART_IRS"),
            "ab_spi": (3, "BISS_MODE_AB_SPI"),
            "default_spi": (4, "BISS_MODE_DEFAULT_SPI")
        }

        if mode not in mode_mapping:
            valid_modes = list(mode_mapping.keys())
            raise ValueError(f'Invalid mode: "{mode}". Must be one of: {valid_modes}')

        mode_num, mode_desc = mode_mapping[mode]
        logger.info(f"Selected FlashTool mode: {mode_num} - {mode_desc}")

        tx_row = bytes.fromhex(generate_hex_line(0, UartCmd.CMD_SELECT_FLASHTOOL_MODE, [mode_num])[1:])
        self._port.reset_output_buffer()
        self._port.write(tx_row)
        self._port.flush()
        time.sleep(0.05)

    def select_FlashTool_current_sensor_mode(self, mode: Literal["disable", "enable"]) -> None:
        """
        Select FlashTool Current sensor mode.

        Sends a SELECT Current sensor mode command to the FlashTool.

        Available modes:
            "disable" - CURRENT_SENSOR_MODE_DISABLE (0)
            "enable"  - CURRENT_SENSOR_MODE_ENABLE (1)

        Args:
            mode: Current sensor mode as descriptive string:
                - "disable" (0: CURRENT_SENSOR_MODE_DISABLE)
                - "enable"  (1: CURRENT_SENSOR_MODE_ENABLE)

        Returns:
            None

        Raises:
            ValueError: If invalid mode string provided

        Example:
            >>> ft = FlashTool()
            >>> ft.select_FlashTool_current_sensor_mode("disable")
            >>> ft.select_FlashTool_current_sensor_mode("enable")
        """
        mode_mapping = {
            "disable": (0, "CURRENT_SENSOR_MODE_DISABLE"),
            "enable": (1, "CURRENT_SENSOR_MODE_ENABLE")
        }

        if mode not in mode_mapping:
            valid_modes = list(mode_mapping.keys())
            raise ValueError(f'Invalid mode: "{mode}". Must be one of: {valid_modes}')

        mode_num, mode_desc = mode_mapping[mode]
        logger.info(f"Selected current sensor mode: {mode_num} - {mode_desc}")

        tx_row = bytes.fromhex(generate_hex_line(0, UartCmd.CMD_SELECT_FLASHTOOL_CURRENT_SENSOR_MODE, [mode_num])[1:])
        logger.debug(f"Current sensor mode command: {tx_row.hex()}")
        self._port.reset_output_buffer()
        self._port.write(tx_row)
        self._port.flush()

    def select_spi_ch1_mode(self, mode: Literal["lenz_biss", "lir_ssi", "lir_biss_21b"]) -> None:
        """
        Select SPI channel 1 mode.

        Sends a SELECT channel 1 SPI mode command to the FlashTool.

        Available modes:
            "lenz_biss"    - CH1_LENZ_BISS (0)
            "lir_ssi"      - CH1_LIR_SSI (1)
            "lir_biss_21b" - CH1_LIR_BISS_21B (2)

        Args:
            mode: SPI channel 1 mode as descriptive string:
                - "lenz_biss"    (0: CH1_LENZ_BISS)
                - "lir_ssi"      (1: CH1_LIR_SSI)
                - "lir_biss_21b" (2: CH1_LIR_BISS_21B)

        Returns:
            None

        Raises:
            ValueError: If invalid mode string provided

        Example:
            >>> ft = FlashTool()
            >>> ft.select_spi_ch1_mode("lenz_biss")
            >>> ft.select_spi_ch1_mode("lir_ssi")
        """
        mode_mapping = {
            "lenz_biss": (0, "CH1_LENZ_BISS"),
            "lir_ssi": (1, "CH1_LIR_SSI"),
            "lir_biss_21b": (2, "CH1_LIR_BISS_21B")
        }

        if mode not in mode_mapping:
            valid_modes = list(mode_mapping.keys())
            raise ValueError(f'Invalid mode: "{mode}". Must be one of: {valid_modes}')

        mode_num, mode_desc = mode_mapping[mode]
        logger.info(f"Selected SPI channel 1 Mode: {mode_num} - {mode_desc}")

        tx_row = bytes.fromhex(generate_hex_line(0, UartCmd.CMD_SELECT_CH1_MODE, [mode_num])[1:])
        self._port.reset_output_buffer()
        self._port.write(tx_row)
        self._port.flush()
