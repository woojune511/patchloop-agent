"""Bounded, advisory call-scoped tracing of host-bound public Python functions.

This stdlib-only module is copied into the sandbox. It never evaluates expressions,
calls repr/getattr on observed values, or records an unrestricted locals mapping.
Like LineTrace, an in-process trace is diagnostic evidence, not an attestation.
"""

from __future__ import annotations

import ast
import dis
import hashlib
import json
import math
import os
import re
import stat
import sys
import types
from contextlib import suppress
from pathlib import Path, PurePosixPath

MAX_WATCHES = 4
MAX_LINES = 32
MAX_FIELDS = 6
MAX_EVENTS = 48
MAX_REPORT_BYTES = 24_000
MAX_VALUE_BYTES = 8_000
MAX_TRACE_EVENTS = 200_000
WRAPPER = Path(__file__)
_NAME = re.compile(r"[A-Za-z_][A-Za-z_0-9]*\Z")
_FUNCTION = re.compile(r"[A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)*\Z")
_REASONS = {
    "report_unavailable", "invalid_report", "call_not_observed", "focus_not_observed",
    "call_incomplete", "trace_or_source_changed", "collector_truncated",
    "source_unavailable", "trace_conflict", "duplicate_selected_call",
}


def _json(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
                      allow_nan=False)


def _hash(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def marker(request):
    return b"\x1ePATCHLOOP-CALL-PATH:" + request["request_hash"].encode("ascii") + b":"


def schema():
    identity = {
        "origin": {"type": "string", "enum": ["workspace", "dependency"]},
        "path": {"type": "string", "minLength": 1, "maxLength": 240},
        "function": {"type": "string", "minLength": 1, "maxLength": 160},
    }
    return {"type": "object", "additionalProperties": False,
            "required": ["call_id", "focus", "watches"], "properties": {
                "call_id": {"type": "string", "enum": [f"call-{i}" for i in range(1, 5)]},
                "focus": {"type": "object", "additionalProperties": False,
                          "required": list(identity), "properties": dict(identity)},
                "watches": {"type": "array", "minItems": 1, "maxItems": MAX_WATCHES,
                            "items": {"type": "object", "additionalProperties": False,
                                      "required": [*identity, "lines", "fields"],
                                      "properties": {**identity,
                                          "lines": {"type": "array", "maxItems": MAX_LINES,
                                                    "items": {"type": "integer", "minimum": 1}},
                                          "fields": {"type": "array", "maxItems": MAX_FIELDS,
                                                     "items": {"type": "string"}}}}}}}


def selection_schema():
    """Fresh model requests select functions; replay IDs and lines are host-owned."""
    result = schema()
    del result["properties"]["call_id"]
    result["required"].remove("call_id")
    watch = result["properties"]["watches"]["items"]
    del watch["properties"]["lines"]
    watch["required"].remove("lines")
    return result


def selection_request(selection, call_id):
    """Validate only the new symbolic shape, retaining the legacy wire validator."""
    if type(selection) is not dict or set(selection) != {"focus", "watches"}:
        raise ValueError("diagnosis selects focus and watches; the host supplies call identity")
    watches = selection["watches"]
    if (type(watches) is not list or any(type(w) is not dict
            or set(w) != {"origin", "path", "function", "fields"} for w in watches)
            or type(selection["focus"]) is not dict
            or set(selection["focus"]) != {"origin", "path", "function"}):
        raise ValueError("diagnosis selects public functions and fields, not line coordinates")
    return validate_request({"call_id": call_id, "focus": selection["focus"],
                             "watches": [{**w, "lines": []} for w in watches]})


def validate_request(request):
    """Validate public identities and optional host-only scope; return a detached copy."""
    if (type(request) is not dict or set(request) not in (
            {"call_id", "focus", "watches"}, {"call_id", "focus", "watches", "scope"})
            or "scope" in request and (type(request["scope"]) is not str
                                        or request["scope"] != "selected_call")
            or type(request["call_id"]) is not str
            or request["call_id"] not in {f"call-{i}" for i in range(1, 5)}
            or type(request["watches"]) is not list
            or not 1 <= len(request["watches"]) <= MAX_WATCHES):
        raise ValueError("invalid bounded call-path request")
    for index, target in enumerate([request["focus"], *request["watches"]]):
        expected = {"origin", "path", "function"} | ({"lines", "fields"} if index else set())
        if (type(target) is not dict or set(target) not in (expected, expected | {"file_hash"})
                or "file_hash" in target and (type(target["file_hash"]) is not str
                    or re.fullmatch(r"sha256:[0-9a-f]{64}", target["file_hash"]) is None)):
            raise ValueError("invalid call-path target fields")
        relative, function = target["path"], target["function"]
        if (type(target["origin"]) is not str
                or target["origin"] not in {"workspace", "dependency"}
                or type(relative) is not str or not 1 <= len(relative) <= 240
                or "\\" in relative or ":" in relative
                or PurePosixPath(relative).is_absolute()
                or PurePosixPath(relative).as_posix() != relative
                or any(part.casefold() in {".", "..", ".git", ".patchloop-hidden"}
                       or part.casefold().startswith(".env")
                       for part in PurePosixPath(relative).parts)
                or not relative.endswith(".py")
                or type(function) is not str or len(function) > 160
                or _FUNCTION.fullmatch(function) is None):
            raise ValueError("call-path target must name public relative Python source")
        if index:
            for key, limit in (("lines", MAX_LINES), ("fields", MAX_FIELDS)):
                values = target[key]
                if type(values) is not list or len(values) > limit:
                    raise ValueError("call-path selected field/line bound exceeded")
                if key == "lines":
                    valid = all(type(v) is int and 0 < v <= 1_000_000 for v in values)
                else:
                    valid = all(type(v) is str and len(v) <= 64
                                and _NAME.fullmatch(v) for v in values)
                if not valid or len(set(values)) != len(values):
                    raise ValueError("invalid call-path selected field or line")
    return json.loads(_json(request))


def _function_node(raw, function):
    matches = []

    def visit(node, prefix=""):
        for child in ast.iter_child_nodes(node):
            nested = prefix
            if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                nested = prefix + child.name
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                    nested == function or "." not in function and child.name == function
                ):
                    matches.append(child)
                nested += "."
            visit(child, nested)

    visit(ast.parse(raw))
    if len(matches) != 1:
        raise ValueError("call-path function must resolve uniquely in bound public source")
    return matches[0]


