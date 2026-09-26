"""Opt-in first-batch search context; no task-specific selectors or live collector."""

from __future__ import annotations

import ast
import copy
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

from patchloop.dev import runner
from patchloop.dev.context import source_lines
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.tools import DevToolGateway
from patchloop.errors import ContractError
from patchloop.util import sha256_bytes, sha256_json

POLICY = "python-declaration-doc-v1"
EVENT = "diagnostic_declaration_context_policy"
MAX_SPAN_LINES = 40
MAX_CONTENT_CHARS = 24_000
MAX_FILE_BYTES = 1_000_000


def _require(condition, message):
    if not condition:
        raise ContractError(message)


def declaration_ranges(text: str, query: str) -> list[dict]:
    """Find module/class data declarations followed by a literal documentation string.

    Only the assigned name is matched, not its uses, value, comments or documentation.
    No project imports, evaluation, function bodies or inferred relationships are used.
    """
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError):
        return []
    found = []

    def visit(body):
        for index, node in enumerate(body):
            if isinstance(node, ast.ClassDef):
                visit(node.body)
            targets = (node.targets if isinstance(node, ast.Assign) else
                       [node.target] if isinstance(node, ast.AnnAssign) else [])
            names = [n for n in targets if isinstance(n, ast.Name) and query in n.id]
            if not names or index + 1 >= len(body):
                continue
            following = body[index + 1]
            if not (isinstance(following, ast.Expr)
                    and isinstance(following.value, ast.Constant)
                    and isinstance(following.value.value, str)):
                continue
            found.append({
                "names": sorted(n.id for n in names),
                "name_lines": sorted({n.lineno for n in names}),
                "start_line": node.lineno, "end_line": following.end_lineno,
            })

    visit(tree.body)
    return sorted(found, key=lambda r: (r["start_line"], r["end_line"]))


def expand_search_result(result: dict, read_source: Callable[[str], bytes]) -> tuple[dict, dict]:
    """Expand only already-returned hits; preserve all original hits and source lines.

    The caller supplies the existing gateway's tracked/public file reader. File hashes
    must still match. Oversized whole declarations are skipped rather than cut mid-doc.
    """
    expanded = copy.deepcopy(result)
    spans = expanded["spans"]
    _require(len(spans) <= 20, "search result exceeds the existing span limit")
    content_chars = sum(len(s["content"]) for s in spans)
    _require(content_chars <= MAX_CONTENT_CHARS, "search result exceeds the content limit")
    sources, consumed, changes, omitted = {}, set(), [], []
    for index, span in enumerate(spans):
        path = span["path"]
        if not path.endswith(".py"):
            continue
        if path not in sources:
            raw = read_source(path)
            _require(len(raw) <= MAX_FILE_BYTES, "search source exceeds 1 MB")
            _require(sha256_bytes(raw) == span["file_hash"], "search source changed")
            text = raw.decode("utf-8")
            sources[path] = (source_lines(text), declaration_ranges(text, result["query"]),
                             span["file_hash"])
        lines, declarations, file_hash = sources[path]
        _require(file_hash == span["file_hash"], "search spans disagree on source identity")
        original_start, original_end = span["start_line"], span["end_line"]
        _require(1 <= original_start <= original_end <= len(lines), "invalid search span")
        _require("\n".join(lines[original_start - 1:original_end]) == span["content"],
                 "search span differs from its source")
        start, end = original_start, original_end
        selected = []
        for declaration in declarations:
            identity = (path, declaration["start_line"], declaration["end_line"])
            if identity in consumed or not any(
                original_start <= n <= original_end for n in declaration["name_lines"]
            ):
                continue
            proposed_start = min(start, declaration["start_line"])
            proposed_end = max(end, declaration["end_line"])
            content = "\n".join(lines[proposed_start - 1:proposed_end])
            delta = len(content) - len(span["content"])
            if (proposed_end - proposed_start + 1 > MAX_SPAN_LINES
                    or content_chars + delta > MAX_CONTENT_CHARS):
                omitted.append({"path": path, **declaration, "reason": "whole_block_limit"})
                continue
            consumed.add(identity)
            start, end = proposed_start, proposed_end
            selected.append(declaration)
        if (start, end) == (original_start, original_end):
            continue
        content = "\n".join(lines[start - 1:end])
        content_chars += len(content) - len(span["content"])
        spans[index] = DevToolGateway._span(path, start, end, content, file_hash)
        changes.append({
            "path": path, "file_hash": file_hash,
            "original_span_id": span["span_id"], "expanded_span_id": spans[index]["span_id"],
            "original_range": [original_start, original_end], "expanded_range": [start, end],
            "declarations": selected,
        })
    return expanded, {
        "policy": POLICY, "changes": changes, "omitted": omitted,
        "original_output_hash": sha256_json(result), "expanded_output_hash": sha256_json(expanded),
        "added_content_characters": content_chars - sum(len(s["content"]) for s in result["spans"]),
    }


def identity(experiment_hash: str) -> dict:
    return {
        "official": False, "policy": POLICY, "experiment_hash": experiment_hash,
        "implementation_hash": sha256_bytes(Path(__file__).read_bytes()),
        "scope": "first_tool_batch", "max_span_lines": MAX_SPAN_LINES,
        "max_content_characters": MAX_CONTENT_CHARS, "resume_allowed": False,
        "changes_prompt_or_tool_schema": False,
    }


def gateway_type(base=DevToolGateway, *, experiment_hash: str):
    """Apply before the normal evidence ledger, fingerprint, cache and journal receipt."""
    binding = identity(experiment_hash)

    class DeclarationGateway(base):
        def __init__(self, **kwargs):
            events = kwargs["journal"].events()
            prior = [e["payload"] for e in events if e["event_type"] == EVENT]
            if events and not prior:
                _require(not any(e["event_type"] in {"action_started", "turn_started"}
                                 for e in events),
                         "cannot attach search policy to a running episode")
            _require(not prior or prior == [binding], "declaration policy identity changed")
            super().__init__(**kwargs)
            if not prior:
                self.journal.append(EVENT, binding)

        def _search_files(self, query: str, path_glob: str = "**/*") -> dict:
            result = super()._search_files(query, path_glob)
            if any(e["event_type"] == "tool_batch_finished" for e in self.journal.events()):
                return result

            def read_public(path):
                if self.deadline is not None:
                    self.deadline.check()
                _, selected = self._tracked_path(path)
                return selected.read_bytes()

            expanded, receipt = expand_search_result(result, read_public)
            self.journal.append("diagnostic_declaration_context_observed", receipt)
            return expanded

    return DeclarationGateway


def run(request: DevRunRequest, *, policy: str = "none", experiment_hash: str = ""):
    """Fresh opt-in diagnostic only; the ordinary dev runner owns all execution limits.

    Use a dedicated sequential process. No resume, automatic retry or historical
    checkpoint hydration is provided by this seam. Omission uses the original path.
    """
    _require(policy in ("none", POLICY), "unknown declaration context policy")
    if policy == "none":
        return runner.run_dev(request)
    _require(request.repeat == 1 and request.resume_run_id is None,
             "declaration diagnostic forbids repetition and resume")
    _require(request.state_root is not None and not request.state_root.exists(),
             "declaration diagnostic needs a fresh state root")
    _require(experiment_hash.startswith("sha256:") and len(experiment_hash) == 71
             and all(c in "0123456789abcdef" for c in experiment_hash[7:]),
             "declaration diagnostic needs an experiment hash")
    with patch.object(runner, "DevToolGateway", gateway_type(
        runner.DevToolGateway, experiment_hash=experiment_hash,
    )):
        return runner.run_dev(request)
