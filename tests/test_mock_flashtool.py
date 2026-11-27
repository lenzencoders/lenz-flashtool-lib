"""Smoke tests using MockFlashTool — no hardware required."""

import pytest
import numpy as np
from lenz_flashtool.testing import MockFlashTool
from lenz_flashtool.flashtool.uart import UartBootloaderMemoryStates


@pytest.fixture(autouse=True)
def reset_singleton():
    """Ensure each test gets a fresh MockFlashTool singleton."""
    yield
    if MockFlashTool._instance is not None:
        MockFlashTool._instance._initialized = False
        MockFlashTool._instance = None


class TestSingleton:
    def test_singleton_returns_same_instance(self):
        a = MockFlashTool()
        b = MockFlashTool()
        assert a is b
        a.close()

    def test_close_resets_singleton(self):
        a = MockFlashTool()
        a.close()
        assert MockFlashTool._instance is None

    def test_reinit_after_close(self):
        a = MockFlashTool()
        a.close()
        b = MockFlashTool()
        assert b._initialized is True
        b.close()


class TestContextManager:
    def test_with_block(self):
        with MockFlashTool() as ft:
            assert ft is not None
            assert ft._initialized is True
        assert MockFlashTool._instance is None

    def test_exception_in_with_block(self):
        with pytest.raises(ValueError):
            with MockFlashTool() as ft:
                raise ValueError("test")
        assert MockFlashTool._instance is None


class TestCleanupHandlers:
    def test_register_cleanup_called_on_close(self):
        called = []
        with MockFlashTool() as ft:
            ft.register_cleanup(lambda: called.append(1))
            ft.register_cleanup(lambda: called.append(2))
        # Handlers called in reverse order
        assert called == [2, 1]

    def test_register_cleanup_returns_self(self):
        ft = MockFlashTool()
        result = ft.register_cleanup(lambda: None)
        assert result is ft
        ft.close()


class TestBiSSCommands:
    def test_valid_command(self):
        with MockFlashTool() as ft:
            # Should not raise
            ft.biss_write_command('reboot2bl')
            ft.biss_write_command('zeroing')
            ft.biss_write_command('saveflash')

    def test_invalid_command_raises(self):
        with MockFlashTool() as ft:
            with pytest.raises(ValueError):
                ft.biss_write_command('nonexistent_command')


class TestBiSSBank:
    def test_valid_bank(self):
        with MockFlashTool() as ft:
            ft.biss_set_bank(0)
            ft.biss_set_bank(255)

    def test_invalid_bank_raises(self):
        with MockFlashTool() as ft:
            with pytest.raises(ValueError):
                ft.biss_set_bank(-1)
            with pytest.raises(ValueError):
                ft.biss_set_bank(256)


class TestBiSSWrite:
    def test_valid_write(self):
        with MockFlashTool() as ft:
            ft.biss_write(0, 0)
            ft.biss_write(127, 255)

    def test_address_out_of_range(self):
        with MockFlashTool() as ft:
            with pytest.raises(ValueError):
                ft.biss_write(128, 0)
            with pytest.raises(ValueError):
                ft.biss_write(-1, 0)

    def test_write_word_valid(self):
        with MockFlashTool() as ft:
            ft.biss_write_word(0, 0xFF)
            ft.biss_write_word(0, [0x01, 0x02])

    def test_write_word_address_out_of_range(self):
        with MockFlashTool() as ft:
            with pytest.raises(ValueError):
                ft.biss_write_word(128, 0xFF)

    def test_write_word_empty_list(self):
        with MockFlashTool() as ft:
            with pytest.raises(ValueError):
                ft.biss_write_word(0, [])


class TestReadFlags:
    def test_read_state_flags_returns_array(self):
        with MockFlashTool() as ft:
            flags = ft.biss_read_state_flags()
            assert isinstance(flags, np.ndarray)
            assert flags.dtype == np.uint8

    def test_read_flags_returns_tuple(self):
        with MockFlashTool() as ft:
            result = ft.biss_read_flags()
            assert isinstance(result, tuple)
            assert len(result) == 2
            flags, cmd_state = result
            assert isinstance(flags, list)
            assert isinstance(cmd_state, list)

    def test_read_command_state(self):
        with MockFlashTool() as ft:
            state = ft.biss_read_command_state()
            assert state is not None


