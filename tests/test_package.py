"""Cobre o fallback de versão quando o pacote não está instalado."""

from __future__ import annotations

import importlib
from importlib.metadata import PackageNotFoundError
from typing import TYPE_CHECKING

import midea_dishwasher_api

if TYPE_CHECKING:
    import pytest


def test_version_is_exposed() -> None:
    assert isinstance(midea_dishwasher_api.__version__, str)


def test_version_fallback_when_not_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sem metadata instalada, __version__ cai para o sentinela local."""

    def boom(_name: str) -> str:
        raise PackageNotFoundError

    monkeypatch.setattr("importlib.metadata.version", boom)
    reloaded = importlib.reload(midea_dishwasher_api)
    try:
        assert reloaded.__version__ == "0.0.0+local"
    finally:
        # restaura o módulo ao estado normal para os demais testes
        monkeypatch.undo()
        importlib.reload(midea_dishwasher_api)
