# Code Style Guide

Style conventions for the `midea-dishwasher-api` Python SDK. Run
`uv run ruff format . && uv run ruff check . --fix && uv run mypy src` before
committing — all three must exit cleanly. `uv run pytest` follows.

**Always read this file before adding or restructuring code.**

## Language

- Code is written in **English**: file names, class names, function names,
  variable names, dictionary keys, identifier strings.
- The conversation language with the user can be Portuguese or anything else;
  what is committed to disk stays English.

## File organization

- **Source layout is `src/midea_dishwasher_api/`.** Tests in `tests/`,
  packaging in `pyproject.toml`. Hatchling is the build backend.
- **One top-level class per file.** Multiple semantically related classes get
  grouped into a package directory with one class per submodule and an
  `__init__.py` re-exporting the public symbols.
  - Example: `enums/` contains `mode.py`, `cycle_state.py`,
    `wash_stage.py`, … plus `__init__.py`.
  - Example: `protocol/` contains `codec.py`, `frame_error.py`,
    `__init__.py`.
- **Public surface goes through the package `__init__.py`.** Anything not
  re-exported there is internal — prefix with `_` if intended to stay private.
- **TypedDicts and `type` aliases do not count as "classes"** for this rule —
  they live alongside related code.
- **Helper functions** may live in the same file as the single class that
  uses them. Module-level private helpers are prefixed `_`.

## Naming

- Public classes are `CapWords`: `DishwasherClient`, `V3Transport`, `FrameCodec`.
- Exception classes end with `Error`: `FrameError`, `V3Error`.
- Enums end with their domain noun: `MachineState`, `WashStage`, `ErrorCode`,
  `MsgType`.
- Module names are `snake_case`. Subpackages are organized by concern
  (`protocol`, `transport`, `security`, `enums`).
- Private attributes / functions are prefixed with `_`.

## Typing

**Strict typing. No `Any`, no bare collection generics.** Mypy enforces this.

Banned: `typing.Any`, `object` as a value type, bare `dict` / `list` /
`tuple` / `set`, `dict[str, Any]`.

Required:

- `@dataclass` for structured records (e.g. `DishwasherStatus`).
- Named `type` aliases for shared shapes.
- `frozenset[str]` / `tuple[str, ...]` for fixed string collections.
- Always type return values explicitly. Never rely on type inference for
  public APIs.
- Type-hinted module-level loggers: `log: logging.Logger = logging.getLogger(...)`.

The SDK ships a `py.typed` marker so downstream consumers get type info.

## Imports

- Always start every module with `from __future__ import annotations` so type
  hints become lazy strings.
- Same-package relative imports (`from .module import …`) are the default.
- Move type-only imports into a `TYPE_CHECKING` block:

  ```python
  from __future__ import annotations
  from typing import TYPE_CHECKING

  if TYPE_CHECKING:
      from collections.abc import Iterable
      from .protocol import Frame
  ```

- `noqa` comments require a written justification inline. Never silence to
  "make ruff happy" — fix the underlying code.

## Docstrings

- Every public class, function, method (including `@property`) has a docstring.
- A single sentence is usually enough. Describe the *contract* or the *why*,
  not the obvious implementation.
- Module-level docstring at the top of every `.py` file.
- Avoid restating the type — the signature already does that.

## Comments

- Default to **no comments**. Add one only when the *why* is not obvious from
  the code: a hidden constraint, a workaround, a subtle invariant, a
  protocol-spec reference (e.g. `# device_type 0xE1, plugin v5`).
- Never describe *what* the code does — well-named identifiers handle that.
- **No section dividers** like `# --- Frame helpers ---` to group related
  declarations. If a file has so many sections that you feel the need for
  visual separators, split it into multiple files instead.

## Logging

- Module-level logger: `log: logging.Logger = logging.getLogger("midea_dishwasher_api.<area>")`
  (e.g. `"midea_dishwasher_api.transport"`). Don't use `__name__` directly —
  the explicit dotted name lets users scope log levels precisely.
