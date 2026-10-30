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
from dataclasses import dataclass
from typing import Dict, Literal, Optional, Tuple, List
from datetime import datetime, timezone
from ..biss import BiSSBank
from .uart import UartCmd
from .hex_utils import generate_hex_line
from .errors import FlashToolError

logger = logging.getLogger(__name__)


RESOLUTION_MAP: Dict[int, str] = {
    0: "17-bit", 1: "18-bit", 2: "19-bit", 3: "20-bit",
    4: "18-bit", 5: "22-bit", 6: "23-bit", 7: "24-bit",
}
"""REV_RES HystRes field (bits 27:25) code → resolution label. Used by
``FlashTool.set_resolution_and_direction`` and the CLI register-dump decoder."""


_BITS_TO_HYST_RES: Dict[int, int] = {
    17: 0, 18: 1, 19: 2, 20: 3, 22: 5, 23: 6, 24: 7,
}


@dataclass(frozen=True)
class DetectedSensor:
    """Result of ``detect_sensor``.
    
    Attributes:
        mode: FlashTool mode string (``"spi_spi"`` or ``"ab_uart"``).
        channel: Channel string (``"channel1"`` or ``"channel2"``).
        serial_number: Tuple ``(ver, sn, date, program)`` decoded from
            ``biss_read_snum``. ``None`` if the sensor did not respond.
        is_uart: ``True`` for ``ab_uart`` (UART sensor), ``False`` for
            ``spi_spi`` (SPI sensor)
    """
    mode: str               # "spi_spi" | "ab_uart"
    channel: str            # "channel1" | "channel2"
    serial_number: Optional[Tuple[str, str, str, str]]
    is_uart: bool           # True for ab_uart, False for spi

    @property
    def is_spi(self) -> bool:
        """Convenience: True for SPI sensors (``spi_spi``)."""
        return not self.is_uart

    @property
    def sn(self) -> Optional[str]:
        """Human-readable serial number, e.g. '2K8010'."""
        if self.serial_number is None:
            return None
        try:
            raw = bytes.fromhex(self.serial_number[1])
        except (ValueError, TypeError, IndexError):
            return None
        if len(raw) != 4:
            return None
        # First two bytes: ASCII prefix.
        try:
            prefix = raw[:2].decode("ascii")
        except UnicodeDecodeError:
            # If the prefix is not valid ASCII, fall back to hex for all bytes.
            return raw.hex().upper()
        # Remaining bytes: keep as uppercase hex.
        suffix = raw[2:].hex().upper()
        return prefix + suffix

    @property
    def mfg_date(self) -> Optional[datetime]:
        """Manufacturing date as a UTC datetime, or None."""
        if self.serial_number is None:
            return None
        try:
            return datetime.fromtimestamp(
                int(self.serial_number[2], 16), tz=timezone.utc
            )
        except (ValueError, TypeError, OSError, OverflowError):
            return None

    @property
    def program(self) -> Optional[str]:
        """Program version, e.g. '01.01.05.25'."""
        if self.serial_number is None:
            return None
        try:
            return ".".join(
                f"{b:02d}" for b in bytes.fromhex(self.serial_number[3])[::-1]
            )
        except (ValueError, TypeError):
            return None

    @property
    def bootloader(self) -> Optional[str]:
        """Bootloader version, e.g. '01.00.01.00'."""
        if self.serial_number is None:
            return None
        try:
            return ".".join(
                f"{b:02d}" for b in bytes.fromhex(self.serial_number[0])[::-1]
            )
        except (ValueError, TypeError):
            return None

    def __str__(self) -> str:
        kind = "UART" if self.is_uart else "SPI"
        if self.mfg_date is not None:
            mfg = self.mfg_date.strftime("%Y-%m-%d %H:%M:%S")
        else:
            mfg = "?"
        return (
            f"{kind} sensor on {self.mode}/{self.channel} "
            f"(SN={self.sn or '?'}, "
            f"Mfg={mfg}, "
            f"Program={self.program or '?'}, "
            f"Bootloader={self.bootloader or '?'})"
        )



_MODE_CANDIDATES: List[Tuple[str, bool, List[str]]] = [
    ("spi_spi", False, ["channel2", "channel1"]),
    ("ab_uart", True,  ["channel2"]),
]

