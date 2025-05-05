import time
import sys
import numpy as np
from typing import List, Optional, Any, Dict, Union, Tuple, Callable, Type
import logging
import signal
from types import TracebackType
from ..biss.registers import BiSSBank
from ..biss.commands import (
    biss_commands, interpret_biss_commandstate, interpret_error_flags
)
from ..utils.progress import percent_complete


logger = logging.getLogger(__name__)


class MockFlashTool:
    """
    A mock implementation of FlashTool for testing purposes without hardware access.
    Simulates the behavior of the real FlashTool class.
    """

    _instance = None
    _original_signal_handlers: Dict[int, Any] = {}

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(MockFlashTool, cls).__new__(cls)
            cls._instance._cleanup_handlers = []
        return cls._instance

    def __init__(self, port_description_prefixes=('XR21V',), baud_rate=12000000):
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._initialized = True
        self.__port_name = "MOCK_PORT"
        self._mock_data = {}
        self._mock_responses = {}
        self._setup_default_mock_data()
        logger.debug(f'Mock FlashTool {self.__port_name} - Connected!')

    def __enter__(self) -> 'MockFlashTool':
        return self

    def __exit__(
            self,
            exc_type: Optional[Type[BaseException]],
            exc_val: Optional[BaseException],
            exc_tb: Optional[TracebackType]
            ) -> bool:
        self.close()
        return False

    def register_cleanup(self, handler: Callable[[], None]) -> 'MockFlashTool':
        self._cleanup_handlers.append(handler)
        return self

    def enable_signal_handling(self, signals: Tuple[int, ...] = (signal.SIGINT,)) -> 'MockFlashTool':
        for sig in signals:
            self._original_signal_handlers[sig] = signal.getsignal(sig)
            signal.signal(sig, self._signal_handler)
        return self

    def _signal_handler(self, signum: int, frame: Any) -> None:
        logger.info("Mock: Signal %s received, cleaning up...", signum)
        self.close()
        sys.exit(1)

    def _setup_default_mock_data(self):
        """Initialize default mock responses and data"""
        # State flags response
        self._mock_responses['state_flags'] = np.array([0x00, 0x00], dtype='uint8')

        # Command state response
        self._mock_responses['command_state'] = np.array([0x00], dtype='uint8')

        # Serial number response
        self._mock_responses['snum'] = {
            "Bootloader": "01020304",
            "Serial No ": "A1B2C3D4",
            "Mfg. Date ": "11111111",
            "Program   ": "AABBCCDD",
            "Dev ID_H  ": "4D4F434B",
            "Dev ID_L  ": "494E0A"
        }

        # Register read responses
        self._mock_responses['registers'] = {
            BiSSBank.BISS_BANK_SERV: np.random.randint(0, 256, 128, dtype='uint8'),
            0: np.random.randint(0, 256, 128, dtype='uint8'),
            1: np.random.randint(0, 256, 128, dtype='uint8'),
            2: np.random.randint(0, 256, 128, dtype='uint8'),
            3: np.random.randint(0, 256, 128, dtype='uint8'),
            4: np.random.randint(0, 256, 128, dtype='uint8'),
            5: np.random.randint(0, 256, 128, dtype='uint8')
        }

        # Encoder data simulation
        self._mock_responses['encoder_data'] = {
            'single': np.random.randint(0, 2**24, 1000, dtype='int32'),
            'dual': (np.random.randint(0, 2**24, 1000, dtype='int32'),
                     np.random.randint(0, 2**24, 1000, dtype='int32'))
        }

        # HSI response
        self._mock_responses['hsi'] = "1A"

    def _wait_for_data(self, size: int, timeout: float = 1.0) -> bool:
        """Mock implementation always returns True immediately"""
        return True

    def port_read(self, length: int) -> np.ndarray:
        """Mock port read with simulated data"""
        # For simplicity, return random data of requested length
        data = np.random.randint(0, 256, length, dtype='uint8')
        # Add CRC byte (simple XOR of all bytes)
        crc = np.bitwise_xor.reduce(data)
        result = np.concatenate((data, np.array([crc], dtype='uint8')))
        return result

    def close(self):
        """Mock close method"""
        for handler in reversed(self._cleanup_handlers):
            try:
                handler()
            except Exception as e:
                logger.warning("Mock: Cleanup error: %s", str(e))

        # Restore original signal handlers
        for sig, handler in self._original_signal_handlers.items():
            try:
                signal.signal(sig, handler)
            except Exception as e:
                logger.warning("Mock: Error restoring signal handler: %s", e)

        logger.info(f'Mock FlashTool: {self.__port_name} - disconnected!')
        MockFlashTool._instance = None
        self._initialized = False

    def biss_cmd_reboot2bl(self):
        """Mock reboot to bootloader command"""
        logger.debug("Mock: Sending reboot to bootloader command")
        time.sleep(0.1)

    def biss_write_command(self, command: str):
        """Mock command writing"""
        if command not in biss_commands:
            logger.error(f"Mock: Unknown command: '{command}'")
            raise ValueError(f"Unknown command: '{command}'.")
        logger.debug(f"Mock: Sending BiSS {command} command")
        time.sleep(0.01)

    def hex_line_send(self, hex_line: str) -> bytes:
        """Mock hex line sending"""
        logger.debug(f'Mock: Uploading {hex_line} to the encoder.')
        return bytes.fromhex(hex_line[1:])

    def biss_set_bank(self, bank_num: int):
        """Mock bank selection"""
        if not 0 <= bank_num <= 255:
            raise ValueError(f"Mock: Bank {bank_num} out of range (0-255)")
        logger.debug(f'Mock: Setting bank {bank_num}')

    def biss_write(self, addr: int, data: int):
        """Mock write operation"""
        if not 0 <= addr <= 127:
            raise ValueError(f"Mock: Address {addr} out of range (0-127)")
        logger.debug(f'Mock: Writing {data} to address {addr}')

    def biss_write_word(self, addr: int, word: Union[int, List[int]]) -> None:
        """Mock word writing"""
        if not 0 <= addr <= 127:
            raise ValueError(f"Mock: Address {addr} out of range (0-127)")

        words = [word] if isinstance(word, int) else word
        if not words:
            raise ValueError("Mock: Empty word list provided")

        logger.debug(f"Mock: Sending word {words} with starting index {addr}")

    def biss_read_state_flags(self) -> np.ndarray:
        """Mock state flags reading"""
        return self._mock_responses['state_flags']

    def biss_read_registers(self, bissbank: int):
        """Mock register reading"""
        logger.debug(f"Mock: Reading registers from bank {bissbank}")
        return self._mock_responses['registers'].get(bissbank, np.zeros(128, dtype='uint8'))

    def encoder_power_off(self) -> None:
        """Mock power off"""
        logger.debug('Mock: Sending POWER_OFF command')

    def encoder_power_on(self) -> None:
        """Mock power on"""
        logger.debug('Mock: Sending POWER_ON command')

    def encoder_ch1_power_off(self) -> None:
        """Mock channel 1 power off"""
        logger.debug('Mock: Sending CH1 POWER_OFF command')

    def encoder_ch1_power_on(self) -> None:
        """Mock channel 1 power on"""
        logger.debug('Mock: Sending CH1 POWER_ON command')

    def encoder_power_cycle(self) -> None:
        """Mock power cycle"""
        self.encoder_power_off()
        time.sleep(0.1)
        self.encoder_power_on()
        time.sleep(0.1)
        logger.debug('Mock: Performed power cycle')

    def encoder_ch1_power_cycle(self) -> None:
        """Mock channel 1 power cycle"""
        self.encoder_ch1_power_off()
        time.sleep(0.1)
        self.encoder_ch1_power_on()
        time.sleep(0.1)
        logger.debug('Mock: Performed CH1 power cycle')

    def flashtool_rst(self) -> None:
        """Mock reset"""
        logger.info('Mock: Sending RESET command')

    def read_data(self, read_time: float):
        """Mock data reading"""
        logger.debug(f'Mock: Reading data for {read_time} seconds')
        return self._mock_responses['encoder_data']['single']

    def read_data_enc1_enc2_SPI(self, read_time: float, status=True) -> Tuple[List[int], List[int]]:
        """Mock dual encoder reading"""
        status and logger.debug(f'Mock: Reading dual encoder data for {read_time} seconds')
        return self._mock_responses['encoder_data']['dual']

    def biss_read_snum(self) -> Optional[Tuple[str, str, str, str]]:
        """Mock serial number reading"""
        try:
            snum = self._mock_responses['snum']
            logger.info('======= MOCK ENCODER DATA ========')
            for name, val in snum.items():
                logger.info(f'{str(name)}: \t {str(val)}')
            logger.info('==================================')
            try:
                logger.info(f"DEVID: {bytes.fromhex(snum['Dev ID_H  '] + snum['Dev ID_L  ']).decode('ascii')}, " +
                            f"Serial No: {bytes.fromhex(snum['Serial No '][0:4]).decode('ascii')}" +
                            f"{snum['Serial No '][4:8]}, " +
                            f"Mfg date: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(int(snum['Mfg. Date '], 16)))} "
                            + "(UTC)")
            except UnicodeDecodeError:
                pass
            return (
                snum["Bootloader"],
                snum["Serial No "],
                snum["Mfg. Date "],
                snum["Program   "],
            )
        except Exception as e:
            logger.error(f"Mock ERROR: Can't read registers data! {e}")
            return None

    def biss_read_HSI(self) -> Optional[Tuple[str]]:
        """Mock HSI reading"""
        try:
            hsi = self._mock_responses['hsi']
            logger.info('======= MOCK ENCODER DATA ========')
            logger.info(f'HSI: \t {hsi}')
            logger.info('==================================')
            return (hsi,)
        except Exception as e:
            logger.error(f"Mock ERROR: Can't read HSI data! {e}")
            return None

    def biss_read_progver(self) -> None:
        """Mock program version reading"""
        progver = self._mock_responses['snum']["Program   "]
        logger.info("Mock: Encoder's program version: " + ".".join(
                    f"{progver[i:i+2]}" for i in range(0, len(progver), 2)))

    def biss_read_calibration_temp_vcc(self) -> None:
        """Mock calibration data reading"""
        degree_sign = "\N{DEGREE SIGN}"
        while True:
            print("Mock: CalState: 32, SignalMod: [3671, 4362], " +
                  f"EncTemp = 27 {degree_sign}C, Vcc = 4.98 V")
            time.sleep(1)

    def biss_read_command_state(self) -> Optional[np.ndarray]:
        """Mock command state reading"""
        return self._mock_responses['command_state']

    def biss_addr_readb(self, bissbank: int, addr: int, length: int) -> np.ndarray:
        """Mock address reading with bank"""
        logger.debug(f"Mock: Reading {length} bytes from bank {bissbank} at address {addr}")
        return np.random.randint(0, 256, length, dtype='uint8')

    def biss_addr_read(self, addr: int, length: int) -> np.ndarray:
        """Mock address reading"""
        logger.debug(f"Mock: Reading {length} bytes at address {addr}")
        return np.random.randint(0, 256, length, dtype='uint8')

    def biss_read_flags_flashCRC(self) -> int:
        """Mock flash CRC flag reading"""
        return 0  # No error by default

    def biss_read_flags(self) -> Tuple[List[str], List[str]]:
        """Mock flags reading"""
        try:
            state_flags = self.biss_read_state_flags()
            flags = (state_flags[1] << 8) | state_flags[0]
            interpreted_flags = interpret_error_flags(flags)
            command_state = self.biss_read_command_state()[0]
            interpreted_command_state = interpret_biss_commandstate(command_state)

            return interpreted_flags, interpreted_command_state
        except Exception as e:
            logger.error(f"Mock: Failed to read flags: {e}")
            raise

    def biss_read_angle_once(self) -> None:
        """Mock single angle reading"""
        degree_sign = "\N{DEGREE SIGN}"
        _, ans = self.read_data_enc1_enc2_SPI(0.01, False)
        res = 2**24
        ang = int(ans[0]) * 360 / res
        degrs = int(ang)
        mins = int((ang - degrs) * 60)
        secs = int((ang - degrs - (mins / 60)) * 3600)
        sys.stdout.write("\r" + f'[{ans[0]}]: \t {str(degrs):>3}{degree_sign} {str(mins):2}\' {str(secs):2}\"' + '\t\t')

    def biss_zeroing(self) -> None:
        """Mock zeroing calibration"""
        self.flashtool_rst()
        self.encoder_power_cycle()
        self.biss_write_command('unlocksetup')
        self.biss_write_command('unlockflash')
        self.biss_write_command('zeroing')
        self.biss_write_command('saveflash')
        time.sleep(0.2)
        self.encoder_power_cycle()

    def biss_set_dir_cw(self) -> None:
        """Mock set direction clockwise"""
        self.flashtool_rst()
        self.encoder_power_cycle()
        self.biss_write_command('unlocksetup')
        self.biss_write_command('unlockflash')
        self.biss_write_command('set_dir_cw')
        self.biss_write_command('saveflash')
        time.sleep(0.2)
        self.encoder_power_cycle()

    def biss_set_dir_ccw(self) -> None:
        """Mock set direction counter-clockwise"""
        self.flashtool_rst()
        self.encoder_power_cycle()
        self.biss_write_command('unlocksetup')
        self.biss_write_command('unlockflash')
        self.biss_write_command('set_dir_ccw')
        self.biss_write_command('saveflash')
        time.sleep(0.2)
        self.encoder_power_cycle()

    def biss_set_shift(self, shift_angle: int) -> None:
        """Mock set shift angle"""
        if not isinstance(shift_angle, int):
            raise ValueError(f"Mock: Shift angle must be an integer, got {type(shift_angle)}")

        self.biss_read_angle_once()
        self.biss_write_command('unlocksetup')
        self.biss_write_command('unlockflash')
        self.biss_write_word(BiSSBank.SHIFT_REG_INDEX, shift_angle)
        self.biss_write_command('saveflash')
        time.sleep(0.1)
        print(self.biss_addr_read(BiSSBank.SHIFT_REG_INDEX, 1))
        self.encoder_power_cycle()
        print(self.biss_addr_read(BiSSBank.SHIFT_REG_INDEX, 1))
        self.biss_read_angle_once()

    def send_data_to_device(self,
                            pages: List[List[bytes]],
                            crc_values: List[int],
                            page_numbers: List[int],
                            start_page: int,
                            end_page: int,
                            pbar: Optional[Any] = None,
                            difmode: bool = False
                            ) -> None:
        """Mock data sending to device"""
        max_retries = 3

        for page_idx, (page_data, crc, page_num) in enumerate(zip(pages, crc_values, page_numbers), start=start_page):
            if page_idx > end_page:
                break

            retry_count = 0
            success = False

            while retry_count < max_retries and not success:
                if page_idx > 1:
                    self.biss_set_bank(BiSSBank.BISS_BANK_SERV)
                    self.biss_write_word(BiSSBank.CRC32_REG_INDEX, crc)
                    self.biss_write_word(BiSSBank.PAGENUM_REG_INDEX, page_num)
                    time.sleep(0.02)

                for bank_idx, bank_data in enumerate(page_data):
                    bank_num = bank_idx + BiSSBank.BISS_USERBANK_START
                    if bank_num == 5:
                        self.biss_set_bank(bank_num)
                    time.sleep(0.02)

                    if pbar:
                        percent_complete(bank_idx, BiSSBank.BANKS_PER_PAGE - 1,
                                         title=f"Mock: Sending Page {page_idx}")

                time.sleep(0.3)
                if difmode:
                    self.biss_write_command('savediftable')
                else:
                    self.biss_write_command('load2k')

                time.sleep(0.25)
                success = True  # Mock always succeeds

        logger.info("Mock: Done uploading!")