class TestReadSnum:
    def test_read_snum_returns_tuple(self):
        with MockFlashTool() as ft:
            result = ft.biss_read_snum()
            assert result is not None
            assert len(result) == 4
            bootloader, sn, mfg, prog = result
            assert isinstance(bootloader, str)
            assert isinstance(sn, str)


class TestEncoderControl:
    def test_power_cycle(self):
        with MockFlashTool() as ft:
            ft.encoder_power_off()
            ft.encoder_power_on()
            ft.encoder_power_cycle()

    def test_ch1_power_cycle(self):
        with MockFlashTool() as ft:
            ft.encoder_ch1_power_off()
            ft.encoder_ch1_power_on()
            ft.encoder_ch1_power_cycle()

    def test_flashtool_rst(self):
        with MockFlashTool() as ft:
            ft.flashtool_rst()


class TestAddrRead:
    def test_addr_read_returns_array(self):
        with MockFlashTool() as ft:
            data = ft.biss_addr_read(0, 4)
            assert isinstance(data, np.ndarray)
            assert len(data) == 4
            assert data.dtype == np.uint8

    def test_addr_readb_returns_array(self):
        with MockFlashTool() as ft:
            data = ft.biss_addr_readb(0, 0, 4)
            assert isinstance(data, np.ndarray)
            assert len(data) == 4


class TestReadData:
    def test_read_data_returns_array(self):
        with MockFlashTool() as ft:
            data = ft.read_data(0.01)
            assert data is not None

    def test_read_dual_encoder(self):
        with MockFlashTool() as ft:
            enc1, enc2 = ft.read_data_enc1_enc2_SPI(0.01, status=False)
            assert enc1 is not None
            assert enc2 is not None

    def test_read_data_enc1_AB_enc2_SPI(self):
        with MockFlashTool() as ft:
            enc2, enc1 = ft.read_data_enc1_AB_enc2_SPI(0.01, status=False)
            assert isinstance(enc2, np.ndarray)
            assert isinstance(enc1, np.ndarray)
            assert enc2.dtype == np.int32
            assert enc1.dtype == np.int32

    def test_read_enc2_current(self):
        with MockFlashTool() as ft:
            result = ft.read_enc2_current()
            assert isinstance(result, tuple)
            data_hex, current_ma = result
            assert isinstance(data_hex, str)
            assert isinstance(current_ma, float)

    def test_read_instant_angle(self):
        with MockFlashTool() as ft:
            result = ft.read_instant_angle_enc_SPI()
            assert isinstance(result, tuple)
            angle_value, parts = result
            assert isinstance(angle_value, (int, np.integer))
            assert len(parts) == 3  # degrees, minutes, seconds

    def test_read_instant_angle_packet(self):
        with MockFlashTool() as ft:
            result = ft.read_instant_angle_packet_enc_SPI()
            assert isinstance(result, tuple)
            angle_value, parts = result
            assert isinstance(angle_value, (int, np.integer))
            assert len(parts) == 7  # degrees, minutes, seconds, nE, nW, crc, status
            assert parts[6] == "OK"


class TestModeSelection:
    def test_select_spi_channel_valid(self):
        with MockFlashTool() as ft:
            ft.select_spi_channel("channel1")
            ft.select_spi_channel("channel2")

    def test_select_spi_channel_invalid(self):
        with MockFlashTool() as ft:
            with pytest.raises(ValueError):
                ft.select_spi_channel("channel3")

    def test_select_flashtool_mode_valid(self):
        with MockFlashTool() as ft:
            ft.select_flashtool_mode("spi_spi")
            ft.select_flashtool_mode("default_spi")

    def test_select_flashtool_mode_invalid(self):
        with MockFlashTool() as ft:
            with pytest.raises(ValueError):
                ft.select_flashtool_mode("invalid_mode")

    def test_select_current_sensor_mode(self):
        with MockFlashTool() as ft:
            ft.select_FlashTool_current_sensor_mode("enable")
            ft.select_FlashTool_current_sensor_mode("disable")

    def test_select_current_sensor_mode_invalid(self):
        with MockFlashTool() as ft:
            with pytest.raises(ValueError):
                ft.select_FlashTool_current_sensor_mode("invalid")

    def test_select_spi_ch1_mode_valid(self):
        with MockFlashTool() as ft:
            ft.select_spi_ch1_mode("lenz_biss")
            ft.select_spi_ch1_mode("lir_ssi")
            ft.select_spi_ch1_mode("lir_biss_21b")

    def test_select_spi_ch1_mode_invalid(self):
        with MockFlashTool() as ft:
            with pytest.raises(ValueError):
                ft.select_spi_ch1_mode("invalid")


