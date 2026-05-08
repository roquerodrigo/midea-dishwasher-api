"""Testes da camada V3 (8370 + AES-CBC + SHA256) e V2 (5A5A + AES-ECB + MD5)."""

from __future__ import annotations

import os
from hashlib import sha256

import pytest

from midea_dishwasher_api.security import (
    HEADER_LEN,
    PACKET_ID_LEN,
    SIGN_LEN,
    Security,
    TYPE_ENCRYPTED_REQUEST,
    TYPE_ENCRYPTED_RESPONSE,
    TYPE_HANDSHAKE_REQUEST,
    TYPE_HANDSHAKE_RESPONSE,
    V2_ENC_KEY,
    V2_HEADER_LEN,
    V2_SIGN_LEN,
    V2_SIGN_KEY,
    V3Error,
    aes_cbc_encrypt,
    v2_pack,
    v2_unpack,
)


DEVICE_ID = 151732606394621
TOKEN = bytes.fromhex(
    "ce02074c2489ecd0a77d0116526490354203f34443cf1d64eadeffb0c070335d"
    "0b663a9d8642a2628b287de9ce3da93a11eac19f3d16009a65f1ddad0e2a8328"
)
KEY = bytes.fromhex(
    "ab02a6952e5647c5bf0253d2b06f8e68687a2a2b5b3641e4bfee81d3f6291475"
)


def test_handshake_packet_layout() -> None:
    sec = Security()
    pkt = sec.handshake_request(TOKEN)
    assert len(pkt) == HEADER_LEN + PACKET_ID_LEN + 64
    assert pkt[:2] == b"\x83\x70"
    assert (pkt[2] << 8) | pkt[3] == 64
    assert pkt[4] == 0x20
    assert pkt[5] == TYPE_HANDSHAKE_REQUEST
    assert pkt[HEADER_LEN + PACKET_ID_LEN:] == TOKEN


def test_authenticate_with_valid_handshake_response() -> None:
    sec = Security()
    plain = os.urandom(32)
    body = aes_cbc_encrypt(plain, KEY, b"\x00" * 16) + sha256(plain).digest()
    fake = b"\x83\x70" + (64).to_bytes(2, "big") + b"\x20\x01" + b"\x00\x00" + body
    sec.authenticate(fake, KEY)
    assert sec.tcp_key is not None
    assert sec.tcp_key == bytes(p ^ k for p, k in zip(plain, KEY))


def test_authenticate_rejects_bad_signature() -> None:
    sec = Security()
    plain = os.urandom(32)
    body = aes_cbc_encrypt(plain, KEY, b"\x00" * 16) + b"\x00" * 32
    fake = b"\x83\x70" + (64).to_bytes(2, "big") + b"\x20\x01" + b"\x00\x00" + body
    with pytest.raises(V3Error, match="signature mismatch"):
        sec.authenticate(fake, KEY)


def _establish_session() -> Security:
    sec = Security()
    plain = os.urandom(32)
    body = aes_cbc_encrypt(plain, KEY, b"\x00" * 16) + sha256(plain).digest()
    fake = b"\x83\x70" + (64).to_bytes(2, "big") + b"\x20\x01" + b"\x00\x00" + body
    sec.authenticate(fake, KEY)
    return sec


def test_v3_encode_pad_and_size() -> None:
    sec = _establish_session()
    data = b"x" * 12
    pkt = sec.encode(data)
    assert pkt[:2] == b"\x83\x70"
    pad = (pkt[5] >> 4) & 0xF
    msg_type = pkt[5] & 0xF
    assert msg_type == TYPE_ENCRYPTED_REQUEST
    assert (12 + PACKET_ID_LEN + pad) % 16 == 0
    size = (pkt[2] << 8) | pkt[3]
    assert size == 12 + pad + SIGN_LEN
    assert len(pkt) == HEADER_LEN + PACKET_ID_LEN + 12 + pad + SIGN_LEN


def test_v3_encode_decode_roundtrip() -> None:
    """Roundtrip ‘fingindo ser device': cliente codifica como REQ, simulamos
    o device alterando type para RESP e regerando o sign sobre o NOVO header."""
    from midea_dishwasher_api.security import aes_cbc_decrypt
    sec = _establish_session()
    data = b"\xaa\x0b\xe1" + b"\x00" * 8 + b"\x03\x00\x11"
    pkt = sec.encode(data)
    pad = (pkt[5] >> 4) & 0xF
    flipped = bytearray(pkt)
    flipped[5] = (pad << 4) | TYPE_ENCRYPTED_RESPONSE
    plaintext = aes_cbc_decrypt(
        bytes(flipped[HEADER_LEN:-SIGN_LEN]), sec.tcp_key, b"\x00" * 16
    )
    flipped[-SIGN_LEN:] = sha256(bytes(flipped[:HEADER_LEN]) + plaintext).digest()
    msg_type, body = sec.decode(bytes(flipped))
    assert msg_type == TYPE_ENCRYPTED_RESPONSE
    assert body == data


def test_v3_packet_id_increments_and_wraps() -> None:
    sec = _establish_session()
    pid_before = sec.packet_id
    sec.encode(b"x" * 12)
    pid_after_first = sec.packet_id
    sec.encode(b"x" * 12)
    pid_after_second = sec.packet_id
    assert pid_after_first == pid_before + 1
    assert pid_after_second == pid_before + 2


def test_v2_constants() -> None:
    assert len(V2_ENC_KEY) == 16
    assert V2_SIGN_KEY == b"xhdiwjnchekd4d512chdjx5d8e4c394D2D7S"


def test_v2_pack_layout() -> None:
    aa = bytes.fromhex("aa0be1000000000000030011")
    pkt = v2_pack(DEVICE_ID, aa)
    assert pkt[:2] == b"\x5a\x5a"
    assert pkt[2:4] == b"\x01\x11"
    length = int.from_bytes(pkt[4:6], "little")
    assert length == len(pkt)
    assert pkt[6:8] == b"\x20\x00"
    assert pkt[8:12] == b"\x00\x00\x00\x00"
    assert int.from_bytes(pkt[20:28], "little") == DEVICE_ID
    assert pkt[28:40] == b"\x00" * 12
    encrypted_size = length - V2_HEADER_LEN - V2_SIGN_LEN
    assert encrypted_size % 16 == 0


def test_v2_pack_unpack_roundtrip() -> None:
    aa = bytes.fromhex(
        "aa30e1000000000000020803040003000000000000000001"
        "0000000000000000000000000000000000000000000000da"
    )
    pkt = v2_pack(DEVICE_ID, aa)
    assert v2_unpack(pkt) == aa


def test_v2_unpack_rejects_bad_md5() -> None:
    aa = bytes.fromhex("aa0be1000000000000030011")
    pkt = bytearray(v2_pack(DEVICE_ID, aa))
    pkt[-1] ^= 0x01
    with pytest.raises(V3Error, match="MD5"):
        v2_unpack(bytes(pkt))


def test_v2_unpack_rejects_wrong_magic() -> None:
    with pytest.raises(V3Error, match="not a v2"):
        v2_unpack(b"\x5b\x5a\x01\x11\x40\x00")
