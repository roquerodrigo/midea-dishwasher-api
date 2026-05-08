"""Tipo de mensagem do frame (byte 9)."""

from __future__ import annotations

from enum import IntEnum


class MsgType(IntEnum):
    CONTROL = 0x02
    QUERY = 0x03
    PUSH = 0x04
