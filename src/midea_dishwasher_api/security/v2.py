"""V2 (5A5A) layer: AES-ECB + MD5 wrapping of an AA frame inside a V3 frame."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import md5

from .crypto import (
    V2_ENC_KEY,
    V2_HEADER_LEN,
    V2_SIGN_KEY,
    V2_SIGN_LEN,
    aes_ecb_decrypt,
    aes_ecb_encrypt,
    pkcs7_pad,
    pkcs7_unpad,
)
from .v3_error import V3Error

_V2_MAGIC = b"\x5a\x5a"
_V2_LENGTH_OFFSET_END = 6


def _v2_timestamp() -> bytes:
    """Return the V2 timestamp: 8 BCD-ish bytes, YYYYMMDDhhmmssXX."""
    now = datetime.now(UTC)
    return bytes(
        [
            now.microsecond // 10000,
            now.second,
            now.minute,
            now.hour,
            now.day,
            now.month,
            now.year % 100,
            now.year // 100,
        ]
    )


def v2_pack(device_id: int, frame: bytes) -> bytes:
    """Wrap an AA frame in a V2 (5A5A) packet."""
    encrypted_payload = aes_ecb_encrypt(pkcs7_pad(frame), V2_ENC_KEY)
    length = V2_HEADER_LEN + len(encrypted_payload) + V2_SIGN_LEN
    header = (
        _V2_MAGIC
        + b"\x01\x11"
        + length.to_bytes(2, "little")
        + b"\x20\x00"
        + bytes(4)
        + _v2_timestamp()
        + device_id.to_bytes(8, "little")
        + bytes(12)
    )
    packet = header + encrypted_payload
    return packet + md5(packet + V2_SIGN_KEY).digest()  # noqa: S324


def v2_unpack(packet: bytes) -> bytes:
    """Extract the AA frame carried by a V2 (5A5A) packet."""
    if len(packet) < _V2_LENGTH_OFFSET_END:
        msg = f"Failed to unpack v2 packet: too short, {len(packet)} bytes"
        raise V3Error(msg)
    if packet[:2] != _V2_MAGIC:
        msg = f"Failed to unpack v2 packet: starts with {packet[:2].hex()}"
        raise V3Error(msg)
    length = int.from_bytes(packet[4:_V2_LENGTH_OFFSET_END], "little")
    if len(packet) < length:
        msg = f"Failed to unpack v2 packet: truncated, {len(packet)} < {length}"
        raise V3Error(msg)
    packet = packet[:length]
    encrypted_frame = packet[V2_HEADER_LEN:-V2_SIGN_LEN]
    received_sign = packet[-V2_SIGN_LEN:]
    if md5(packet[:-V2_SIGN_LEN] + V2_SIGN_KEY).digest() != received_sign:  # noqa: S324
        msg = "Failed to unpack v2 packet: MD5 sign mismatch"
        raise V3Error(msg)
    decrypted = aes_ecb_decrypt(encrypted_frame, V2_ENC_KEY)
    return pkcs7_unpad(decrypted)
