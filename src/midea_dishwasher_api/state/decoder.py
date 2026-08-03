"""Decodes a device response frame into a `DishwasherStatus`."""

from __future__ import annotations

from ..enums import (
    BrightLevel,
    CycleState,
    ErrorCode,
    MachineState,
    Mode,
    MsgType,
    WashStage,
)
from ..protocol import parse_frame
from .dishwasher_status import DishwasherStatus

_OFFSET_CYCLE_STATE = 1
_OFFSET_MODE = 2
_OFFSET_EXTRA_DRYING = 3
_OFFSET_FLAGS5 = 5
_OFFSET_LEFT_TIME_LOW = 6
_OFFSET_WASH_STAGE = 9
_OFFSET_ERROR_CODE = 10
_OFFSET_BRIGHT = 24
_OFFSET_LEFT_TIME_HIGH = 32

_FLAG_DOOR_CLOSED = 0x01
_FLAG_BRIGHT_LACK = 0x02

_ACK_OPCODE = 0x01

_DECODABLE_MSG_TYPES = {MsgType.CONTROL, MsgType.QUERY, MsgType.PUSH}


def decode_response(frame: bytes) -> DishwasherStatus:
    """Decode a response frame; frames that carry no state come back empty."""
    msg_type, body = parse_frame(frame)
    status = DishwasherStatus(raw=frame, msg_type=msg_type)

    if msg_type not in _DECODABLE_MSG_TYPES:
        return status
    if len(body) >= 1 and body[0] == _ACK_OPCODE:
        status.ack_only = True
        return status

    _decode_body(body, status)
    return status


def _decode_body(body: bytes, status: DishwasherStatus) -> None:
    """Fill the status in place from the body of a decodable frame."""
    if (cycle_state := _byte_at(body, _OFFSET_CYCLE_STATE)) is not None:
        status.cycle_state = CycleState.from_byte(cycle_state)
        status.machine_state = MachineState.from_byte(cycle_state)

    if (mode := _byte_at(body, _OFFSET_MODE)) is not None:
        status.mode = Mode.from_byte(mode)

    if (extra_drying := _byte_at(body, _OFFSET_EXTRA_DRYING)) is not None:
        status.extra_drying = bool(extra_drying)

    flags = _byte_at(body, _OFFSET_FLAGS5) or 0
    status.door_closed = bool(flags & _FLAG_DOOR_CLOSED)
    status.bright_lack = bool(flags & _FLAG_BRIGHT_LACK)

    if (wash_stage := _byte_at(body, _OFFSET_WASH_STAGE)) is not None:
        status.wash_stage = WashStage.from_byte(wash_stage)

    if (error_code := _byte_at(body, _OFFSET_ERROR_CODE)) is not None:
        status.error_code = ErrorCode.from_byte(error_code)

    if (bright := _byte_at(body, _OFFSET_BRIGHT)) is not None:
        status.bright = BrightLevel.from_byte(bright)

    if status.cycle_state == CycleState.WORK:
        status.left_time = _decode_left_time(body)


def _decode_left_time(body: bytes) -> int:
    """Return the remaining minutes, split across a low and a high byte."""
    low = _byte_at(body, _OFFSET_LEFT_TIME_LOW) or 0
    high = _byte_at(body, _OFFSET_LEFT_TIME_HIGH)
    return (high << 8 | low) if high is not None else low


def _byte_at(body: bytes, offset: int) -> int | None:
    """Return the byte at an offset, or None when the body is shorter."""
    return body[offset] if offset < len(body) else None
