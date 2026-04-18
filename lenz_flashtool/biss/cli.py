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

import struct
import sys
import logging
import time
import datetime
from typing import List
from ..flashtool import FlashTool, biss_send_hex, generate_hex_line
from ..utils.termcolors import TermColors
from . import (
    BiSSBank,
    biss_commands,
    interpret_error_flags,
    interpret_biss_commandstate,
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
        print("  dump                     - Read and decode fixed-address registers (0x40-0x7F) with color map")
        print("  dump <bank>              - Read and decode bank (0-37) calibration page + fixed registers")
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
            elif command == "dump":
                self._dump_registers(args)
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

    # ------------------------------------------------------------------
    #  dump – read & decode fixed-address registers (0x40-0x7F)
    # ------------------------------------------------------------------

    # Pastel 256-color ANSI foreground palette (no extra libraries)
    # Works on macOS Terminal, iTerm2, Windows Terminal (+ colorama)
    _P_BLUE      = "\033[38;5;153m"   # Baby Blue
    _P_CYAN      = "\033[38;5;116m"   # Aquamarine
    _P_GREEN     = "\033[38;5;150m"   # Sage
    _P_MINT      = "\033[38;5;114m"   # Seafoam
    _P_YELLOW    = "\033[38;5;222m"   # Buttercup
    _P_CREAM     = "\033[38;5;229m"   # Lemon
    _P_PEACH     = "\033[38;5;216m"   # Light Coral
    _P_SALMON    = "\033[38;5;210m"   # Salmon
    _P_ROSE      = "\033[38;5;217m"   # Rose
    _P_PINK      = "\033[38;5;174m"   # Pink
    _P_BLUSH     = "\033[38;5;224m"   # Blush
    _P_LAVENDER  = "\033[38;5;139m"   # Lavender
    _P_ORCHID    = "\033[38;5;182m"   # Orchid
    _P_MAUVE     = "\033[38;5;181m"   # Dusty Pink
    _P_SAND      = "\033[38;5;179m"   # Sand
    _P_KHAKI     = "\033[38;5;186m"   # Khaki
    _P_SILVER    = "\033[38;5;188m"   # Silver
    _P_GRAY      = "\033[38;5;253m"   # Light Gray
    _P_ICE       = "\033[38;5;152m"   # Powder Blue
    _P_CORAL     = "\033[38;5;208m"   # Orange
    _P_PERI      = "\033[38;5;146m"   # Periwinkle
    _P_DUSTY     = "\033[38;5;137m"   # Dusty Rose
    _RST         = "\033[0m"

    # Register map: (start_offset, length, name, bg_color)
    # Offsets relative to 0x40
    _FIXED_REG_MAP = [
        (0x00, 1, "BankSelect",    _P_BLUE),
        (0x01, 1, "EDSBankNum",    _P_CYAN),
        (0x02, 2, "ProfileID",     _P_GREEN),
        (0x04, 4, "SerialNum",     _P_PEACH),
        (0x08, 2, "CMD",           _P_SALMON),
        (0x0A, 2, "EncoderState",  _P_CREAM),
        (0x0C, 1, "EncoderTemp",   _P_ORCHID),
        (0x0D, 1, "ExternalTemp",  _P_MAUVE),
        (0x0E, 2, "Vcc",           _P_MINT),
        (0x10, 4, "FirstHarm",     _P_GREEN),
        (0x14, 4, "OutCfg",        _P_ROSE),
        (0x18, 2, "SignalAmp",     _P_PERI),
        (0x1A, 1, "CalPhase",      _P_KHAKI),
        (0x1B, 1, "ExcPhase",      _P_SAND),
        (0x1C, 4, "CalParams",     _P_YELLOW),
        (0x20, 1, "(Reserved)",    _P_GRAY),
        (0x21, 1, "CommandState",  _P_LAVENDER),
        (0x22, 2, "ErrorFlags",    _P_CORAL),
        (0x24, 8, "(Reserved)",    _P_GRAY),
        (0x2C, 4, "BootloaderVer", _P_ICE),
        (0x30, 4, "ProgramVer",    _P_MINT),
        (0x34, 4, "ProdDate",      _P_PEACH),
        (0x38, 6, "DevID",         _P_PINK),
        (0x3E, 2, "MfrID",         _P_BLUSH),
    ]

    # Encoder state bitfield definitions: (start_bit, width, name, values_map)
    _ENCODER_STATE_FIELDS = [
        (0,  1, "SetupLock",      {0: "LOCKED", 1: "UNLOCKED"}),
        (1,  1, "FlashLock",      {0: "LOCKED", 1: "UNLOCKED"}),
        (2,  2, "Zeroing",        {0: "IDLE", 1: "REQ", 2: "DONE"}),
        (4,  2, "ClearDifLUT",    {0: "IDLE", 1: "REQ", 2: "DONE"}),
        (6,  2, "AmpCalibration", {0: "IDLE", 1: "REQ", 2: "SECOND_TURN", 3: "DONE"}),
        (8,  1, "ArcCalibration", {0: "DISABLED", 1: "ENABLED"}),
        (9,  2, "Flashing",       {0: "IDLE", 1: "REQ", 2: "DONE"}),
        (11, 2, "ClearDifFlash",  {0: "IDLE", 1: "REQ", 2: "DONE"}),
        (13, 2, "FlashDifLUT",    {0: "IDLE", 1: "REQ", 2: "DONE", 3: "CRC_FAULT"}),
        (15, 1, "UserBankState",  {0: "IDLE", 1: "DIFLUT_REQ"}),
    ]

    # OutCfg (REV_RES) resolution lookup
    _RESOLUTION_MAP = {0: "17-bit", 1: "18-bit", 2: "19-bit", 3: "20-bit",
                       4: "18-bit", 5: "22-bit", 6: "23-bit", 7: "24-bit"}

    def _dump_registers(self, args: List[str]) -> None:
        """Read and decode fixed-address registers 0x40-0x7F with colored hex dump."""
        bank = None
        if len(args) > 2:
            bank = int(args[2])

        # Read 64 bytes of fixed-address region
        raw = self.ft.biss_addr_readb(bank if bank is not None else 0, 0x40, 64)
        data = bytes(int(b) for b in raw)

        bank_data = None
        if bank is not None:
            raw_bank = self.ft.biss_addr_readb(bank, 0x00, 64)
            bank_data = bytes(int(b) for b in raw_bank)

        if bank_data is not None:
            if bank == 0:
                print(f"\n{TermColors.Bold}=== Bank 0 Calibration Page (0x00-0x3F) ==={TermColors.ENDC}")
                self._print_bank0_dump(bank_data)
                self._decode_bank0(bank_data)
            else:
                print(f"\n{TermColors.Bold}=== Bank {bank} Raw Data (0x00-0x3F) ==={TermColors.ENDC}")
                self._print_raw_dump(bank_data, base_addr=0x00)

        print(f"\n{TermColors.Bold}=== Fixed-Address Registers (0x40-0x7F) ==={TermColors.ENDC}")
        self._print_fixed_dump(data)
        self._decode_fixed_registers(data)

    def _print_dump_header(self) -> None:
        """Print the hex dump table header."""
        hdr = f"  {TermColors.Bold}Addr   "
        for i in range(16):
            hdr += f" +{i:X} "
        hdr += TermColors.ENDC
        print(hdr)
        print("  " + "-" * 71)

    def _print_raw_dump(self, data: bytes, base_addr: int = 0x00) -> None:
        """Print 64 bytes as plain hex dump without field coloring."""
        self._print_dump_header()
        for row in range(4):
            base = row * 16
            addr = base_addr + base
            line = f"  {TermColors.Bold}0x{addr:02X}{TermColors.ENDC}  "
            for col in range(16):
                line += f"  {TermColors.Blue}{data[base + col]:02X}{TermColors.ENDC}"
            print(line)

    def _print_fixed_dump(self, data: bytes) -> None:
        """Print 64 bytes at 0x40-0x7F with per-register background colors."""
        # Build a color map: offset -> bg_color
        color_map = {}
        for off, length, _, bg in self._FIXED_REG_MAP:
            for i in range(off, off + length):
                color_map[i] = bg
        self._print_dump_header()
        for row in range(4):
            base = row * 16
            addr = 0x40 + base
            line = f"  {TermColors.Bold}0x{addr:02X}{TermColors.ENDC}  "
            for col in range(16):
                offset = base + col
                bg = color_map.get(offset, self._P_GRAY)
                line += f"  {bg}{data[offset]:02X}{self._RST}"
            print(line)

    def _decode_fixed_registers(self, data: bytes) -> None:
        """Decode and display all fixed-address register fields."""
        print(f"\n  {TermColors.Bold}{'Register':<21} {'Addr':>6}  {'Raw':>23}  Decoded{TermColors.ENDC}")
        print("  " + "-" * 80)

        for off, length, name, fg in self._FIXED_REG_MAP:
            raw_bytes = data[off:off + length]
            hex_str = " ".join(f"{b:02X}" for b in raw_bytes)
            addr_str = f"0x{0x40 + off:02X}"

            decoded = self._decode_field(name, raw_bytes, data)
            print(f"  {fg}>> {name:<18}{self._RST} {addr_str:>6}  {fg}{hex_str:>23}{self._RST}  {decoded}")

    def _decode_field(self, name: str, raw: bytes, full_data: bytes) -> str:
        """Decode a single register field into a human-readable string."""
        if name == "BankSelect":
            return f"Bank {raw[0]}"

        if name == "EDSBankNum":
            return f"EDS Bank {raw[0]}"

        if name == "ProfileID":
            val = struct.unpack_from("<H", raw)[0]
            return f"0x{val:04X}"

        if name == "SerialNum":
            try:
                ascii_part = raw[0:2].decode("ascii")
                hex_part = raw[2:4].hex().upper()
                return f"{ascii_part}{hex_part} (ASCII+hex)"
            except (UnicodeDecodeError, ValueError):
                return raw.hex().upper()

        if name == "CMD":
            val = struct.unpack_from("<H", raw)[0]
            if val == 0:
                return "No command"
            # Try to find command name
            for cmd_name, (opcode, _) in biss_commands.items():
                if opcode == val:
                    return f"0x{val:04X} ({cmd_name})"
            return f"0x{val:04X}"

        if name == "EncoderState":
            val = struct.unpack_from("<H", raw)[0]
            if val == 0:
                return "OK (all clear)"
            return self._decode_encoder_state(val)

        if name == "EncoderTemp":
            return f"{raw[0] - 64} C (raw {raw[0]})" if raw[0] != 0 else "N/A"

        if name == "ExternalTemp":
            return f"{raw[0] - 64} C" if raw[0] != 0 else "No sensor"

        if name == "Vcc":
            val = struct.unpack_from("<H", raw)[0]
            return f"{val / 1000:.3f} V (raw {val})"

        if name == "FirstHarm":
            amp = struct.unpack_from("<H", raw, 0)[0]
            ang = struct.unpack_from("<H", raw, 2)[0]
            if amp == 0 and ang == 0:
                return "Not calibrated"
            return f"amp={amp}, angle={ang}"

        if name == "OutCfg":
            val = struct.unpack_from("<I", raw)[0]
            hyst_res = (val >> 25) & 0x07
            cv_cfg = (val >> 24) & 0x01
            out_dif = val & 0x00FFFFFF
            res_str = self._RESOLUTION_MAP.get(hyst_res, f"unknown({hyst_res})")
            dir_str = "CW" if cv_cfg == 0 else "CCW"
            return f"{res_str}, {dir_str}, OutDif={out_dif}"

        if name == "SignalAmp":
            val = struct.unpack_from("<H", raw)[0]
            return f"0x{val:04X} ({val})"

        if name in ("CalPhase", "ExcPhase"):
            return f"0x{raw[0]:02X} ({raw[0]})"

        if name == "CalParams":
            val = struct.unpack_from("<I", raw)[0]
            return f"0x{val:08X}" if val != 0 else "Not set"

        if name == "CommandState":
            states = interpret_biss_commandstate(raw[0])
            return states[0]

        if name == "ErrorFlags":
            val = struct.unpack_from("<H", raw)[0]
            flags = interpret_error_flags(val)
            if val == 0:
                return "OK (0x0000)"
            return f"0x{val:04X}: {', '.join(flags)}"

        if name == "BootloaderVer" or name == "ProgramVer":
            return f"{raw[3]}.{raw[2]}.{raw[1]}.{raw[0]}"

        if name == "ProdDate":
            val = struct.unpack_from(">I", raw)[0]
            try:
                dt = datetime.datetime.fromtimestamp(val, tz=datetime.timezone.utc)
                return f"{dt.strftime('%Y-%m-%d %H:%M')}"
            except (OSError, OverflowError, ValueError):
                return f"0x{val:08X}"

        if name == "DevID":
            try:
                return f"\"{raw.decode('ascii')}\" (ASCII)"
            except (UnicodeDecodeError, ValueError):
                return raw.hex().upper()

        if name == "MfrID":
            try:
                return f"\"{raw.decode('ascii')}\" (ASCII)"
            except (UnicodeDecodeError, ValueError):
                return f"0x{raw.hex().upper()}"

        if name == "(Reserved)":
            return f"{TermColors.DarkGray}---{TermColors.ENDC}"

        return raw.hex().upper()

    def _decode_encoder_state(self, val: int) -> str:
        """Decode EncoderState 16-bit bitfield into active flags."""
        parts = []
        for start_bit, width, name, values in self._ENCODER_STATE_FIELDS:
            mask = (1 << width) - 1
            field_val = (val >> start_bit) & mask
            if field_val != 0:
                label = values.get(field_val, f"?{field_val}")
                parts.append(f"{name}={label}")
        if not parts:
            return "OK (all clear)"
        return f"0x{val:04X}: " + ", ".join(parts)

    # ------------------------------------------------------------------
    #  Bank 0 (calibration page) dump & decode
    # ------------------------------------------------------------------

    _BANK0_REG_MAP = [
        (0x00, 2, "Sin.Min.Low",   _P_BLUE),
        (0x02, 2, "Sin.Min.High",  _P_ICE),
        (0x04, 2, "Sin.Max.Low",   _P_CYAN),
        (0x06, 2, "Sin.Max.High",  _P_MINT),
        (0x08, 2, "Cos.Min.Low",   _P_YELLOW),
        (0x0A, 2, "Cos.Min.High",  _P_CREAM),
        (0x0C, 2, "Cos.Max.Low",   _P_ORCHID),
        (0x0E, 2, "Cos.Max.High",  _P_BLUSH),
        (0x10, 4, "Coarse[0]",     _P_PEACH),
        (0x14, 4, "Coarse[1]",     _P_SAND),
        (0x18, 4, "Coarse[2]",     _P_PEACH),
        (0x1C, 4, "Coarse[3]",     _P_SAND),
        (0x20, 4, "Coarse[4]",     _P_PEACH),
        (0x24, 4, "Coarse[5]",     _P_SAND),
        (0x28, 4, "Coarse[6]",     _P_PEACH),
        (0x2C, 4, "Coarse[7]",     _P_SAND),
        (0x30, 4, "Harmonic[0]",   _P_SALMON),
        (0x34, 4, "Harmonic[1]",   _P_ROSE),
        (0x38, 4, "Harmonic[2]",   _P_SALMON),
        (0x3C, 4, "Harmonic[3]",   _P_ROSE),
    ]

    def _print_bank0_dump(self, data: bytes) -> None:
        """Print 64-byte bank with per-field background colors."""
        color_map = {}
        for off, length, _, bg in self._BANK0_REG_MAP:
            for i in range(off, off + length):
                color_map[i] = bg

        self._print_dump_header()
        for row in range(4):
            base = row * 16
            addr = base
            line = f"  {TermColors.Bold}0x{addr:02X}{TermColors.ENDC}  "
            for col in range(16):
                offset = base + col
                bg = color_map.get(offset, self._P_GRAY)
                line += f"  {bg}{data[offset]:02X}{self._RST}"
            print(line)

    def _decode_bank0(self, data: bytes) -> None:
        """Decode bank 0 calibration page fields."""
        import math

        print(f"\n  {TermColors.Bold}{'Field':<19} {'Addr':>6}  {'Raw':>6}  Decoded{TermColors.ENDC}")
        print("  " + "-" * 44)

        # Amplitude calibration (Sin/Cos min/max)
        amp_fields = [
            (0x00, "Sin.Min.Low"),  (0x02, "Sin.Min.High"),
            (0x04, "Sin.Max.Low"),  (0x06, "Sin.Max.High"),
            (0x08, "Cos.Min.Low"),  (0x0A, "Cos.Min.High"),
            (0x0C, "Cos.Max.Low"),  (0x0E, "Cos.Max.High"),
        ]
        for off, name in amp_fields:
            val = struct.unpack_from("<h", data, off)[0]
            hex_str = f"{data[off]:02X} {data[off+1]:02X}"
            # Find color
            fg = next(c for o, _, _, c in self._BANK0_REG_MAP if o == off)
            print(f"  {fg}>> {name:<16}{self._RST} "
                  f"  0x{off:02X}  {fg}{hex_str:>6}{self._RST}  {val}")

        # Coarse offset channels
        print()
        print(f"  {TermColors.Bold}{'Channel':<18} {'Addr':>7}  {'ZeroL':>5} {'ZeroH':>5} "
              f"{'PosL':>5} {'NegH':>5}{TermColors.ENDC}")
        print("  " + "-" * 53)
        for ch in range(8):
            off = 0x10 + ch * 4
            zl, zh, pl, nh = struct.unpack_from("<bbbb", data, off)
            fg = self._P_PEACH if ch % 2 == 0 else self._P_SAND
            print(f"  {fg}>> Coarse[{ch}]       {self._RST} "
                  f"  0x{off:02X}  {fg}{zl:>5} {zh:>5} {pl:>5} {nh:>5}{self._RST}")

        # Harmonics
        print()
        print(f"  {TermColors.Bold}{'Harmonic':<19} {'Addr':>6}  {'Real':>6} {'Imag':>6} "
              f"{'Mag':>9} {'Phase':>8}{TermColors.ENDC}")
        print("  " + "-" * 66)
        harmonics_raw = struct.unpack_from("<8h", data, 0x30)
        for i in range(4):
            off = 0x30 + i * 4
            re_val = harmonics_raw[i * 2]
            im_val = harmonics_raw[i * 2 + 1]
            mag = math.hypot(re_val, im_val)
            phase = math.degrees(math.atan2(im_val, re_val))
            fg = self._P_SALMON if i % 2 == 0 else self._P_ROSE
            mag_color = TermColors.White if mag > 500 else TermColors.Yellow if mag > 100 else TermColors.DarkGray
            print(f"  {fg}>> H{i}              {self._RST} "
                  f"  0x{off:02X}  {fg}{re_val:>+6} {im_val:>+6}{self._RST} "
                  f" {mag_color}{mag:>8.1f}{TermColors.ENDC} {phase:>+7.1f} deg")

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
