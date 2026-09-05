"""Repository-rooted, case-sensitive path globs for public source search."""

from __future__ import annotations

from fnmatch import fnmatchcase


def matches_source_glob(path: str, pattern: str) -> bool:
    """Match normalized relative paths; only a whole ``**`` can cross directories.

    ``*``, ``?``, and character classes match within a component. A ``**`` component
    matches zero or more components, so ``**/*.py`` includes root-level Python files.
    Callers remain responsible for public-path and tracked-file admission.
    """

    parts = path.split("/")
    matched = [True] + [False] * len(parts)
    for component in pattern.split("/"):
        if component == "**":
            for index in range(1, len(matched)):
                matched[index] = matched[index] or matched[index - 1]
        else:
            matched = [False] + [
                matched[index] and fnmatchcase(part, component)
                for index, part in enumerate(parts)
            ]
    return matched[-1]
