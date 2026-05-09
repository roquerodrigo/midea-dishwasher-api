"""Cliente Python para a lava-louças Midea (device type `0xE1`)."""

from importlib.metadata import PackageNotFoundError, version

from .client import Client
from .enums import (
    BrightLevel,
    CycleState,
    ErrorCode,
    MachineState,
    Mode,
    WashStage,
)
from .protocol import FrameError
from .security import V3Error
from .state import DishwasherStatus
from .transport import V3Transport

try:
    __version__ = version("midea-dishwasher-api")
except PackageNotFoundError:
    __version__ = "0.0.0+local"

__all__ = [
    "BrightLevel",
    "Client",
    "CycleState",
    "DishwasherStatus",
    "ErrorCode",
    "FrameError",
    "MachineState",
    "Mode",
    "V3Error",
    "V3Transport",
    "WashStage",
    "__version__",
]
