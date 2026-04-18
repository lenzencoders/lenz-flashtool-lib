"""Tests that the mixin-based FlashTool structure imports correctly and exposes all methods."""

import pytest
from lenz_flashtool.flashtool.core import FlashTool
from lenz_flashtool.flashtool.serial_io import SerialIOMixin
from lenz_flashtool.flashtool.encoder_control import EncoderControlMixin
from lenz_flashtool.flashtool.biss_io import BiSSIOMixin
from lenz_flashtool.flashtool.data_streaming import DataStreamingMixin
from lenz_flashtool.flashtool.bootloader import BootloaderMixin


class TestMRO:
    def test_flashtool_inherits_all_mixins(self):
        mro_names = [c.__name__ for c in FlashTool.__mro__]
        assert 'SerialIOMixin' in mro_names
        assert 'BiSSIOMixin' in mro_names
        assert 'EncoderControlMixin' in mro_names
        assert 'DataStreamingMixin' in mro_names
        assert 'BootloaderMixin' in mro_names

    def test_mro_order(self):
        mro = FlashTool.__mro__
        names = [c.__name__ for c in mro]
        assert names[0] == 'FlashTool'
        assert names[-1] == 'object'


class TestPackageLevelImports:
    def test_flashtool_from_package(self):
        from lenz_flashtool.flashtool import FlashTool as FT
        assert FT is FlashTool

    def test_top_level_import(self):
        from lenz_flashtool import FlashTool as FT
        assert FT is FlashTool

    def test_mock_flashtool_import(self):
        from lenz_flashtool.testing import MockFlashTool
        assert MockFlashTool is not None

    def test_cli_import(self):
        from lenz_flashtool.biss.cli import BiSSCommandLine
        assert BiSSCommandLine is not None

    def test_operations_import(self):
        from lenz_flashtool.flashtool.operations import biss_send_hex, biss_send_dif, send_hex_irs_enc
        assert callable(biss_send_hex)
        assert callable(biss_send_dif)
        assert callable(send_hex_irs_enc)


SERIAL_IO_METHODS = [
    '_find_linux_port_enhanced', '_wait_for_data', '_write_to_port',
    'port_read', 'hex_line_send',
]

ENCODER_CONTROL_METHODS = [
    'encoder_power_off', 'encoder_power_on',
    'encoder_ch1_power_off', 'encoder_ch1_power_on',
    'encoder_power_cycle', 'encoder_ch1_power_cycle',
    'flashtool_rst',
    'select_spi_channel', 'select_flashtool_mode',
    'select_FlashTool_current_sensor_mode', 'select_spi_ch1_mode',
]

BISS_IO_METHODS = [
    'biss_set_bank', 'biss_write', 'biss_write_word', 'biss_write_command',
    'biss_read_state_flags', 'biss_read_registers',
    'biss_read_snum', 'biss_read_HSI', 'biss_read_progver',
    'biss_read_calibration_temp_vcc', 'biss_read_command_state',
    'biss_addr_readb', 'biss_addr_read',
    'biss_read_flags_flashCRC', 'biss_read_flags',
    'biss_read_angle_once',
    'biss_zeroing', 'biss_set_dir_cw', 'biss_set_dir_ccw', 'biss_set_shift',
    'send_data_to_device',
]

DATA_STREAMING_METHODS = [
    'read_data', 'read_data_enc1_enc2_SPI', 'read_data_enc1_AB_enc2_SPI',
    'read_enc2_current', 'read_instant_angle_enc_SPI',
    'read_instant_angle_packet_enc_SPI',
]

BOOTLOADER_METHODS = [
    'biss_cmd_reboot2bl', 'reboot_to_bl', 'reboot_to_fw',
    'read_fw_bl_ver', 'read_memory_state_bl', '_decode_memory_state_bl',
    'check_main_fw_crc32', 'download_fw_to_ft',
    'enter_bl_biss_encoder', 'enter_bl_irs', 'enter_fw_irs', 'set_pos_irs',
]

CORE_METHODS = [
    '__enter__', '__exit__', 'close', 'register_cleanup',
    'enable_signal_handling', '_signal_handler', '_default_cleanup',
]

ALL_METHODS = (
    SERIAL_IO_METHODS + ENCODER_CONTROL_METHODS + BISS_IO_METHODS
    + DATA_STREAMING_METHODS + BOOTLOADER_METHODS + CORE_METHODS
)


class TestMethodPresence:
    @pytest.mark.parametrize("method", SERIAL_IO_METHODS)
    def test_serial_io_methods(self, method):
        assert hasattr(FlashTool, method), f"FlashTool missing SerialIOMixin.{method}"

    @pytest.mark.parametrize("method", ENCODER_CONTROL_METHODS)
    def test_encoder_control_methods(self, method):
        assert hasattr(FlashTool, method), f"FlashTool missing EncoderControlMixin.{method}"

    @pytest.mark.parametrize("method", BISS_IO_METHODS)
    def test_biss_io_methods(self, method):
        assert hasattr(FlashTool, method), f"FlashTool missing BiSSIOMixin.{method}"

    @pytest.mark.parametrize("method", DATA_STREAMING_METHODS)
    def test_data_streaming_methods(self, method):
        assert hasattr(FlashTool, method), f"FlashTool missing DataStreamingMixin.{method}"

    @pytest.mark.parametrize("method", BOOTLOADER_METHODS)
    def test_bootloader_methods(self, method):
        assert hasattr(FlashTool, method), f"FlashTool missing BootloaderMixin.{method}"

    @pytest.mark.parametrize("method", CORE_METHODS)
    def test_core_methods(self, method):
        assert hasattr(FlashTool, method), f"FlashTool missing core method {method}"