def _function(raw, function):
    node = _function_node(raw, function)
    start = min([node.lineno, *[item.lineno for item in node.decorator_list]])
    arguments = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
    if node.args.vararg:
        arguments.append(node.args.vararg)
    if node.args.kwarg:
        arguments.append(node.args.kwarg)
    return {"first_line": start, "def_line": node.lineno, "last_line": node.end_lineno,
            "parameters": [arg.arg for arg in arguments[:MAX_FIELDS]]}


def _selected_lines(raw, function, identity, changes):
    """Compile without execution; prioritize changed lines within the selected frame."""
    name = _function_node(raw, function).name
    matches = []

    def visit(code):
        if (code.co_name == name
                and code.co_firstlineno in {identity["first_line"], identity["def_line"]}):
            matches.append(code)
        for value in code.co_consts:
            if isinstance(value, types.CodeType):
                visit(value)

    visit(compile(raw, "<public-call-path-selection>", "exec", dont_inherit=True))
    if len(matches) != 1:
        raise ValueError("call-path executable function must resolve uniquely")
    lines = sorted({line for _, line in dis.findlinestarts(matches[0])
                    if line is not None and identity["def_line"] <= line <= identity["last_line"]
                    and (line > identity["def_line"]
                         or identity["def_line"] == identity["last_line"])})
    priority = [line for line in lines if any(start <= line <= end for start, end in changes)]
    chosen = sorted((priority + [line for line in lines if line not in priority])[:MAX_LINES])
    return chosen, len(lines) - len(chosen)


