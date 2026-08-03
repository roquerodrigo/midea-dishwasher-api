"""Message type of an application frame (byte 9)."""

from __future__ import annotations

from enum import IntEnum


class MsgType(IntEnum):
    """Kind of application frame exchanged with the machine."""

    CONTROL = 0x02
    QUERY = 0x03
    PUSH = 0x04
