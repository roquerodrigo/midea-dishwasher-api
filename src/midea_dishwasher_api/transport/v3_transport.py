"""Transporte LAN V3 da Midea: TCP socket + handshake + send/recv 8370."""

from __future__ import annotations

import logging
import socket
from types import TracebackType
from typing import Callable, Self

from ..security import (
    HEADER_LEN,
    PACKET_ID_LEN,
    Security,
    TYPE_ENCRYPTED_RESPONSE,
    TYPE_HANDSHAKE_RESPONSE,
    V3Error,
    v2_pack,
    v2_unpack,
)

log: logging.Logger = logging.getLogger("midea_dishwasher_api.transport")

OnWireCallback = Callable[[str, bytes], None]


def _noop_on_wire(_direction: str, _data: bytes) -> None:
    return None


class V3Transport:
    """Sessão LAN V3. Use como context manager OU `connect()` + `close()`.

    Pode ser passado direto como `send` para `Client(send=transport)`.
    """

    def __init__(
        self,
        host: str,
        device_id: int,
        token: bytes,
        key: bytes,
        port: int = 6444,
        timeout: float = 10.0,
        on_wire: OnWireCallback | None = None,
    ) -> None:
        if len(token) != 64:
            raise ValueError(f"token must be 64 bytes (got {len(token)})")
        if len(key) != 32:
            raise ValueError(f"key must be 32 bytes (got {len(key)})")
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
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def connect(self) -> None:
        log.debug("connecting to %s:%d", self.host, self.port)
        self._sock = socket.create_connection(
            (self.host, self.port), timeout=self._timeout
        )
        self._handshake()

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def __call__(self, frame: bytes) -> bytes:
        if self._sock is None:
            raise V3Error("transport not connected — call connect() first")
        v2 = v2_pack(self.device_id, frame)
        request = self._security.encode(v2)
        self._on_wire("TX", request)
        self._send_all(request)

        while True:
            packet = self._recv_packet()
            self._on_wire("RX", packet)
            msg_type, v2_body = self._security.decode(packet)
            if msg_type == TYPE_ENCRYPTED_RESPONSE:
                return v2_unpack(v2_body)
            log.debug("ignoring frame with msg_type=0x%x while waiting for ENC_RESP", msg_type)

    def _handshake(self) -> None:
        request = self._security.handshake_request(self._token)
        self._on_wire("TX", request)
        self._send_all(request)

        packet = self._recv_packet()
        self._on_wire("RX", packet)
        msg_type, _body = self._security.decode(packet)
        if msg_type != TYPE_HANDSHAKE_RESPONSE:
            raise V3Error(
                f"expected handshake response (type=1), got type=0x{msg_type:x}"
            )
        self._security.authenticate(packet, self._key)
        log.info("V3 session established with %s", self.host)

    def _send_all(self, data: bytes) -> None:
        assert self._sock is not None
        self._sock.sendall(data)

    def _recv_packet(self) -> bytes:
        assert self._sock is not None
        head = self._recv_exact(HEADER_LEN)
        if head[:2] != b"\x83\x70":
            raise V3Error(f"bad magic in response: {head[:2].hex()}")
        size = (head[2] << 8) | head[3]
        body = self._recv_exact(PACKET_ID_LEN + size)
        return head + body

    def _recv_exact(self, n: int) -> bytes:
        assert self._sock is not None
        buf = bytearray()
        while len(buf) < n:
            chunk = self._sock.recv(n - len(buf))
            if not chunk:
                raise V3Error(
                    f"connection closed after {len(buf)}/{n} bytes"
                )
            buf.extend(chunk)
        return bytes(buf)