class TestBootloader:
    def test_reboot_to_bl(self):
        with MockFlashTool() as ft:
            ft.reboot_to_bl()

    def test_reboot_to_fw(self):
        with MockFlashTool() as ft:
            ft.reboot_to_fw()

    def test_read_fw_bl_ver(self):
        with MockFlashTool() as ft:
            fw_ver, bl_ver = ft.read_fw_bl_ver()
            assert isinstance(fw_ver, str)
            assert isinstance(bl_ver, str)
            assert len(fw_ver) == 8
            assert len(bl_ver) == 8

    def test_read_memory_state_bl(self):
        with MockFlashTool() as ft:
            state = ft.read_memory_state_bl()
            assert isinstance(state, UartBootloaderMemoryStates)

    def test_check_main_fw_crc32(self):
        with MockFlashTool() as ft:
            ft.check_main_fw_crc32()

    def test_download_fw_to_ft(self):
        with MockFlashTool() as ft:
            ft.download_fw_to_ft("fake_firmware.hex")

    def test_enter_bl_biss_encoder(self):
        with MockFlashTool() as ft:
            result = ft.enter_bl_biss_encoder()
            assert result is True

    def test_enter_bl_irs(self):
        with MockFlashTool() as ft:
            assert ft.enter_bl_irs() is True

    def test_enter_fw_irs(self):
        with MockFlashTool() as ft:
            assert ft.enter_fw_irs() is True

    def test_set_pos_irs_valid(self):
        with MockFlashTool() as ft:
            b_1, b_2 = ft.set_pos_irs(180.0)
            assert b_1 is not None
            assert b_2 is not None

    def test_set_pos_irs_reverse(self):
        with MockFlashTool() as ft:
            b_1, b_2 = ft.set_pos_irs(90.0, reverse=True)
            assert b_1 is not None
            assert b_2 is not None

    def test_set_pos_irs_invalid_angle(self):
        with MockFlashTool() as ft:
            b_1, b_2 = ft.set_pos_irs(-10.0)
            assert b_1 is None
            assert b_2 is None
            b_1, b_2 = ft.set_pos_irs(400.0)
            assert b_1 is None
            assert b_2 is None


class TestSerialIO:
    def test_port_read_returns_array(self):
        with MockFlashTool() as ft:
            data = ft.port_read(8)
            assert isinstance(data, np.ndarray)
            assert data.dtype == np.uint8

    def test_port_read_has_valid_crc(self):
        with MockFlashTool() as ft:
            data = ft.port_read(4)
            # Last byte is XOR of all preceding bytes
            expected_crc = np.bitwise_xor.reduce(data[:-1])
            assert data[-1] == expected_crc

    def test_hex_line_send(self):
        with MockFlashTool() as ft:
            result = ft.hex_line_send(":0A0000000102030405060708090A")
            assert isinstance(result, bytes)

    def test_biss_cmd_reboot2bl(self):
        with MockFlashTool() as ft:
            ft.biss_cmd_reboot2bl()


