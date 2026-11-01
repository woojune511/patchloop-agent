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
MAX_SELECTED_EVENTS = 200_000
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


def _target_key(target):
    # Bare and qualified names may resolve to the same unique function node.
    return (target["origin"], target["path"], target["function"].rsplit(".", 1)[-1],
            target["first_line"], target["def_line"])


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
        # A focus and a watch can name the same frame. They share a physical
        # sample budget; each public row still projects only its selected fields.
        self.groups = {}
        self.group_for = {}
        for index, target in enumerate(self.targets):
            identity = _target_key(target)
            owner = next((i for i in self.groups
                          if _target_key(self.targets[i]) == identity), index)
            self.groups.setdefault(owner, []).append(index)
            self.group_for[index] = owner
        self.samples = {owner: [] for owner in self.groups}
        self.sample_bytes = {owner: 0 for owner in self.groups}
        self.record_quota = MAX_EVENTS // len(self.groups)
        self.byte_quota = MAX_VALUE_BYTES // len(self.groups)
        self.counts = [{event: 0 for event in ("call", "line", "return", "exception")}
                       for _ in self.targets]
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
        self.selected_events = self.sample_id = self.coalesced = self.omitted = 0
        self.limits = []
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

    def _limit(self, budget, limit, observed, frame, event, index=None):
        if not any(item["budget"] == budget for item in self.limits):
            self.limits.append({"budget": budget, "limit": limit, "observed": observed,
                                "target_index": index, "event": event,
                                "line": frame.f_lineno if index is not None else None})

    def _record(self, index, frame, event, arg=None):
        indexes = self.groups[index]
        parent = frame.f_back
        while parent is not None and id(parent) not in self.frames:
            parent = parent.f_back
        fields = {key for i in indexes
                  if event != "line" or frame.f_lineno in self.targets[i]["lines"]
                  for key in self.targets[i]["fields"]}
        values = {key: _value(frame.f_locals[key]) for key in fields
                  if key in frame.f_locals}
        item = {"event": event, "line": frame.f_lineno,
                "parent_index": self.frames.get(id(parent)), "values": values}
        if event == "return":
            item["value"] = _value(arg)
        elif event == "exception":
            item["exception_type"] = type.__getattribute__(arg[0], "__name__")[:128]
        signature = _json(item)
        samples = self.samples[index]
        for sample in samples:
            if sample["signature"] == signature:
                sample["occurrences"] += 1
                self.coalesced += 1
                return
        size = len(signature.encode())
        if size > self.byte_quota or not self.record_quota:
            self._limit("function_value_bytes" if size > self.byte_quota else "function_records",
                        self.byte_quota if size > self.byte_quota else self.record_quota,
                        size if size > self.byte_quota else 1, frame, event, index)
            self.omitted += 1
            return
        while (len(samples) >= self.record_quota
               or self.sample_bytes[index] + size > self.byte_quota):
            records = len(samples) >= self.record_quota
            self._limit("function_records" if records else "function_value_bytes",
                        self.record_quota if records else self.byte_quota,
                        len(samples) + 1 if records else self.sample_bytes[index] + size,
                        frame, event, index)
            # Keep the first sample plus recent distinct values, instead of
            # allowing initialization to permanently occupy the entire report.
            old = samples.pop(1 if len(samples) > 1 else 0)
            self.sample_bytes[index] -= old["size"]
            self.omitted += old["occurrences"]
        self.sample_id += 1
        samples.append({"item": item, "signature": signature, "size": size,
                        "sample_id": self.sample_id, "occurrences": 1})
        self.sample_bytes[index] += size

    def _trace(self, frame, event, arg):
        # The host's end hook closes the window; it is not a target call.
        if frame.f_code is type(self).end.__code__:
            return None
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
        if scoped and event == "call":
            self.trace_events = min(self.trace_events + 1, MAX_TRACE_EVENTS + 1)
            if self.trace_events > MAX_TRACE_EVENTS:
                self.reason = self.reason or "collector_truncated"
                self._limit("call_events", MAX_TRACE_EVENTS, self.trace_events, frame, event,
                            matches[0] if matches else None)
            else:
                for index in matches:
                    self.rows[index]["entries"] += 1
                    self.counts[index]["call"] += 1
                if matches:
                    self.frames[key] = self.group_for[matches[0]]
        if scoped and key in self.frames and self.trace_events <= MAX_TRACE_EVENTS:
            owner = self.frames[key]
            self.selected_events = min(self.selected_events + 1, MAX_SELECTED_EVENTS + 1)
            if self.selected_events > MAX_SELECTED_EVENTS:
                self.reason = self.reason or "collector_truncated"
                self._limit("selected_events", MAX_SELECTED_EVENTS, self.selected_events,
                            frame, event, owner)
            else:
                record = event in {"call", "return", "exception"}
                for index in self.groups[owner]:
                    if event == "line" and frame.f_lineno in self.targets[index]["lines"]:
                        self.counts[index]["line"] += 1
                        if frame.f_lineno not in self.rows[index]["line_hits"]:
                            self.rows[index]["line_hits"].append(frame.f_lineno)
                        record = True
                    elif event in {"return", "exception"}:
                        self.counts[index][event] += 1
                if record:
                    self._record(owner, frame, event, arg)
        if event == "return":
            self.frames.pop(key, None)
            self.focus_frames.discard(key)
            self.delegates.pop(key, None)
        # Global tracing discovers calls. Only selected frames (or a trusted
        # changed-line delegate) need local line/return/exception delivery.
        return (self.trace if (key in self.frames or key in self.focus_frames
                              or key in self.delegates) else None)

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
        self.event_count = sum(len(samples) for samples in self.samples.values())
        self.value_bytes = sum(self.sample_bytes.values())
        for index, row in enumerate(self.rows):
            target = self.targets[index]
            row["event_counts"] = self.counts[index]
            row["events"] = [{**sample["item"], "sample_id": sample["sample_id"],
                              "occurrences": sample["occurrences"],
                              "values": {key: value
                                         for key, value in sample["item"]["values"].items()
                                         if key in target["fields"]}}
                             for sample in self.samples[self.group_for[index]]
                             if sample["item"]["event"] != "line"
                             or sample["item"]["line"] in target["lines"]]
        collection = {"policy": "entry-and-detail-v2", "coverage": {
            "status": "unknown" if reason else "complete", "call_events": self.trace_events,
            "call_limit": MAX_TRACE_EVENTS, "selected_events": self.selected_events,
            "selected_limit": MAX_SELECTED_EVENTS}, "details": {
                "status": "sampled" if self.omitted else "complete",
                "record_limit": MAX_EVENTS, "value_byte_limit": MAX_VALUE_BYTES,
                "retained_records": self.event_count, "retained_value_bytes": self.value_bytes,
                "coalesced_events": self.coalesced, "omitted_events": self.omitted},
            "limits": self.limits}
        report = {"request_hash": self.request["request_hash"],
                  **({"scope": self.request["scope"]} if "scope" in self.request else {}),
                  "status": "unknown" if reason else "complete", "reason": reason,
                  "rows": self.rows, "collection": collection}
        raw = _json(report).encode()
        if len(raw) > MAX_REPORT_BYTES:
            collection["limits"].append({"budget": "report_bytes", "limit": MAX_REPORT_BYTES,
                "observed": len(raw), "target_index": None, "event": None, "line": None})
            omitted = sum(s["occurrences"] for samples in self.samples.values() for s in samples)
            collection["details"].update(status="sampled", retained_records=0,
                                        retained_value_bytes=0,
                                        omitted_events=self.omitted + omitted)
            for row in self.rows:
                row["events"] = []
            self.event_count = self.value_bytes = 0
            raw = _json(report).encode()
        with suppress(OSError):
            self.write(2, marker(self.request) + raw + b"\n")
        return report


