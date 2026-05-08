"""Cliente de alto nível: cada método replica uma operação `$api(...)` do app."""

from __future__ import annotations

from typing import Callable

from .enums import BrightLevel, Mode
from .protocol import ControlPayload, build_control, build_query
from .state import DishwasherStatus, decode_response

Send = Callable[[bytes], bytes]


class Client:
    def __init__(self, send: Send) -> None:
        self._send: Send = send

    def query_status(self) -> DishwasherStatus:
        return decode_response(self._send(build_query()))

    def power_on(self) -> None:
        self._control({"machine_state": "power_on"})

    def power_off(self) -> None:
        self._control({"machine_state": "power_off"})

    def cancel_work(self) -> None:
        self._control({"machine_state": "cancel"})

    def start_to_work(self, mode: Mode, extra_drying: bool = False) -> None:
        self._control({
            "mode": str(mode),
            "machine_state": "work",
            "additional": 1 if extra_drying else 0,
        })

    def set_bright(self, level: BrightLevel) -> None:
        self._control({"bright": int(BrightLevel(level))})

    def _control(self, payload: ControlPayload) -> None:
        self._send(build_control(payload))
