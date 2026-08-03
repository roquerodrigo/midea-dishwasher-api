"""Stage of the running wash cycle (byte 9 of the status response)."""

from __future__ import annotations

from enum import IntEnum


class WashStage(IntEnum):
    """Stage the machine reports for the cycle in progress."""

    IDLE = 0
    PRE_WASH = 1
    MAIN_WASH = 2
    RINSE = 3
    DRY = 4
    FINISH = 5

    @classmethod
    def from_byte(cls, byte: int) -> WashStage | int:
        """Return the stage for a status byte, or the byte itself if unknown."""
        try:
            return cls(byte)
        except ValueError:
            return byte
