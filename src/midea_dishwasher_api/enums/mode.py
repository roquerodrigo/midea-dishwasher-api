"""Modos de lavagem suportados pela máquina (byte 2 do controle 0x08)."""

from __future__ import annotations

from enum import StrEnum


class Mode(StrEnum):
    AUTO = "auto"
    INTENSIVE = "intensive"
    NORMAL = "normal"
    ECO = "eco"
    GLASS = "glass"
    NINETY_MIN = "90min"
    ONE_HOUR = "1hour"
    RAPID = "rapid"
    SOAK = "soak"
    THREE_IN_ONE = "3in1"
    HYGIENE = "hygiene"
    QUIET = "quiet"
    PARTY = "party"
    FRUIT = "fruit"

    def to_byte(self) -> int:
        return _MODE_TO_BYTE[self]

    @classmethod
    def byte_for(cls, mode: str | None) -> int:
        if mode is None:
            return 0x00
        try:
            return _MODE_TO_BYTE[cls(mode)]
        except ValueError:
            return 0x00


_MODE_TO_BYTE: dict[Mode, int] = {
    Mode.AUTO: 0x01,
    Mode.INTENSIVE: 0x02,
    Mode.NORMAL: 0x03,
    Mode.ECO: 0x04,
    Mode.GLASS: 0x05,
    Mode.NINETY_MIN: 0x06,
    Mode.RAPID: 0x07,
    Mode.SOAK: 0x08,
    Mode.ONE_HOUR: 0x09,
    Mode.THREE_IN_ONE: 0x0A,
    Mode.PARTY: 0x0C,
    Mode.QUIET: 0x0D,
    Mode.HYGIENE: 0x0F,
    Mode.FRUIT: 0x13,
}
