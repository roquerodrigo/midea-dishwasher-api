# midea-dishwasher-api

Python SDK for Midea dishwashers (`device_type 0xE1`, plugin v5): the `AA … E1`
application codec plus the LAN V3 transport (8370 handshake, AES-128-CBC +
SHA-256, inner V2 `5A5A` framing). Published to PyPI, consumed by a separate
Home Assistant custom integration — the package `__init__.py` re-exports ARE
the public contract, so renaming/removing any of them is a `BREAKING CHANGE:`.

The two hand-written docs are authoritative; read them before touching code:
- `CODE_STYLE.md` — layout, typing, logging, docstrings, commit/release rules.
- `README.md` — public API surface and usage.

## Ground truth this SDK was reverse-engineered from

- The protocol is not documented by Midea; behavior comes from captured device
  traffic. Byte offsets in `protocol/` and `state/decoder.py` are load-bearing —
  change them only against real captures, never by guessing.
- Control methods (`power_on`, `start_to_work`, …) return nothing: the machine
  takes seconds to reflect a change. Call `query_status()` for fresh state.
- `left_time` is only populated when `cycle_state == WORK`.
- Credentials are per-device: `token` = 128 hex chars (64 bytes), `key` = 64 hex
  chars (32 bytes). Validate lengths before opening a socket (see CODE_STYLE
  "Error messages").

## Workflow gotchas

- `requires-python = ">=3.11"`, the lowest interpreter the source runs on.
  `[tool.ruff] target-version`, `[tool.mypy] python_version` and the
  `Programming Language :: Python :: 3.x` classifiers track it — a guard test
  fails if they drift. Bumping the floor is a `BREAKING CHANGE:`.
- Verify before committing: `uv run ruff format . && uv run ruff check . --fix &&
  uv run mypy src && uv run pytest`. All four must be clean. Coverage gate is 90%
  (`--cov-fail-under=90`).
- Ruff selects **every** rule (`select = ["ALL"]`); the exceptions live in
  `ignore` and `per-file-ignores` with the reason recorded next to them. Exempt
  a protocol-mandated primitive (the V2 layer's ECB/MD5) **per file, never with
  an inline `# noqa`** — an inline directive rewrites the source line, and
  CodeQL then reports the long-standing weak-cipher finding as a *new* alert,
  failing the branch's required check.
- The test suite never touches hardware: every frame is assembled byte by byte,
  so a protocol change has to be mirrored in the fixtures by hand.
- `scripts/` is excluded from ruff and from mypy (`files = ["src"]`); those
  scripts hit a **real device** using a repo-root `.env` (host, device_id, token,
  key) and are not run in CI. Do not rely on them for verification.
- `release-please` owns `pyproject.toml` `version` and `CHANGELOG.md` — never
  hand-edit either. Merging its release PR publishes to PyPI through the
  `pypi` GitHub Environment, authenticating with the `PYPI_API_TOKEN` secret.
- Public repo with branch protection: land changes via PR with green CI, and
  merge with **rebase merge only** (squash/merge-commit are disabled). Start a
  feature by branching from an up-to-date `main`.
