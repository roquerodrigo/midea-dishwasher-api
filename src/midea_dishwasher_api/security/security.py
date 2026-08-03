"""
V3 LAN cryptography: AES-128-CBC + SHA-256 over the 8370 framing.

The "MSC V3" protocol, implemented from scratch. The frame layout was validated
against a real device (Midea dishwasher model 7600024L) and cross-checked with
the documented protocol reference.

V3 frame layout (header + payload + sign):

```
HEADER (6 bytes, plaintext):
  [0:2]  0x83 0x70                      magic
  [2:4]  uint16 BE                      size = len(data) + pad + 32
                                        (excludes the 2-byte packet_id and
                                         the header itself)
  [4]    0x20                           constant
  [5]    (pad << 4) | type              pad in the high nibble, type in the low
                                        type in {0=HS_REQ, 1=HS_RESP,
                                                 3=ENC_RESP, 6=ENC_REQ, 0xF=ERROR}

PLAINTEXT PAYLOAD (size_to_encrypt = 2 + N + pad, always 16-aligned):
  [0:2]  packet_id (uint16 BE)          12-bit counter, incremented per request
  [2:2+N] data                          (the AA application frame)
  [2+N:end] random padding (pad bytes)

WIRE (encrypted):
  header (6) | AES_CBC(payload, tcp_key, IV=0) (=size_to_encrypt B)
            | SHA256(header || payload) (32 B)

HANDSHAKE (neither encrypted nor signed):
  header (6, type=0) | packet_id (2) | token (64 B)
```

Deriving the `tcp_key` from the handshake response:
```
plain = AES_CBC_Decrypt(payload[:32], cloud_key, IV=0)
assert sha256(plain) == payload[32:]
tcp_key = plain XOR cloud_key      # byte by byte (32 bytes)
```
"""

from __future__ import annotations

from hashlib import sha256
from os import urandom

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
    aes_cbc_decrypt,
    aes_cbc_encrypt,
    build_header,
)
from .v3_error import V3Error

MAGIC = b"\x83\x70"
TOKEN_LEN = 64
KEY_LEN = 32
ZERO_IV = b"\x00" * AES_BLOCK_LEN

_OFFSET_CONSTANT = 4
_CONSTANT_BYTE = 0x20


