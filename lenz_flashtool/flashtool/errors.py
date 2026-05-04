"""
Error handling module for FlashTool library.

This module defines error types, error codes, fault states, and custom
exceptions used throughout the FlashTool library.
"""

from enum import IntEnum
from typing import Optional, Dict, Any


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
        error_type: UARTErrorType = UARTErrorType.ERROR_TYPE_NONE,
        error_code: UARTErrorCode = UARTErrorCode.UART_ERROR_NONE,
        fault_state: Optional[BiSSFaultState] = None
    ):
        """
        Initialize FlashToolError with error details.
        
        Args:
            message: Human-readable error message
            error_type: Type of error (UART or BiSS)
            error_code: Specific error code
            fault_state: BiSS fault state (if applicable)
        """
        self.error_type = error_type
        self.error_code = error_code
        self.fault_state = fault_state
        self._message = message

        # Generate message if needed (backward compatibility)
        if message and (error_type == UARTErrorType.ERROR_TYPE_UART and
                        error_code == UARTErrorCode.UART_ERROR_NONE):
            self._message = message
        else:
            self._message = self._generate_message()

        super().__init__(self._message)

    def _generate_message(self) -> str:
        """
        Generate human-readable error message from error details.
        
        Returns:
            Formatted error message string
        """
        if self.error_type == UARTErrorType.ERROR_TYPE_BISS:
            fault_msg = self.BISS_FAULT_MESSAGES.get(
                self.fault_state, f"Unknown BiSS fault: {self.fault_state}"
            )
            return f"BiSS Error: {fault_msg} (State: {self.fault_state})"
        else:
            error_msg = self.ERROR_MESSAGES.get(
                self.error_code, f"Unknown error: {self.error_code}"
            )
            return f"UART Error: {error_msg} (Code: {self.error_code:#04x})"

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