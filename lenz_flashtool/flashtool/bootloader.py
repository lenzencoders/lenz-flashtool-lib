r'''
 _     _____ _   _ _____   _____ _   _  ____ ___  ____  _____ ____  ____
| |   | ____| \ | |__  /  | ____| \ | |/ ___/ _ \|  _ \| ____|  _ \/ ___|
| |   |  _| |  \| | / /   |  _| |  \| | |  | | | | | | |  _| | |_) \___ \
| |___| |___| |\  |/ /_   | |___| |\  | |__| |_| | |_| | |___|  _ < ___) |
|_____|_____|_| \_/____|  |_____|_| \_|\____\___/|____/|_____|_| \_|____/


BootloaderMixin — Bootloader entry, firmware download, and IRS encoder bootloader operations.

Author:
    LENZ ENCODERS, 2020-2026
'''

import time
import logging
from typing import Optional, Any
import numpy as np
from ..biss import biss_commands, BiSSBank
from .uart import UartCmd, UartBootloaderCmd, UartBootloaderMemoryStates, UartBootloaderSeq
from .hex_utils import generate_hex_line, HexBlockExtractor
from ..utils.progress import percent_complete

logger = logging.getLogger(__name__)


class BootloaderMixin:
    """Mixin providing bootloader entry/exit, firmware download, and IRS encoder bootloader ops."""

    def biss_cmd_reboot2bl(self):
        """
        Sends the BiSS command to reboot the device into bootloader mode.

        Issues the 'reboot2bl' command to the BiSS encoder, initiating a reboot into bootloader
        mode for firmware updates. Note: This method is deprecated and should be replaced with `biss_write_command('reboot2bl')`.

        Returns:
            None

        Example:
            >>> ft = FlashTool()
            >>> ft.biss_cmd_reboot2bl()
            WARNING: Deprecated method. Use biss_write_command('reboot2bl') instead.
        """
        logger.debug("Sending reboot to bootloader command")
        command_code: int = biss_commands['reboot2bl'][0]
        command_list: list[int] = [command_code & 0xFF, (command_code >> 8) & 0xFF]
        self.biss_write_word(BiSSBank.CMD_REG_INDEX, command_list)
        time.sleep(0.5)

    def reboot_to_bl(self) -> None:
        """
        Reboot to BOOTLOADER FlashTool device.

        Sends a Reboot to Bootloader command to the FlashTool.

        Returns:
            None

        Example:
            >>> ft = FlashTool()
            >>> ft.reboot_to_bl()
        """
        logger.info('Sending REBOOT to BOOTLOADER command to FlashTool')
        tx_row = bytes.fromhex(generate_hex_line(
            address=0x0000,
            command=UartCmd.CMD_REBOOT_TO_BL,
            data=[0x00]
        )[1:])
        self._write_to_port(tx_row)
        time.sleep(0.01)

    def reboot_to_fw(self):
        """
        Reboot to FIRMWARE FlashTool device.

        Sends a Reboot to Firmware command to the FlashTool.

        Returns:
            None

        Example:
            >>> ft = FlashTool()
            >>> ft.reboot_to_fw()
        """
        logger.info('Sending REBOOT to FIRMWARE command to FlashTool')
        tx_row = bytes.fromhex(generate_hex_line(
            address=0x0000,
            command=UartBootloaderCmd.UART_COMMAND_RUN_PROGRAM,
            data=[0x00]
        )[1:])
        logger.debug(f"Sent BiSS Data: {tx_row.hex()}")
        self._write_to_port(tx_row)
        time.sleep(0.01)

    def read_fw_bl_ver(self) -> tuple[str, str]:
        """
        Read firmware and bootloader version from FlashTool device.

        Sends a command to read both firmware and bootloader versions from the device.
        The response contains 8 bytes where:

        * First 4 bytes represent firmware version
        * Last 4 bytes represent bootloader version

        Returns:
            tuple[str, str]: A tuple containing:
                - Firmware version as hexadecimal string (4 characters)
                - Bootloader version as hexadecimal string (4 characters)

        Example:
            >>> ft = FlashTool()
            >>> fw_ver, bl_ver = ft.read_fw_bl_ver()
            >>> print(f"Firmware: {fw_ver}, Bootloader: {bl_ver}")
            Firmware: 00010007, Bootloader: 00010002

        Note:
            - Each version is represented as 4-byte value in big-endian format
            - The function converts individual bytes to concatenated hexadecimal string
            - Requires device to be in bootloader mode
        """
        tx_row = bytes.fromhex(generate_hex_line(
            address=0x0000,
            command=UartBootloaderCmd.UART_COMMAND_READ_PROGRAM_BOOTLOADER_VER,
            data=[0x00]*8
        )[1:])
        logger.debug(f"Sent BiSS Data: {tx_row.hex()}")
        self._write_to_port(tx_row)
        response = self.port_read(len(tx_row) - 5)
        fw_ver = f"{response[0]:02X}{response[1]:02X}{response[2]:02X}{response[3]:02X}"
        bl_ver = f"{response[4]:02X}{response[5]:02X}{response[6]:02X}{response[7]:02X}"
        logger.info(f"Firmware version: {fw_ver}, Bootloader version: {bl_ver}")
        return fw_ver, bl_ver

    def read_memory_state_bl(self) -> UartBootloaderMemoryStates:
        """
        Read Memory State of FlashTool bootloader.

        Sends a Read Memory State command to FlashTool.

        Returns:
            UartBootloaderMemoryStates

        Example:
            >>> ft = FlashTool()
            >>> ft.read_memory_state_bl()
        """
        tx_row = bytes.fromhex(generate_hex_line(
            address=0x0000,
            command=UartBootloaderCmd.UART_COMMAND_READ_MEMORYSTATE,
            data=[0x00]
        )[1:])
        logger.debug(f"Sent BiSS Data: {tx_row.hex()}")
        self._write_to_port(tx_row)
        response = self.port_read(len(tx_row) - 5)
        state = self._decode_memory_state_bl(response)
        time.sleep(0.01)
        return state

    def _decode_memory_state_bl(self, response: np.ndarray) -> UartBootloaderMemoryStates:
        """
        Decode Memory State of FlashTool bootloader.

        Input:
            response: value from read_memory_state_bl

        Returns:
            UartBootloaderMemoryStates

        Example:
            >>> ft = FlashTool()
            >>> ft._decode_memory_state_bl(response)
            UartBootloaderMemoryStates
        """
        response = response[0]
        if response in {state.value for state in UartBootloaderMemoryStates}:
            matched_state = UartBootloaderMemoryStates(response)
            logger.debug(f"Response: {matched_state.name} (0x{response:02x})")
            if matched_state == UartBootloaderMemoryStates.UART_MEMORYSTATE_FLASH_FW_CRC_OK:
                logger.debug('Firmware CRC check passed!')
            elif matched_state == UartBootloaderMemoryStates.UART_MEMORYSTATE_FLASH_FW_CRC_FAULT:
                logger.error('Firmware CRC check failed!')
            elif matched_state == UartBootloaderMemoryStates.UART_MEMORYSTATE_IDLE:
                logger.debug('Uart state is IDLE!')
            elif matched_state == UartBootloaderMemoryStates.UART_MEMORYSTATE_FW_CHECK_CRC32_FAULT:
                logger.error('Firmware CRC check failed!')
            elif matched_state == UartBootloaderMemoryStates.UART_MEMORYSTATE_FW_CHECK_CRC32_OK:
                logger.debug('Firmware CRC check passed!')
        return matched_state

    def check_main_fw_crc32(self) -> None:
        """
        Compare calculated main FlashTool firmware crc32 with ProgramCRC32 value in flash.

        Input:
            None

        Returns:
            None

        Example:
            >>> ft = FlashTool()
            >>> ft.check_main_fw_crc32()
            'Response: UART_MEMORYSTATE_FW_CHECK_CRC32_OK (0x05)'
        """
        logger.info('Sending check main firmware CRC32 command to FlashTool')
        tx_row = bytes.fromhex(generate_hex_line(
            address=0x0000,
            command=UartBootloaderCmd.UART_COMMAND_CHECK_PROGRAM_CRC32,
            data=[0x00]
        )[1:])
        logger.debug(f"Sent BiSS Data: {tx_row.hex()}")
        self._write_to_port(tx_row)
        self.read_memory_state_bl()

    def download_fw_to_ft(self, hex_file_path: str, max_retries: int = 3, pbar: Optional[Any] = None):
        """
        Download main firmware from HEX file to FlashTool device using bootloader protocol.

        Implements a robust flash programming routine with:
        - Automatic CRC verification
        - Retry mechanism for failed pages
        - Progress tracking
        - Error recovery

        Protocol Flow:
        1. For each 2KB block in HEX file:
        1.a. Send block's CRC32 checksum first
        1.b. Transfer data in 64-byte chunks
        1.c. Verify flash operation success
        1.d. Retry on failure (up to max_retries)
        2. Handle both successful and error cases gracefully

        Args:
            hex_file_path (str): Path to Intel HEX format firmware file
            max_retries (int): Maximum retry attempts per page (default: 3)

        Raises:
            RuntimeError: When exceeding max retries for a page
            IOError: For file access problems
            ValueError: For invalid HEX file format
            Exception: For communication errors with device

        Returns:
            None: Success is implied by normal completion

        Side Effects:
            - Programs firmware to target device flash
            - Modifies device memory state
            - May reset communication interface

        Example:
            >>> tool = FlashTool()
            >>> tool.download_fw_to_ft("firmware_v1.2.hex")

        Notes:
            - Requires active bootloader connection
            - Uses 2KB page size (device-specific)
            - 64-byte chunk size optimized for UART throughput
            - Includes mandatory 1s delay after programming
            - CRC verification is mandatory for each page
        """
        extractor = HexBlockExtractor()
        retry_count = 0
        total_pages = 12  # Default value
        metadata_total_pages = 1

        try:
            first_block_start, first_block_data, _ = next(extractor.process_hex_file(hex_file_path))
            first_lower_addr = first_block_start & 0xFFFF
            first_page_number = first_lower_addr // 2048

            # Extract ProgramLen from metadata (offset 0x0C, 4 bytes)
            if len(first_block_data) >= 0x0C + 4:
                program_len_bytes = first_block_data[0x0C:0x0C+4]
                program_total_pages = int.from_bytes(program_len_bytes, byteorder='little')
                logger.info(f"Extracted program total pages from metadata: {program_total_pages}")

            # Extract BootloaderLen from metadata (offset 0x1C, 4 bytes)
            if len(first_block_data) >= 0x1C + 4:
                program_len_bytes = first_block_data[0x1C:0x1C+4]
                bootloader_total_pages = int.from_bytes(program_len_bytes, byteorder='little')
                logger.info(f"Extracted bootloader total pages from metadata: {bootloader_total_pages}")

            total_pages = program_total_pages + bootloader_total_pages + metadata_total_pages
            logger.info(f"Extracted total pages from metadata: {total_pages}")

            for block_start, block_data, block_crc in extractor.process_hex_file(hex_file_path):
                lower_addr = block_start & 0xFFFF
                page_number = lower_addr // 2048
                count_pages = page_number - first_page_number + 1
                success = False

                while not success and retry_count < max_retries:
                    try:
                        # 1. Send CRC Record
                        crc_bytes = [
                            (block_crc >> 24) & 0xFF,
                            (block_crc >> 16) & 0xFF,
                            (block_crc >> 8) & 0xFF,
                            block_crc & 0xFF
                        ]
                        crc_line = generate_hex_line(
                            address=0x0000,
                            command=UartBootloaderCmd.UART_COMMAND_WRITE_CURRENT_PAGE_CRC32,
                            data=crc_bytes
                        )
                        self.hex_line_send(crc_line)

                        # 2. Send Data Records in 64-byte chunks
                        for offset in range(0, len(block_data), 64):
                            chunk = block_data[offset:offset+64]
                            chunk_addr = (0x01 << 8) | ((page_number) & 0xFF)
                            data_line = generate_hex_line(
                                address=chunk_addr,
                                command=UartBootloaderCmd.UART_COMMAND_LOAD_2K,
                                data=list(chunk)
                            )
                            self.hex_line_send(data_line)

                        if pbar:
                            percent_complete(count_pages, total_pages, title=f"Sending Page {count_pages}")
                        # 3. Wait for flash 2048 bytes operation to complete
                        time.sleep(1)

                        # 4. Verify CRC32 check
                        matched_state = self.read_memory_state_bl()
                        if matched_state == UartBootloaderMemoryStates.UART_MEMORYSTATE_FLASH_FW_CRC_FAULT:
                            retry_count += 1
                            logger.error(f"CRC Error on page {count_pages}, retry {retry_count}/{max_retries}")
                            if retry_count >= max_retries:
                                raise RuntimeError(f"Max retries ({max_retries}) exceeded for page {count_pages}")
                            continue
                        elif matched_state == UartBootloaderMemoryStates.UART_MEMORYSTATE_FLASH_FW_CRC_OK:
                            success = True
                            retry_count = 0
                        else:
                            raise RuntimeError(f"Unexpected memory state: {matched_state.name}")

                    except Exception as e:
                        retry_count += 1
                        logger.error(f"Error on page {count_pages}, retry {retry_count}/{max_retries}: {str(e)}")
                        if retry_count >= max_retries:
                            raise RuntimeError(f"Max retries ({max_retries}) exceeded for page {count_pages}")
                        time.sleep(1)
                        continue

        except Exception as e:
            print(f"Fatal error during firmware upload: {str(e)}")
            raise
        print(end="\n")
        self.check_main_fw_crc32()
        time.sleep(0.05)

    def enter_bl_biss_encoder(self, reset_attempts: int = 12, power_cycle_delay: float = 0.01) -> bool:
        """
        Reset the BISS encoder to bootloader mode by power cycling.

        This method performs multiple power cycles to force the encoder
        into bootloader mode. The bootloader mode is indicated by specific
        error flags being set in the encoder's status register.

        Bootloader Mode Indicators:
        - The presence of ['FLAGS_STARTUP_ERROR'] flags typically indicates
        successful entry into bootloader mode.

        Args:
            reset_attempts (int): Number of power cycle attempts (default: 12)
            power_cycle_delay (float): Delay between power cycles in seconds (default: 0.01)

        Returns:
            bool: True if encoder entered bootloader mode (startup error flags detected),
                False otherwise.
        """
        initial_flags, initial_cmd_state = self.biss_read_flags()

        for attempt in range(reset_attempts):
            self.encoder_power_off()
            time.sleep(power_cycle_delay)
            self.encoder_power_on()
            time.sleep(power_cycle_delay)

        final_flags, final_cmd_state = self.biss_read_flags()

        bootloader_entered = 'FLAGS_STARTUP_ERROR' in final_flags

        logger.info("Encoder enter bootloader %s", "successful" if bootloader_entered else "failed")
        return bootloader_entered

    def enter_bl_irs(self) -> bool:
        """
        Enter bootloader of IRS encoder and verify successful connection.

        Workflow:
        - Selects SPI channel 2 for IRS encoder communication
        - Sets flashtool mode to 'spi_uart_irs' for proper protocol configuration
        - Powers off the encoder briefly (100ms) then powers it back on
        - Sends the bootloader stay command sequence
        - Validates the encoder's response against expected bootloader acknowledgment

        Args:
            None

        Returns:
            bool: True if the encoder successfully enters bootloader mode and responds
              correctly, False otherwise.

        Example:
            >>> encoder_handler.reboot_to_bl_irs()
            True  # Encoder successfully entered bootloader mode
        """
        try:
            self.select_spi_channel('channel2')
            self.select_flashtool_mode('spi_uart_irs')
            self.encoder_power_off()
            time.sleep(0.1)
            self.encoder_power_on()
            time.sleep(0.01)

            tx_row = bytes.fromhex(generate_hex_line(
                address=0x0000,
                command=UartCmd.HEX_IRS_ENC_WRITE_READ_CMD,
                data=UartBootloaderSeq.UART_SEQ_STAY_IN_BL,
            )[1:])
            self._write_to_port(tx_row)

            enc_ans = self.port_read(len(tx_row)-1)
            if enc_ans is None or len(enc_ans) == 0:
                logger.error("No response from IRS encoder!")
                return False

            expected_ans = np.array(UartBootloaderSeq.UART_SEQ_ANSWER_TO_STAY_IN_BL, dtype=np.uint8)

            if np.array_equal(expected_ans, enc_ans):
                logger.info("IRS Encoder enter bootloader successfully!")
                return True
            else:
                logger.error("Failed to enter IRS bootloader! Unexpected response.")
                logger.debug(f"Expected: {expected_ans.tobytes().hex()}")
                logger.debug(f"Received: {enc_ans.tobytes().hex()}")
                return False

        except Exception as e:
            logger.error(f"An exception occurred while connecting to encoder: {e}")
            return False

    def enter_fw_irs(self) -> bool:
        """
        Exit bootloader and reboot the IRS encoder into normal firmware operation.

        Workflow:
        - Selects SPI channel 2 and configures 'spi_uart_irs' communication mode
        - Cycles encoder power to ensure clean state transition
        - Sends the bootloader exit command sequence
        - Validates the encoder's acknowledgment of bootloader exit
        - Always restores the flashtool to default SPI mode as cleanup

        Returns:
            bool: True if the encoder successfully exits bootloader mode and responds
              correctly, False otherwise. The system is always returned to default
              SPI mode regardless of the result.

        Example:
            >>> encoder_handler.reboot_to_fw_irs()
            True  # Encoder successfully exited bootloader and returned to firmware mode
        """
        def _cleanup_and_return(success: bool) -> bool:
            self.select_flashtool_mode('default_spi')
            return success

        try:
            self.select_spi_channel('channel2')
            self.select_flashtool_mode('spi_uart_irs')
            self.encoder_power_off()
            time.sleep(0.1)
            self.encoder_power_on()
            time.sleep(0.01)
            tx_row = bytes.fromhex(generate_hex_line(
                address=0x0000,
                command=UartCmd.HEX_IRS_ENC_WRITE_READ_CMD,
                data=UartBootloaderSeq.UART_SEQ_EXIT_BL,
            )[1:])
            self._write_to_port(tx_row)

            enc_ans = self.port_read(len(tx_row)-1)

            if enc_ans is None or len(enc_ans) == 0:
                logger.error("No response from IRS encoder!")
                return _cleanup_and_return(False)

            expected_ans = np.array(UartBootloaderSeq.UART_SEQ_ANSWER_TO_EXIT_BL, dtype=np.uint8)

            if np.array_equal(expected_ans, enc_ans):
                logger.info("IRS Encoder disconnect from bootloader successfully!")
                return _cleanup_and_return(True)
            else:
                logger.error("Failed to disconnect bootloader! Unexpected response.")
                logger.debug(f"Expected: {expected_ans.hex()}")
                logger.debug(f"Received: {enc_ans.hex()}")
                return _cleanup_and_return(False)

        except Exception as e:
            logger.error(f"An exception occurred while disconnecting from bootloader: {e}")
            return _cleanup_and_return(False)

    def set_pos_irs(self, deg: float, reverse: bool = False) -> tuple:
        """
        Set IRS encoder position.

        Args:
            deg (float): Desired angle in degrees (0 to 360).
            reverse (bool): If True, use reverse direction mode.

        Returns:
            tuple: (b_1, b_2) or (None, None) on failure.
        """
        if not (0 <= deg <= 360):
            logger.error(f"Invalid angle {deg}. Must be between 0 and 360 degrees.")
            return None, None

        # Mode configuration
        offset = 13 if reverse else 5
        cmd_byte = 14 if reverse else 6
        checksum_base = 242 if reverse else 250

        try:
            data = np.int32((deg / 360 * 4096) % 4096)
            b_2 = np.uint8(data >> 4)
            b_1 = np.uint8(data << 4) | offset

            if not self.enter_bl_irs():
                logger.error("Failed to connect to bootloader of IRS encoder!")
                return None, None

            set_pos_cmd = bytearray([0, b_1, b_2, cmd_byte,
                                    np.uint8(checksum_base - b_1 - b_2)])
            logger.debug(f"Sending {'reverse' if reverse else 'forward'} command: {set_pos_cmd.hex().upper()}")

            tx = bytes.fromhex(generate_hex_line(
                address=0x0000,
                command=UartCmd.HEX_IRS_ENC_WRITE_READ_CMD,
                data=set_pos_cmd,
            )[1:])
            self._write_to_port(tx)

            enc_ans = self.port_read(len(tx) - UartCmd.PKG_INFO_LENGTH)

            if enc_ans is None:
                logger.error("No response from IRS encoder!")
                return None, None

            if not self.enter_fw_irs():
                logger.error("Failed to exit bootloader mode of IRS encoder!")
                return None, None

            return b_1, b_2

        except Exception as e:
            logger.error(f"Exception while setting IRS encoder position: {e}")
            return None, None
