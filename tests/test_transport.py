"""Testes do transporte LAN V3 com socket falso (sem rede/hardware real).

Os frames de resposta são construídos byte-a-byte da mesma forma que o device
real responderia: handshake response 8370 type=1 e ENC_RESP type=3 contendo um
frame V2 (5A5A) que embrulha o frame AA da aplicação.
"""

from __future__ import annotations

import os
import socket
from hashlib import sha256

import pytest

from midea_dishwasher_api.protocol import assemble_frame
from midea_dishwasher_api.security import (
    HEADER_LEN,
    PACKET_ID_LEN,
    SIGN_LEN,
    Security,
    aes_cbc_encrypt,
    v2_pack,
)
from midea_dishwasher_api.security.v3_error import V3Error
from midea_dishwasher_api.transport import V3Transport

DEVICE_ID = 151732606394621
TOKEN = os.urandom(64)
KEY = bytes.fromhex("ab02a6952e5647c5bf0253d2b06f8e68687a2a2b5b3641e4bfee81d3f6291475")


class FakeSocket:
    """Socket falso: serve bytes de uma fila e grava tudo que for enviado."""

    def __init__(self, inbound: bytes) -> None:
        self._inbound = bytearray(inbound)
        self.sent = bytearray()
        self.closed = False

    def sendall(self, data: bytes) -> None:
        self.sent.extend(data)

    def recv(self, n: int) -> bytes:
        chunk = bytes(self._inbound[:n])
        del self._inbound[:n]
        return chunk

    def close(self) -> None:
        self.closed = True


def _handshake_response(plain: bytes) -> bytes:
    """8370 type=1 com payload AES(plain)+sha256(plain), igual ao device."""
    body = aes_cbc_encrypt(plain, KEY, b"\x00" * 16) + sha256(plain).digest()
    return b"\x83\x70" + (64).to_bytes(2, "big") + b"\x20\x01" + b"\x00\x00" + body


def _enc_response(sec: Security, aa_frame: bytes) -> bytes:
    """Constrói um ENC_RESP (type=3) válido envolvendo `aa_frame` num V2.

    Reaproveita o `Security` já autenticado: encode produz um REQ; viramos o
    type para RESP e regeramos o sign sobre o novo header, como o device faz.
    """
    from midea_dishwasher_api.security import TYPE_ENCRYPTED_RESPONSE, aes_cbc_decrypt

    v2 = v2_pack(DEVICE_ID, aa_frame)
    pkt = bytearray(sec.encode(v2))
    pad = (pkt[5] >> 4) & 0xF
    pkt[5] = (pad << 4) | TYPE_ENCRYPTED_RESPONSE
    assert sec.tcp_key is not None
    plaintext = aes_cbc_decrypt(bytes(pkt[HEADER_LEN:-SIGN_LEN]), sec.tcp_key, b"\x00" * 16)
    pkt[-SIGN_LEN:] = sha256(bytes(pkt[:HEADER_LEN]) + plaintext).digest()
    return bytes(pkt)


def _status_aa() -> bytes:
    body = bytearray(46)
    body[0] = 0x08
    body[1] = 0x03
    return assemble_frame(bytes(body), 0x02)


def _patch_socket(monkeypatch: pytest.MonkeyPatch, fake: FakeSocket) -> list[object]:
    """Faz socket.create_connection devolver o socket falso e registra args."""
    calls: list[object] = []

    def fake_create_connection(address: object, timeout: object = None) -> FakeSocket:
        calls.append((address, timeout))
        return fake

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)
    return calls


def _full_session_inbound() -> tuple[bytes, Security]:
    """Bytes que o device enviaria: handshake response + um ENC_RESP de status."""
    plain = os.urandom(32)
    sec = Security()
    sec.authenticate(_handshake_response(plain), KEY)
    inbound = _handshake_response(plain) + _enc_response(sec, _status_aa())
    # devolve um Security "fresco" igual ao que o transport derivará internamente
    return inbound, sec


def test_init_rejects_bad_token_length() -> None:
    with pytest.raises(ValueError, match="token must be 64 bytes"):
        V3Transport("1.2.3.4", DEVICE_ID, os.urandom(63), KEY)


def test_init_rejects_bad_key_length() -> None:
    with pytest.raises(ValueError, match="key must be 32 bytes"):
        V3Transport("1.2.3.4", DEVICE_ID, TOKEN, os.urandom(31))


def test_call_before_connect_raises() -> None:
    t = V3Transport("1.2.3.4", DEVICE_ID, TOKEN, KEY)
    with pytest.raises(V3Error, match="not connected"):
        t(b"\xaa\x0b\xe1")