- Use **lazy `%`-formatting**, never f-strings — they force string interpolation
  even when the level is filtered:

  ```python
  log.debug("Sending frame: type=%s body_len=%d", msg_type, len(body))   # ✓
  log.debug(f"Sending frame: type={msg_type} body_len={len(body)}")      # ✗
  ```

- Levels:
  - `debug` — frame-level traces, byte counts, handshake steps.
  - `info` — successful connection, version negotiated.
  - `warning` — recoverable failures (single retry, fallback path).
  - `error` / `exception` — unrecoverable. `exception` inside `except` blocks
    captures the traceback.
- Never log raw `token`, `key`, decrypted secrets, or full frames containing
  them. Truncate to length / hash if diagnostics need correlation.

## Error messages

- Format: `"Failed to <verb> <object>: <cause>"`. Keep them short and
  grep-able.
- Custom exceptions form a hierarchy: `FrameError` (malformed frames) and
  `V3Error` (handshake / authentication issues) are the public errors. Wrap
  raw `OSError` or `socket` errors at the transport boundary so callers only
  catch this hierarchy.
- Pre-validate inputs (token must be 128 hex chars, key 64) before opening a
  socket so user-facing errors point at the bad input, not a downstream
  traceback.

## Public API surface

- Anything imported in the package `__init__.py` is the public contract.
  Renaming or removing those symbols is a `BREAKING CHANGE:`.
- Internal modules can change shape freely as long as the public re-exports
  keep working.

## Pre-commit hooks

`pre-commit` is recommended. Add `.pre-commit-config.yaml` mirroring the
lint commands (ruff format, ruff check, mypy) and install once per clone:

```bash
pre-commit install
```

The hook runs the same gates as CI on every commit. Skip it only on
emergency `git commit --no-verify` and immediately re-run the lint commands.

## Conventional commits

All commits follow [Conventional Commits](https://www.conventionalcommits.org/),
which `release-please` parses to bump `pyproject.toml` `version` and
generate `CHANGELOG.md`:

| Type | Meaning | Bump |
|---|---|---|
| `feat` | New feature | minor |
| `fix` | Bug fix | patch |
| `perf` | Performance improvement | patch |
| `deps` | Dependency bump | patch |
| `docs` | Documentation only | none |
| `refactor` | Refactor without behavior change | none |
| `test` | Test-only change | none |
| `ci` | CI / tooling change | none |
| `chore` | Anything else (rarely) | none |

- Subject line: imperative mood, lowercase, no trailing period.
- Use scopes when useful: `feat(transport): support v3 plugin negotiation`.
- A `BREAKING CHANGE:` footer (or `!` after type) bumps the major version.

## Packaging

- Build backend: `hatchling`. Wheel and sdist contain
  `src/midea_dishwasher_api`.
- `requires-python = ">=3.14"`. Don't bump this without a `BREAKING CHANGE:`
  footer.
- Public dependencies: keep them minimal and use `>=` lower bounds, not
  pins. The SDK is meant to coexist with arbitrary downstream resolvers.
- The `[project.optional-dependencies] dev` group carries test-only deps.
- A `py.typed` marker ships in the wheel so consumers see type info.

## Releasing

- `release-please` runs on `main` and opens a release-PR with the next
  version + `CHANGELOG.md`. Merging that PR triggers the publish job:
  - Tags the release on GitHub.
  - Builds sdist + wheel via `python -m build`.
  - Publishes to PyPI via the `pypi` GitHub Environment + Trusted Publisher
    (no token in repo secrets).
- Don't manually edit `pyproject.toml` `version` — release-please owns it.

## Testing

- Tests live in `tests/`. `uv run pytest` runs the suite. Aim for high
  coverage on protocol/codec/transport layers since they're the
  byte-level surface most likely to regress silently.
- Hardware-dependent tests (real device connections) are gated behind an
  env var and skipped in CI; pure unit tests use captured byte fixtures.

## Linting and verification

- Ruff configuration in `pyproject.toml` under `[tool.ruff]`.
- Mypy configuration in `pyproject.toml` under `[tool.mypy]` (strict).
- After every change run the three-step lint pipeline + `pytest`. Both
  gates mirror CI.
