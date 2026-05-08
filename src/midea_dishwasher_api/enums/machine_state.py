from __future__ import annotations

from enum import StrEnum


class MachineState(StrEnum):
    POWER_ON = "power_on"
    POWER_OFF = "power_off"

    @classmethod
    def from_byte(cls, byte: int) -> "MachineState":
        return cls.POWER_OFF if byte == 0x00 else cls.POWER_ON
