"""Midea LAN V3 transport: TCP socket, handshake and 8370 send/receive."""

from __future__ import annotations

import logging
import socket
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Self

from ..enums import MsgType
from ..protocol import FrameError, parse_frame
from ..security import (
    KEY_LEN,
    MAGIC,
    PACKET_HEADER_LEN,
    PACKET_ID_LEN,
    TOKEN_LEN,
    TYPE_ENCRYPTED_RESPONSE,
    TYPE_HANDSHAKE_RESPONSE,
    Security,
    V3Error,
    v2_pack,
    v2_unpack,
)

if TYPE_CHECKING:
    from types import TracebackType

log: logging.Logger = logging.getLogger("midea_dishwasher_api.transport")

OnWireCallback = Callable[[str, bytes], None]

_QUERY_REPLY_GRACE = 1.0


def _noop_on_wire(_direction: str, _data: bytes) -> None:
    """Drop wire traces when the caller asked for none."""
    return


def _aa_msg_type(frame: bytes) -> int | None:
    """Return the message type of an AA frame, or None when the frame is not one."""
    try:
        msg_type, _body = parse_frame(frame)
    except FrameError:
        return None
    return msg_type


class V3Transport:
    """
    A LAN V3 session, usable as a context manager or via connect()/close().

    An instance is callable, so it can be passed straight to
    ``Client(send=transport)``.
    """

    def __init__(  # noqa: PLR0913, PLR0917 — host plus credentials are one logical bundle.
        self,
        host: str,
        device_id: int,
        token: bytes,
        key: bytes,
        port: int = 6444,
        timeout: float = 10.0,
        on_wire: OnWireCallback | None = None,
    ) -> None:
        """Validate the credentials up front and prepare an unconnected session."""
        if len(token) != TOKEN_LEN:
            msg = f"Failed to build transport: token must be {TOKEN_LEN} bytes (got {len(token)})"
            raise ValueError(msg)
        if len(key) != KEY_LEN:
            msg = f"Failed to build transport: key must be {KEY_LEN} bytes (got {len(key)})"
            raise ValueError(msg)
        self.host: str = host
        self.port: int = port
        self.device_id: int = device_id
        self._token: bytes = token
        self._key: bytes = key
        self._timeout: float = timeout
        self._sock: socket.socket | None = None
        self._security: Security = Security()
        self._on_wire: OnWireCallback = on_wire or _noop_on_wire

    def __enter__(self) -> Self:
        """Open the session on entry."""
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the session on exit."""
        self.close()

    def connect(self) -> None:
        """Open the TCP connection and complete the V3 handshake."""
        log.debug("connecting to %s:%d", self.host, self.port)
        try:
            self._sock = socket.create_connection((self.host, self.port), timeout=self._timeout)
        except OSError as error:
            msg = f"Failed to connect to {self.host}:{self.port}: {error}"
            raise V3Error(msg) from error
        self._handshake()

    def close(self) -> None:
        """Close the TCP connection, if one is open."""
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def __call__(self, frame: bytes) -> bytes:
        """Send an application frame and return the frame that answers it."""
        if self._sock is None:
            msg = "Failed to send frame: transport not connected"
            raise V3Error(msg)
        v2 = v2_pack(self.device_id, frame)
        request = self._security.encode(v2)
        self._on_wire("TX", request)
        self._send_all(request)

        return self._await_answer(_aa_msg_type(frame))

    def _await_answer(self, request_type: int | None) -> bytes:
        """Return the reply matching the request type, or the status push for a query."""
        # The machine pushes its status (0x04) unsolicited, even to a wrong
        # device_id, and drops some 0x03 query replies.
        deadline = time.monotonic() + self._timeout
        push: bytes | None = None
        while True:
            try:
                reply = self._recv_reply(deadline)
            except V3Error as error:
                if push is not None and isinstance(error.__cause__, TimeoutError):
                    log.debug("no reply to the query, answering with the status push")
                    return push
                raise
            reply_type = _aa_msg_type(reply)
            if request_type is None or reply_type in {request_type, None}:
                return reply
            if request_type == MsgType.QUERY and reply_type == MsgType.PUSH:
                if push is None:
                    deadline = min(deadline, time.monotonic() + _QUERY_REPLY_GRACE)
                push = reply
                continue
            log.debug(
                "ignoring AA frame of type 0x%02x while waiting for type 0x%02x",
                reply_type,
                request_type,
            )

    def _recv_reply(self, deadline: float) -> bytes:
        """Return the next AA frame the device sends, failing once the deadline passes."""
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                msg = "Failed to read response: no matching reply in time"
                raise V3Error(msg) from TimeoutError()
            # Periodic pushes would keep a per-recv timeout from ever firing.
            self._connected_socket().settimeout(remaining)
            packet = self._recv_packet()
            self._on_wire("RX", packet)
            msg_type, v2_body = self._security.decode(packet)
            if msg_type == TYPE_ENCRYPTED_RESPONSE:
                return v2_unpack(v2_body)
            log.debug("ignoring frame with msg_type=0x%x while waiting for ENC_RESP", msg_type)

    def _handshake(self) -> None:
        """Exchange the handshake and derive the session key."""
        request = self._security.handshake_request(self._token)
        self._on_wire("TX", request)
        self._send_all(request)

        packet = self._recv_packet()
        self._on_wire("RX", packet)
        msg_type, _body = self._security.decode(packet)
        if msg_type != TYPE_HANDSHAKE_RESPONSE:
            msg = f"Failed to handshake: expected type=1, got type=0x{msg_type:x}"
            raise V3Error(msg)
        self._security.authenticate(packet, self._key)
        log.info("V3 session established with %s", self.host)

    def _send_all(self, data: bytes) -> None:
        """Write every byte to the socket."""
        sock = self._connected_socket()
        try:
            sock.sendall(data)
        except OSError as error:
            msg = f"Failed to send request: {error}"
            raise V3Error(msg) from error

    def _recv_packet(self) -> bytes:
        """Read one whole 8370 packet off the socket."""
        head = self._recv_exact(PACKET_HEADER_LEN)
        if head[:2] != MAGIC:
            msg = f"Failed to read response: bad magic {head[:2].hex()}"
            raise V3Error(msg)
        size = (head[2] << 8) | head[3]
        body = self._recv_exact(PACKET_ID_LEN + size)
        return head + body

    def _recv_exact(self, size: int) -> bytes:
        """Read exactly ``size`` bytes, or fail if the device hangs up first."""
        sock = self._connected_socket()
        buffer = bytearray()
        while len(buffer) < size:
            try:
                chunk = sock.recv(size - len(buffer))
            except OSError as error:
                msg = f"Failed to read response: {error}"
                raise V3Error(msg) from error
            if not chunk:
                msg = f"Failed to read response: closed after {len(buffer)}/{size} bytes"
                raise V3Error(msg)
            buffer.extend(chunk)
        return bytes(buffer)

    def _connected_socket(self) -> socket.socket:
        """Return the open socket, or fail when the session is not connected."""
        if self._sock is None:
            msg = "Failed to use transport: not connected"
            raise V3Error(msg)
        return self._sock
