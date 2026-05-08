"""Etapa atual do ciclo de lavagem (byte 9 da resposta)."""

from __future__ import annotations

from enum import IntEnum


class WashStage(IntEnum):
    IDLE = 0
    PRE_WASH = 1
    MAIN_WASH = 2
    RINSE = 3
    DRY = 4
    FINISH = 5

    @classmethod
    def from_byte(cls, byte: int) -> "WashStage | int":
        try:
            return cls(byte)
        except ValueError:
            return byte
