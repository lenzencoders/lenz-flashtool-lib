r'''
 _     _____ _   _ _____   _____ _   _  ____ ___  ____  _____ ____  ____
| |   | ____| \ | |__  /  | ____| \ | |/ ___/ _ \|  _ \| ____|  _ \/ ___|
| |   |  _| |  \| | / /   |  _| |  \| | |  | | | | | | |  _| | |_) \___ \
| |___| |___| |\  |/ /_   | |___| |\  | |__| |_| | |_| | |___|  _ < ___) |
|_____|_____|_| \_/____|  |_____|_| \_|\____\___/|____/|_____|_| \_|____/


Timing constants for FlashTool hardware communication.

These values are determined by the BiSS encoder and FlashTool hardware
timing requirements. Do not modify without hardware verification.

Author:
    LENZ ENCODERS, 2020-2026
'''

# ── Serial communication ─────────────────────────────────────────────
SERIAL_POLL_INTERVAL_S = 0.001      # Polling interval during data streaming loops
SERIAL_DATA_WAIT_POLL_S = 0.01      # Polling interval in _wait_for_data

# ── Command processing ───────────────────────────────────────────────
COMMAND_SETTLE_S = 0.01             # Wait after sending a BiSS/UART command
REGISTER_READ_SETTLE_S = 0.01      # Wait after register read command before reading buffer
REGISTER_READ_LONG_SETTLE_S = 0.1  # Wait after bulk register read (full bank)

# ── Power management ─────────────────────────────────────────────────
ENCODER_POWER_STABILIZE_S = 0.1    # Encoder supply stabilization after power on/off
ENCODER_POWER_ON_FAST_S = 0.01     # Short stabilization for IRS encoder after power on

# ── FlashTool device control ─────────────────────────────────────────
FLASHTOOL_RESET_SETTLE_S = 0.01    # Wait after FlashTool non-volatile reset
MODE_SWITCH_SETTLE_S = 0.05        # Wait after FlashTool mode or channel switch

# ── BiSS encoder flash operations ────────────────────────────────────
REBOOT_TO_BL_DELAY_S = 0.5         # Wait after reboot-to-bootloader command
REBOOT_TO_BL_SHORT_DELAY_S = 0.3   # Shorter wait for DIF table upload reboot
RUN_CMD_DELAY_S = 0.4              # Wait after 'run' command (exit bootloader)
FLASH_SAVE_SETTLE_S = 0.2          # Wait after saveflash command
FLASH_SAVE_SHORT_SETTLE_S = 0.1    # Shorter wait after saveflash (shift operations)

# ── Page transmission timing ─────────────────────────────────────────
BANK_DATA_SETTLE_S = 0.05          # Wait between bank data writes within a page
PAGE_DATA_SETTLE_S = 0.3           # Wait after all banks sent, before load command
BISS_PAGE_FLASH_TIME_S = 1.25      # Flash write time for BiSS 2KB page via register interface
FT_PAGE_FLASH_TIME_S = 1.0         # Flash write time for FlashTool bootloader 2KB page

# ── IRS encoder operations ───────────────────────────────────────────
IRS_WRITE_DELAY_S = 0.1            # Wait after IRS encoder data write

# ── Post-operation delays ────────────────────────────────────────────
FLAG_READ_SETTLE_S = 0.2           # Wait after reading flags before next operation
POST_UPLOAD_SETTLE_S = 0.5         # Wait after firmware/DIF upload completes
CRC_CHECK_SETTLE_S = 0.05          # Wait after CRC32 verification command

# ── Calibration ──────────────────────────────────────────────────────
CALIBRATION_READ_INTERVAL_S = 1.0  # Interval between calibration data reads

# ── Retry/recovery ───────────────────────────────────────────────────
RETRY_DELAY_S = 0.1                # Wait between retry attempts
ERROR_RECOVERY_DELAY_S = 1.0       # Wait after communication error before retry
