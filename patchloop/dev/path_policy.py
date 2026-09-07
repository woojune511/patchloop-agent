"""Existing mutation path permission, shared by admission and public presentation."""

from collections.abc import Sequence
from fnmatch import fnmatchcase


def mutation_path_allowed(
    path: str, *, allowed_paths: Sequence[str], forbidden_paths: Sequence[str],
) -> bool:
    """Keep the gateway's case-sensitive glob semantics and forbidden precedence."""
    return any(fnmatchcase(path, item) for item in allowed_paths) and not any(
        fnmatchcase(path, item) for item in forbidden_paths
    )
