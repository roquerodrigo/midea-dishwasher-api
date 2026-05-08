"""Cliente Python para a lava-louças Midea (device type `0xE1`)."""

from importlib.metadata import PackageNotFoundError, version

from .client import Client
from .enums import (
    BrightLevel,
    CycleState,
    ErrorCode,
    MachineState,
    Mode,
    MsgType,
    WashStage,
)
from .protocol import (
    ControlPayload,
    FrameError,
    assemble_frame,
    build_control,
    build_query,
    parse_frame,
)
from .state import DishwasherStatus, decode_response
from .transport import OnWireCallback, V3Transport

try:
    __version__ = version("midea-dishwasher-api")
except PackageNotFoundError:
    __version__ = "0.0.0+local"

__all__ = [
    "BrightLevel",
    "Client",
    "ControlPayload",
    "CycleState",
    "DishwasherStatus",
    "ErrorCode",
    "FrameError",
    "MachineState",
    "Mode",
    "MsgType",
    "OnWireCallback",
    "V3Transport",
    "WashStage",
    "__version__",
    "assemble_frame",
    "build_control",
    "build_query",
    "decode_response",
    "parse_frame",
]