class EncoderControlMixin:
    """Mixin providing encoder power control, FlashTool reset, and mode/channel selection."""


    def detect_sensor(
        self,
        status: bool = True,
        settle_s: float = 0.5,
        retry_per_combo: int = 2,
        power_cycle_on_retry: bool = True,
    ) -> Optional[DetectedSensor]:
        """
        Probe every (mode, channel) combination and return the first one
        that answers ``biss_read_snum`` with a valid serial number.

        Combinations tried, in order:
            spi_spi / channel2
            spi_spi / channel1
            ab_uart / channel2

        ``ab_uart`` is only probed on ``channel2`` — the UART sensor is
        wired to USART2 and channel1 is not used in that mode.

        On failure, the firmware is reset via ``flashtool_rst()`` and (if
        ``power_cycle_on_retry``) the encoder on the current channel is
        power-cycled before retrying the same combination.

        Args:
            status: If True, log each attempt at INFO level; if False, only
                log the final result and errors.
            settle_s: Seconds to wait after a mode switch before probing.
            retry_per_combo: How many times to retry a single (mode, channel)
                combination.
            power_cycle_on_retry: If True, power-cycle the encoder on the
                current channel after a failed attempt.

        Returns:
            DetectedSensor if a sensor was found, None otherwise. The
            FlashTool is left in the detected mode/channel on success;
            on failure the original mode/channel is restored.

        Example:
            >>> ft = FlashTool()
            >>> sensor = ft.detect_sensor()
            >>> if sensor:
            ...     print(sensor.mode, sensor.channel, sensor.serial_number)
            spi_spi channel2 ('0100', '12345678', '20230101', '0200')
        """
        logger.info("Detecting sensor...")

        original_mode = getattr(self, "_current_mode", None)
        original_channel = getattr(self, "_current_channel", None)

        def _recover(channel: str) -> None:
            """Reset the firmware and (optionally) power-cycle the encoder."""
            try:
                logger.debug("Recovering: firmware reset")
                self.flashtool_rst()
                time.sleep(0.3)
            except Exception as exc:
                logger.warning("Firmware reset failed: %s", exc)
            if power_cycle_on_retry:
                try:
                    logger.debug("Recovering: power cycle on %s", channel)
                    if channel == "channel1":
                        self.encoder_ch1_power_cycle()
                    else:
                        self.encoder_power_cycle()
                except Exception as exc:
                    logger.warning("Power cycle on %s failed: %s", channel, exc)

        try:
            for mode, is_uart, channels in _MODE_CANDIDATES:
                for channel in channels:
                    for attempt in range(retry_per_combo):
                        # Detailed attempt log only when `status` is on.
                        log_attempt = logger.info if status else logger.debug
                        log_attempt(
                            "[%s/%s] attempt %d/%d",
                            mode, channel, attempt + 1, retry_per_combo,
                        )
                        try:
                            self.select_flashtool_mode(mode)
                            self.select_spi_channel(channel)
                            time.sleep(settle_s)

                            sn = self.biss_read_snum()
                            if sn is not None:
                                sensor = DetectedSensor(
                                    mode=mode,
                                    channel=channel,
                                    serial_number=sn,
                                    is_uart=is_uart,
                                )
                                return sensor

                            logger.debug("[%s/%s] no reply", mode, channel)

                        except FlashToolError as exc:
                            logger.debug(
                                "[%s/%s] error: %s", mode, channel, exc,
                            )

                        if attempt + 1 < retry_per_combo:
                            _recover(channel)

            logger.warning("No sensor detected in any mode/channel")
            return None

        finally:
            if original_mode is not None and original_channel is not None:
                try:
                    logger.debug(
                        "Restoring original mode/channel: %s/%s",
                        original_mode, original_channel,
                    )
                    self.select_flashtool_mode(original_mode)
                    self.select_spi_channel(original_channel)
                except Exception as exc:
                    logger.warning(
                        "Failed to restore mode/channel %s/%s: %s",
                        original_mode, original_channel, exc,
                    )

    def set_resolution_and_direction(
        self,
        bits: int = 24,
        direction: Literal["CW", "CCW"] = "CW",
    ) -> None:
        """
        Configures encoder resolution and rotation direction, persists to flash, and power-cycles.

        Writes the REV_RES register (``BiSSBank.REV_RES_REG_INDEX``, 0x54) with the
        requested HystRes / CvCfg combination and runs the full
        ``unlocksetup → unlockflash → write → saveflash → power_cycle`` sequence
        so the new configuration is active on return.

        Register layout (32-bit word):
            bits 31:28 — reserved (0)
            bits 27:25 — HystRes (resolution code)
            bit  24    — CvCfg: 0 = CW-increasing, 1 = CCW-increasing
            bits 23:0  — OutDif (written as 0)

        Args:
            bits: Resolution in bits. Accepted: 17, 18, 19, 20, 22, 23, 24. Defaults to 24.
            direction: "CW" (default) or "CCW".

        Raises:
            ValueError: If ``bits`` or ``direction`` is outside the supported set.

        Example:
            >>> ft.set_resolution_and_direction()                # 24-bit, CW (defaults)
            >>> ft.set_resolution_and_direction(bits=22)         # 22-bit, CW
            >>> ft.set_resolution_and_direction(24, "CCW")       # 24-bit, CCW
        """
        if bits not in _BITS_TO_HYST_RES:
            raise ValueError(
                f"Unsupported resolution: {bits}. "
                f"Supported: {sorted(_BITS_TO_HYST_RES)} bits."
            )
        if direction not in ("CW", "CCW"):
            raise ValueError(f'Direction must be "CW" or "CCW", got {direction!r}')

        hyst_res = _BITS_TO_HYST_RES[bits]
        cv_cfg = 0 if direction == "CW" else 1
        value = (hyst_res << 25) | (cv_cfg << 24)

        logger.info(
            "Setting encoder: %d-bit %s (REV_RES = 0x%08X)",
            bits, direction, value,
        )

        self.biss_write_command('unlocksetup')
        self.biss_write_command('unlockflash')
        self.biss_write_word(BiSSBank.REV_RES_REG_INDEX, value)
        self.biss_write_command('saveflash')
        time.sleep(0.2)
        self.encoder_power_cycle()

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
        self._write_to_port(tx_row)
        try:
            self._check_write_response(0.005)
        except FlashToolError as exc:
            logger.error("Channel switch to %r failed: %s", channel, exc)
            raise

        self._current_channel = channel

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
        self._write_to_port(tx_row)
        time.sleep(0.5)
        try:
            self._check_write_response(0.005)
        except FlashToolError as exc:
            logger.error("Mode switch to %r failed: %s", mode, exc)
            raise

        self._current_mode = mode

    def select_flashtool_current_sensor_mode(self, mode: Literal["disable", "enable"]) -> None:
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
        self._write_to_port(tx_row)
        try:
            self._check_write_response(0.005)
        except FlashToolError as exc:
            logger.error("Current sensor mode switch to %r failed: %s", mode, exc)
            raise

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
