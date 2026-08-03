"""Power state of the machine (byte 1 of the status response)."""

from __future__ import annotations

from enum import StrEnum


class MachineState(StrEnum):
    """Whether the machine is powered on."""

    POWER_ON = "power_on"
    POWER_OFF = "power_off"

    @classmethod
    def from_byte(cls, byte: int) -> MachineState:
        """Return the power state a cycle-state byte implies."""
        return cls.POWER_OFF if byte == 0x00 else cls.POWER_ON
