r'''
 _     _____ _   _ _____   _____ _   _  ____ ___  ____  _____ ____  ____
| |   | ____| \ | |__  /  | ____| \ | |/ ___/ _ \|  _ \| ____|  _ \/ ___|
| |   |  _| |  \| | / /   |  _| |  \| | |  | | | | | | |  _| | |_) \___ \
| |___| |___| |\  |/ /_   | |___| |\  | |__| |_| | |_| | |___|  _ < ___) |
|_____|_____|_| \_/____|  |_____|_| \_|\____\___/|____/|_____|_| \_|____/


BiSS Encoder State Bitfield Definitions.

Describes the 16-bit EncoderState register (BiSSBank.ENC_DATA_REG_INDEX, 0x4A)
as a set of named IntEnum bitfields. Mirrors the firmware C struct
`EncoderState_t` exactly:

    struct EncoderState_t {
        enum SetupLock_t           SetupLock:1;              // bit 0
        enum FlashLock_t           FlashLock:1;              // bit 1
        enum Zeroing_t             Zeroing:2;                // bits 2-3
        enum ClearDifLUT_t         ClearDifLUT:2;            // bits 4-5
        enum AmpCal_t              AmplitudeCalibration:2;   // bits 6-7
        enum ArcCalibration_t      ArcCalibration:1;         // bit 8
        enum Flashing_t            Flashing:2;               // bits 9-10
        enum ClearDifFlash_t       ClearDifFlash:2;          // bits 11-12
        enum FlashDifLUT_t         FlashDifLUT:2;            // bits 13-14
        enum UserBankState_t       UserBankState:1;          // bit 15
    };

`ENCODER_STATE_FIELDS` maps each field name to its `(enum_cls, bit_pos, width)`
tuple and is the single source of truth used by `FlashTool.read_encoder_flag`,
`FlashTool.wait_for_flag`, and the CLI decoder.

Author:
    LENZ ENCODERS, 2020-2026
'''
from enum import IntEnum
from typing import Dict, Tuple, Type

__all__ = [
    'SetupLock',
    'FlashLock',
    'Zeroing',
    'ClearDifLUT',
    'AmplitudeCalibration',
    'ArcCalibration',
    'Flashing',
    'ClearDifFlash',
    'FlashDifLUT',
    'UserBankState',
    'ENCODER_STATE_FIELDS',
]


class SetupLock(IntEnum):
    LOCKED = 0
    UNLOCKED = 1


class FlashLock(IntEnum):
    LOCKED = 0
    UNLOCKED = 1


class Zeroing(IntEnum):
    IDLE = 0
    REQ = 1
    DONE = 2


class ClearDifLUT(IntEnum):
    IDLE = 0
    REQ = 1
    DONE = 2


class AmplitudeCalibration(IntEnum):
    IDLE = 0
    REQ = 1
    SECOND_TURN = 2
    DONE = 3


class ArcCalibration(IntEnum):
    DISABLED = 0
    ENABLED = 1


class Flashing(IntEnum):
    IDLE = 0
    REQ = 1
    DONE = 2


class ClearDifFlash(IntEnum):
    IDLE = 0
    REQ = 1
    DONE = 2


class FlashDifLUT(IntEnum):
    IDLE = 0
    REQ = 1
    DONE = 2
    CRC_FAULT = 3


class UserBankState(IntEnum):
    IDLE = 0
    DIFLUT_REQ = 1


ENCODER_STATE_FIELDS: Dict[str, Tuple[Type[IntEnum], int, int]] = {
    'SetupLock':            (SetupLock,            0,  1),
    'FlashLock':            (FlashLock,            1,  1),
    'Zeroing':              (Zeroing,              2,  2),
    'ClearDifLUT':          (ClearDifLUT,          4,  2),
    'AmplitudeCalibration': (AmplitudeCalibration, 6,  2),
    'ArcCalibration':       (ArcCalibration,       8,  1),
    'Flashing':             (Flashing,             9,  2),
    'ClearDifFlash':        (ClearDifFlash,        11, 2),
    'FlashDifLUT':          (FlashDifLUT,          13, 2),
    'UserBankState':        (UserBankState,        15, 1),
}
