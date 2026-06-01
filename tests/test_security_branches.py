"""Cobertura dos ramos de erro/validação da camada de segurança V3/V2.

Mesma abordagem byte-a-byte dos demais testes: frames montados à mão para
exercitar cada guarda de validação sem rede nem hardware.
"""

from __future__ import annotations

import os
from hashlib import sha256

import pytest

from midea_dishwasher_api.security import (
    HEADER_LEN,
    PACKET_ID_LEN,
    SIGN_LEN,
    TYPE_ENCRYPTED_RESPONSE,
    TYPE_ERROR,
    TYPE_HANDSHAKE_RESPONSE,
    Security,
    V3Error,
    aes_cbc_encrypt,
    v2_pack,
    v2_unpack,
)
from midea_dishwasher_api.security.crypto import pkcs7_pad, pkcs7_unpad

KEY = bytes.fromhex("ab02a6952e5647c5bf0253d2b06f8e68687a2a2b5b3641e4bfee81d3f6291475")
DEVICE_ID = 151732606394621


def _authed() -> Security:
    sec = Security()
    plain = os.urandom(32)
    body = aes_cbc_encrypt(plain, KEY, b"\x00" * 16) + sha256(plain).digest()
    fake = b"\x83\x70" + (64).to_bytes(2, "big") + b"\x20\x01" + b"\x00\x00" + body
    sec.authenticate(fake, KEY)
    return sec


def test_handshake_request_rejects_bad_token_length() -> None:
    with pytest.raises(V3Error, match="token must be 64 bytes"):
        Security().handshake_request(os.urandom(63))


def test_authenticate_rejects_literal_error_sentinel() -> None:
    with pytest.raises(V3Error, match="returned ERROR"):
        Security().authenticate(b"ERROR", KEY)


def test_authenticate_rejects_too_short_response() -> None:
    with pytest.raises(V3Error, match="too short"):
        Security().authenticate(b"\x83\x70\x00\x40\x20\x01\x00\x00", KEY)


def test_authenticate_rejects_bad_magic() -> None:
    bad = b"\x99\x99" + (64).to_bytes(2, "big") + b"\x20\x01" + b"\x00\x00" + b"\x00" * 64
    with pytest.raises(V3Error, match="bad magic"):
        Security().authenticate(bad, KEY)


def test_authenticate_rejects_bad_key_length() -> None:
    plain = os.urandom(32)
    body = aes_cbc_encrypt(plain, KEY, b"\x00" * 16) + sha256(plain).digest()
    fake = b"\x83\x70" + (64).to_bytes(2, "big") + b"\x20\x01" + b"\x00\x00" + body
    with pytest.raises(V3Error, match="key must be 32 bytes"):
        Security().authenticate(fake, os.urandom(16))


def test_encode_before_authenticate_raises() -> None:
    with pytest.raises(V3Error, match="not authenticated"):
        Security().encode(b"x" * 12)


def test_decode_rejects_too_short_frame() -> None:
    with pytest.raises(V3Error, match="frame too short"):
        Security().decode(b"\x83\x70\x00")


def test_decode_rejects_bad_magic() -> None:
    with pytest.raises(V3Error, match="bad magic"):
        Security().decode(b"\x99\x99\x00\x40\x20\x03")


def test_decode_rejects_unexpected_byte4() -> None:
    with pytest.raises(V3Error, match="unexpected byte 4"):
        Security().decode(b"\x83\x70\x00\x40\x21\x03")


def test_decode_error_frame_returns_raw_body() -> None:
    raw = b"\x83\x70" + (3).to_bytes(2, "big") + b"\x20" + bytes([TYPE_ERROR]) + b"\x01\x02\x03"
    msg_type, body = Security().decode(raw)
    assert msg_type == TYPE_ERROR
    assert body == b"\x01\x02\x03"


def test_decode_handshake_response_returns_body_after_packet_id() -> None:
    body = os.urandom(64)
    raw = (
        b"\x83\x70"
        + (64).to_bytes(2, "big")
        + b"\x20"
        + bytes([TYPE_HANDSHAKE_RESPONSE])
        + b"\x00\x00"
        + body
    )
    msg_type, out = Security().decode(raw)
    assert msg_type == TYPE_HANDSHAKE_RESPONSE
    assert out == body


def test_decode_encrypted_without_tcp_key_raises() -> None:
    raw = (
        b"\x83\x70"
        + (48).to_bytes(2, "big")
        + b"\x20"
        + bytes([TYPE_ENCRYPTED_RESPONSE])
        + b"\x00" * 48
    )
    with pytest.raises(V3Error, match="without tcp_key"):
        Security().decode(raw)


def test_decode_encrypted_rejects_unaligned_ciphertext() -> None:
    sec = _authed()
    # corpo (ciphertext) com 1 byte → não múltiplo de 16
    raw = (
        b"\x83\x70"
        + (1 + SIGN_LEN).to_bytes(2, "big")
        + b"\x20"
        + bytes([TYPE_ENCRYPTED_RESPONSE])
        + b"\xaa"
        + b"\x00" * SIGN_LEN
    )
    with pytest.raises(V3Error, match="not 16-aligned"):
        sec.decode(raw)


def test_decode_encrypted_rejects_bad_sign() -> None:
    sec = _authed()
    pkt = bytearray(sec.encode(b"x" * 12))
    pad = (pkt[5] >> 4) & 0xF
    pkt[5] = (pad << 4) | TYPE_ENCRYPTED_RESPONSE
    # não regeramos o sign → SHA256 mismatch
    with pytest.raises(V3Error, match="SHA256 mismatch"):
        sec.decode(bytes(pkt))


def test_decode_rejects_unknown_msg_type() -> None:
    raw = b"\x83\x70" + (0).to_bytes(2, "big") + b"\x20" + bytes([0x05])
    with pytest.raises(V3Error, match="unknown msg_type"):
        Security().decode(raw)


def test_packet_total_length_none_when_too_short() -> None:
    assert Security.packet_total_length(b"\x83\x70\x00") is None


def test_packet_total_length_bad_magic() -> None:
    with pytest.raises(V3Error, match="bad magic"):
        Security.packet_total_length(b"\x99\x99\x00\x40\x20\x03")


def test_packet_total_length_computes_expected_size() -> None:
    raw = b"\x83\x70" + (64).to_bytes(2, "big") + b"\x20\x01"
    assert Security.packet_total_length(raw) == HEADER_LEN + PACKET_ID_LEN + 64


def test_v2_unpack_rejects_too_short() -> None:
    with pytest.raises(V3Error, match="too short"):
        v2_unpack(b"\x5a\x5a\x01")


def test_v2_unpack_rejects_truncated() -> None:
    pkt = bytearray(v2_pack(DEVICE_ID, b"\xaa\x0b\xe1"))
    truncated = bytes(pkt[:-1])  # menos bytes do que o `length` declarado
    with pytest.raises(V3Error, match="truncated"):
        v2_unpack(truncated)


def test_pkcs7_unpad_empty_returns_empty() -> None:
    assert pkcs7_unpad(b"") == b""


def test_pkcs7_unpad_invalid_padding_returns_input() -> None:
    # último byte 0xFF não é padding PKCS7 válido → retorna como veio
    data = b"hello\xff"
    assert pkcs7_unpad(data) == data


def test_pkcs7_pad_unpad_roundtrip() -> None:
    data = b"\x01\x02\x03"
    assert pkcs7_unpad(pkcs7_pad(data)) == data
