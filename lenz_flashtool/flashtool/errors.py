"""
Error handling module for FlashTool library.

This module defines error types, error codes, fault states, and custom
exceptions used throughout the FlashTool library.
"""

from enum import IntEnum
from typing import Optional, Dict, Any
from .uart import UartCmd


class UARTErrorType(IntEnum):
    """
    UART error type classification.
    
    Defines the high-level category of error reported by the device.
    """
    ERROR_TYPE_NONE = 0x00      # No error present
    ERROR_TYPE_BISS = 0x01      # BiSS communication error
    ERROR_TYPE_UART = 0x02      # UART protocol error


class UARTErrorCode(IntEnum):
    """
    UART error code enumeration.
    
    Specific error codes providing detailed information about UART errors.
    """
    UART_ERROR_NONE = 0x00                   # No error
    UART_ERROR_CRC = 0x01                    # CRC verification failed
    UART_ERROR_QUEUE_FULL = 0x02             # UART queue is full
    UART_ERROR_BISS = 0x03                   # BiSS communication error
    UART_ERROR_BISS_WRITE_FAULT = 0x04       # BiSS write operation failed
    UART_ERROR_BISS_READ_FAULT = 0x05        # BiSS read operation failed
    UART_ERROR_LEN_DATA_IS_ZERO = 0x06       # Zero-length data received
    UART_ERROR_LEN_IS_NOT_CORRECT = 0x07     # Incorrect data length
    UART_ERROR_INVALID_CMD = 0x08            # Invalid command received
    UART_ERROR_INVALID_MODE = 0x09           # Invalid operation mode
    UART_ERROR_INVALID_CHANNEL = 0x10        # Invalid channel


class BiSSFaultState(IntEnum):
    """
    BiSS interface fault state enumeration.
    
    Defines possible fault states reported by the BiSS interface.
    """
    BISS_NO_FAULTS = 0x00        # No faults detected
    BISS_FAULT_IDL = 0x01        # IDLE state fault
    BISS_FAULT_WRITE = 0x02      # Write operation fault
    BISS_FAULT_READ_CRC = 0x03   # Read CRC verification fault


class FlashToolError(Exception):
    """
    Custom exception for FlashTool errors with detailed error information.

    This exception provides rich context about what went wrong, including
    error type, specific error code, and BiSS fault state when applicable.

    Attributes:
        error_type: Type of error (UART or BiSS)
        error_code: Specific error code
        fault_state: BiSS fault state (if applicable)
        message: Human-readable error message
    """

    UART_CMD_ERROR_FRAME = 0xE0

    ERROR_MESSAGES = {
        UARTErrorCode.UART_ERROR_NONE: "No UART errors",
        UARTErrorCode.UART_ERROR_CRC: "UART CRC error",
        UARTErrorCode.UART_ERROR_QUEUE_FULL: "UART queue full",
        UARTErrorCode.UART_ERROR_BISS: "BiSS communication error",
        UARTErrorCode.UART_ERROR_BISS_WRITE_FAULT: "BiSS write fault",
        UARTErrorCode.UART_ERROR_BISS_READ_FAULT: "BiSS read fault",
        UARTErrorCode.UART_ERROR_LEN_DATA_IS_ZERO: "Zero length data",
        UARTErrorCode.UART_ERROR_LEN_IS_NOT_CORRECT: "Incorrect data length",
        UARTErrorCode.UART_ERROR_INVALID_CMD: "Incorrect cmd",
        UARTErrorCode.UART_ERROR_INVALID_MODE: "Incorrect mode",
    }

    BISS_FAULT_MESSAGES = {
        BiSSFaultState.BISS_NO_FAULTS: "No BiSS faults",
        BiSSFaultState.BISS_FAULT_IDL: "BiSS IDLE fault",
        BiSSFaultState.BISS_FAULT_WRITE: "BiSS write fault",
        BiSSFaultState.BISS_FAULT_READ_CRC: "BiSS read CRC fault",
    }

    def __init__(
        self,
        message: str,
        offender_cmd: Optional[int] = None,
        error_type: UARTErrorType = UARTErrorType.ERROR_TYPE_NONE,
        error_code: UARTErrorCode = UARTErrorCode.UART_ERROR_NONE,
        fault_state: Optional[BiSSFaultState] = None,
    ):
        """
        Initialize FlashToolError with error details.
        
        Args:
            message: Human-readable error message
            error_type: Type of error (UART or BiSS)
            error_code: Specific error code
            fault_state: BiSS fault state (if applicable)
        """
        self.offender_cmd = offender_cmd
        self.error_type = error_type
        self.error_code = error_code
        self.fault_state = fault_state
        self._message = message

        self._message = message or self._generate_message()

        super().__init__(self._message)

    def _offender_repr(self, value: int) -> str:
        """Human-readable representation of offender_cmd."""
        if value is None:
            return "(none)"
        if UartCmd is not None:
            try:
                member = UartCmd(value)
                return f"0x{value:02X} ({member.name})"
            except ValueError:
                return f"0x{value:02X} (UNKNOWN_CMD)"
        return f"0x{value:02X}"

    def _enum_repr(self, enum_cls, value) -> str:
        try:
            member = enum_cls(value)
        except (ValueError, TypeError):
            return f"0x{value:02X} (UNKNOWN)"
        desc = ""
        if enum_cls is UARTErrorCode:
            desc = self.ERROR_MESSAGES.get(member, "")
        elif enum_cls is BiSSFaultState:
            desc = self.BISS_FAULT_MESSAGES.get(member, "")
        if desc:
            return f"0x{value:02X} ({member.name}: {desc})"
        return f"0x{value:02X} ({member.name})"

    def _generate_message(self) -> str:
        parts = []
        if self.offender_cmd is not None:
            parts.append(f"offender_cmd={self._offender_repr(self.offender_cmd)}")
        if self.error_type is not None:
            parts.append(f"error_type={self._enum_repr(UARTErrorType, int(self.error_type))}")
        if self.error_code is not None:
            parts.append(f"error_code={self._enum_repr(UARTErrorCode, int(self.error_code))}")
        if self.fault_state is not None:
            parts.append(f"fault_state={self._enum_repr(BiSSFaultState, int(self.fault_state))}")

        if self.error_type == UARTErrorType.ERROR_TYPE_BISS:
            header = "BiSS error"
        elif self.error_type == UARTErrorType.ERROR_TYPE_UART:
            header = "UART error"
        else:
            header = "FlashTool error"

        return f"{header}: " + ", ".join(parts) if parts else header

    def __str__(self) -> str:
        """Return string representation of the error."""
        return self._message

    @property
    def details(self) -> Dict[str, Any]:
        """
        Return detailed error information as a dictionary.
        
        Returns:
            Dictionary with error_type, error_code, fault_state, and message
        """
        return {
            'offender_cmd': self.offender_cmd,
            'error_type': self.error_type,
            'error_code': self.error_code,
            'fault_state': self.fault_state,
            'message': self._message
        }

    def is_biss_error(self) -> bool:
        """
        Check if this is a BiSS-related error.
        
        Returns:
            True if error type is BiSS, False otherwise
        """
        return self.error_type == UARTErrorType.ERROR_TYPE_BISS

    def is_uart_error(self) -> bool:
        """
        Check if this is a UART-related error.
        
        Returns:
            True if error type is UART, False otherwise
        """
        return self.error_type == UARTErrorType.ERROR_TYPE_UART