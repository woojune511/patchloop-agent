"""Optional syntax support, never a resolved call graph or semantic proof.

Only complete, parseable observed Python function fragments participate. The two
declared citations remain the authority for focus; this module just selects source
lines for their local parameter/dispatch context and possible immediate callers.
"""

from __future__ import annotations

import ast
import io
import re
import textwrap
import tokenize
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

LineKey = tuple[str, str, int]
_DEF = re.compile(r"^(\s*)(?:async\s+)?def\s+\w+\s*\(")
_BOUNDARY = re.compile(r"^(\s*)(?:(?:async\s+)?def\s|class\s|@)")
_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
_SUITES = {"body", "orelse", "handlers", "finalbody", "cases"}


def _walk(node):
    yield node
    for child in ast.iter_child_nodes(node):
        if not isinstance(child, _SCOPES):
            yield from _walk(child)


def _header(node):
    body = getattr(node, "body", None)
    end = max(node.lineno, body[0].lineno - 1) if body else node.end_lineno
    return set(range(node.lineno, end + 1))


def _expression_nodes(node):
    for name, value in ast.iter_fields(node):
        if name not in _SUITES:
            for item in value if isinstance(value, list) else [value]:
                if isinstance(item, ast.AST):
                    yield from _walk(item)


def _names(node, context):
    names = {n.id for n in _expression_nodes(node)
             if isinstance(n, ast.Name) and isinstance(n.ctx, context)}
    if context is ast.Store and isinstance(node, (ast.Import, ast.ImportFrom)):
        names.update(alias.asname or alias.name.split(".")[0] for alias in node.names
                     if alias.name != "*")
    return names


def _call_name(call):
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


@dataclass
class Function:
    path: str
    file_hash: str
    node: Any
    lines: dict[int, str]

    def scope(self):
        return list(_walk(self.node))


def observed_functions(observed: dict[LineKey, tuple[str, int, int]]) -> list[Function]:
    """Require an observed dedent boundary; do not parse across gaps or versions."""
    files: dict[tuple[str, str], dict[int, str]] = defaultdict(dict)
    for (path, digest, number), (text, _, _) in observed.items():
        if path.endswith((".py", ".pyi")):
            files[path, digest][number] = text
    functions = []
    for (path, digest), lines in sorted(files.items()):
        chunks: list[list[int]] = []
        for number in sorted(lines):
            if chunks and chunks[-1][-1] + 1 == number:
                chunks[-1].append(number)
            else:
                chunks.append([number])
        for chunk in chunks:
            # Lex only this contiguous fragment. Flatten indentation in the scratch
            # copy to recognize literals even when a read starts inside a suite.
            excluded = set()
            scratch = "\n".join(lines[n].lstrip() for n in chunk)
            try:
                for token in tokenize.generate_tokens(io.StringIO(scratch).readline):
                    if token.type in {tokenize.STRING, getattr(tokenize, "FSTRING_MIDDLE", -1),
                                      getattr(tokenize, "TSTRING_MIDDLE", -1)}:
                        # A quoted annotation/default after `def` is not a literal
                        # containing the header. Only mask rows whose header column
                        # lies inside the literal, including multiline f-string text.
                        first = token.start[0] + int(token.start[1] > 0)
                        excluded.update(range(first, token.end[0] + 1))
            except (tokenize.TokenError, IndentationError, SyntaxError):
                # An unknown literal/continuation state is not safe to expand.
                continue
            headers = [n for n in chunk if n - chunk[0] + 1 not in excluded
                       and _DEF.match(lines[n])]
            for start in headers:
                indent = len(lines[start]) - len(lines[start].lstrip())
                boundary = next((n for n in chunk if n > start
                                 and n - chunk[0] + 1 not in excluded
                                 and (m := _BOUNDARY.match(lines[n]))
                                 and len(m[1]) <= indent), chunk[-1] + 1)
                text = textwrap.dedent("\n".join(lines[n] for n in range(start, boundary)))
                try:
                    module = ast.parse(text)
                except (SyntaxError, ValueError, RecursionError):
                    continue
                if not module.body or not isinstance(module.body[0], _SCOPES[:2]):
                    continue
                node = module.body[0]
                ast.increment_lineno(node, start - 1)
                # A truncated but parseable function body is not a complete scope.
                if not any(n > node.end_lineno and lines[n].strip()
                           and not lines[n].lstrip().startswith("#")
                           and len(lines[n]) - len(lines[n].lstrip()) <= indent for n in chunk):
                    continue
                if any(f.path == path and f.file_hash == digest
                       and f.node.lineno <= start <= f.node.end_lineno for f in functions):
                    continue  # Nested function bodies have a different local scope.
                functions.append(Function(path, digest, node, lines))
    return functions


