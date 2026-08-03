"""State of the cycle (byte 1 of the status response)."""

from __future__ import annotations

from enum import StrEnum


class CycleState(StrEnum):
    """What the machine is doing right now."""

    POWER_OFF = "power_off"
    IDLE = "idle"
    ORDER = "order"
    WORK = "work"
    ERROR = "error"
    SOFT_GEAR = "soft_gear"

    @classmethod
    def from_byte(cls, byte: int) -> CycleState | None:
        """Return the cycle state for a status byte, or None if unknown."""
        return _BYTE_TO_CYCLE_STATE.get(byte)


_BYTE_TO_CYCLE_STATE: dict[int, CycleState] = {
    0x00: CycleState.POWER_OFF,
    0x01: CycleState.IDLE,
    0x02: CycleState.ORDER,
    0x03: CycleState.WORK,
    0x04: CycleState.ERROR,
    0x05: CycleState.SOFT_GEAR,
}
