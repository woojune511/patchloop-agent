"""Minimal, value-safe loading for PatchLoop's repository credential file."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from patchloop.errors import ContractError

OPENAI_API_KEY = "OPENAI_API_KEY"


def _parse_exact_openai_api_key(path: str | Path) -> str:
    """Read one dotenv key without importing or expanding general dotenv syntax.

    Blank lines and comments are allowed. Every assignment must be the exact
    ``OPENAI_API_KEY`` key, exactly once. Error messages intentionally omit the
    credential value and source line.
    """

    selected = Path(path)
    try:
        text = selected.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ContractError(f"credential file is unavailable or not UTF-8: {selected}") from exc

    value: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ContractError("credential file contains a malformed assignment")
        name, candidate = line.split("=", 1)
        if name.strip() != OPENAI_API_KEY:
            raise ContractError("credential file may contain only OPENAI_API_KEY")
        if name != OPENAI_API_KEY:
            raise ContractError("credential file key must be exactly OPENAI_API_KEY")
        if value is not None:
            raise ContractError("credential file contains duplicate OPENAI_API_KEY assignments")

        candidate = candidate.strip()
        if (
            len(candidate) >= 2
            and candidate[0] in {'"', "'"}
            and candidate[-1] == candidate[0]
        ):
            candidate = candidate[1:-1]
        if not candidate:
            raise ContractError("credential file contains an empty OPENAI_API_KEY")
        if "\x00" in candidate or "\r" in candidate or "\n" in candidate:
            raise ContractError("credential file contains an invalid OPENAI_API_KEY")
        value = candidate

    if value is None:
        raise ContractError("credential file is missing OPENAI_API_KEY")
    return value


def exact_openai_api_key_present(path: str | Path) -> bool:
    """Validate the exact credential file without mutating the process environment.

    The parsed value remains local to this call and is deliberately not returned.
    This is the credential-membership boundary used by no-call preflight checks so
    Git and Docker observation subprocesses cannot inherit the file credential.
    """

    _parse_exact_openai_api_key(path)
    return True


@contextmanager
def exact_openai_api_key_environment(path: str | Path) -> Iterator[None]:
    """Temporarily load the sole allowed key, then restore the parent environment."""

    value = _parse_exact_openai_api_key(path)
    sentinel = object()
    previous: str | object = os.environ.get(OPENAI_API_KEY, sentinel)
    os.environ[OPENAI_API_KEY] = value
    try:
        yield
    finally:
        if previous is sentinel:
            os.environ.pop(OPENAI_API_KEY, None)
        else:
            assert isinstance(previous, str)
            os.environ[OPENAI_API_KEY] = previous
