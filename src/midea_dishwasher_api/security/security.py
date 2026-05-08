"""Cripto da camada V3 LAN da Midea: AES-128-CBC + SHA-256 + framing 8370.

Protocolo "MSC V3" implementado do zero. Layout do frame validado contra
device real (lava-louças Midea modelo 7600024L) e cruzado com a referência
documentada do protocolo.

Layout do frame V3 (header + payload + sign):

```
HEADER (6 bytes, plaintext):
  [0:2]  0x83 0x70                      magic
  [2:4]  uint16 BE                      size = len(data) + pad + 32
                                        (NÃO inclui o packet_id de 2B
                                         nem o próprio header)
  [4]    0x20                           constante
  [5]    (pad << 4) | type              pad no nibble alto, type no baixo
                                        type ∈ {0=HS_REQ, 1=HS_RESP,
                                                3=ENC_RESP, 6=ENC_REQ, 0xF=ERROR}

PAYLOAD em claro (size_to_encrypt = 2 + N + pad, sempre 16-alinhado):
  [0:2]  packet_id (uint16 BE)          contador, 12-bit, incrementado por request
  [2:2+N] data                          (frame AA da aplicação)
  [2+N:end] random padding (pad bytes)

WIRE (encrypted):
  header (6) | AES_CBC(payload, tcp_key, IV=0) (=size_to_encrypt B)
            | SHA256(header || payload) (32 B)

HANDSHAKE (sem encrypt, sem sign):
  header (6, type=0) | packet_id (2) | token (64 B)
```

Derivação da `tcp_key` (handshake response, mesmo que para encrypted):
```
plain = AES_CBC_Decrypt(payload[:32], cloud_key, IV=0)
assert sha256(plain) == payload[32:]
tcp_key = plain XOR cloud_key      # byte-a-byte (32 bytes)
```
"""

from __future__ import annotations

from hashlib import sha256
from os import urandom

from .crypto import (
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


class Security:
    def __init__(self) -> None:
        self.tcp_key: bytes | None = None
        self.packet_id: int = 0

    def handshake_request(self, token: bytes) -> bytes:
        if len(token) != 64:
            raise V3Error(f"token must be 64 bytes (got {len(token)})")
        header = build_header(len(token), TYPE_HANDSHAKE_REQUEST)
        packet = header + self._next_packet_id_bytes() + token
        return packet

    def authenticate(self, response: bytes, key: bytes) -> None:
        """Recebe o frame inteiro do handshake response (8370 …)."""
        if response == b"ERROR":
            raise V3Error("device returned ERROR during handshake")
        if len(response) < HEADER_LEN + PACKET_ID_LEN + 64:
            raise V3Error(f"handshake response too short: {len(response)} bytes")
        if response[:2] != b"\x83\x70":
            raise V3Error(f"bad magic: {response[:2].hex()}")
        body = response[HEADER_LEN + PACKET_ID_LEN:]
        if len(body) < 64:
            raise V3Error(f"handshake body too short: {len(body)}")
        if len(key) != 32:
            raise V3Error(f"key must be 32 bytes (got {len(key)})")
        payload = body[:32]
        sign = body[32:64]
        plain = aes_cbc_decrypt(payload, key, b"\x00" * 16)
        if sha256(plain).digest() != sign:
            raise V3Error("handshake signature mismatch — wrong key?")
        self.tcp_key = bytes(p ^ k for p, k in zip(plain, key))

    def encode(self, data: bytes) -> bytes:
        if self.tcp_key is None:
            raise V3Error("not authenticated — call authenticate() first")
        remainder = (len(data) + PACKET_ID_LEN) % 16
        pad = 16 - remainder if remainder else 0
        size = len(data) + pad + SIGN_LEN
        byte5 = (pad << 4) | TYPE_ENCRYPTED_REQUEST
        header = build_header(size, byte5)

        plaintext_payload = (
            self._next_packet_id_bytes()
            + data
            + (urandom(pad) if pad else b"")
        )
        ciphertext = aes_cbc_encrypt(plaintext_payload, self.tcp_key, b"\x00" * 16)
        sign = sha256(header + plaintext_payload).digest()
        return header + ciphertext + sign

    def decode(self, packet: bytes) -> tuple[int, bytes]:
        """Decodifica frame V3 recebido. Retorna (msg_type, AA_frame_or_raw_body)."""
        if len(packet) < HEADER_LEN:
            raise V3Error(f"frame too short: {len(packet)} bytes")
        if packet[:2] != b"\x83\x70":
            raise V3Error(f"bad magic: {packet[:2].hex()}")
        if packet[4] != 0x20:
            raise V3Error(f"unexpected byte 4: 0x{packet[4]:02x}")

        msg_type = packet[5] & 0x0F
        pad = (packet[5] >> 4) & 0x0F

        if msg_type == TYPE_ERROR:
            return msg_type, packet[HEADER_LEN:]

        if msg_type in (TYPE_HANDSHAKE_REQUEST, TYPE_HANDSHAKE_RESPONSE):
            return msg_type, packet[HEADER_LEN + PACKET_ID_LEN :]

        if msg_type in (TYPE_ENCRYPTED_REQUEST, TYPE_ENCRYPTED_RESPONSE):
            if self.tcp_key is None:
                raise V3Error("cannot decode encrypted frame without tcp_key")
            sign = packet[-SIGN_LEN:]
            ciphertext = packet[HEADER_LEN:-SIGN_LEN]
            if len(ciphertext) % 16:
                raise V3Error(
                    f"ciphertext not 16-aligned: {len(ciphertext)} bytes"
                )
            plaintext = aes_cbc_decrypt(ciphertext, self.tcp_key, b"\x00" * 16)
            expected_sign = sha256(packet[:HEADER_LEN] + plaintext).digest()
            if expected_sign != sign:
                raise V3Error("SHA256 mismatch on response")
            payload = plaintext[PACKET_ID_LEN:]
            if pad:
                payload = payload[:-pad]
            return msg_type, payload

        raise V3Error(f"unknown msg_type: 0x{msg_type:x}")

    def _next_packet_id_bytes(self) -> bytes:
        pid = self.packet_id.to_bytes(2, "big")
        self.packet_id = (self.packet_id + 1) & 0xFFF
        return pid

    @staticmethod
    def packet_total_length(buffer: bytes) -> int | None:
        """Lê o tamanho total esperado do frame se houver pelo menos 6 bytes."""
        if len(buffer) < HEADER_LEN:
            return None
        if buffer[:2] != b"\x83\x70":
            raise V3Error(f"bad magic: {buffer[:2].hex()}")
        size = (buffer[2] << 8) | buffer[3]
        return HEADER_LEN + PACKET_ID_LEN + size
