"""Pre-dispatch validation of a helper's syntax and declared host API usage.

This does not execute imports, resolve dynamic namespaces, or classify target
exceptions. A valid program can still fail at runtime; that is separate evidence.
"""

from __future__ import annotations

import ast
import symtable

from patchloop.errors import ContractError
from patchloop.util import sha256_bytes

ORIGINAL_ONLY_APIS = frozenset({"reproduction_workspace", "observed_target", "record_observation"})
_DYNAMIC_NAMESPACES = frozenset({"eval", "exec", "globals", "locals", "vars", "__builtins__"})

DESCRIPTION = (
    "Helper mode automatically supplies only check_setup(label, actual, expected), in addition "
    "to normal Python builtins. reproduction_workspace, observed_target and record_observation "
    "are original_requirement-only observer APIs; helper mode does not supply them. "
    "Create a helper fixture with Python's own temporary directory API, for example:\n"
    "from pathlib import Path\nfrom tempfile import TemporaryDirectory\n"
    "with TemporaryDirectory() as work:\n"
    "    root = Path(work)\n"
    "    (root / 'input.txt').write_text('sample', encoding='utf-8')\n"
    "Run the helper's target calls inside that with block. This is an independent helper "
    "fixture, not a replacement for the frozen original reproduction. Preflight checks syntax "
    "and unbound original-only names; it does not execute imports, resolve dynamic namespaces "
    "or certify target behavior. "
)


def _error(source, kind, requirement, *, names=(), line=None):
    return ContractError(requirement, details={
        "invalid_fields": [{"path": "/python_source", "requirement": requirement}],
        "helper_program_error": {
            "kind": kind, "source_hash": sha256_bytes(source.encode("utf-8")),
            "names": sorted(names), "line": line,
        },
    })


def _scopes(root):
    yield root
    for child in root.get_children():
        yield from _scopes(child)


def validate(source: str) -> None:
    """Reject only compile errors or statically unbound original-only APIs.

    Bindings are lexical, not execution-order proofs. Dynamic namespace access
    makes name resolution inconclusive, so only compilation is checked there.
    """
    try:
        compile(source, "<patchloop-helper>", "exec", dont_inherit=True)
        tree = ast.parse(source, filename="<patchloop-helper>")
        root = symtable.symtable(source, "<patchloop-helper>", "exec")
    except SyntaxError as exc:
        raise _error(source, "syntax_error", "Helper program cannot compile: " + exc.msg,
                     line=exc.lineno) from exc
    nodes = list(ast.walk(tree))
    if any((isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
            and node.id in _DYNAMIC_NAMESPACES)
           or (isinstance(node, ast.ImportFrom) and any(a.name == "*" for a in node.names))
           for node in nodes):
        return
    scopes = list(_scopes(root))
    global_bindings = {
        symbol.get_name() for scope in scopes for symbol in scope.get_symbols()
        if symbol.is_global() and (symbol.is_assigned() or symbol.is_imported())
    }
    unavailable = {
        symbol.get_name() for scope in scopes for symbol in scope.get_symbols()
        if symbol.get_name() in ORIGINAL_ONLY_APIS
        and symbol.is_referenced() and symbol.is_global()
        and symbol.get_name() not in global_bindings
    }
    if unavailable:
        positions = [node.lineno for node in nodes if isinstance(node, ast.Name)
                     and isinstance(node.ctx, ast.Load) and node.id in unavailable]
        # A repeated spelling may also belong to a correctly bound inner scope.
        # Do not point at that scope as the error without a unique source witness.
        line = positions[0] if len(positions) == 1 else None
        raise _error(
            source, "unavailable_api",
            "Helper mode does not supply these original_requirement-only APIs and the program "
            "has no lexical binding for them: " + ", ".join(sorted(unavailable))
            + ". Use a Python temporary directory for helper fixtures; check_setup is available.",
            names=unavailable, line=line,
        )
