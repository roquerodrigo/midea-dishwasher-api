"""Casos de borda dos enums: bytes desconhecidos caem no fallback inteiro."""

from __future__ import annotations

import pytest

from midea_dishwasher_api import ErrorCode, Mode, WashStage


def test_error_code_known_byte() -> None:
    assert ErrorCode.from_byte(1) is ErrorCode.WATER_SUPPLY


def test_error_code_unknown_byte_passes_through() -> None:
    assert ErrorCode.from_byte(99) == 99


def test_wash_stage_known_byte() -> None:
    assert WashStage.from_byte(2) is WashStage.MAIN_WASH


def test_wash_stage_unknown_byte_passes_through() -> None:
    assert WashStage.from_byte(99) == 99


def test_mode_to_byte() -> None:
    assert Mode.ECO.to_byte() == 0x04
    assert Mode.FRUIT.to_byte() == 0x13


def test_mode_byte_for_none_is_zero() -> None:
    assert Mode.byte_for(None) == 0x00


def test_mode_byte_for_known_string() -> None:
    assert Mode.byte_for("intensive") == 0x02


def test_mode_byte_for_unknown_string_is_zero() -> None:
    assert Mode.byte_for("does-not-exist") == 0x00


def test_mode_from_byte_zero_is_none() -> None:
    assert Mode.from_byte(0x00) is None


def test_mode_from_byte_known() -> None:
    assert Mode.from_byte(0x04) is Mode.ECO


def test_mode_from_byte_unknown_passes_through() -> None:
    assert Mode.from_byte(0x10) == 0x10


@pytest.mark.parametrize("mode", list(Mode))
def test_every_mode_has_a_byte(mode: Mode) -> None:
    assert isinstance(mode.to_byte(), int)
