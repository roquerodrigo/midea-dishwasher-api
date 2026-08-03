"""High-level client: one method per operation the vendor app performs."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from .enums import BrightLevel
from .protocol import build_control, build_query
from .state import decode_response

if TYPE_CHECKING:
    from .enums import Mode
    from .protocol import ControlPayload
    from .state import DishwasherStatus

Send = Callable[[bytes], bytes]


class Client:
    """Talks the application protocol over any request/response transport."""

    def __init__(self, send: Send) -> None:
        """Bind the client to the transport that carries its frames."""
        self._send: Send = send

    def query_status(self) -> DishwasherStatus:
        """Return the machine's current status."""
        return decode_response(self._send(build_query()))

    def power_on(self) -> None:
        """Power the machine on."""
        self._control({"machine_state": "power_on"})

    def power_off(self) -> None:
        """Power the machine off."""
        self._control({"machine_state": "power_off"})

    def cancel_work(self) -> None:
        """Cancel the running cycle and return the machine to idle."""
        self._control({"machine_state": "cancel"})

    def start_to_work(self, mode: Mode, *, extra_drying: bool = False) -> None:
        """Start a wash cycle with the given program."""
        self._control(
            {
                "mode": str(mode),
                "machine_state": "work",
                "additional": 1 if extra_drying else 0,
            }
        )

    def set_bright(self, level: BrightLevel) -> None:
        """Set the rinse-aid dosage level, rejecting levels outside 1-5."""
        self._control({"bright": int(BrightLevel(level))})

    def _control(self, payload: ControlPayload) -> None:
        """Send a control frame and drop the acknowledgement."""
        self._send(build_control(payload))
