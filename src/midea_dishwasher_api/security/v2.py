"""V2 (5A5A): empacotamento AES-ECB + MD5 do frame AA dentro do frame V3."""

from __future__ import annotations

from datetime import datetime, timezone
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


def _v2_timestamp() -> bytes:
    """Timestamp do V2: 8 bytes BCD-ish YYYYMMDDhhmmssXX (centiseconds)."""
    now = datetime.now(timezone.utc)
    return bytes([
        now.microsecond // 10000,
        now.second,
        now.minute,
        now.hour,
        now.day,
        now.month,
        now.year % 100,
        now.year // 100,
    ])


def v2_pack(device_id: int, frame: bytes) -> bytes:
    """Empacote um frame AA em um pacote V2 (5A5A)."""
    encrypted_payload = aes_ecb_encrypt(pkcs7_pad(frame), V2_ENC_KEY)
    length = V2_HEADER_LEN + len(encrypted_payload) + V2_SIGN_LEN
    header = (
        b"\x5a\x5a"
        + b"\x01\x11"
        + length.to_bytes(2, "little")
        + b"\x20\x00"
        + bytes(4)
        + _v2_timestamp()
        + device_id.to_bytes(8, "little")
        + bytes(12)
    )
    packet = header + encrypted_payload
    return packet + md5(packet + V2_SIGN_KEY).digest()


def v2_unpack(packet: bytes) -> bytes:
    """Extrai o frame AA de um pacote V2 (5A5A)."""
    if len(packet) < 6:
        raise V3Error(f"v2 packet too short: {len(packet)}")
    if packet[:2] != b"\x5a\x5a":
        raise V3Error(f"not a v2 packet: starts with {packet[:2].hex()}")
    length = int.from_bytes(packet[4:6], "little")
    if len(packet) < length:
        raise V3Error(f"v2 packet truncated: {len(packet)} < {length}")
    packet = packet[:length]
    encrypted_frame = packet[V2_HEADER_LEN:-V2_SIGN_LEN]
    rx_sign = packet[-V2_SIGN_LEN:]
    if md5(packet[:-V2_SIGN_LEN] + V2_SIGN_KEY).digest() != rx_sign:
        raise V3Error("v2 MD5 sign mismatch")
    decrypted = aes_ecb_decrypt(encrypted_frame, V2_ENC_KEY)
    return pkcs7_unpad(decrypted)
