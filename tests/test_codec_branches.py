"""Ramos de validação do codec AA e do decoder/cliente de alto nível."""

from __future__ import annotations

import pytest

from midea_dishwasher_api import Client, FrameError
from midea_dishwasher_api.enums.machine_state import MachineState
from midea_dishwasher_api.protocol import assemble_frame, make_sum, parse_frame
from midea_dishwasher_api.state import decode_response


def test_parse_frame_rejects_too_short() -> None:
    with pytest.raises(FrameError, match="too short"):
        parse_frame(b"\xaa\x0b\xe1")


def test_parse_frame_rejects_bad_sync() -> None:
    frame = bytearray(assemble_frame(bytes(12), 0x02))
    frame[0] = 0xBB
    with pytest.raises(FrameError, match="bad sync"):
        parse_frame(bytes(frame))


def test_parse_frame_rejects_wrong_device_type() -> None:
    frame = bytearray(assemble_frame(bytes(12), 0x02))
    frame[2] = 0xAC
    # consertar o checksum para chegar até a checagem de device_type
    frame[-1] = make_sum(frame, 1, len(frame) - 2)
    with pytest.raises(FrameError, match="not a dishwasher frame"):
        parse_frame(bytes(frame))


def test_parse_frame_rejects_declared_length_mismatch() -> None:
    frame = bytearray(assemble_frame(bytes(12), 0x02))
    frame[1] = 0x05  # mente sobre o comprimento
    frame[-1] = make_sum(frame, 1, len(frame) - 2)
    with pytest.raises(FrameError, match="declared length"):
        parse_frame(bytes(frame))


def test_parse_frame_rejects_checksum_mismatch() -> None:
    frame = bytearray(assemble_frame(bytes(12), 0x02))
    frame[-1] ^= 0xFF
    with pytest.raises(FrameError, match="checksum mismatch"):
        parse_frame(bytes(frame))


def test_build_control_unknown_mode_starting_work_falls_back_to_eco() -> None:
    from midea_dishwasher_api.protocol import build_control

    # mode desconhecido + machine_state=work → byte de modo cai para ECO (0x04)
    frame = build_control({"mode": "does-not-exist", "machine_state": "work"})
    body = frame[10:48]
    assert body[1] == 0x03  # estado work
    assert body[2] == 0x04  # ECO fallback


def test_decode_response_ignores_non_decodable_msg_type() -> None:
    # msg_type 0x05 não está em _DECODABLE_MSG_TYPES → retorna status cru
    frame = assemble_frame(bytes(46), 0x05)
    status = decode_response(frame)
    assert status.msg_type == 0x05
    assert status.cycle_state is None
    assert status.ack_only is False


def test_client_query_power_off_cancel_set_bright() -> None:
    captured: list[bytes] = []

    def fake_send(frame: bytes) -> bytes:
        captured.append(frame)
        body = bytearray(46)
        body[0] = 0x08
        return assemble_frame(bytes(body), 0x02)

    c = Client(send=fake_send)
    c.power_off()
    assert captured[-1][11] == 0x00

    c.cancel_work()
    assert captured[-1][11] == 0x01

    c.set_bright(3)
    assert captured[-1][10] == 0x84
    assert captured[-1][11] == 0x03


def test_machine_state_from_byte() -> None:
    assert MachineState.from_byte(0x00) is MachineState.POWER_OFF
    assert MachineState.from_byte(0x01) is MachineState.POWER_ON
