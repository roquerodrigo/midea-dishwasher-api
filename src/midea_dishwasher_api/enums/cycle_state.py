"""Estado atual do ciclo (byte 1 da resposta de status)."""

from __future__ import annotations

from enum import StrEnum


class CycleState(StrEnum):
    POWER_OFF = "power_off"
    IDLE = "idle"
    ORDER = "order"
    WORK = "work"
    ERROR = "error"
    SOFT_GEAR = "soft_gear"

    @classmethod
    def from_byte(cls, byte: int) -> "CycleState | None":
        return _BYTE_TO_CYCLE_STATE.get(byte)


_BYTE_TO_CYCLE_STATE: dict[int, CycleState] = {
    0x00: CycleState.POWER_OFF,
    0x01: CycleState.IDLE,
    0x02: CycleState.ORDER,
    0x03: CycleState.WORK,
    0x04: CycleState.ERROR,
    0x05: CycleState.SOFT_GEAR,
}
