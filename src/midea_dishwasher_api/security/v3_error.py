"""Error raised by the LAN V3 session layer."""

from __future__ import annotations


class V3Error(RuntimeError):
    """Raised on handshake, authentication, framing or transport failures."""
