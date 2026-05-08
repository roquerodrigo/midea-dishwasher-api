from __future__ import annotations

from dataclasses import dataclass

from ..enums import CycleState, ErrorCode, MachineState, WashStage


@dataclass(slots=True)
class DishwasherStatus:
    raw: bytes
    msg_type: int
    ack_only: bool = False

    machine_state: MachineState | None = None
    cycle_state: CycleState | None = None
    wash_stage: WashStage | int | None = None
    error_code: ErrorCode | int = ErrorCode.NONE
    left_time: int | None = None
    door_closed: bool = False
    bright_lack: bool = False
