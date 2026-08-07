"""Shared loader for the repo-root `.env` used by the device scripts."""

from __future__ import annotations

from pathlib import Path


def load_env(path: Path) -> dict[str, str]:
    """Parse `KEY=VALUE` lines, skipping comments and blank lines."""
    values: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values
