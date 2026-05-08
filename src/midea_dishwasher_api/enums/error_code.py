"""Código de falha reportado pela máquina (byte 10 da resposta)."""

from __future__ import annotations

from enum import IntEnum


class ErrorCode(IntEnum):
    NONE = 0
    WATER_SUPPLY = 1
    HEATING = 2
    OVERFLOW = 3
    WATER_VALVE = 4

    @classmethod
    def from_byte(cls, byte: int) -> "ErrorCode | int":
        try:
            return cls(byte)
        except ValueError:
            return byte
