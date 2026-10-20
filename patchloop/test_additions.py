"""Conservative structural separation of additions to existing pytest files."""

from __future__ import annotations

import ast
import copy
from collections import Counter


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


def _parameter_case(value: ast.AST) -> None:
    """Validate a new literal case without evaluating pytest or user expressions."""
    if not isinstance(value, ast.Call):
        ast.literal_eval(value)
        return
    if not (
        isinstance(value.func, ast.Attribute)
        and isinstance(value.func.value, ast.Name)
        and value.func.value.id == "pytest"
        and value.func.attr == "param"
        and value.args
        and len(value.keywords) <= 1
    ):
        raise ValueError("new cases must be literals or pytest.param with literal arguments")
    if value.keywords:
        keyword = value.keywords[0]
        if not (
            keyword.arg == "id"
            and isinstance(keyword.value, ast.Constant)
            and isinstance(keyword.value.value, str)
        ):
            raise ValueError("new pytest.param cases allow only a literal string id; no marks")
    for argument in value.args:
        if any(isinstance(node, (ast.Call, ast.BinOp)) for node in ast.walk(argument)):
            raise ValueError("new pytest.param arguments must be literal values")
        ast.literal_eval(argument)


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
                _parameter_case(value)
                added.append(i)
        if cursor != len(old_values) or not added:
            raise ValueError("existing cases removed/reordered/changed, or no cases added")
    except (ValueError, TypeError, SyntaxError) as exc:
        raise UnsupportedTestChange(str(exc)) from exc
    current.args[1] = copy.deepcopy(previous.args[1])
    if _dump(old) != _dump(candidate):
        raise UnsupportedTestChange("existing test, fixture or decorator changed")
    return {"function": new.name, "parameter_names": list(names), "indices": added}


def _added_statements(old, new, path, *, suite_additions):
    names = Counter(node.name for node in old if isinstance(node, (ast.FunctionDef, ast.ClassDef)))
    seen, cursor, additions = set(), 0, []
    for node in new:
        previous = old[cursor] if cursor < len(old) else None
        unchanged = previous is not None and _dump(previous) == _dump(node)
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            # Preserve original duplicates in order; editing either occurrence is ambiguous.
            if not unchanged and (node.name in seen or names[node.name] > 1):
                raise UnsupportedTestChange("duplicate definitions cannot be separated")
            seen.add(node.name)
        if unchanged:
            cursor += 1
        elif (suite_additions and isinstance(node, ast.ClassDef)
              and node.name.startswith("Test") and node.name not in names):
            body = node.body
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                body = body[1:]
            methods = _added_statements([], body, path, suite_additions=True)
            if not methods:
                raise UnsupportedTestChange("new test class must contain tests")
            additions.extend({**method, "function": node.name + "::" + method["function"]}
                             for method in methods)
        elif (
            suite_additions
            and isinstance(previous, ast.ClassDef)
            and isinstance(node, ast.ClassDef)
            and previous.name == node.name
        ):
            header = copy.deepcopy(node)
            header.body = previous.body
            if _dump(previous) != _dump(header):
                raise UnsupportedTestChange("existing test class header changed")
            methods = _added_statements(previous.body, node.body, path, suite_additions=True)
            additions.extend({**method, "function": node.name + "::" + method["function"]}
                             for method in methods)
            cursor += 1
        elif isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            if isinstance(previous, ast.FunctionDef) and previous.name == node.name:
                additions.append({"path": path, **_parameters(previous, node)})
                cursor += 1
            elif node.name not in names and (suite_additions or all(
                _mark(dec) in {"parametrize", "skip", "skipif", "xfail"}
                for dec in node.decorator_list
            )):
                additions.append(
                    {"path": path, "function": node.name, "parameter_names": [], "indices": None}
                )
            else:
                raise UnsupportedTestChange("new test is ambiguous or has unsupported decorators")
        else:
            raise UnsupportedTestChange(
                "existing tests, imports, helpers, fixtures or classes changed"
            )
    if cursor != len(old):
        raise UnsupportedTestChange("existing module statements removed")
    return additions


def added_tests(before: bytes, after: bytes, path: str, *, suite_additions=False) -> list[dict]:
    """Separate additive tests; repair-verify retains its top-level selector contract."""
    try:
        old, new = ast.parse(before), ast.parse(after)
    except (SyntaxError, ValueError) as exc:
        raise UnsupportedTestChange(f"test file cannot be parsed: {exc}") from exc
    return _added_statements(old.body, new.body, path, suite_additions=suite_additions)