class Security:
    """Encodes, decodes and authenticates frames of one LAN V3 session."""

    def __init__(self) -> None:
        """Start a session with no negotiated key and a zeroed packet id."""
        self.tcp_key: bytes | None = None
        self.packet_id: int = 0

    def handshake_request(self, token: bytes) -> bytes:
        """Build the handshake request that opens the session."""
        if len(token) != TOKEN_LEN:
            msg = f"Failed to build handshake: token must be {TOKEN_LEN} bytes (got {len(token)})"
            raise V3Error(msg)
        header = build_header(len(token), TYPE_HANDSHAKE_REQUEST)
        return header + self._next_packet_id_bytes() + token

    def authenticate(self, response: bytes, key: bytes) -> None:
        """Derive the session key from the whole handshake response frame."""
        if response == b"ERROR":
            msg = "Failed to authenticate: device returned ERROR during handshake"
            raise V3Error(msg)
        if len(response) < HEADER_LEN + PACKET_ID_LEN + TOKEN_LEN:
            msg = f"Failed to authenticate: response too short, {len(response)} bytes"
            raise V3Error(msg)
        if response[:2] != MAGIC:
            msg = f"Failed to authenticate: bad magic {response[:2].hex()}"
            raise V3Error(msg)
        body = response[HEADER_LEN + PACKET_ID_LEN :]
        # Defensive: the length guard above already guarantees a full body.
        if len(body) < TOKEN_LEN:  # pragma: no cover
            msg = f"Failed to authenticate: body too short, {len(body)} bytes"
            raise V3Error(msg)
        if len(key) != KEY_LEN:
            msg = f"Failed to authenticate: key must be {KEY_LEN} bytes (got {len(key)})"
            raise V3Error(msg)
        payload = body[:KEY_LEN]
        sign = body[KEY_LEN:TOKEN_LEN]
        plain = aes_cbc_decrypt(payload, key, ZERO_IV)
        if sha256(plain).digest() != sign:
            msg = "Failed to authenticate: signature mismatch, wrong key?"
            raise V3Error(msg)
        self.tcp_key = bytes(p ^ k for p, k in zip(plain, key, strict=False))

    def encode(self, data: bytes) -> bytes:
        """Wrap application data in an encrypted, signed V3 frame."""
        if self.tcp_key is None:
            msg = "Failed to encode frame: not authenticated"
            raise V3Error(msg)
        remainder = (len(data) + PACKET_ID_LEN) % AES_BLOCK_LEN
        pad = AES_BLOCK_LEN - remainder if remainder else 0
        size = len(data) + pad + SIGN_LEN
        byte5 = (pad << 4) | TYPE_ENCRYPTED_REQUEST
        header = build_header(size, byte5)

        plaintext_payload = self._next_packet_id_bytes() + data + (urandom(pad) if pad else b"")
        ciphertext = aes_cbc_encrypt(plaintext_payload, self.tcp_key, ZERO_IV)
        sign = sha256(header + plaintext_payload).digest()
        return header + ciphertext + sign

    def decode(self, packet: bytes) -> tuple[int, bytes]:
        """Decode a received V3 frame into its message type and body."""
        if len(packet) < HEADER_LEN:
            msg = f"Failed to decode frame: too short, {len(packet)} bytes"
            raise V3Error(msg)
        if packet[:2] != MAGIC:
            msg = f"Failed to decode frame: bad magic {packet[:2].hex()}"
            raise V3Error(msg)
        if packet[_OFFSET_CONSTANT] != _CONSTANT_BYTE:
            msg = f"Failed to decode frame: byte 4 is 0x{packet[_OFFSET_CONSTANT]:02x}"
            raise V3Error(msg)

        msg_type = packet[5] & 0x0F
        pad = (packet[5] >> 4) & 0x0F

        if msg_type == TYPE_ERROR:
            return msg_type, packet[HEADER_LEN:]

        if msg_type in (TYPE_HANDSHAKE_REQUEST, TYPE_HANDSHAKE_RESPONSE):
            return msg_type, packet[HEADER_LEN + PACKET_ID_LEN :]

        if msg_type in (TYPE_ENCRYPTED_REQUEST, TYPE_ENCRYPTED_RESPONSE):
            return msg_type, self._decrypt_payload(packet, pad)

        msg = f"Failed to decode frame: unknown msg_type 0x{msg_type:x}"
        raise V3Error(msg)

    def _decrypt_payload(self, packet: bytes, pad: int) -> bytes:
        """Verify and decrypt the payload of an encrypted frame."""
        if self.tcp_key is None:
            msg = "Failed to decode frame: no session key negotiated"
            raise V3Error(msg)
        sign = packet[-SIGN_LEN:]
        ciphertext = packet[HEADER_LEN:-SIGN_LEN]
        if len(ciphertext) % AES_BLOCK_LEN:
            msg = f"Failed to decode frame: ciphertext not aligned, {len(ciphertext)} bytes"
            raise V3Error(msg)
        plaintext = aes_cbc_decrypt(ciphertext, self.tcp_key, ZERO_IV)
        expected_sign = sha256(packet[:HEADER_LEN] + plaintext).digest()
        if expected_sign != sign:
            msg = "Failed to decode frame: SHA256 mismatch on response"
            raise V3Error(msg)
        payload = plaintext[PACKET_ID_LEN:]
        return payload[:-pad] if pad else payload

    def _next_packet_id_bytes(self) -> bytes:
        """Return the current packet id and advance the 12-bit counter."""
        packet_id = self.packet_id.to_bytes(PACKET_ID_LEN, "big")
        self.packet_id = (self.packet_id + 1) & 0xFFF
        return packet_id

    @staticmethod
    def packet_total_length(buffer: bytes) -> int | None:
        """Return the frame's expected total length once the header is in."""
        if len(buffer) < HEADER_LEN:
            return None
        if buffer[:2] != MAGIC:
            msg = f"Failed to read frame length: bad magic {buffer[:2].hex()}"
            raise V3Error(msg)
        size = (buffer[2] << 8) | buffer[3]
        return HEADER_LEN + PACKET_ID_LEN + size
