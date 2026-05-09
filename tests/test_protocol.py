"""Testes byte-exatos contra o que o plugin Lua T_0000_E1_5.lua produziria."""

from __future__ import annotations

from midea_dishwasher_api import (
    BrightLevel,
    Client,
    CycleState,
    DishwasherStatus,
    Mode,
    WashStage,
)
from midea_dishwasher_api.protocol import (
    assemble_frame,
    build_control,
    build_query,
    make_sum,
    parse_frame,
)
from midea_dishwasher_api.state import decode_response


def test_make_sum_matches_lua_two_complement() -> None:
    assert make_sum(b"\x0b\xe1\x03\x00", 0, 3) == 0x11
    assert make_sum(b"\xff\x01", 0, 1) == 0x00


def test_query_frame() -> None:
    f = build_query()
    assert len(f) == 12
    assert f[0] == 0xAA
    assert f[1] == 0x0B
    assert f[2] == 0xE1
    assert f[9] == 0x03
    assert f[10] == 0x00
    assert make_sum(f, 1, len(f) - 2) == f[-1]


def test_power_on_frame_matches_lua() -> None:
    f = build_control({"machine_state": "power_on"})
    assert len(f) == 49
    assert f[:10] == b"\xaa\x30\xe1\x00\x00\x00\x00\x00\x00\x02"
    assert f[10] == 0x08
    assert f[11] == 0x01
    assert all(b == 0 for b in f[12:48])
    assert f[-1] == make_sum(f, 1, 47)


def test_power_off_frame() -> None:
    f = build_control({"machine_state": "power_off"})
    assert f[10] == 0x08
    assert f[11] == 0x00


def test_set_bright_uses_opcode_84() -> None:
    f = build_control({"bright": int(BrightLevel.L4)})
    assert f[10] == 0x84
    assert f[11] == 0x04


def test_start_to_work_eco_layout() -> None:
    f = build_control({"mode": "eco", "machine_state": "work"})
    body = f[10:48]
    assert body[0] == 0x08
    assert body[1] == 0x03
    assert body[2] == 0x04


def test_start_to_work_defaults_mode_to_eco_when_missing() -> None:
    f = build_control({"machine_state": "work"})
    body = f[10:48]
    assert body[0] == 0x08
    assert body[1] == 0x03
    assert body[2] == 0x04


def test_parse_frame_roundtrip() -> None:
    f = build_control({"machine_state": "power_on"})
    msg_type, body = parse_frame(f)
    assert msg_type == 0x02
    assert len(body) == 38
    assert body[0] == 0x08
    assert body[1] == 0x01


def test_decode_response_status() -> None:
    body = bytearray(46)
    body[0] = 0x08
    body[1] = 0x03
    body[2] = 0x04  # mode = ECO
    body[5] = 0x01 | 0x02  # bit0 = door_closed; bit1 = bright_lack
    body[6] = 100
    body[9] = 2
    body[10] = 1
    body[24] = 4  # bright level
    body[32] = 1
    frame = assemble_frame(bytes(body), 0x02)

    s = decode_response(frame)
    assert s.cycle_state == CycleState.WORK
    assert s.mode == Mode.ECO
    assert s.door_closed is True
    assert s.bright_lack is True
    assert s.left_time == 0x0164
    assert s.wash_stage == WashStage.MAIN_WASH
    assert s.error_code == 1
    assert s.bright == BrightLevel.L4


def test_decode_response_mode_zero_means_no_program() -> None:
    body = bytearray(46)
    body[0] = 0x08
    body[1] = 0x01  # cancel
    body[2] = 0x00  # mode = null
    frame = assemble_frame(bytes(body), 0x02)

    s = decode_response(frame)
    assert s.mode is None


def test_decode_response_mode_unknown_byte_passes_through() -> None:
    body = bytearray(46)
    body[0] = 0x08
    body[1] = 0x01
    body[2] = 0x10  # self_clean — not in our enum yet
    frame = assemble_frame(bytes(body), 0x02)

    s = decode_response(frame)
    assert s.mode == 0x10


def test_decode_response_bright_unknown_byte_passes_through() -> None:
    body = bytearray(46)
    body[0] = 0x08
    body[1] = 0x01
    body[24] = 99  # outside the 1-5 enum range
    frame = assemble_frame(bytes(body), 0x02)

    s = decode_response(frame)
    assert s.bright == 99


def test_decode_response_bright_absent_when_body_short() -> None:
    body = bytearray(20)  # shorter than offset 24
    body[0] = 0x08
    body[1] = 0x01
    frame = assemble_frame(bytes(body), 0x02)

    s = decode_response(frame)
    assert s.bright is None


def test_client_uses_transport() -> None:
    captured: list[bytes] = []

    def fake_transport(frame: bytes) -> bytes:
        captured.append(frame)
        body = bytearray(46)
        body[0] = 0x08
        return assemble_frame(bytes(body), 0x02)

    c = Client(send=fake_transport)
    assert c.power_on() is None
    assert captured[0][10] == 0x08
    assert captured[0][11] == 0x01

    c.start_to_work(mode=Mode.ECO)
    body = captured[1][10:48]
    assert body[0] == 0x08 and body[1] == 0x03 and body[2] == 0x04

    s = c.query_status()
    assert isinstance(s, DishwasherStatus)


def test_set_bright_validation() -> None:
    c = Client(send=lambda _: assemble_frame(bytes(46), 0x02))
    try:
        c.set_bright(7)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_ack_only_frame() -> None:
    body = bytearray(38)
    body[0] = 0x01
    frame = assemble_frame(bytes(body), 0x02)
    s = decode_response(frame)
    assert s.ack_only is True
