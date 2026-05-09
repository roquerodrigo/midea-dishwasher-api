"""Nível do abrilhantador (rinse aid), 1 a 5."""

from __future__ import annotations

from enum import IntEnum


class BrightLevel(IntEnum):
    L1 = 1
    L2 = 2
    L3 = 3
    L4 = 4
    L5 = 5

    @classmethod
    def from_byte(cls, byte: int) -> "BrightLevel | int":
        try:
            return cls(byte)
        except ValueError:
            return byte
