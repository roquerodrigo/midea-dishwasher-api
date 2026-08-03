"""Error raised when an application frame is malformed."""

from __future__ import annotations


class FrameError(ValueError):
    """Raised when a frame fails sync, device-type, length or checksum checks."""
