"""Rinse-aid dosage level, 1 to 5."""

from __future__ import annotations

from enum import IntEnum


class BrightLevel(IntEnum):
    """Rinse-aid dosage the machine dispenses per cycle."""

    L1 = 1
    L2 = 2
    L3 = 3
    L4 = 4
    L5 = 5

    @classmethod
    def from_byte(cls, byte: int) -> BrightLevel | int:
        """Return the level for a status byte, or the byte itself if unknown."""
        try:
            return cls(byte)
        except ValueError:
            return byte
