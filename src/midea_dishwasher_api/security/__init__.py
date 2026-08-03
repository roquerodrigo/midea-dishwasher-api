"""Cryptography and framing of the LAN V3 / V2 layers."""

from __future__ import annotations

from .crypto import (
    AES_BLOCK_LEN,
    HEADER_LEN,
    PACKET_ID_LEN,
    SIGN_LEN,
    TYPE_ENCRYPTED_REQUEST,
    TYPE_ENCRYPTED_RESPONSE,
    TYPE_ERROR,
    TYPE_HANDSHAKE_REQUEST,
    TYPE_HANDSHAKE_RESPONSE,
    V2_ENC_KEY,
    V2_HEADER_LEN,
    V2_SIGN_KEY,
    V2_SIGN_LEN,
    aes_cbc_decrypt,
    aes_cbc_encrypt,
    aes_ecb_decrypt,
    aes_ecb_encrypt,
)
from .security import KEY_LEN, MAGIC, TOKEN_LEN, ZERO_IV, Security
from .v2 import v2_pack, v2_unpack
from .v3_error import V3Error

__all__ = [
    "AES_BLOCK_LEN",
    "HEADER_LEN",
    "KEY_LEN",
    "MAGIC",
    "PACKET_ID_LEN",
    "SIGN_LEN",
    "TOKEN_LEN",
    "TYPE_ENCRYPTED_REQUEST",
    "TYPE_ENCRYPTED_RESPONSE",
    "TYPE_ERROR",
    "TYPE_HANDSHAKE_REQUEST",
    "TYPE_HANDSHAKE_RESPONSE",
    "V2_ENC_KEY",
    "V2_HEADER_LEN",
    "V2_SIGN_KEY",
    "V2_SIGN_LEN",
    "ZERO_IV",
    "Security",
    "V3Error",
    "aes_cbc_decrypt",
    "aes_cbc_encrypt",
    "aes_ecb_decrypt",
    "aes_ecb_encrypt",
    "v2_pack",
    "v2_unpack",
]
