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
    >>> python -m lenz_flashtool.biss.cli readserial_ils
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
from enum import Enum
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


class ValidModes(Enum):
    SPI_SPI = "spi_spi"
    AB_UART = "ab_uart"
    SPI_UART_IRS = "spi_uart_irs"
    AB_SPI = "ab_spi"
    DEFAULT_SPI = "default_spi"

class ValidSPIChannels(Enum):
    CHANNEL1 = "channel1"
    CHANNEL2 = "channel2"

class BiSSCommandLine:
    """Command line interface for BiSS encoder operations"""

    def __init__(self, flashtool: FlashTool, verbose: int = 0, 
             interactive: bool = False, config: str = None):
        """
        Initialize with a FlashTool instance

        Args:
            flashtool: Initialized FlashTool object
        """
        self.verbose = verbose
        self.interactive = interactive
        self.config_file = config
        self.output_format = 'text'
        self.ft = (flashtool
                   .register_cleanup(self._script_cleanup)
                   .enable_signal_handling())
        self.logger = logging.getLogger(__name__)
        self.exit_flag = False

        if interactive:
            self._setup_completer()
            self._interactive_mode()
        
        if config:
            self.execute_batch(config)

    def _interactive_mode(self) -> None:
        """Interactive command shell for BiSS encoder"""
        print(f"{TermColors.Cyan}BiSS Encoder Interactive Mode{TermColors.ENDC}")
        print("Type 'help' for commands, 'exit' to quit")

        if sys.platform == 'win32' and not self._has_readline():
            print(f"{TermColors.Yellow}Note: Tab completion not available. Install 'pyreadline3' for better experience.{TermColors.ENDC}")
            print(f"{TermColors.Yellow}Command: pip install pyreadline3{TermColors.ENDC}")
        
        print()
        
        while not self.exit_flag:
            try:
                cmd = input(f"{TermColors.Green}biss>{TermColors.ENDC} ").strip()
                
                if not cmd:
                    continue
                    
                if cmd.lower() in ['exit', 'quit']:
                    print("Exiting interactive mode...")
                    break
                elif cmd.lower() == 'help':
                    self._show_usage('interactive')
                    print()
                else:
                    parts = cmd.split()
                    command = parts[0]
                    args = parts[1:] if len(parts) > 1 else []

                    commands_requiring_args = {
                        'read_dual_spi_spi': 'read_time_seconds [output_file.csv]',
                        'read_dual_ab_spi': 'read_time_seconds [output_file.csv]',
                        'reg': '<address> <length>',
                        'regb': '<bank> <address> <length>',
                        'hex': '<address> <command> <data_hex_str>',
                        'sendhexfile': '<filename> [pbar]',
                        'download_fw': '<filename> [pbar]',
                        'setmode': '<mode>',
                        'setspi': '<channel>',
                        'registers': '[bank]'
                    }
                    if command in commands_requiring_args and not args:
                        needed_args = commands_requiring_args[command]
                        print(f"{TermColors.Yellow}Command '{command}' requires arguments: {needed_args}{TermColors.ENDC}")
                        print(f"{TermColors.DarkGray}Example: {command} {self._get_example_args(command)}{TermColors.ENDC}")
                        print()
                        continue
                    
                    # Execute command
                    self.execute_command(['interactive', command] + args)
                    print()
                    
            except KeyboardInterrupt:
                print(f"\n{TermColors.Yellow}Exiting interactive mode...{TermColors.ENDC}")
                self.exit_flag = True
                break
            except EOFError:
                print(f"\n{TermColors.Yellow}Exiting...{TermColors.ENDC}")
                break
            except Exception as e:
                print(f"{TermColors.Red}Error: {e}{TermColors.ENDC}")
                if self.verbose >= 2:
                    import traceback
                    traceback.print_exc()
                print()

    def _get_example_args(self, command: str) -> str:
        """Get example arguments for a command"""
        examples = {
            'read_dual_spi_spi': '0.1 data.csv',
            'read_dual_ab_spi': '0.5 output.csv',
            'reg': '0x10 2',
            'regb': '1 0x10 4',
            'hex': '0x40 0x82 0x11',
            'sendhexfile': 'firmware.hex True',
            'download_fw': 'app_1.0.10.hex True',
            'setmode': 'spi_spi',
            'setspi': 'channel1',
            'registers': '2'
        }
        return examples.get(command, '<required arguments>')

    def _has_readline(self) -> bool:
        """Check if readline is available"""
        try:
            import readline
            return True
        except ImportError:
            try:
                import pyreadline3
                return True
            except ImportError:
                return False

    def _setup_completer(self):
        """Setup command completion for interactive mode"""
        commands = list(biss_commands.keys()) + [
            'registers', 'reg', 'regb', 'hex', 'readserial', 'readserial_ils',
            'readhsi', 'sendhexfile', 'setmode', 'setspi', 'read_dual_spi_spi',
            'read_dual_ab_spi', 'readversions', 'download_fw', 'help', 'exit'
        ]
        
        class Completer:
            def __init__(self, options):
                self.options = sorted(options)
                self.matches = []
                self.last_text = ""
            
            def complete(self, text, state):
                """Return the next possible completion for 'text'."""
                # Store current text
                if state == 0:
                    self.last_text = text
                    # Find all matches
                    self.matches = [opt for opt in self.options if opt.startswith(text)]
                    
                    # If no matches
                    if not self.matches:
                        return None
                    
                    # If only one match
                    if len(self.matches) == 1:
                        return self.matches[0]
                    
                    # Multiple matches - find common prefix
                    common_prefix = self._common_prefix(self.matches)
                    
                    # If common prefix is longer than current text
                    if common_prefix and len(common_prefix) > len(text):
                        return common_prefix
                    
                    # Show all matches
                    if state == 0:
                        self._display_matches(self.matches, text)
                        return None
                
                # Return match for subsequent tab presses
                try:
                    if state > 0 and state <= len(self.matches):
                        return self.matches[state - 1]
                except IndexError:
                    pass
                return None
            
            def _common_prefix(self, strings):
                """Find common prefix of strings"""
                if not strings:
                    return ''
                prefix = strings[0]
                for s in strings[1:]:
                    while not s.startswith(prefix):
                        prefix = prefix[:-1]
                        if not prefix:
                            return ''
                return prefix
            
            def _display_matches(self, matches, current_text):
                """Display matches cleanly"""
                # Save terminal state
                sys.stdout.write('\n')
                
                # Format in columns (2 columns for better readability)
                col_width = max(len(m) for m in matches) + 2
                num_cols = max(1, 80 // col_width)
                
                for i, match in enumerate(matches):
                    # Highlight the differing part
                    if current_text:
                        # Show the full command
                        sys.stdout.write(f"  {match:<{col_width}}")
                    else:
                        sys.stdout.write(f"  {match:<{col_width}}")
                    
                    if (i + 1) % num_cols == 0:
                        sys.stdout.write('\n')
                
                if len(matches) % num_cols != 0:
                    sys.stdout.write('\n')
                
                # Restore prompt
                sys.stdout.write(f"{TermColors.Green}biss>{TermColors.ENDC} {current_text}")
                sys.stdout.flush()
        
        # Initialize readline
        try:
            import readline
            
            completer = Completer(commands)
            readline.set_completer(completer.complete)
            readline.parse_and_bind('tab: complete')
            readline.set_completer_delims(' \t\n;')
            
            # Disable default match display
            if hasattr(readline, 'set_completion_display_matches_hook'):
                readline.set_completion_display_matches_hook(lambda *args: None)
            
            # History setup
            import os
            history_file = os.path.expanduser('~/.biss_cli_history')
            try:
                readline.read_history_file(history_file)
            except FileNotFoundError:
                pass
            
            import atexit
            atexit.register(lambda: readline.write_history_file(history_file))
            
            self.logger.info("Completer initialized")
            
        except ImportError:
            # Try pyreadline3 for Windows
            try:
                import pyreadline3 as readline
                completer = Completer(commands)
                readline.set_completer(completer.complete)
                readline.parse_and_bind('tab: complete')
                self.logger.info("Pyreadline3 completer initialized")
            except ImportError:
                if self.verbose:
                    self.logger.warning("No readline module available")

    def _print_formatted(self, data: dict, text_func=None):
        """Print data in configured format"""
        if self.output_format == 'json':
            import json
            print(json.dumps(data, indent=2, default=str))
        elif self.output_format == 'csv':
            import csv
            import sys
            if isinstance(data, dict):
                writer = csv.DictWriter(sys.stdout, fieldnames=data.keys())
                writer.writeheader()
                writer.writerow(data)
            elif isinstance(data, list) and data and isinstance(data[0], dict):
                writer = csv.DictWriter(sys.stdout, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            else:
                writer = csv.writer(sys.stdout)
                for row in data:
                    writer.writerow(row)
        else:
            if text_func:
                text_func()
            else:
                print(data)
        
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
        print("  readserial_ils           - Read ILS encoder serial number (AB/UART mode, channel 2)")
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
        print("  download_fw              - Download FlashTool firmware hex")
        print("                             Example: download_fw app_1.0.10.hex True")
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
            
            readserial_ils
                - Description: Reads ILS encoder serial information using AB/UART mode on channel 2.
                - Usage: readserial_ils

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
            if self.interactive:
                print(f"{TermColors.Yellow}No command specified. Type 'help' for available commands.{TermColors.ENDC}")
                return
            self._show_usage(args[0] if args else 'biss')
            sys.exit(1)

        command = args[1].lower()

        if self.interactive and command in ['read_dual_spi_spi', 'read_dual_ab_spi']:
            if len(args) < 3:
                print(f"{TermColors.Yellow}Usage: {command} <time_in_seconds> [output_file.csv]{TermColors.ENDC}")
                print(f"{TermColors.DarkGray}Example: {command} 0.1{TermColors.ENDC}")
                return

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
            elif command == 'readserial_ils':
                self._read_serial_ils()
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
            elif command == "read_dual_spi_spi":
                self._read_dual_encoders_spi_spi(args)
            elif command == "read_dual_ab_spi":
                self._read_dual_encoders_ab_spi(args)
            elif command == "readversions":
                self._read_versions()
            elif command == "download_fw":
                self._download_fw_to_ft(args)
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
        
        data = {
            'flags': list(flags),
            'command_state': cmd_state[0] if cmd_state else None
        }
        
        def text_output():
            print("\nDevice Status:")
            print("-" * 40)
            for flag in flags:
                print(f"  {flag}")
            print(f"\nCommand State: {cmd_state[0]}")
            print("-" * 40)
        
        self._print_formatted(data, text_output)

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
        
        data = {
            'serial_number': serial,
            'firmware_version': program,
            'manufacture_date': mfg_date,
            'bootloader_version': bootloader
        }

        def text_output():
            print("\nDevice Information:")
            print("-" * 40)
            print(f"Serial Number:   \t {serial}")
            print(f"Firmware Version:\t {program}")
            print(f"Manufacture Date:\t {mfg_date}")
            print(f"Bootloader:      \t {bootloader}")
            print("-" * 40)

        self._print_formatted(data, text_output)

    def _read_serial_ils(self) -> None:
        """Read device serial information ILS encoder"""
        self.ft.select_flashtool_mode("ab_uart")
        self.ft.select_spi_channel("channel2")
        bootloader, serial, mfg_date, program = self.ft.biss_read_snum()

        data = {
            'serial_number': serial,
            'firmware_version': program,
            'manufacture_date': mfg_date,
            'bootloader_version': bootloader
        }

        def text_output():
            print("\nDevice Information:")
            print("-" * 40)
            print(f"Serial Number:   \t {serial}")
            print(f"Firmware Version:\t {program}")
            print(f"Manufacture Date:\t {mfg_date}")
            print(f"Bootloader:      \t {bootloader}")
            print("-" * 40)

        self._print_formatted(data, text_output)

    def _read_hsi(self) -> None:
        """Read hardware status indicator"""
        hsi = self.ft.biss_read_HSI()

        data = {'hsi': hsi}

        def text_output():
            print(f"\n{TermColors.Green}HSI: {hsi}{TermColors.ENDC}")

        self._print_formatted(data, text_output)

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
        self._validate_mode(mode)
        self.ft.select_flashtool_mode(mode)  # Прямой вызов
        print(f"{TermColors.Green}FlashTool mode set to: {mode}{TermColors.ENDC}")

    def _set_spi_channel(self, args: List[str]) -> None:
        """Set the SPI channel"""
        if len(args) < 3:
            raise ValueError("Usage: setspi <channel>")
        
        channel = args[2].lower()
        self._validate_spi_channel(channel)
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
            if self.interactive:
                print(f"{TermColors.Yellow}Missing required argument: read_time_seconds{TermColors.ENDC}")
                print(f"{TermColors.DarkGray}Usage: read_dual_spi_spi <read_time_seconds> [output_file.csv]{TermColors.ENDC}")
                print(f"{TermColors.DarkGray}Example: read_dual_spi_spi 0.1 data.csv{TermColors.ENDC}")
                return
            else:
                raise ValueError("Usage: read_dual_spi_spi <read_time_seconds> [output_file.csv]")
        
        try:
            read_time = float(args[2])
        except ValueError:
            if self.interactive:
                print(f"{TermColors.Red}Error: read_time must be a number{TermColors.ENDC}")
                print(f"{TermColors.DarkGray}Example: read_dual_spi_spi 0.1{TermColors.ENDC}")
                return
            else:
                raise ValueError("read_time must be a number")
        
        # Optional filename for saving data
        save_file = args[3] if len(args) > 3 else None

        self.ft.select_flashtool_mode('spi_spi')
        self.ft.encoder_power_cycle()
        self.ft.encoder_ch1_power_cycle()

        enc1, enc2 = self.ft.read_data_enc1_enc2_SPI(read_time, status=True)
        
        self._print_dual_encoder_results(enc1, enc2, save_file, mode="SPI-SPI", output_format=self.output_format)

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
        
        self._print_dual_encoder_results(enc1, enc2, save_file, mode="AB-SPI", output_format=self.output_format)

    def _read_versions(self) -> None:
        """Read FlashTool firmware and bootloader versions"""
        self.ft.reboot_to_bl()
        fw_ver_hex, bl_ver_hex = self.ft.read_fw_bl_ver()
        self.ft.reboot_to_fw()
        
        fw_ver_readable = self._hex_to_version(fw_ver_hex)
        bl_ver_readable = self._hex_to_version(bl_ver_hex)

        data = {
            'firmware': {
                'hex': fw_ver_hex,
                'readable': fw_ver_readable
            },
            'bootloader': {
                'hex': bl_ver_hex,
                'readable': bl_ver_readable
            }
        }
        
        def text_output():
            print(f"Firmware: {fw_ver_readable}, Bootloader: {bl_ver_readable}")

        self._print_formatted(data, text_output)

    def _download_fw_to_ft(self, args: List[str]) -> None:
        """
        Download firmware to FlashTool device.
        
        This method:
        1. Reboots to bootloader
        2. Downloads the firmware hex file
        3. Reboots back to firmware mode
        
        Args:
            args: Command line arguments containing [filename, pbar]
            
        Example:
            download_fw app_1.0.10.hex True
            download_fw firmware.hex false
        """
        if len(args) < 3:
            raise ValueError("Usage: download_fw <filename> [pbar]")
        
        filename = args[2]
        pbar = len(args) > 3 and args[3].lower() in ('true', '1', 't', 'y', 'yes')

        self.ft.reboot_to_bl()
        print(f"\nSending hex file: {filename} (Progress bar: {'enabled' if pbar else 'disabled'})")
        self.ft.download_fw_to_ft(filename, max_retries=3, pbar=pbar)
        print(f"Firmware downloaded successfully: {filename}")
        self.ft.reboot_to_fw()

    @staticmethod
    def _print_dual_encoder_results(enc1, enc2, save_file: str = None, mode: str = "", output_format: str = 'text') -> None:
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
        
        # Convert numpy ints to Python ints for clean display
        enc1_clean = [int(x) for x in enc1]
        enc2_clean = [int(x) for x in enc2]

        data = {
            'mode': mode,
            'total_samples': len(enc1_clean),
            'encoder1': enc1_clean,
            'encoder2': enc2_clean,
            'statistics': {
                'encoder1_min': min(enc1_clean) if enc1_clean else None,
                'encoder1_max': max(enc1_clean) if enc1_clean else None,
                'encoder1_mean': sum(enc1_clean) / len(enc1_clean) if enc1_clean else None,
                'encoder2_min': min(enc2_clean) if enc2_clean else None,
                'encoder2_max': max(enc2_clean) if enc2_clean else None,
                'encoder2_mean': sum(enc2_clean) / len(enc2_clean) if enc2_clean else None,
            }
        }

        def text_output():
            mode_display = f"Mode: {mode}" if mode else ""
            print(f"\n{TermColors.Green}Encoder Data Summary {mode_display}{TermColors.ENDC}")
            print("=" * 60)
            print(f"Total samples:   {len(enc1)} readings per encoder")
            print("-" * 60)
            print(f"First 5 values:")
            print(f"  Encoder 1: {enc1_clean[:5]}")
            print(f"  Encoder 2: {enc2_clean[:5]}")
            
            if len(enc1) > 10:
                print(f"\nLast 5 values:")
                print(f"  Encoder 1: {enc1_clean[-5:]}")
                print(f"  Encoder 2: {enc2_clean[-5:]}")
            elif len(enc1) > 5:
                print(f"\nRemaining values:")
                print(f"  Encoder 1: {enc1_clean[5:]}")
                print(f"  Encoder 2: {enc2_clean[5:]}")
            print("-" * 60)

        if output_format == 'json':
            import json
            print(json.dumps(data, indent=2, default=str))
        elif output_format == 'csv':
            import csv
            import sys
            writer = csv.writer(sys.stdout)
            writer.writerow(['Index', 'Encoder1', 'Encoder2'])
            for i, (e1, e2) in enumerate(zip(enc1_clean, enc2_clean)):
                writer.writerow([i, e1, e2])
        else:
            text_output()
    
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

    def execute_batch(self, config_file: str) -> None:
        """Execute multiple commands from JSON configuration file"""
        import json
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
        except FileNotFoundError:
            self.logger.error(f"Config file not found: {config_file}")
            return
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in config file: {e}")
            return
        
        results = {}
        print(f"\n{TermColors.Cyan}Executing batch commands from: {config_file}{TermColors.ENDC}")
        print("=" * 60)
        
        for idx, cmd in enumerate(config.get('commands', []), 1):
            name = cmd.get('name', f'command_{idx}')
            command = cmd.get('command')
            cmd_args = cmd.get('args', [])
            
            if not command:
                print(f"{TermColors.Yellow}Warning: No command specified for {name}{TermColors.ENDC}")
                continue
            
            print(f"\n{TermColors.Cyan}[{idx}] Executing: {name}{TermColors.ENDC}")
            print(f"    Command: {command} {' '.join(cmd_args)}")
            
            try:
                # Execute the command
                self.execute_command([config_file, command] + cmd_args)
                results[name] = {'status': 'success', 'result': 'Command executed successfully'}
                print(f"{TermColors.Green}Success{TermColors.ENDC}")
            except Exception as e:
                results[name] = {'status': 'failed', 'error': str(e)}
                print(f"{TermColors.Red}Failed: {e}{TermColors.ENDC}")
                
                # Stop on failure if configured
                if not config.get('continue_on_error', True):
                    print(f"{TermColors.Red}Stopping batch execution due to error{TermColors.ENDC}")
                    break
            
            # Optional delay between commands
            delay = config.get('delay_between_commands', 0)
            if delay > 0 and idx < len(config.get('commands', [])):
                time.sleep(delay)
        
        # Save results
        result_file = config.get('result_file', 'batch_results.json')
        with open(result_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n{TermColors.Green}Batch execution completed. Results saved to: {result_file}{TermColors.ENDC}")
        self._print_batch_summary(results)

    def _print_batch_summary(self, results: dict) -> None:
        """Print summary of batch execution"""
        total = len(results)
        success = sum(1 for r in results.values() if r['status'] == 'success')
        failed = total - success
        
        print("\n" + "=" * 60)
        print(f"{TermColors.CYAN}BATCH EXECUTION SUMMARY{TermColors.ENDC}")
        print("=" * 60)
        print(f"Total commands:  {total}")
        print(f"{TermColors.GREEN}Successful:     {success}{TermColors.ENDC}")
        print(f"{TermColors.RED}Failed:         {failed}{TermColors.ENDC}")
        
        if failed > 0:
            print(f"\n{TermColors.YELLOW}Failed commands:{TermColors.ENDC}")
            for name, result in results.items():
                if result['status'] == 'failed':
                    print(f"  - {name}: {result.get('error', 'Unknown error')}")
        print("=" * 60)

    def _validate_mode(self, mode: str) -> bool:
        """Validate FlashTool mode"""
        try:
            ValidModes(mode.lower())
            return True
        except ValueError:
            valid = [m.value for m in ValidModes]
            raise ValueError(f"Invalid mode. Choose from: {', '.join(valid)}")

    def _validate_spi_channel(self, channel: str) -> bool:
        """Validate SPI channel"""
        try:
            ValidSPIChannels(channel.lower())
            return True
        except ValueError:
            valid = [c.value for c in ValidSPIChannels]
            raise ValueError(f"Invalid channel. Choose from: {', '.join(valid)}")

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
    import argparse
    
    parser = argparse.ArgumentParser(description='BiSS Encoder CLI', formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', nargs='?', help='Command to execute')
    parser.add_argument('args', nargs='*', help='Command arguments')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase verbosity (can be used multiple times)')
    parser.add_argument('-i', '--interactive', action='store_true', help='Start in interactive mode')
    parser.add_argument('-c', '--config', help='Batch configuration file (JSON)')
    parser.add_argument('--format', choices=['text', 'json', 'csv'], default='text',help='Output format (default: text)')
    parser.add_argument('--log-file', default='biss_cli.log', help='Log file path (default: biss_cli.log)')

    parsed_args = parser.parse_args()

    if parsed_args.format == 'text' and not sys.stdout.isatty():
        if not parsed_args.interactive:
            parsed_args.format = 'json'
            if parsed_args.verbose:
                print(f"Auto-detected non-terminal output, switching to JSON format", file=sys.stderr)

    # Configure logging based on verbosity
    log_level = logging.WARNING
    if parsed_args.verbose == 1:
        log_level = logging.INFO
    elif parsed_args.verbose >= 2:
        log_level = logging.DEBUG
    
    lenz.init_logging(
        logfilename=parsed_args.log_file,
        stdout_level=log_level,
        file_level=logging.DEBUG
    )

    try:
        with lenz.FlashTool() as ft:
            if parsed_args.interactive:
                # Interactive mode
                cli = BiSSCommandLine(ft, verbose=parsed_args.verbose, interactive=True)
            elif parsed_args.config:
                # Batch mode
                cli = BiSSCommandLine(ft, verbose=parsed_args.verbose)
                cli.execute_batch(parsed_args.config)
            elif parsed_args.command is None:
                # No command provided - show usage
                cli = BiSSCommandLine(ft, verbose=parsed_args.verbose)
                cli._show_usage(sys.argv[0])
            else:
                # Single command mode
                cli = BiSSCommandLine(ft, verbose=parsed_args.verbose)
                # Store output format for use in commands
                cli.output_format = parsed_args.format
                cli.execute_command([sys.argv[0], parsed_args.command] + parsed_args.args)
    except KeyboardInterrupt:
        print(f"\n{TermColors.Yellow}Interrupted by user{TermColors.ENDC}")
        sys.exit(0)
    except Exception as e:
        logging.critical(f"Fatal error: {e}")
        if parsed_args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