def bind_request(request, snapshot, *, dependency_root=None, dependency_files=None,
                 snapshot_hash=None, execution_identity_hash=None, line_changes=None):
    """Bind only exported regular public bytes or verified prepared dependency members."""
    request = validate_request(request)
    targets = []
    for index, target in enumerate([request["focus"], *request["watches"]]):
        root = snapshot if target["origin"] == "workspace" else dependency_root
        if root is None or (target["origin"] == "dependency"
                            and target["path"] not in (dependency_files or {})):
            raise ValueError("call-path target is outside the prepared public allowlist")
        root = Path(root).resolve()
        path = root / target["path"]
        for parent in (path, *path.parents):
            if parent == root:
                break
            info = parent.lstat()
            if parent.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400:
                raise ValueError("call-path target symlinks/reparse points are forbidden")
        if not path.resolve().is_relative_to(root) or not stat.S_ISREG(path.stat().st_mode):
            raise ValueError("call-path source is not a regular exported file")
        with path.open("rb") as stream:
            raw = stream.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("call-path source exceeds static binding limit")
        file_hash = _hash(raw)
        if target.get("file_hash", file_hash) != file_hash:
            raise ValueError("call-path source differs from its admitted bytes")
        if target["origin"] == "dependency" and dependency_files[target["path"]] != file_hash:
            raise ValueError("call-path dependency differs from prepared public bytes")
        identity = _function(raw, target["function"])
        selection = {}
        if index and line_changes is not None:
            changes = [pair for change in line_changes
                       if target["origin"] == "workspace" and change["path"] == target["path"]
                       for pair in change["ranges"]]
            lines, omitted = _selected_lines(raw, target["function"], identity, changes)
            target = {**target, "lines": lines}
            selection = {"line_selection": {"policy": "function-lines-v1",
                                            "omitted_line_count": omitted}}
        if index and any(not identity["first_line"] <= line <= identity["last_line"]
                         for line in target["lines"]):
            raise ValueError("call-path watched line is outside the selected function")
        targets.append({**target, **identity, **selection, "file_hash": file_hash,
                        "fields": target.get("fields", identity["parameters"]),
                        "lines": target.get("lines", [])})
    bound = {"schema_version": "public-call-path-request-v1", "call_id": request["call_id"],
             **({"scope": request["scope"]} if "scope" in request else {}),
             "focus": targets[0], "watches": targets[1:], "snapshot_hash": snapshot_hash,
             "execution_identity_hash": execution_identity_hash}
    return {**bound, "request_hash": _hash(_json(bound).encode())}


def _value(value):
    if value is None or type(value) in {bool, int}:
        return value if type(value) is not int or value.bit_length() <= 128 else "<large-int>"
    if type(value) is float:
        return value if math.isfinite(value) else "<nonfinite>"
    if type(value) is str:
        return value[:128] + ("..." if len(value) > 128 else "")
    if type(value) in {list, tuple}:
        return [_value(item) if type(item) in {type(None), bool, int, float, str}
                else "<non-scalar>" for item in value[:8]] + (
                    ["<remaining-items>"] if len(value) > 8 else [])
    return "<non-scalar>"


