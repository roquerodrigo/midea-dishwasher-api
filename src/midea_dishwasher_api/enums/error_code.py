"""Fault code reported by the machine (byte 10 of the status response)."""

from __future__ import annotations

from enum import IntEnum


class ErrorCode(IntEnum):
    """Fault the machine is currently reporting."""

    NONE = 0
    WATER_SUPPLY = 1
    HEATING = 2
    OVERFLOW = 3
    WATER_VALVE = 4

    @classmethod
    def from_byte(cls, byte: int) -> ErrorCode | int:
        """Return the fault for a status byte, or the byte itself if unknown."""
        try:
            return cls(byte)
        except ValueError:
            return byte
