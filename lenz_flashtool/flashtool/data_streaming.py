r'''
 _     _____ _   _ _____   _____ _   _  ____ ___  ____  _____ ____  ____
| |   | ____| \ | |__  /  | ____| \ | |/ ___/ _ \|  _ \| ____|  _ \/ ___|
| |   |  _| |  \| | / /   |  _| |  \| | |  | | | | | | |  _| | |_) \___ \
| |___| |___| |\  |/ /_   | |___| |\  | |__| |_| | |_| | |___|  _ < ___) |
|_____|_____|_| \_/____|  |_____|_| \_|\____\___/|____/|_____|_| \_|____/


DataStreamingMixin — Encoder data acquisition and angle readout.

Author:
    LENZ ENCODERS, 2020-2026
'''


import time
import logging
from typing import List, Tuple
import numpy as np
from ..biss import biss_crc6_calc
from .uart import UartCmd
from .hex_utils import calculate_checksum, generate_byte_line, generate_hex_line

logger = logging.getLogger(__name__)


class DataStreamingMixin:
    """Mixin providing encoder data streaming, angle readout, and current measurement."""

    def read_data(self, read_time: float) -> np.ndarray:
        """
        Reads encoder data via SPI over USB for a specified duration.

        Sends a command to read data, collects incoming packets, validates them with checksums,
        and extracts encoder values. Prints progress indicators during reading.

        Args:
            read_time: The duration in seconds to read data.

        Returns:
            np.ndarray: A NumPy array of int32 values containing the encoder readings.

        Raises:
            ValueError: If a checksum or command error occurs in the received data.

        Example:
            >>> ft = FlashTool()
            >>> data = ft.read_data(2.0)
            Read USB data for 2.0 seconds: ..... OK!
            >>> print(data)
            array([12345, 12346, ...], dtype=int32)
        """
        print('Read USB data for ', read_time, ' seconds: ', end='')
        size = int(read_time * 500)
        size_l = int(size) % 256
        size_m = int(size / 256) % 256
        self._port.flushInput()
        start_time = time.time()
        self._write_to_port(bytearray([1, size_m, size_l, 129, 0, int((126 - size_m - size_l) % 256)]))
        ok = 1
        dot_time = start_time + 0.2
        new_line_time = start_time + 10
        gu = []
        cou = []
        encoder = []
        while time.time() < start_time + read_time + 1:
            if self._port.inWaiting() > 250:
                rx_data = np.array(list(self._port.read(245)), 'int32')
                crc_hex = - sum(rx_data[0:244]) % 256
                if (rx_data[0] == 240) & (rx_data[3] == 145):
                    if crc_hex == rx_data[244]:
                        cou.extend(rx_data[7:244:4])
                        encoder.extend(rx_data[6:244:4]*65536 + rx_data[5:244:4]*256 + rx_data[4:244:4])
                    else:
                        print('HEX CheckSum ERROR!')
                        ok = 0
                        break
                else:
                    print('HEX Command ERROR!')
                    ok = 0
                    break
                if (rx_data[1] == 0) & (rx_data[2] == 0):
                    gu = np.array(gu, 'int32')
                    encoder = np.array(encoder, 'int32')
                    break
            else:
                time.sleep(0.001)
            if time.time() > new_line_time:
                new_line_time = new_line_time + 10
                print('\n', end='')

            elif time.time() > dot_time:
                dot_time = dot_time + 0.5
                print('.', end='')
        if ok:
            print(' OK!')
        return encoder

    def read_data_enc1_enc2_SPI(self, read_time: float, status: bool = True) -> Tuple[List[int], List[int]]:
        """
        Reads data from two encoders via SPI over USB for a specified duration.

        Sends a command to read data from both encoders, processes incoming packets, validates checksums,
        and extracts encoder values for both channels. Optionally prints progress indicators.

        Args:
            read_time: The duration in seconds to read data.
            status: If True, prints progress indicators (dots and status messages). Defaults to True.

        Returns:
            Tuple[List[int], List[int]]: Two lists containing the readings from encoder 1 and encoder 2, respectively.

        Raises:
            ValueError: If a checksum or command error occurs in the received data.

        Example:
            >>> ft = FlashTool()
            >>> enc1, enc2 = ft.read_data_enc1_enc2_SPI(2.0)
            Read USB data for 2.0 seconds: ..... OK!
            >>> print(enc1[:5], enc2[:5])
            [12345, 12346, ...], [54321, 54322, ...]
        """
        status and print('Read USB data for ', read_time, ' seconds: ', end='')
        logger.debug('Reading USB encoder 1 and encoder 2 data for %s seconds.', read_time)
        size = int(read_time * 1000)
        size_l = int(size) % 256
        size_m = int(size / 256) % 256
        b1 = size_l.to_bytes(1, 'big')
        b2 = size_m.to_bytes(1, 'big')
        address = b''.join([b2, b1])
        addr = int.from_bytes(address, 'big')
        tx_row = bytes.fromhex(generate_hex_line(addr, UartCmd.HEX_READ_ANGLE_TWO_ENC_SPI, [0])[1:])
        logger.debug("Reading CMD: %s", generate_hex_line(addr, UartCmd.HEX_READ_ANGLE_TWO_ENC_SPI, [0])[1:])
        self._port.flushInput()
        start_time = time.time()
        self._write_to_port(tx_row)
        ok = 1
        dot_time = start_time + 0.2
        new_line_time = start_time + 10
        cou1 = []
        cou2 = []
        encoder1 = []
        encoder2 = []
        while time.time() < start_time + read_time + 1:
            if self._port.inWaiting() > 250:
                rx_data = np.array(list(self._port.read(245)), 'int32')
                crc_hex = - sum(rx_data[0:244]) % 256
                if (rx_data[0] == 240) & (rx_data[3] == 144):
                    if crc_hex == rx_data[244]:
                        cou1.extend(rx_data[7:244:8])
                        encoder1.extend(rx_data[6:244:8]*65536 + rx_data[5:244:8]*256 + rx_data[4:244:8])
                        cou2.extend(rx_data[11:244:8])
                        encoder2.extend(rx_data[10:244:8]*65536 + rx_data[9:244:8]*256 + rx_data[8:244:8])
                    else:
                        print('HEX CheckSum ERROR!')
                        ok = 0
                        break
                else:
                    print('HEX Command ERROR!')
                    ok = 0
                    break
                if (rx_data[1] == 0) & (rx_data[2] == 0):
                    break
            else:
                time.sleep(0.001)
            if time.time() > new_line_time:
                new_line_time = new_line_time + 10
                status and print('\n', end='')

            elif time.time() > dot_time:
                dot_time = dot_time + 0.5
                status and print('.', end='')
        if ok:
            status and print(' OK!')
        return encoder1, encoder2

    def read_data_enc1_AB_enc2_SPI(self, read_time: float, status: bool = True) -> tuple[np.ndarray, np.ndarray]:
        """
        Read data from Encoder SPI (SIB, IRS) and AB over USB for a specified duration.

        Sends a command to read data from both encoders, processes incoming packets, validates checksums,
        and extracts encoder values for both channels. Optionally prints progress indicators.

        Data frame: 6 bytes
        0 byte  1 byte  2 byte  3 byte  4 byte   5 byte
        Enc2    *256    *65536  Cou     Enc1     *256

        Returns:
            tuple[np.ndarray, np.ndarray]: Two np.ndarrays containing:
                - Encoder2 data.
                - Encoder1 data.
        Raises:
            ValueError: If a checksum or command error occurs in the received data.
        """
        status and print('Read USB data for ', read_time, ' seconds: ', end='')
        size = int(read_time * 750)
        size_l = int(size) % 256
        size_m = int(size / 256) % 256
        b1 = size_l.to_bytes(1, 'big')
        b2 = size_m.to_bytes(1, 'big')
        address = b''.join([b2, b1])
        addr = int.from_bytes(address, 'big')
        tx_row = bytes.fromhex(generate_hex_line(addr, UartCmd.HEX_READ_ANGLE_TWO_ENC_AB_SPI, [0])[1:])

        self._write_to_port(tx_row)

        Encoder2 = []
        Encoder1 = []
        ok = 1
        start_time = time.time()
        dot_time = start_time + 0.2
        new_line_time = start_time + 10

        try:
            while time.time() < start_time + read_time + 1:
                if self._port.inWaiting() > 250:
                    rx_data = np.array(list(self._port.read(245)), 'int32')
                    CRC_HEX = - sum(rx_data[0:244]) % 256
                    if (rx_data[0] == 240) & (rx_data[3] == UartCmd.HEX_READ_ANGLE_TWO_ENC_AB_SPI + 0x10):
                        if (CRC_HEX == rx_data[244]):
                            Encoder2.extend(rx_data[6:244:6]*65536 + rx_data[5:244:6]*256 + rx_data[4:244:6])
                            Encoder1.extend(rx_data[9:244:6]*256 + rx_data[8:244:6])
                        else:
                            ok = 0
                            raise ValueError("HEX Command ERROR!")
                    else:
                        ok = 0
                        raise ValueError("HEX CheckSum ERROR!")

                    if (rx_data[1] == 0) & (rx_data[2] == 0):
                        raise ValueError("Recieved Data Size ERROR!")
                else:
                    time.sleep(0.001)

                if time.time() > new_line_time:
                    new_line_time = new_line_time + 10
                    status and print('\n', end='')
                elif time.time() > dot_time:
                    dot_time = dot_time + 0.5
                    status and print('.', end='')
            if ok:
                status and print(' OK!')
            return np.array(Encoder2, dtype='int32'), np.array(Encoder1, dtype='int32')

        except ValueError as e:
            logger.error(str(e))
            return np.array([], dtype='int32'), np.array([], dtype='int32')

    def read_enc2_current(self) -> tuple[str, float] | bool:
        """
        Read current of the encoder on channel 2.

        Args:
            None

        Returns:
            tuple[str, int]: If successful, returns:
                - str: Encoder2 current in hexadecimal format
                - float: Current in mA
            bool: False if operation fails (CRC error, no response, etc.)
        """
        try:
            self._port.reset_output_buffer()
            self._port.reset_input_buffer()
            self._port.write(generate_byte_line(0, UartCmd.HEX_READ_ENC2_CURRENT, list(range(UartCmd.RX_DATA_LENGTH_CURRENT))))
            self._port.flush()

            enc_ans = self._port.read(UartCmd.RX_DATA_LENGTH_CURRENT + UartCmd.PKG_INFO_LENGTH)

            logger.debug(enc_ans.hex())

            if not enc_ans:
                logger.error("No response from encoder!")
                return False

            enc_data_np = np.array(list(enc_ans), dtype='uint8')

            if (enc_data_np[0] != enc_data_np.size - UartCmd.PKG_INFO_LENGTH) or \
               (enc_data_np[3] != UartCmd.HEX_READ_ENC2_CURRENT + UartCmd.CMD_VAL_ADD):
                logger.error("Invalid response structure from encoder!")
                return False

            calculated_crc = calculate_checksum(enc_ans[0:-1].hex())
            if calculated_crc != enc_data_np[-1]:
                logger.error(f"CRC mismatch: calculated {calculated_crc}, expected {enc_data_np[-1]}")
                return False

            logger.debug("CRC check passed.")

            enc2_current = enc_ans[4:4+UartCmd.RX_DATA_LENGTH_CURRENT]

            data_hex = enc2_current.hex()

            ans_enc2_current_ma = int.from_bytes(enc2_current, byteorder='little', signed=False) / 1000

            return data_hex, ans_enc2_current_ma

        except Exception as e:
            logger.error(f"Error reading encoder current: {str(e)}", exc_info=True)
            return False

    def read_instant_angle_enc_SPI(self) -> tuple[str, list[int]] | bool:
        """
        Read instant angle encoder via SPI over USB.

        Returns:
            tuple[str, list[int]] | bool:
                If successful, returns a tuple containing:
                    - str: Encoder angle in hexadecimal format (24-bit value)
                    - list[int]: Angle parts [degrees, minutes, seconds]
                bool: False if operation fails
                    - No response from encoder
                    - Invalid response structure
                    - CRC mismatch in packet checksum
                    - Communication errors

        Example:
            >>> ft = FlashTool()
            >>> result = ft.read_instant_angle_enc_SPI()
            [16733568]:    359° 03' 48"
        """
        RX_DATA_LENGTH = 4
        DEGREE_SIGN = "\N{DEGREE SIGN}"

        try:
            self._port.reset_output_buffer()
            self._port.reset_input_buffer()
            self._port.write(generate_byte_line(
                address=0x0000,
                command=UartCmd.HEX_READ_INSTANT_ANGLE_ENC_SPI,
                data=list(range(RX_DATA_LENGTH))
            ))
            self._port.flush()

            enc_ans = self._port.read(RX_DATA_LENGTH + UartCmd.PKG_INFO_LENGTH)

            if not enc_ans:
                logger.error("No response from encoder!")
                return False

            enc_data_np = np.array(list(enc_ans), dtype='uint8')

            if (enc_data_np[0] != enc_data_np.size - UartCmd.PKG_INFO_LENGTH) or \
               (enc_data_np[3] != UartCmd.HEX_READ_INSTANT_ANGLE_ENC_SPI + UartCmd.CMD_VAL_ADD):
                logger.error("Invalid response structure from encoder!")
                return False

            calculated_crc = calculate_checksum(enc_ans[0:-1].hex())
            if calculated_crc != enc_data_np[-1]:
                logger.error(f"CRC mismatch: calculated {calculated_crc}, expected {enc_data_np[-1]}")
                return False

            logger.debug("CRC check passed.")

            angle_data = enc_ans[4:4+RX_DATA_LENGTH]

            data_hex = angle_data.hex()

            ans_angle = int.from_bytes(angle_data[:3], byteorder='little', signed=False)

            angle_raw = (
                int(data_hex[4:6], 16) * 65536 +
                int(data_hex[2:4], 16) * 256 +
                int(data_hex[0:2], 16)
            )
            angle_deg = angle_raw * 360 / 2**24

            degrees = int(angle_deg)
            remaining = angle_deg - degrees
            minutes = int(remaining * 60)
            seconds = int((remaining * 60 - minutes) * 60)

            logger.info(
                f"[{ans_angle}]: {degrees:>3}{DEGREE_SIGN} "
                f"{minutes:02d}' {seconds:02d}\""
            )

            return ans_angle, [degrees, minutes, seconds]

        except Exception as e:
            logger.error(f"Error reading encoder angle: {str(e)}", exc_info=True)
            return False

    def read_instant_angle_packet_enc_SPI(self) -> tuple[str, list[int]] | bool:
        """
        Read instant extended angle packet from encoder via SPI over USB.

        This method reads not only the angle value but also additional status
        information including error/warning flags and CRC for data integrity
        verification.

        Returns:
            tuple[str, list[int]] | bool:
                If successful, returns a tuple containing:
                    - str: Encoder angle in hexadecimal format (24-bit value)
                    - list[int]: Extended angle information:
                        [degrees, minutes, seconds, nE_flag, nW_flag, received_crc, status]
                        where:
                        - degrees: Integer degrees (0-359)
                        - minutes: Integer minutes (0-59)
                        - seconds: Integer seconds (0-59)
                        - nE_flag: Error flag (0=no error, 1=error detected)
                        - nW_flag: Warning flag (0=no warning, 1=warning present)
                        - received_crc: Received 6-bit CRC value from encoder
                        - status: "OK" if CRC matches, "ERR" if CRC mismatch
                bool: False if operation fails due to:
                    - No response from encoder
                    - Invalid response structure
                    - CRC mismatch in packet checksum
                    - Communication errors

        Example:
            >>> ft = FlashTool()
            >>> result = ft.read_instant_angle_packet_enc_SPI()
            [16733568]:    359° 03' 48"
            nE:1 nW:1 CRC:0F (OK)
        """
        RX_DATA_LENGTH = 6
        DEGREE_SIGN = "\N{DEGREE SIGN}"

        try:
            self._port.reset_input_buffer()
            self._port.reset_output_buffer()
            self._port.write(generate_byte_line(
                address=0x0000,
                command=UartCmd.HEX_READ_INSTANT_ANGLE_PACKET_ENC_SPI,
                data=list(range(RX_DATA_LENGTH))
            ))
            self._port.flush()

            enc_ans = self._port.read(RX_DATA_LENGTH + UartCmd.PKG_INFO_LENGTH)

            if not enc_ans:
                logger.error("No response from encoder!")
                return False

            enc_data_np = np.array(list(enc_ans), dtype='uint8')

            if (enc_data_np[0] != enc_data_np.size - UartCmd.PKG_INFO_LENGTH) or \
               (enc_data_np[3] != UartCmd.HEX_READ_INSTANT_ANGLE_PACKET_ENC_SPI + UartCmd.CMD_VAL_ADD):
                logger.error("Invalid response structure from encoder!")
                return False

            calculated_crc = calculate_checksum(enc_ans[0:-1].hex())
            if calculated_crc != enc_data_np[-1]:
                logger.error(f"CRC mismatch: calculated {calculated_crc}, expected {enc_data_np[-1]}")
                return False

            logger.debug("CRC check passed.")

            angle_data = enc_ans[4:4+RX_DATA_LENGTH]

            angle_bytes = angle_data[:3]
            nE_nW_bits = angle_data[4] & 0x03
            nE = (nE_nW_bits >> 1) & 0x01
            nW = nE_nW_bits & 0x01
            received_crc = angle_data[5]

            angle_value = int.from_bytes(angle_bytes, byteorder='little', signed=False)
            data_for_crc = np.uint32(angle_value << 2) | np.uint32(nE_nW_bits)
            expected_crc = biss_crc6_calc(data_for_crc)

            angle_deg = angle_value * 360 / 2**24
            degrees = int(angle_deg)
            remaining = angle_deg - degrees
            minutes = int(remaining * 60)
            seconds = int((remaining * 60 - minutes) * 60)

            crc_ok = (expected_crc == received_crc)
            status = "OK" if crc_ok else "ERR"

            logger.info(
                f"[{angle_value}]: {degrees:>3}{DEGREE_SIGN} "
                f"{minutes:02d}' {seconds:02d}\"\n"
                f"nE:{nE:01X} nW:{nW:01X} CRC:{received_crc:02X} "
                f"({status})"
            )

            return angle_value, [degrees, minutes, seconds, nE, nW, received_crc, status]

        except Exception as e:
            logger.error(f"Error reading encoder angle: {str(e)}", exc_info=True)
            return False
