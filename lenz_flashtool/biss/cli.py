"""

LENZ BiSS Encoder Command Line Interface Module

Provides a command-line interface for interacting with LENZ BiSS encoders through
the FlashTool library. Supports all major device operations including register access,
command execution, and device information reading.

Features:

- Direct register reading (single/bank/range)
- Predefined command execution
- Raw hex command sending
- Serial number and device info reading
- Comprehensive error handling
- Sending hex files to the encoder
- FlashTool mode selection
- SPI channel selection
- Multi-encoder data reading (SPI-SPI and AB-SPI modes)
- FlashTool firmware and bootloader version reading

Usage:
    >>> python -m lenz_flashtool.biss.cli <command> [arguments]

Example Commands:
    >>> python -m lenz_flashtool.biss.cli run
    >>> python -m lenz_flashtool.biss.cli registers 2
    >>> python -m lenz_flashtool.biss.cli reg 0x02 0x10
    >>> python -m lenz_flashtool.biss.cli hex 41 82 AA55FF
    >>> python -m lenz_flashtool.biss.cli readserial
    >>> python -m lenz_flashtool.biss.cli sendhexfile SAB039_1_1_4.hex
    >>> python -m lenz_flashtool.biss.cli setmode spi_spi
    >>> python -m lenz_flashtool.biss.cli setspi channel1
    >>> python -m lenz_flashtool.biss.cli read_dual_spi_spi 0.1
    >>> python -m lenz_flashtool.biss.cli read_dual_ab_spi 2.0 data.csv
    >>> python -m lenz_flashtool.biss.cli readversions
"""
#
# r'''
#  _     _____ _   _ _____   _____ _   _  ____ ___  ____  _____ ____  ____
# | |   | ____| \ | |__  /  | ____| \ | |/ ___/ _ \|  _ \| ____|  _ \/ ___|
# | |   |  _| |  \| | / /   |  _| |  \| | |  | | | | | | |  _| | |_) \___ \
# | |___| |___| |\  |/ /_   | |___| |\  | |__| |_| | |_| | |___|  _ < ___) |
# |_____|_____|_| \_/____|  |_____|_| \_|\____\___/|____/|_____|_| \_|____/
#

import sys
import logging
import time
from typing import List
from ..flashtool import FlashTool, biss_send_hex, generate_hex_line
from ..utils.termcolors import TermColors
from . import (
    BiSSBank,
    biss_commands
)
try:
    import colorama
    colorama.init()
except ImportError:
    pass