class CallPathTrace:
    """Observe one call, optionally restricted to its selected focus subtree."""

    def __init__(self, request, roots=None, line_trace=None):
        self.request = request
        self.selected_call_scope = request.get("scope") == "selected_call"
        self.roots = roots or {"workspace": "/workspace",
                               "dependency": "/opt/patchloop-dependencies"}
        self.targets = [request["focus"], *request["watches"]]
        self.paths = [str(Path(self.roots[t["origin"]]) / t["path"]) for t in self.targets]
        self.rows = [{"index": i, "entries": 0, "line_hits": [], "events": []}
                     for i in range(len(self.targets))]
        self.frames, self.focus_frames, self.delegates = {}, set(), {}
        self.trace = self._trace
        self.settrace, self.gettrace, self.write, self.open = (
            sys.settrace, sys.gettrace, os.write, open)
        self.previous = None
        self.authorized_previous = line_trace.trace if line_trace is not None else None
        self.changing_trace = False
        self.selected = self.ended = False
        self.closed = False
        self.reason = None
        self.event_count = self.value_bytes = self.trace_events = 0
        self._check_sources()
        sys.addaudithook(self._audit)

    def _audit(self, event, _arguments):
        if (event == "sys.settrace" and self.selected and not self.ended and not self.closed
                and not self.changing_trace):
            self.reason = "trace_or_source_changed"

    def _settrace(self, tracer):
        self.changing_trace = True
        try:
            self.settrace(tracer)
        finally:
            self.changing_trace = False

    def _check_sources(self):
        for index, target in enumerate(self.targets):
            path = self.paths[index]
            try:
                with self.open(path, "rb") as stream:
                    raw = stream.read(2_000_001)
                if _hash(raw) != target["file_hash"]:
                    self.reason = "trace_or_source_changed"
            except OSError:
                self.reason = "source_unavailable"

    def begin(self, call_id):
        if call_id != self.request["call_id"]:
            return
        if self.selected:
            self.reason = "duplicate_selected_call"
            return
        self.selected = True
        self.previous = self.gettrace()
        # Only the trusted LineTrace dispatcher is admitted as a previous tracer.
        if self.previous is not self.authorized_previous:
            self.reason = "trace_conflict"
            return
        self._settrace(self.trace)

    def end(self, call_id):
        if call_id != self.request["call_id"]:
            return
        self.ended = True
        if self.gettrace() is not self.trace:
            self.reason = "trace_or_source_changed"
        else:
            self._settrace(self.previous)

    def _record(self, index, frame, event, arg=None):
        if self.event_count >= MAX_EVENTS:
            self.reason = "collector_truncated"
            return
        row, target = self.rows[index], self.targets[index]
        parent = frame.f_back
        while parent is not None and id(parent) not in self.frames:
            parent = parent.f_back
        values = {key: _value(frame.f_locals[key]) for key in target["fields"]
                  if key in frame.f_locals}
        item = {"event": event, "line": frame.f_lineno,
                "parent_index": self.frames.get(id(parent)), "values": values}
        if event == "return":
            item["value"] = _value(arg)
        elif event == "exception":
            item["exception_type"] = type.__getattribute__(arg[0], "__name__")[:128]
        size = len(_json(item).encode())
        if self.value_bytes + size > MAX_VALUE_BYTES:
            self.reason = "collector_truncated"
            return
        self.value_bytes += size
        self.event_count += 1
        row["events"].append(item)

    def _trace(self, frame, event, arg):
        key = id(frame)
        if self.previous is not None:
            delegate = self.previous if event == "call" else self.delegates.get(key)
            if delegate is not None:
                returned = delegate(frame, event, arg)
                if returned is not None:
                    self.delegates[key] = returned
                else:
                    self.delegates.pop(key, None)
        matches = []
        if event == "call":
            matches = [i for i, target in enumerate(self.targets)
                       if frame.f_code.co_filename == self.paths[i]
                       and frame.f_code.co_name == target["function"].rsplit(".", 1)[-1]
                       and frame.f_code.co_firstlineno in {
                           target["first_line"], target["def_line"]}]
            if 0 in matches:
                self.focus_frames.add(key)
        # Legacy focus scope excludes initialization/unrelated work. Host-selected
        # call scope includes the entire begin/end window, even without a focus hit.
        scoped = (self.selected and not self.ended and not self.closed
                  if self.selected_call_scope else bool(self.focus_frames))
        if scoped:
            self.trace_events += 1
            if self.trace_events > MAX_TRACE_EVENTS:
                self.reason = "collector_truncated"
        if scoped and self.trace_events <= MAX_TRACE_EVENTS:
            if event == "call":
                for index in matches:
                    self.rows[index]["entries"] += 1
                    self._record(index, frame, "call")
                if matches:
                    self.frames[key] = matches[0]
            elif key in self.frames:
                # A focus may also be explicitly watched. Keep both bound rows coherent.
                for index, target in enumerate(self.targets):
                    if (frame.f_code.co_filename == self.paths[index]
                            and frame.f_code.co_name == target["function"].rsplit(".", 1)[-1]
                            and frame.f_code.co_firstlineno in {
                                target["first_line"], target["def_line"]}):
                        if event == "line" and frame.f_lineno in target["lines"]:
                            if frame.f_lineno not in self.rows[index]["line_hits"]:
                                self.rows[index]["line_hits"].append(frame.f_lineno)
                            self._record(index, frame, event)
                        elif event in {"return", "exception"}:
                            self._record(index, frame, event, arg)
        if event == "return":
            self.frames.pop(key, None)
            self.focus_frames.discard(key)
            self.delegates.pop(key, None)
        # Non-target frames still need return events to maintain nested focus state.
        return (self.trace if (self.selected_call_scope and scoped) or self.focus_frames
                or key in self.frames or key in self.delegates
                else None)

    def finish(self):
        if self.gettrace() is self.trace:
            self._settrace(self.previous)
            self.reason = self.reason or "call_incomplete"
        self._check_sources()
        reason = self.reason or ("call_not_observed" if not self.selected else
                                 "call_incomplete" if not self.ended else
                                 "focus_not_observed" if not self.selected_call_scope
                                 and not self.rows[0]["entries"] else None)
        self.closed = True
        report = {"request_hash": self.request["request_hash"],
                  **({"scope": self.request["scope"]} if "scope" in self.request else {}),
                  "status": "unknown" if reason else "complete", "reason": reason,
                  "rows": self.rows}
        raw = _json(report).encode()
        if len(raw) > MAX_REPORT_BYTES:
            report.update(status="unknown", reason="collector_truncated", rows=[])
            raw = _json(report).encode()
        with suppress(OSError):
            self.write(2, marker(self.request) + raw + b"\n")
        return report


