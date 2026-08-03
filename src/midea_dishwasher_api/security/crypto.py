"""AES helpers and shared constants of the V3 and V2 layers."""

from __future__ import annotations

from hashlib import md5

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

HEADER_LEN = 6
SIGN_LEN = 32
PACKET_ID_LEN = 2

TYPE_HANDSHAKE_REQUEST = 0x0
TYPE_HANDSHAKE_RESPONSE = 0x1
TYPE_ENCRYPTED_RESPONSE = 0x3
TYPE_ENCRYPTED_REQUEST = 0x6
TYPE_ERROR = 0xF

V2_HEADER_LEN = 40
V2_SIGN_LEN = 16
V2_SIGN_KEY = b"xhdiwjnchekd4d512chdjx5d8e4c394D2D7S"
# MD5 and ECB below are what the V2 layer specifies; they are not our choice.
V2_ENC_KEY = md5(V2_SIGN_KEY).digest()

AES_BLOCK_LEN = 16


def aes_cbc_encrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    """Encrypt data with AES-CBC."""
    enc = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    return enc.update(data) + enc.finalize()


def aes_cbc_decrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    """Decrypt data with AES-CBC."""
    dec = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    return dec.update(data) + dec.finalize()


def aes_ecb_encrypt(data: bytes, key: bytes) -> bytes:
    """Encrypt data with AES-ECB, as the V2 layer requires."""
    enc = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
    return enc.update(data) + enc.finalize()


def aes_ecb_decrypt(data: bytes, key: bytes) -> bytes:
    """Decrypt data with AES-ECB, as the V2 layer requires."""
    dec = Cipher(algorithms.AES(key), modes.ECB()).decryptor()
    return dec.update(data) + dec.finalize()


def build_header(size: int, byte5: int) -> bytes:
    """Build the six-byte V3 header for a payload of the given size."""
    return b"\x83\x70" + size.to_bytes(2, "big") + b"\x20" + bytes([byte5])


def pkcs7_pad(data: bytes, block: int = AES_BLOCK_LEN) -> bytes:
    """Pad data to a whole number of blocks, PKCS#7 style."""
    pad = block - (len(data) % block)
    return data + bytes([pad] * pad)


def pkcs7_unpad(data: bytes) -> bytes:
    """Strip PKCS#7 padding, leaving the data untouched when there is none."""
    if not data:
        return data
    pad = data[-1]
    if 1 <= pad <= AES_BLOCK_LEN and data[-pad:] == bytes([pad] * pad):
        return data[:-pad]
    return data