def test_connect_handshake_and_request_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    inbound, _ = _full_session_inbound()
    fake = FakeSocket(inbound)
    calls = _patch_socket(monkeypatch, fake)

    on_wire: list[tuple[str, int]] = []
    t = V3Transport(
        "10.0.0.5",
        DEVICE_ID,
        TOKEN,
        KEY,
        port=6444,
        timeout=3.0,
        on_wire=lambda d, b: on_wire.append((d, len(b))),
    )
    t.connect()

    assert calls == [(("10.0.0.5", 6444), 3.0)]
    # handshake request foi enviado e começa com o magic 8370
    assert fake.sent[:2] == b"\x83\x70"

    reply = t(b"\xaa\x0b\xe1" + b"\x00" * 8 + b"\x03\x00\x11")
    assert reply == _status_aa()
    # TX handshake, RX handshake, TX request, RX response
    directions = [d for d, _ in on_wire]
    assert directions == ["TX", "RX", "TX", "RX"]


def test_context_manager_connects_and_closes(monkeypatch: pytest.MonkeyPatch) -> None:
    inbound, _ = _full_session_inbound()
    fake = FakeSocket(inbound)
    _patch_socket(monkeypatch, fake)

    with V3Transport("10.0.0.5", DEVICE_ID, TOKEN, KEY) as t:
        assert t(b"\xaa\x0b\xe1" + b"\x00" * 8 + b"\x03\x00\x11") == _status_aa()
    assert fake.closed is True


def test_close_is_idempotent_and_safe_without_socket() -> None:
    t = V3Transport("1.2.3.4", DEVICE_ID, TOKEN, KEY)
    # nunca conectou: close não deve explodir
    t.close()
    t.close()


def test_handshake_wrong_response_type_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    # frame ERROR (type=0xF) onde deveria vir um handshake response (type=1).
    # Decodifica sem tcp_key (não é encrypted) e bate na checagem de type.
    from midea_dishwasher_api.security import TYPE_ERROR

    # _recv_packet lê HEADER_LEN + PACKET_ID_LEN + size; com size=3 são 5 bytes
    wrong = (
        b"\x83\x70"
        + (3).to_bytes(2, "big")
        + b"\x20"
        + bytes([TYPE_ERROR])
        + b"\x00\x00"
        + b"\x01\x02\x03"
    )
    fake = FakeSocket(wrong)
    _patch_socket(monkeypatch, fake)

    t = V3Transport("1.2.3.4", DEVICE_ID, TOKEN, KEY)
    with pytest.raises(V3Error, match="expected handshake response"):
        t.connect()


def test_recv_packet_bad_magic_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    # header com magic errado: 6 bytes suficientes para _recv_exact(HEADER_LEN)
    bad = b"\x99\x99" + (64).to_bytes(2, "big") + b"\x20\x01"
    fake = FakeSocket(bad)
    _patch_socket(monkeypatch, fake)

    t = V3Transport("1.2.3.4", DEVICE_ID, TOKEN, KEY)
    with pytest.raises(V3Error, match="bad magic"):
        t.connect()


def test_recv_exact_eof_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    # só 3 bytes disponíveis; _recv_exact(HEADER_LEN=6) verá EOF
    fake = FakeSocket(b"\x83\x70\x00")
    _patch_socket(monkeypatch, fake)

    t = V3Transport("1.2.3.4", DEVICE_ID, TOKEN, KEY)
    with pytest.raises(V3Error, match="connection closed after"):
        t.connect()


def test_call_skips_non_enc_resp_frames(monkeypatch: pytest.MonkeyPatch) -> None:
    """Frames com msg_type != ENC_RESP devem ser ignorados até chegar o RESP."""
    plain = os.urandom(32)
    sec = Security()
    sec.authenticate(_handshake_response(plain), KEY)

    # primeiro um handshake response (type=1) ruído, depois o ENC_RESP real
    noise = _handshake_response(os.urandom(32))
    inbound = _handshake_response(plain) + noise + _enc_response(sec, _status_aa())
    fake = FakeSocket(inbound)
    _patch_socket(monkeypatch, fake)

    t = V3Transport("1.2.3.4", DEVICE_ID, TOKEN, KEY)
    t.connect()
    assert t(b"\xaa\x0b\xe1" + b"\x00" * 8 + b"\x03\x00\x11") == _status_aa()


def test_recv_exact_reassembles_fragmented_chunks() -> None:
    """_recv_exact deve concatenar leituras parciais do socket."""

    class DripSocket:
        def __init__(self, data: bytes) -> None:
            self._data = bytearray(data)

        def recv(self, _n: int) -> bytes:
            if not self._data:
                return b""
            one = bytes(self._data[:1])
            del self._data[:1]
            return one

    t = V3Transport("1.2.3.4", DEVICE_ID, TOKEN, KEY)
    t._sock = DripSocket(b"abcd")  # type: ignore[assignment]
    assert t._recv_exact(4) == b"abcd"


def test_recv_packet_reads_full_frame_by_size() -> None:
    """_recv_packet lê HEADER_LEN e depois PACKET_ID_LEN+size do corpo."""
    payload = b"\xee" * (PACKET_ID_LEN + 10)
    head = b"\x83\x70" + (10).to_bytes(2, "big") + b"\x20\x03"
    fake = FakeSocket(head + payload)
    t = V3Transport("1.2.3.4", DEVICE_ID, TOKEN, KEY)
    t._sock = fake  # type: ignore[assignment]
    assert t._recv_packet() == head + payload