class TestBiSSRead:
    def test_read_HSI(self):
        with MockFlashTool() as ft:
            result = ft.biss_read_HSI()
            assert result is not None
            assert isinstance(result, tuple)
            assert len(result) == 1
            assert result[0] == "1A"

    def test_read_progver(self):
        with MockFlashTool() as ft:
            # Should not raise; logs the version
            ft.biss_read_progver()

    def test_read_calibration_temp_vcc_does_not_hang(self):
        with MockFlashTool() as ft:
            # Fixed: no longer an infinite loop, runs `iterations` times
            ft.biss_read_calibration_temp_vcc(iterations=2)

    def test_read_flags_flashCRC(self):
        with MockFlashTool() as ft:
            result = ft.biss_read_flags_flashCRC()
            assert result == 0

    def test_read_registers_known_bank(self):
        with MockFlashTool() as ft:
            data = ft.biss_read_registers(0)
            assert isinstance(data, np.ndarray)
            assert len(data) == 128
            assert data.dtype == np.uint8

    def test_read_registers_unknown_bank_returns_zeros(self):
        with MockFlashTool() as ft:
            data = ft.biss_read_registers(99)
            assert isinstance(data, np.ndarray)
            assert len(data) == 128
            assert np.all(data == 0)

    def test_read_angle_once(self):
        with MockFlashTool() as ft:
            # Should not raise; writes angle to stdout
            ft.biss_read_angle_once()


class TestBiSSOperations:
    def test_zeroing(self):
        with MockFlashTool() as ft:
            ft.biss_zeroing()

    def test_set_dir_cw(self):
        with MockFlashTool() as ft:
            ft.biss_set_dir_cw()

    def test_set_dir_ccw(self):
        with MockFlashTool() as ft:
            ft.biss_set_dir_ccw()

    def test_set_shift(self):
        with MockFlashTool() as ft:
            ft.biss_set_shift(100)

    def test_set_shift_invalid_type(self):
        with MockFlashTool() as ft:
            with pytest.raises(ValueError):
                ft.biss_set_shift(3.14)

    def test_send_data_to_device(self):
        with MockFlashTool() as ft:
            # Minimal payload: 1 page, 1 bank
            pages = [[[b'\x00' * 128]]]
            crc_values = [0xDEADBEEF]
            page_numbers = [1]
            ft.send_data_to_device(pages, crc_values, page_numbers,
                                   start_page=0, end_page=0)

    def test_send_data_to_device_difmode(self):
        with MockFlashTool() as ft:
            pages = [[[b'\xFF' * 128]]]
            crc_values = [0x12345678]
            page_numbers = [1]
            ft.send_data_to_device(pages, crc_values, page_numbers,
                                   start_page=0, end_page=0, difmode=True)


class TestSignalHandling:
    def test_enable_signal_handling_returns_self(self):
        with MockFlashTool() as ft:
            result = ft.enable_signal_handling()
            assert result is ft


class TestMockResponseCustomization:
    def test_override_fw_bl_ver(self):
        with MockFlashTool() as ft:
            ft._mock_responses['fw_ver'] = "AABBCCDD"
            ft._mock_responses['bl_ver'] = "11223344"
            fw, bl = ft.read_fw_bl_ver()
            assert fw == "AABBCCDD"
            assert bl == "11223344"

    def test_override_memory_state(self):
        with MockFlashTool() as ft:
            ft._mock_responses['memory_state'] = UartBootloaderMemoryStates.UART_MEMORYSTATE_FLASH_FW_CRC_FAULT
            state = ft.read_memory_state_bl()
            assert state == UartBootloaderMemoryStates.UART_MEMORYSTATE_FLASH_FW_CRC_FAULT

    def test_override_snum(self):
        with MockFlashTool() as ft:
            ft._mock_responses['snum']["Bootloader"] = "DEADBEEF"
            result = ft.biss_read_snum()
            assert result[0] == "DEADBEEF"

    def test_override_enc2_current(self):
        with MockFlashTool() as ft:
            ft._mock_responses['enc2_current'] = ("d0070000", 2.0)
            data_hex, current_ma = ft.read_enc2_current()
            assert current_ma == 2.0

    def test_override_state_flags(self):
        with MockFlashTool() as ft:
            ft._mock_responses['state_flags'] = np.array([0x01, 0x00], dtype='uint8')
            flags = ft.biss_read_state_flags()
            assert flags[0] == 0x01