def public_feedback(request, report=None):
    """Reconstruct identities and reject unbounded/foreign report data at the host."""
    targets = [request["focus"], *request["watches"]]
    valid = (type(report) is dict and report.get("request_hash") == request["request_hash"]
             and ("scope" in report) == ("scope" in request)
             and report.get("scope") == request.get("scope")
             and type(report.get("status")) is str
             and report.get("status") in {"complete", "unknown"}
             and type(report.get("rows")) is list and len(report["rows"]) == len(targets))
    rows = []
    event_total = 0
    if valid:
        for index, target in enumerate(targets):
            row = report["rows"][index]
            valid = (type(row) is dict and set(row) == {"index", "entries", "line_hits", "events"}
                     and type(row["index"]) is int and row["index"] == index
                     and type(row["entries"]) is int and 0 <= row["entries"] <= MAX_TRACE_EVENTS
                     and type(row["line_hits"]) is list and len(row["line_hits"]) <= MAX_LINES
                     and all(type(line) is int and line in target["lines"]
                             for line in row["line_hits"])
                     and type(row["events"]) is list)
            if not valid:
                break
            event_total += len(row["events"])
            for item in row["events"]:
                valid = (type(item) is dict and type(item.get("event")) is str
                    and item.get("event") in {
                    "call", "line", "return", "exception"}
                    and set(item) <= {"event", "line", "parent_index", "values", "value",
                                     "exception_type"}
                    and type(item.get("line")) is int
                    and target["first_line"] <= item["line"] <= target["last_line"]
                    and (item.get("parent_index") is None or type(item["parent_index"]) is int
                         and 0 <= item["parent_index"] < len(targets))
                    and type(item.get("values")) is dict
                    and set(item["values"]) <= set(target["fields"]))
                if not valid:
                    break
                # Only safe scalar projections emitted by the trusted collector are accepted.
                values = [*item["values"].values()]
                if "value" in item:
                    values.append(item["value"])
                if "exception_type" in item:
                    values.append(item["exception_type"])
                valid = all(type(value) in {type(None), bool, int, float, str, list}
                            and _value(value) == value for value in values)
                if not valid:
                    break
            if not valid:
                break
            rows.append(row)
        valid = valid and event_total <= MAX_EVENTS
    try:
        valid = valid and len(_json(report).encode()) <= MAX_REPORT_BYTES
    except (TypeError, ValueError, OverflowError, RecursionError):
        valid = False
    complete = bool(valid and report["status"] == "complete" and not report.get("reason")
                    and rows and (request.get("scope") == "selected_call"
                                  or rows[0]["entries"] > 0))
    reason = None if complete else (
        report.get("reason") if valid and type(report.get("reason")) is str
        and report.get("reason") in _REASONS else
        "invalid_report" if report is not None else "report_unavailable")
    result = {"schema_version": "public-call-path-feedback-v1", "diagnostic_only": True,
              "scope": ("selected_call_launch_thread" if request.get("scope") == "selected_call"
                        else "selected_call_focus_launch_thread"), "call_id": request["call_id"],
              "request_hash": request["request_hash"], "snapshot_hash": request["snapshot_hash"],
              "execution_identity_hash": request["execution_identity_hash"],
              "status": "complete" if complete else "unknown", "reason": reason,
              "interpretation": "Bounded public function/line observations only; no-hit requires "
              + ("complete selected-call coverage. Other calls/threads are unmeasured. "
                 if request.get("scope") == "selected_call" else
                 "complete selected-call/focus coverage. Other calls/threads are unmeasured. ") +
              "Line values precede execution; exceptions can be caught. Parent indexes identify "
              "the nearest bound ancestor. In-process observations are advisory, not semantic "
              "correctness or attestation."}
    for index, target in enumerate(targets):
        row = rows[index] if valid else {"entries": 0, "line_hits": [], "events": []}
        bound = {key: target[key] for key in ("origin", "path", "function", "file_hash",
                                             "first_line", "def_line", "last_line", "fields")}
        bound.update(entries=row["entries"] if valid else None,
                     observed_lines=row["line_hits"], events=row["events"],
                     not_observed_lines=sorted(set(target["lines"]) - set(row["line_hits"]))
                     if complete else None,
                     observation=("observed" if row["entries"] else "not_observed")
                     if complete else "unknown")
        if index:
            result.setdefault("watches", []).append(bound)
        else:
            result["focus"] = bound
    return result