def _valid_collection(collection, report, targets, samples):
    """Validate the versioned counters before allowing coverage-based absence."""
    if (type(collection) is not dict or set(collection) != {
            "policy", "coverage", "details", "limits"}
            or collection["policy"] != "entry-and-detail-v2"):
        return False
    coverage, details, limits = (collection[key] for key in ("coverage", "details", "limits"))
    if (type(coverage) is not dict or set(coverage) != {
            "status", "call_events", "call_limit", "selected_events", "selected_limit"}
            or coverage["status"] != report["status"]
            or type(details) is not dict or set(details) != {
                "status", "record_limit", "value_byte_limit", "retained_records",
                "retained_value_bytes", "coalesced_events", "omitted_events"}
            or type(limits) is not list or len(limits) > 5):
        return False
    integers = {**{k: v for k, v in coverage.items() if k != "status"},
                **{k: v for k, v in details.items() if k != "status"}}
    if (not all(type(v) is int and 0 <= v <= 1_000_000 for v in integers.values())
            or coverage["call_limit"] != MAX_TRACE_EVENTS
            or coverage["selected_limit"] != MAX_SELECTED_EVENTS
            or coverage["call_events"] > MAX_TRACE_EVENTS + 1
            or coverage["selected_events"] > MAX_SELECTED_EVENTS + 1
            or details["record_limit"] != MAX_EVENTS
            or details["value_byte_limit"] != MAX_VALUE_BYTES
            or details["retained_records"] != len(samples)
            or len(samples) > MAX_EVENTS
            or details["retained_value_bytes"] != sum(
                len(_json(sample["item"]).encode()) for sample in samples.values())
            or details["retained_value_bytes"] > MAX_VALUE_BYTES
            or details["status"] != ("sampled" if details["omitted_events"] else "complete")):
        return False
    groups = {_target_key(t) for t in targets}
    grouped = {}
    for index, target in enumerate(targets):
        row = report["rows"][index]
        counts = row["event_counts"]
        hits = row["line_hits"]
        if (not row["entries"] and (hits or any(counts[k] for k in ("line", "return", "exception")))
                or bool(counts["line"]) != bool(hits)
                or len(set(hits)) != len(hits) or counts["line"] < len(hits)
                or counts["return"] > counts["call"]):
            return False
        prior = grouped.setdefault(_target_key(target), [])
        for old_target, old_row in prior:
            if any(counts[k] != old_row["event_counts"][k]
                   for k in ("call", "return", "exception")):
                return False
            shared = set(target["lines"]) & set(old_target["lines"])
            if set(hits) & shared != set(old_row["line_hits"]) & shared:
                return False
        prior.append((target, row))
    if sum(rows[0][1]["entries"] for rows in grouped.values()) > coverage["call_events"]:
        return False
    if report["status"] == "complete":
        selected = sum(sum(rows[0][1]["event_counts"][k] for k in ("call", "return", "exception"))
                       + max(row["event_counts"]["line"] for _, row in rows)
                       for rows in grouped.values())
        retained = sum(sample["occurrences"] for sample in samples.values())
        if (selected > coverage["selected_events"]
                or retained + details["omitted_events"] > coverage["selected_events"]
                or details["coalesced_events"] > coverage["selected_events"]):
            return False
        if details["status"] == "complete":
            for row in report["rows"]:
                if any(sum(item["occurrences"] for item in row["events"] if item["event"] == k)
                       != count for k, count in row["event_counts"].items()):
                    return False
    budgets = {"call_events": MAX_TRACE_EVENTS, "selected_events": MAX_SELECTED_EVENTS,
               "function_records": MAX_EVENTS // len(groups),
               "function_value_bytes": MAX_VALUE_BYTES // len(groups),
               "report_bytes": MAX_REPORT_BYTES}
    seen = set()
    for limit in limits:
        if (type(limit) is not dict or set(limit) != {
                "budget", "limit", "observed", "target_index", "event", "line"}
                or type(limit["budget"]) is not str or limit["budget"] not in budgets
                or limit["budget"] in seen or type(limit["limit"]) is not int
                or limit["limit"] != budgets[limit["budget"]]
                or type(limit["observed"]) is not int
                or not limit["limit"] < limit["observed"] <= 1_000_000
                or limit["event"] not in (None, "call", "line", "return", "exception")):
            return False
        index = limit["target_index"]
        if index is None:
            if limit["line"] is not None:
                return False
        elif (type(index) is not int or not 0 <= index < len(targets)
              or type(limit["line"]) is not int
              or not targets[index]["first_line"] <= limit["line"] <= targets[index]["last_line"]):
            return False
        seen.add(limit["budget"])
    for field, maximum in (("call_events", MAX_TRACE_EVENTS),
                           ("selected_events", MAX_SELECTED_EVENTS)):
        if (coverage[field] > maximum) != (field in seen):
            return False
    if bool(details["omitted_events"]) != bool(
            seen & {"function_records", "function_value_bytes", "report_bytes"}):
        return False
    return not (report["status"] == "complete" and seen & {"call_events", "selected_events"})


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
    versioned = type(report) is dict and "collection" in report
    samples = {}
    if valid:
        for index, target in enumerate(targets):
            row = report["rows"][index]
            valid = (type(row) is dict and set(row) == (
                         {"index", "entries", "line_hits", "events"}
                         | ({"event_counts"} if versioned else set()))
                     and type(row["index"]) is int and row["index"] == index
                     and type(row["entries"]) is int and 0 <= row["entries"] <= MAX_TRACE_EVENTS
                     and type(row["line_hits"]) is list and len(row["line_hits"]) <= MAX_LINES
                     and all(type(line) is int and line in target["lines"]
                             for line in row["line_hits"])
                     and type(row["events"]) is list)
            if valid and versioned:
                counts = row["event_counts"]
                valid = (type(counts) is dict and set(counts) == {
                    "call", "line", "return", "exception"}
                    and all(type(v) is int and 0 <= v <= max(MAX_TRACE_EVENTS, MAX_SELECTED_EVENTS)
                            for v in counts.values()) and counts["call"] == row["entries"])
            if not valid:
                break
            event_total += len(row["events"])
            retained = {event: 0 for event in ("call", "line", "return", "exception")}
            row_sample_ids = set()
            for item in row["events"]:
                valid = (type(item) is dict and type(item.get("event")) is str
                    and item.get("event") in {
                    "call", "line", "return", "exception"}
                    and set(item) <= {"event", "line", "parent_index", "values", "value",
                                     "exception_type", *(["sample_id", "occurrences"]
                                                         if versioned else [])}
                    and type(item.get("line")) is int
                    and target["first_line"] <= item["line"] <= target["last_line"]
                    and (item.get("parent_index") is None or type(item["parent_index"]) is int
                         and 0 <= item["parent_index"] < len(targets))
                    and type(item.get("values")) is dict
                    and set(item["values"]) <= set(target["fields"]))
                if not valid:
                    break
                if versioned:
                    sample_id, occurrences = item.get("sample_id"), item.get("occurrences")
                    valid = (type(sample_id) is int and 0 < sample_id <= MAX_SELECTED_EVENTS
                             and sample_id not in row_sample_ids
                             and type(occurrences) is int and 0 < occurrences <= MAX_SELECTED_EVENTS
                             and (item["event"] != "line" or item["line"] in target["lines"]))
                    valid = valid and (item["event"] != "line" or item["line"] in row["line_hits"])
                    if not valid:
                        break
                    row_sample_ids.add(sample_id)
                    retained[item["event"]] += occurrences
                    projected = {k: v for k, v in item.items()
                                 if k not in {"sample_id", "occurrences"}}
                    identity = _target_key(target)
                    prior = samples.get(sample_id)
                    if prior is not None:
                        valid = (prior["identity"] == identity
                                 and prior["occurrences"] == occurrences
                                 and {k: v for k, v in prior["item"].items() if k != "values"}
                                 == {k: v for k, v in projected.items() if k != "values"}
                                 and all(prior["item"]["values"].get(k, v) == v
                                         for k, v in projected["values"].items()))
                        if not valid:
                            break
                        prior["item"]["values"].update(projected["values"])
                    else:
                        samples[sample_id] = {
                            "identity": identity, "occurrences": occurrences,
                            "item": {**projected, "values": dict(projected["values"])}}
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
            if versioned and any(retained[k] > row["event_counts"][k] for k in retained):
                valid = False
                break
            rows.append(row)
        valid = valid and (versioned or event_total <= MAX_EVENTS)
    try:
        valid = valid and len(_json(report).encode()) <= MAX_REPORT_BYTES
        if valid and versioned:
            valid = _valid_collection(report["collection"], report, targets, samples)
    except (TypeError, ValueError, OverflowError, RecursionError):
        valid = False
    complete = bool(valid and report["status"] == "complete" and not report.get("reason")
                    and rows and (request.get("scope") == "selected_call"
                                  or rows[0]["entries"] > 0))
    reason = None if complete else (
        report.get("reason") if valid and type(report.get("reason")) is str
        and report.get("reason") in _REASONS else
        "invalid_report" if report is not None else "report_unavailable")
    result = {"schema_version": ("public-call-path-feedback-v2" if versioned
                                 else "public-call-path-feedback-v1"), "diagnostic_only": True,
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
    if valid and versioned:
        result["collection"] = report["collection"]
        result["interpretation"] += (
            " Entry/selected-line/event counts cover the window independently of detail sampling. "
            "Details retain first and recent distinct values per function; occurrences coalesce "
            "equal projections, not necessarily consecutive calls. Shared sample IDs count once. "
            "Use event_counts for event absence, never missing sampled records.")
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
        if valid and versioned:
            bound["event_counts"] = row["event_counts"]
        if index:
            result.setdefault("watches", []).append(bound)
        else:
            result["focus"] = bound
    return result