def _slice(function: Function, seeds: set[ast.AST], *, parameters: bool) -> set[int]:
    nodes = function.scope()
    parents = {child: node for node in nodes for child in ast.iter_child_nodes(node)}
    statements = [n for n in nodes if isinstance(n, (ast.stmt, ast.ExceptHandler))
                  and n is not function.node]
    selected = set(seeds)
    dependency_nodes = set(seeds)
    if parameters:
        args = {n.arg for n in ast.walk(function.node.args) if isinstance(n, ast.arg)}
        # Include later normalization of supplied parameters too: its ordering may
        # exclude it as the cause of an earlier call failure.
        rebindings = {n for n in statements if _names(n, ast.Store) & args}
        selected.update(rebindings)
        dependency_nodes.update(rebindings)
    cutoff = max((n.end_lineno for n in selected), default=function.node.lineno)
    # Show bypass/fallthrough conditions, without pulling in every alternative return's data
    # construction. These fragments remain source excerpts, not executable slices.
    selected.update(n for n in statements if isinstance(n, (ast.Return, ast.Raise)))
    # Calls used for their effects may alter the environment seen by a later call
    # without assigning a local variable (e.g. directory/context setup).
    effects = {n for n in statements if isinstance(n, ast.Expr) and n.lineno < cutoff
               and any(isinstance(child, ast.Call) for child in _walk(n))}
    selected.update(effects)
    dependency_nodes.update(effects)
    extra_lines = set()
    while True:
        before = set(selected)
        for node in list(selected):
            child, parent = node, parents.get(node)
            while parent is not None and parent is not function.node:
                if isinstance(parent, (ast.stmt, ast.ExceptHandler)):
                    selected.add(parent)
                    dependency_nodes.add(parent)
                    # Else/finally delimiters are not AST nodes. Retain their
                    # observed header when the selected statement uses that arm.
                    for field in ("orelse", "finalbody"):
                        body = getattr(parent, field, [])
                        if child in body:
                            prior = [n for n in function.lines if parent.lineno < n < child.lineno
                                     and re.match(r"(?:else|finally)\s*:",
                                                  function.lines[n].lstrip())
                                     and len(function.lines[n]) - len(function.lines[n].lstrip())
                                     == parent.col_offset + (
                                         len(function.lines[function.node.lineno])
                                         - len(function.lines[function.node.lineno].lstrip()))]
                            if prior:
                                extra_lines.add(max(prior))
                    if isinstance(parent, (ast.Try, ast.TryStar)):
                        # The assignments inside a try may not complete. Keep its
                        # exception alternatives and cleanup, not just the success arm.
                        for alternative in [*parent.handlers, *parent.finalbody]:
                            related = {n for n in _walk(alternative)
                                       if isinstance(n, (ast.stmt, ast.ExceptHandler))}
                            selected.update(related)
                            dependency_nodes.update(related)
                child, parent = parent, parents.get(parent)
        needed: dict[str, int] = {}
        for node in dependency_nodes:
            for name in _names(node, ast.Load):
                needed[name] = max(needed.get(name, 0), node.end_lineno)
        for node in statements:
            stores = _names(node, ast.Store)
            if isinstance(node, ast.ExceptHandler) and node.name:
                stores.add(node.name)
            if any(node.lineno <= needed.get(name, 0) for name in stores):
                selected.add(node)
                dependency_nodes.add(node)
        if selected == before:
            break
    return _header(function.node) | extra_lines | set().union(*(_header(n) for n in selected))


def question_support(
    observed: dict[LineKey, tuple[str, int, int]], references: list[dict[str, Any]],
) -> set[LineKey]:
    """Return one optional bundle; admission/actual delivery belongs to the selector."""
    refs = [r for r in references if r.get("kind") == "source"
            and r.get("role") in {"primary", "countercheck"} and not r.get("unavailable_reason")
            and all((r["path"], r["file_hash"], n) in observed
                    for n in range(r["start_line"], r["end_line"] + 1))]
    if not refs:
        return set()
    functions = observed_functions(observed)
    roots = [(f, r) for f in functions for r in refs
             if (f.path, f.file_hash) == (r["path"], r["file_hash"])
             and f.node.lineno <= r["start_line"] <= r["end_line"] <= f.node.end_lineno]
    counts = Counter(f.node.name for f in functions)
    names = {f.node.name for f, _ in roots if counts[f.node.name] == 1}
    # The immediate, observed target of a cited call supplies its argument/return
    # conditions too. Do not recursively expand calls found in this added support.
    targets = set()
    for function, ref in roots:
        targets.update(_call_name(n) for n in function.scope() if isinstance(n, ast.Call)
                       and n.lineno <= ref["end_line"] and n.end_lineno >= ref["start_line"])
    targets = {name for name in targets if counts[name] == 1}
    support = set()
    for function in functions:
        own_refs = [r for f, r in roots if f is function]
        seeds = set()
        for node in function.scope():
            if not isinstance(node, (ast.stmt, ast.ExceptHandler)) or node is function.node:
                continue
            if any(_header(node) & set(range(r["start_line"], r["end_line"] + 1))
                   for r in own_refs):
                seeds.add(node)
            for call in _expression_nodes(node):
                if isinstance(call, ast.Call) and _call_name(call) in names:
                    seeds.add(node)
            if function.node.name in targets and isinstance(node, (ast.Return, ast.Raise)):
                seeds.add(node)
        if seeds:
            support.update((function.path, function.file_hash, n)
                           for n in _slice(function, seeds, parameters=(
                               bool(own_refs) or function.node.name in targets)))
    assert support <= observed.keys()
    return support
