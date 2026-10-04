"""Conservative structural separation of additions to existing pytest files."""

from __future__ import annotations

import ast
import copy


class UnsupportedTestChange(ValueError):
    pass


def _dump(node: ast.AST) -> str:
    return ast.dump(node, include_attributes=False)


def _mark(node: ast.AST) -> str | None:
    if isinstance(node, ast.Call):
        node = node.func
    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "mark"
        and isinstance(node.value.value, ast.Name)
        and node.value.value.id == "pytest"
    ):
        return node.attr
    return None


def _parameters(old: ast.FunctionDef, new: ast.FunctionDef) -> dict:
    """Only an additive literal case list in one unchanged parametrization."""
    candidate = copy.deepcopy(new)
    indexes = [i for i, dec in enumerate(candidate.decorator_list) if _mark(dec) == "parametrize"]
    if len(indexes) != 1 or len(old.decorator_list) != len(new.decorator_list):
        raise UnsupportedTestChange("existing test body/decorators changed")
    index = indexes[0]
    previous, current = old.decorator_list[index], candidate.decorator_list[index]
    if (
        not isinstance(previous, ast.Call)
        or not isinstance(current, ast.Call)
        or len(previous.args) != 2
        or len(current.args) != 2
        or previous.keywords
        or current.keywords
        or not isinstance(previous.args[1], (ast.List, ast.Tuple))
        or not isinstance(current.args[1], type(previous.args[1]))
    ):
        raise UnsupportedTestChange("parametrization must use an inline case list without keywords")
    try:
        names = ast.literal_eval(current.args[0])
        if isinstance(names, str):
            names = [part.strip() for part in names.split(",")]
        if (
            not isinstance(names, (list, tuple))
            or not names
            or not all(isinstance(name, str) and name.isidentifier() for name in names)
        ):
            raise ValueError("invalid parameter names")
        old_values = previous.args[1].elts
        added, cursor = [], 0
        for i, value in enumerate(current.args[1].elts):
            if cursor < len(old_values) and _dump(value) == _dump(old_values[cursor]):
                cursor += 1
            else:
                ast.literal_eval(value)  # No new computed cases or pytest.param marks.
                added.append(i)
        if cursor != len(old_values) or not added:
            raise ValueError("existing cases removed/reordered/changed, or no cases added")
    except (ValueError, TypeError, SyntaxError) as exc:
        raise UnsupportedTestChange(str(exc)) from exc
    current.args[1] = copy.deepcopy(previous.args[1])
    if _dump(old) != _dump(candidate):
        raise UnsupportedTestChange("existing test, fixture or decorator changed")
    return {"function": new.name, "parameter_names": list(names), "indices": added}


def added_tests(before: bytes, after: bytes, path: str) -> list[dict]:
    """No rewriting: return selectors or refuse the entire changed test file."""
    try:
        old, new = ast.parse(before), ast.parse(after)
    except (SyntaxError, ValueError) as exc:
        raise UnsupportedTestChange(f"test file cannot be parsed: {exc}") from exc
    names = {node.name for node in old.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    seen, cursor, additions = set(), 0, []
    for node in new.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            if node.name in seen:
                raise UnsupportedTestChange("duplicate definitions cannot be separated")
            seen.add(node.name)
        previous = old.body[cursor] if cursor < len(old.body) else None
        if previous is not None and _dump(previous) == _dump(node):
            cursor += 1
        elif isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            if isinstance(previous, ast.FunctionDef) and previous.name == node.name:
                additions.append({"path": path, **_parameters(previous, node)})
                cursor += 1
            elif node.name not in names and all(
                _mark(dec) in {"parametrize", "skip", "skipif", "xfail"}
                for dec in node.decorator_list
            ):
                additions.append(
                    {"path": path, "function": node.name, "parameter_names": [], "indices": None}
                )
            else:
                raise UnsupportedTestChange("new test is ambiguous or has unsupported decorators")
        else:
            raise UnsupportedTestChange(
                "existing tests, imports, helpers, fixtures or classes changed"
            )
    if cursor != len(old.body):
        raise UnsupportedTestChange("existing module statements removed")
    return additions
