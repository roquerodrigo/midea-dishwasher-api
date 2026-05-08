"""Encoder/decoder do frame de aplicação `AA … E1` da lava-louças Midea."""

from __future__ import annotations

from typing import TypedDict

from ..enums import Mode, MsgType
from .frame_error import FrameError


class ControlPayload(TypedDict, total=False):
    machine_state: str
    mode: str
    additional: int
    bright: int

SYNC = 0xAA
DEVICE_TYPE = 0xE1
HEADER_LEN = 10
CONTROL_BODY_LEN = 38
QUERY_BODY = b"\x00"

_OPCODE_MAIN = 0x08
_OPCODE_BRIGHT = 0x84

_MAIN_OPCODE = 0
_MAIN_MACHINE_STATE = 1
_MAIN_MODE = 2
_MAIN_ADDITIONAL = 3

_BRIGHT_OPCODE = 0
_BRIGHT_LEVEL = 1

_CONTROL_STATE_BYTE: dict[str, int] = {
    "power_off": 0x00,
    "power_on": 0x01,
    "cancel": 0x01,
    "work": 0x03,
}

_STATE_BYTE_WORK = _CONTROL_STATE_BYTE["work"]
_MODE_BYTE_ECO = 0x04


def make_sum(buf: bytes | bytearray, start: int, end_inclusive: int) -> int:
    s = sum(buf[start : end_inclusive + 1]) & 0xFF
    return (-s) & 0xFF


def assemble_frame(body: bytes | bytearray, msg_type: int) -> bytes:
    total = HEADER_LEN + len(body) + 1
    frame = bytearray(total)
    frame[0] = SYNC
    frame[1] = total - 1
    frame[2] = DEVICE_TYPE
    frame[9] = msg_type
    frame[HEADER_LEN : HEADER_LEN + len(body)] = body
    frame[-1] = make_sum(frame, 1, total - 2)
    return bytes(frame)


def parse_frame(frame: bytes) -> tuple[int, bytes]:
    if len(frame) < HEADER_LEN + 1:
        raise FrameError(f"frame too short: {len(frame)} bytes")
    if frame[0] != SYNC:
        raise FrameError(f"bad sync byte: 0x{frame[0]:02x}")
    if frame[2] != DEVICE_TYPE:
        raise FrameError(f"not a dishwasher frame (device_type=0x{frame[2]:02x})")
    declared = frame[1] + 1
    if declared != len(frame):
        raise FrameError(f"declared length {declared} != actual {len(frame)}")
    expected = make_sum(frame, 1, len(frame) - 2)
    if expected != frame[-1]:
        raise FrameError(
            f"checksum mismatch: got 0x{frame[-1]:02x}, expected 0x{expected:02x}"
        )
    return frame[9], bytes(frame[HEADER_LEN:-1])


def build_query() -> bytes:
    return assemble_frame(QUERY_BODY, MsgType.QUERY)


def build_control(payload: ControlPayload) -> bytes:
    return assemble_frame(_encode_control_body(payload), MsgType.CONTROL)


def _encode_control_body(payload: ControlPayload) -> bytes:
    if "bright" in payload:
        return _encode_bright(int(payload["bright"]))
    return _encode_main(
        machine_state=payload.get("machine_state"),
        mode=payload.get("mode"),
        additional=int(payload.get("additional", 0)),
    )


def _encode_bright(level: int) -> bytes:
    body = bytearray(CONTROL_BODY_LEN)
    body[_BRIGHT_OPCODE] = _OPCODE_BRIGHT
    body[_BRIGHT_LEVEL] = level & 0xFF
    return bytes(body)


def _encode_main(machine_state: str | None, mode: str | None, additional: int) -> bytes:
    state_byte = _CONTROL_STATE_BYTE.get(machine_state, 0x00) if machine_state else 0x00
    mode_byte = _resolve_mode_byte(mode, state_byte)

    body = bytearray(CONTROL_BODY_LEN)
    body[_MAIN_OPCODE] = _OPCODE_MAIN
    body[_MAIN_MACHINE_STATE] = state_byte
    body[_MAIN_MODE] = mode_byte
    body[_MAIN_ADDITIONAL] = additional & 0xFF
    return bytes(body)


def _resolve_mode_byte(mode: str | None, state_byte: int) -> int:
    """Mode encoding falls back to ECO when starting a cycle without a mode."""
    if mode is None or mode == "null":
        return _MODE_BYTE_ECO if state_byte == _STATE_BYTE_WORK else 0x00
    byte = Mode.byte_for(mode)
    if byte == 0x00 and state_byte == _STATE_BYTE_WORK:
        return _MODE_BYTE_ECO
    return byte