class BiSSCommandLine:
    """Command line interface for BiSS encoder operations"""

    def __init__(self, flashtool: FlashTool):
        """
        Initialize with a FlashTool instance

        Args:
            flashtool: Initialized FlashTool object
        """
        self.ft = (flashtool
                   .register_cleanup(self._script_cleanup)
                   .enable_signal_handling())
        self.logger = logging.getLogger(__name__)
        self.exit_flag = False

    def _script_cleanup(self):
        """Cleanup function"""
        # Get rid of logging level reset
        logging.getLogger('lenz_flashtool.flashtool.core').setLevel(logging.WARNING)

        logging.info('Performing script cleanup...')

        print('', end="\n", flush=True)
        # logging.info('Ctrl-c was pressed. Wrapping up...')
        self.exit_flag = True  # Set the flag to exit the loop

    def _show_usage(self, script_name: str) -> None:
        """Display command usage information"""
        print("LENZ BiSS Encoder Command Line Interface\n")
        print(f"Usage: {script_name} <command> [arguments]\n")
        print("Available commands:")
        for cmd, (_, desc) in biss_commands.items():
            print(f"  {cmd.ljust(14)} - {desc}")
        print("\nRegister Access:")
        print("  registers [bank]         - Read all registers in specified bank (default: service bank 2)")
        print("  reg <addr> <len>         - Read specific register(s) at hex address with byte length")
        print("                             Example: reg 0x1A 2  - Reads 2 bytes from address 0x1A")
        print("  regb <bank> <addr> <len> - Read registers in specified bank at hex address")
        print("                             Example: regb 1 0x10 4 - Reads 4 bytes from BiSS C bank")
        print("\nDevice Information:")
        print("  readserial               - Read encoder serial number, manufacturing date, device ID, and firmware version")
        print("  readhsi                  - Read hardware status indicator")
        print("\nAdvanced Operation:")
        print("  hex <addr> <cmd> <data>  - Send custom hexadecimal FlashTool command sequence")
        print("                             Format: <target_addr> <command_byte> <data_bytes...>")
        print("                             Examples: hex 0x0 0x0B 0x10    - Turn off power of first channel")
        print("                                       hex 0x40 0x82 0x11   - Read 0x40 register, any <data> defines lenght.")
        print("                                       hex 0x40 0x82 0x1111 - Read 0x40 and 0x41 registers, ")
        print("                                                              <data> used only for length.")
        print("  sendhexfile <filename>   - Send a hex file to the encoder")
        print("                             Example: sendhexfile SAB039_1_1_4.hex")
        print("\nFlashTool Configuration:")
        print("  setmode <mode>           - Set FlashTool operation mode")
        print("                             Modes: spi_spi, ab_uart, spi_uart_irs, ab_spi, default_spi")
        print("  setspi <channel>         - Select SPI channel (channel1 or channel2)")
        print("\nDual Encoder Reading:")
        print("  read_dual_spi_spi <time> [output.csv] - Read data from both encoders via SPI interface")
        print("                             Both encoders use SPI protocol")
        print("                             Example: read_dual_spi_spi 0.1           - Read for 100ms")
        print("                                      read_dual_spi_spi 2.0 data.csv   - Save to CSV file")
        print("  read_dual_ab_spi <time> [output.csv]  - Read data from encoders in mixed mode")
        print("                             Encoder 1: AB interface, Encoder 2: SPI interface")
        print("                             Example: read_dual_ab_spi 0.5             - Read for 500ms")
        print("                                      read_dual_ab_spi 3.0 data.csv    - Save to CSV file")
        print("\nSystem Information:")
        print("  readversions             - Read FlashTool firmware and bootloader versions")
        print("                             Shows versions in readable format (e.g., 0.1.0.11)")

    def execute_command(self, args: List[str]) -> None:
        """
        Execute a command provided via command-line arguments.

        Supports a wide range of operations with LENZ BiSS encoders through the FlashTool
        backend. This function serves as the central dispatcher for interpreting CLI
        arguments and executing the appropriate action.

        Args:
            args (List[str]): A list of command-line arguments (typically from sys.argv).

        Supported Commands:
            run
                - Description: Runs the encoder or initiates default operational mode.
                - Usage: run

            registers [bank]
                - Description: Reads all registers in a given bank.
                - Default bank: 2 (service bank)
                - Usage: registers              # reads from bank 2
                        registers 1           # reads from bank 1

            reg <addr> <len>
                - Description: Reads a specific number of bytes from a register address.
                - Address and length must be in hex or decimal format.
                - Usage: reg 0x10 2            # reads 2 bytes from address 0x10

            regb <bank> <addr> <len>
                - Description: Reads registers from a specific bank and address.
                - Usage: regb 1 0x10 4         # reads 4 bytes from address 0x10 in bank 1

            hex <addr> <cmd> [data...]
                - Description: Sends a raw command composed of address, command byte, and optional data bytes.
                - The data is sent as-is and interpreted by the encoder.
                - Usage:
                    hex 0x00 0x0B 0x10         # turns off power of first channel
                    hex 0x40 0x82 0x11         # reads one byte from register 0x40
                    hex 0x40 0x82 0x1122       # reads two bytes from 0x40 and 0x41
                    hex 0x80 0x91              # generic command with no data

            readserial
                - Description: Reads device serial number, date of manufacture, firmware version, and ID.
                - Usage: readserial

            readhsi
                - Description: Reads the hardware status indicator.
                - Usage: readhsi

            sendhexfile <filename>
                - Description: Sends a hex file to the encoder.
                - Usage: sendhexfile <filename.hex>

            setmode <mode>
                - Description: Sets the FlashTool communication mode for both channels.
                - Available modes:
                    spi_spi      - Channel 1: SPI, Channel 2: SPI
                    ab_uart      - Channel 1: AB signal, Channel 2: UART
                    spi_uart_irs - Channel 1: SPI, Channel 2: UART for IRS encoders
                    ab_spi       - Channel 1: AB signal, Channel 2: SPI
                    default_spi  - Default mode: Channel 1: None, Channel 2: SPI
                - Usage: setmode spi_spi        # sets SPI on both channels
                        setmode ab_uart         # sets AB on channel1, UART on channel2

            setspi <channel>
                - Description: Selects which SPI channel to use for communication.
                - Available channels:
                    channel1     - Select SPI channel 1
                    channel2     - Select SPI channel 2
                - Usage: setspi channel1        # selects channel 1 for SPI communication
                        setspi channel2         # selects channel 2 for SPI communication

            read_dual <time>
                - Description: Reads data from both encoders simultaneously via SPI interface.
                - Requires FlashTool mode to be set to 'spi_spi' using setmode command first.
                - Reads encoder data for specified duration and displays sample values.
                - Time parameter specifies reading duration in seconds (can be fractional).
                - Usage: read_dual 0.1          # reads data for 100 milliseconds
                        read_dual 2.0           # reads data for 2 seconds

            readversions
                - Description: Reads firmware and bootloader versions from the FlashTool device.
                - Automatically reboots device to bootloader mode, reads versions, and reboots back.
                - Returns version strings as 8-character hexadecimal values.
                - Usage: readversions

            <predefined command>
                - Description: Executes a predefined command from the biss_commands registry.
                - Examples:
                    run
                    ampcalibrate
                    reboot2bl
                    zeroing
                - Use `_show_usage()` or run without arguments to list all predefined commands.

        Raises:
            ValueError: If arguments are missing or invalid.
            FlashToolError: On communication or device interaction failure.

        Notes:
            - All addresses and data bytes can be in either hexadecimal (0xNN) or decimal (NN) format.
            - The method logs each step and captures errors for user-friendly CLI output.
            - For read_dual command, ensure the encoder is properly connected and powered.
            - The setmode command must be issued before read_dual when using SPI-SPI configuration.
            - Some commands require specific hardware configurations and encoder types.
        """

        if len(args) < 2:
            self._show_usage(args[0])
            sys.exit(1)

        command = args[1].lower()

        try:
            if command in biss_commands:
                self._send_biss_command(command)
            elif command == "registers":
                self._read_registers(args)
            elif command == "flags":
                self._read_flags()
            elif command == "ctv":
                self._ctv()
            elif command == "reg":
                self._read_register(args)
            elif command == "regb":
                self._read_bank_register(args)
            elif command == "hex":
                self._send_hex(args)
            elif command == "readserial":
                self._read_serial()
            elif command == "readhsi":
                self._read_hsi()
            elif command == "angle":
                self._read_angle_once()
            elif command == "angleloop":
                self._read_angle_loop()
            elif command == "sendhexfile":
                self._send_hex_file(args)
            elif command == "setmode":
                self._set_flashtool_mode(args)
            elif command == "setspi":
                self._set_spi_channel(args)
            # elif command == "read_dual":
            #     self._read_dual_encoders(args)
            elif command == "read_dual_spi_spi":
                self._read_dual_encoders_spi_spi(args)
            elif command == "read_dual_ab_spi":
                self._read_dual_encoders_ab_spi(args)
            elif command == "readversions":
                self._read_versions()
            else:
                raise ValueError(f"Unknown command: {command}")
        except ValueError as e:
            self.logger.error("Invalid input: %s", e)
            self._show_usage(args[0])
            sys.exit(1)
        except Exception as e:
            self.logger.error("Operation failed: %s", e)
            sys.exit(1)

    def _send_biss_command(self, command: str) -> None:
        """Send a predefined BiSS command"""
        cmd_data = [
            biss_commands[command][0] & 0xFF,
            (biss_commands[command][0] >> 8) & 0xFF
        ]
        self.ft.biss_write_word(BiSSBank.CMD_REG_INDEX, cmd_data)
        time.sleep(0.3)
        self.ft.biss_read_flags()

    def _read_registers(self, args: List[str]) -> None:
        """Read all registers in specified bank"""
        bank = int(args[2]) if len(args) > 2 else 2  # Default to service bank
        self.ft.biss_read_registers(bank)

    def _read_flags(self) -> None:
        """Read and display status flags"""
        flags, cmd_state = self.ft.biss_read_flags()
        print("\nDevice Status:")
        print("-" * 40)
        for flag in flags:
            print(f"  {flag}")
        print(f"\nCommand State: {cmd_state[0]}")
        print("-" * 40)

    def _ctv(self) -> None:
        """Read and display calibration, temperature and Vcc data"""
        self.ft.biss_read_calibration_temp_vcc()

    def _read_register(self, args: List[str]) -> None:
        """Read specific register range"""
        if len(args) < 3:
            raise ValueError("Usage: reg <address> <length>")

        address = self._parse_hex(args[2])
        length = self._parse_hex(args[3]) if len(args) > 3 else 1  # default one register

        print(f"\nReading registers {hex(address)}-{hex(address + length - 1)}:")
        result = self.ft.biss_addr_read(address, length)
        self._print_register_data(result)

    def _read_bank_register(self, args: List[str]) -> None:
        """Read registers in specific bank"""
        if len(args) < 4:
            raise ValueError("Usage: regb <bissbank> <address> <length>")

        bank = self._parse_hex(args[2])
        address = self._parse_hex(args[3])
        length = self._parse_hex(args[4]) if len(args) > 4 else 1  # default one register

        print(f"\nReading bank {bank}, registers {hex(address)}-{hex(address + length - 1)}:")
        result = self.ft.biss_addr_readb(bank, address, length)
        self._print_register_data(result)

    def _send_hex(self, args: List[str]) -> None:
        """Send raw hex command"""
        if len(args) < 5:
            raise ValueError("Usage: hex <address> <command> <data_hex_str>")

        address = self._parse_hex(args[2])
        command = self._parse_hex(args[3])
        hex_str = args[4].replace('0x', '').replace(' ', '')

        try:
            data = bytes.fromhex(hex_str)
        except ValueError:
            raise ValueError("Invalid hex string format")

        hex_line = generate_hex_line(address, command, data)
        print("Sending hex line: %s", hex_line)
        self.ft.hex_line_send(hex_line)

        if len(data) > 0:
            print("\nTrying to read response data...")
            response = self.ft.port_read(len(data))  # +1 for checksum
            self._print_register_data(response)

    def _read_serial(self) -> None:
        """Read device serial information"""
        bootloader, serial, mfg_date, program = self.ft.biss_read_snum()

        print("\nDevice Information:")
        print("-" * 40)
        print(f"Serial Number:   \t {serial}")
        print(f"Firmware Version:\t {program}")
        print(f"Manufacture Date:\t {mfg_date}")
        print(f"Bootloader:      \t {bootloader}")
        print("-" * 40)

    def _read_hsi(self) -> None:
        """Read hardware status indicator"""
        hsi = self.ft.biss_read_HSI()
        print(f"\n{TermColors.Green}HSI: {hsi}{TermColors.ENDC}")

    def _read_angle_once(self) -> None:
        """Read angle"""
        self.ft.biss_read_angle_once()

    def _read_angle_loop(self) -> None:
        """Read angle in loop"""
        degree_sign = "\N{DEGREE SIGN}"
        res = 2**24
        while not self.exit_flag:
            _, ans = self.ft.read_data_enc1_enc2_SPI(0.01, False)
            if self.exit_flag:  # Check the flag immediately after reading
                break
            ang = int(ans[0]) * 360 / res
            degrs = int(ang)
            mins = int((ang - degrs) * 60)
            secs = int((ang - degrs - (mins / 60)) * 3600)
            self._std(ans[0], degrs, degree_sign, mins, secs)

    def _send_hex_file(self, args: List[str]) -> None:
        """Send a hex file to the encoder"""
        if len(args) < 3:
            raise ValueError("Usage: sendhexfile <filename> [pbar]")

        filename = args[2]
        pbar = len(args) > 3 and args[3].lower() in ('true', '1', 't', 'y', 'yes')

        print(f"\nSending hex file: {filename} (Progress bar: {'enabled' if pbar else 'disabled'})")
        biss_send_hex(filename, pbar=pbar)
        print(f"Successfully sent hex file: {filename}")

    def _set_flashtool_mode(self, args: List[str]) -> None:
        """Set the FlashTool operation mode"""
        if len(args) < 3:
            raise ValueError("Usage: setmode <mode>")
        
        mode = args[2].lower()
        self.ft.select_flashtool_mode(mode)  # Прямой вызов
        print(f"{TermColors.Green}FlashTool mode set to: {mode}{TermColors.ENDC}")

    def _set_spi_channel(self, args: List[str]) -> None:
        """Set the SPI channel"""
        if len(args) < 3:
            raise ValueError("Usage: setspi <channel>")
        
        channel = args[2].lower()
        self.ft.select_spi_channel(channel)
        print(f"{TermColors.Green}SPI channel set to: {channel}{TermColors.ENDC}")

    def _read_dual_encoders_spi_spi(self, args: List[str]) -> None:
        """
        Read data from both encoders in SPI-SPI mode.
        
        Both encoders communicate via SPI interface.
        
        Args:
            args: Command line arguments containing read time and optional output file
        """
        if len(args) < 3:
            raise ValueError("Usage: read_dual_spi_spi <read_time_seconds> [output_file.csv]")
        
        try:
            read_time = float(args[2])
        except ValueError:
            raise ValueError("read_time must be a number")
        
        # Optional filename for saving data
        save_file = args[3] if len(args) > 3 else None
        
        self.ft.select_flashtool_mode('spi_spi')
        self.ft.encoder_power_cycle()
        self.ft.encoder_ch1_power_cycle()

        enc1, enc2 = self.ft.read_data_enc1_enc2_SPI(read_time, status=True)
        
        self._print_dual_encoder_results(enc1, enc2, save_file, mode="SPI-SPI")

    def _read_dual_encoders_ab_spi(self, args: List[str]) -> None:
        """
        Read data from both encoders in AB-SPI mode.
        
        Encoder 1 communicates via AB interface, Encoder 2 via SPI.
        
        Args:
            args: Command line arguments containing read time and optional output file
        """
        if len(args) < 3:
            raise ValueError("Usage: read_dual_ab_spi <read_time_seconds> [output_file.csv]")
        
        try:
            read_time = float(args[2])
        except ValueError:
            raise ValueError("read_time must be a number")
        
        # Optional filename for saving data
        save_file = args[3] if len(args) > 3 else None
        
        self.ft.select_flashtool_mode('ab_spi')
        self.ft.encoder_power_cycle()
        self.ft.encoder_ch1_power_cycle()

        enc1, enc2 = self.ft.read_data_enc1_AB_enc2_SPI(read_time, status=True)
        
        self._print_dual_encoder_results(enc1, enc2, save_file, mode="AB-SPI")

    def _read_versions(self) -> None:
        """Read FlashTool firmware and bootloader versions"""
        self.ft.reboot_to_bl()
        fw_ver_hex, bl_ver_hex = self.ft.read_fw_bl_ver()
        self.ft.reboot_to_fw()
        
        fw_ver_readable = self._hex_to_version(fw_ver_hex)
        bl_ver_readable = self._hex_to_version(bl_ver_hex)
        
        print(f"Firmware: {fw_ver_readable}, Bootloader: {bl_ver_readable}")

    @staticmethod
    def _print_dual_encoder_results(enc1, enc2, save_file: str = None, mode: str = "") -> None:
        """
        Print and save results from dual encoder readings.
        
        Args:
            enc1: Data from encoder 1
            enc2: Data from encoder 2
            save_file: Optional CSV filename to save data
            mode: Mode description for display (e.g., "SPI-SPI" or "AB-SPI")
        """
        # Save to file if requested (without index column)
        if save_file:
            import csv
            with open(save_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Encoder1', 'Encoder2'])  # Header without index
                for e1, e2 in zip(enc1, enc2):
                    writer.writerow([int(e1), int(e2)])
            print(f"\n{TermColors.Green}Data saved to: {save_file}{TermColors.ENDC}")
        
        # Console output - summary
        mode_display = f"Mode: {mode}" if mode else ""
        print(f"\n{TermColors.Green}Encoder Data Summary {mode_display}{TermColors.ENDC}")
        print("=" * 60)
        print(f"Total samples:   {len(enc1)} readings per encoder")
        print("-" * 60)
        
        # Convert numpy ints to Python ints for clean display
        enc1_clean = [int(x) for x in enc1]
        enc2_clean = [int(x) for x in enc2]
        
        # First 5 values
        print(f"First 5 values:")
        print(f"  Encoder 1: {enc1_clean[:5]}")
        print(f"  Encoder 2: {enc2_clean[:5]}")
        
        # Last 5 values (if more than 10 total samples)
        if len(enc1) > 10:
            print(f"\nLast 5 values:")
            print(f"  Encoder 1: {enc1_clean[-5:]}")
            print(f"  Encoder 2: {enc2_clean[-5:]}")
        elif len(enc1) > 5:
            print(f"\nRemaining values:")
            print(f"  Encoder 1: {enc1_clean[5:]}")
            print(f"  Encoder 2: {enc2_clean[5:]}")
        
        print("-" * 60)
    
    def _parse_hex(self, value: str) -> int:
        """Safely parse hex or decimal string"""
        try:
            return int(value, 16 if value.startswith('0x') else 10)
        except ValueError:
            raise ValueError(f"Invalid number format: {value}")

    def _print_register_data(self, data) -> None:
        """Format register data for display"""
        print(f'{TermColors.Green}{data}{TermColors.ENDC}')
        if hasattr(data, 'tolist'):  # numpy array
            data = data.tolist()

        for i, byte in enumerate(data):
            print(f"{TermColors.DarkGray}{i:04X}: {byte:02X} ({byte:3d}){TermColors.ENDC}")

    @staticmethod
    def _hex_to_version(hex_str: str) -> str:
        """Convert hex version string to dotted decimal format"""
        hex_value = int(hex_str, 16) if isinstance(hex_str, str) else hex_str
        
        major = (hex_value >> 24) & 0xFF
        minor = (hex_value >> 16) & 0xFF
        patch = (hex_value >> 8) & 0xFF
        build = hex_value & 0xFF
        
        if build == 0:
            return f"{major}.{minor}.{patch}"
        return f"{major}.{minor}.{patch}.{build}"

    @staticmethod
    def _std(ans2, degrs, degree_sign, mins, secs):
        """stdout format"""
        sys.stdout.write("\r" + f'[{ans2}]: \t {str(degrs):>3}{degree_sign} {str(mins):2}\' {str(secs):2}\"' + '\t\t')
        sys.stdout.flush()


def main():
    """Command line entry point, making the library script executes directly:
    >>> python -m lenz_flashtool.biss.cli <command>
    """
    import lenz_flashtool as lenz

    # Configure logging
    lenz.init_logging(
        # TODO review each function's output and change stdout_level to .WARNING
        logfilename='biss_cli.log',
        stdout_level=logging.DEBUG,
        file_level=logging.DEBUG
    )

    try:
        with lenz.FlashTool() as ft:
            cli = BiSSCommandLine(ft)
            cli.execute_command(sys.argv)
    except Exception as e:
        logging.critical("Fatal error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
