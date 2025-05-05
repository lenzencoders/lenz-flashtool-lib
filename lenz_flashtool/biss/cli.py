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

Usage:
    >>> python -m lenz_flashtool.biss.cli <command> [arguments]

Example Commands:
    >>> python -m lenz_flashtool.biss.cli run
    >>> python -m lenz_flashtool.biss.cli registers 2
    >>> python -m lenz_flashtool.biss.cli reg 0x02 0x10
    >>> python -m lenz_flashtool.biss.cli hex 41 82 AA55FF
    >>> python -m lenz_flashtool.biss.cli readserial
    >>> python -m lenz_flashtool.biss.cli sendhexfile SAB039_1_1_4.hex
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
from ..flashtool import FlashTool, biss_send_hex
from ..flashtool import generate_hex_line
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
        self.ft.biss_write_word(BiSSBank.CMD_REG_INDEX, 0, cmd_data)
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

    @staticmethod
    def _std(ans2, degrs, degree_sign, mins, secs):
        """stdout format"""
        sys.stdout.write("\r" + f'[{ans2}]: \t {str(degrs):>3}{degree_sign} {str(mins):2}\' {str(secs):2}\"' + '\t\t')
        sys.stdout.flush()

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
