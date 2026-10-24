"""Bounded explanations of exact JSON differences, never semantic verdicts."""
from __future__ import annotations

import json

from patchloop.util import canonical_json

MAX_DIFFERENCES = 8
MAX_PATH_CHARS = 160
MAX_FEEDBACK_BYTES = 2048
_MISSING = object()
_TYPES = {dict: "object", list: "array", str: "string", bool: "boolean",
          int: "integer", float: "float", type(None): "null"}


def differences(expected_json: str, observed_json: str) -> dict:
    """Explain already validated JSON; values remain in the original receipt.

    Paths are JSON Pointers (empty for the root). Keep exact canonical scalar
    comparison: Python equality would hide true/1, 1/1.0 and -0.0/0.0 differences.
    """
    feedback = {"differences": [], "omitted_count": 0}
    pending = [("", json.loads(expected_json), json.loads(observed_json))]
    while pending:
        path, expected, observed = pending.pop()
        if expected is _MISSING:
            kind = "extra"
        elif observed is _MISSING:
            kind = "missing"
        elif type(expected) is not type(observed):
            kind = "type"
        elif isinstance(expected, dict):
            pending.extend((path + "/" + key.replace("~", "~0").replace("/", "~1"),
                            expected.get(key, _MISSING), observed.get(key, _MISSING))
                           for key in sorted(expected.keys() | observed.keys(), reverse=True))
            continue
        elif isinstance(expected, list):
            pending.extend((path + "/" + str(i),
                            expected[i] if i < len(expected) else _MISSING,
                            observed[i] if i < len(observed) else _MISSING)
                           for i in reversed(range(max(len(expected), len(observed)))))
            continue
        elif canonical_json(expected) == canonical_json(observed):
            continue
        else:
            kind = "value"
        if len(feedback["differences"]) >= MAX_DIFFERENCES:
            feedback["omitted_count"] += 1
            continue
        row = {"path": path[:MAX_PATH_CHARS], "kind": kind}
        if len(path) > MAX_PATH_CHARS:
            row["path_truncated"] = True
        if kind == "type":
            row.update(expected_type=_TYPES[type(expected)], observed_type=_TYPES[type(observed)])
        feedback["differences"].append(row)
    while len(canonical_json(feedback).encode("utf-8")) > MAX_FEEDBACK_BYTES:
        feedback["differences"].pop()
        feedback["omitted_count"] += 1
    return feedback
