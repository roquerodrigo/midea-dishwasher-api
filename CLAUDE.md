# midea-dishwasher-api

Python SDK for Midea dishwashers (`device_type 0xE1`, plugin v5). Implements
the `AA … E1` application protocol and the LAN V3 transport (8370 handshake +
AES-128-CBC + SHA-256, with internal V2 5A5A framing). Published to PyPI.

This is a standalone SDK, consumed by the `ha-midea-dishwasher` Home
Assistant integration (a separate repo) — it has no Home Assistant
dependency itself.

**Read `CODE_STYLE.md` before adding or restructuring any code.** It is the
authoritative, detailed style guide (naming, typing, imports, docstrings,
logging, error messages, commit format, releasing). This file only covers
what `CODE_STYLE.md` doesn't: project shape and day-to-day commands.

## Layout

`src/midea_dishwasher_api/` splits by concern: `protocol/` (byte-level frame
codec), `security/` (AES/SHA crypto + V2 framing), `transport/` (`V3Transport`
LAN socket), `state/` (`DishwasherStatus` + `decode_response()`), `enums/`, and
`client.py` (high-level `Client`, one method per app operation). `scripts/` are
manual tools against a real device, not part of the package or CI.

Public API surface is exactly what `src/midea_dishwasher_api/__init__.py`
re-exports (`Client`, `V3Transport`, `DishwasherStatus`, the enums,
`FrameError`, `V3Error`, `__version__`). Everything else is internal.

## Setup

Requires Python ≥3.14 and [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync                 # installs dev + lint groups by default (tool.uv.default-groups)
```

## Running things

```bash
uv run pytest                                       # tests, coverage gated at 90% (see pyproject.toml)
uv run ruff format . && uv run ruff check . --fix    # format + lint
uv run mypy src                                      # strict type check (src/ only, not tests/)
```

All three (format, check, mypy) must exit clean, then `pytest`, before
committing — this mirrors CI exactly.

`scripts/dump_state.py` and `scripts/test_device.py` talk to a **real
device** over LAN using credentials from a local `.env` (`DEVICE_HOST`,
`DEVICE_PORT`, `DEVICE_ID`, `DEVICE_TOKEN`, `DEVICE_KEY`) — they are
excluded from ruff (`exclude = ["scripts"]` in `pyproject.toml`) and from
the test suite. Don't expect them to run in CI or without hardware.

## CI / release

- `.github/workflows/ci.yml` delegates lint, tests, CodeQL, and release to
  reusable workflows in `roquerodrigo/.github` (`sdk-lint.yml`,
  `sdk-tests.yml`, `sdk-codeql.yml`, `sdk-release.yml`, pinned to `@v2`).
- `main` is protected — changes land via PR with CI green, per this repo
  being public (see global git conventions).
- `release-please` owns `pyproject.toml`'s `version` and `CHANGELOG.md` —
  never bump the version by hand. Conventional commit types map to bumps
  (`feat`→minor, `fix`/`perf`/`deps`→patch, `docs`/`refactor`/`test`/`ci`/`chore`→none);
  full table in `CODE_STYLE.md`.
- Merging the release-please PR tags the release and publishes to PyPI via
  the `pypi` GitHub Environment + Trusted Publisher (no PyPI token in repo
  secrets).

## Gotchas

- README and in-repo docstrings/comments are in **Portuguese** (existing
  convention in this repo) — this predates the global instruction to write
  code/comments in English. Don't mass-rewrite existing Portuguese content
  just to conform; write *new* code/comments in English per `CODE_STYLE.md`
  and the global convention, and ask before touching existing Portuguese
  docs at scale.
- `Client` methods that mutate state (`power_on`, `start_to_work`, …) return
  `None` — the device takes a few seconds to reflect the change. Call
  `query_status()` again for fresh state; don't assume synchronous effect.
- `token`/`key` are per-device credentials from the Midea cloud — never log
  them (see `CODE_STYLE.md` logging section). They must be obtained via
  external tools (`midea-msmart`, `midea-beautiful-air`, `midea-discover`);
  this repo has no cloud-auth flow of its own.
- Coverage gate is 90% overall, but protocol/codec/transport are expected
  near 100% since they're the byte-level surface most likely to regress
  silently.
