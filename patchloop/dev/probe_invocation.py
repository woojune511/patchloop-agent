"""Bounded invocation adapter for new public reproductions; legacy observers stay frozen."""
from __future__ import annotations

import copy

from patchloop.util import canonical_json, sha256_json

CHANNEL = "invoke-declared-call-v1"

# Runs inside the existing probe sandbox and counts toward its 8,000 source chars.
# In-process diagnostic feedback is not an attestation against a hostile program.
OBSERVER = '''import os as _pr_os, sys as _pr_sys, json as _pr_json
import importlib as _pr_import, hashlib as _pr_hash, inspect as _pr_inspect
_pr_rows, _pr_more = [], [False]
_pr_start = _pr_os.getcwd()
_pr_observation = {"count": 0, "json": None, "error": None, "call_count": 0}
def _pr_value(v, depth=0):
    if v is None or type(v) in (bool, int, float, str):
        if type(v) is not str or len(v) <= 256:
            return v
    elif depth < 3 and type(v) is list and len(v) <= 16:
        return [_pr_value(x, depth+1) for x in v]
    elif depth < 3 and type(v) is dict and len(v) <= 16 and all(type(k) is str for k in v):
        return {k: _pr_value(x, depth+1) for k, x in v.items()}
    _pr_more[0] = True
    return {"omitted_type": type(v).__name__}
def _pr_snapshot(path, budget):
    rows = []
    def visit(p, name):
        budget[0] -= 1
        if budget[0] < 0 or _pr_os.path.islink(p):
            raise ValueError("input snapshot incomplete")
        if _pr_os.path.isdir(p):
            rows.append([name, "directory", _pr_os.stat(p).st_mode & 511])
            with _pr_os.scandir(p) as entries:
                names = []
                for entry in entries:
                    names.append(entry.name)
                    if len(names) > budget[0]:
                        raise ValueError("input snapshot limit")
            for child in sorted(names):
                visit(_pr_os.path.join(p, child), name + "/" + child)
        elif _pr_os.path.isfile(p):
            with open(p, "rb") as stream:
                data = stream.read(budget[1]+1)
            budget[1] -= len(data)
            if budget[1] < 0:
                raise ValueError("input byte limit")
            rows.append([name, "file", _pr_os.stat(p).st_mode & 511,
                         _pr_hash.sha256(data).hexdigest()])
        elif not _pr_os.path.lexists(p):
            rows.append([name, "missing"])
        else:
            raise ValueError("unsupported input")
    visit(path, ".")
    data = _pr_json.dumps(rows, ensure_ascii=True, separators=(",", ":"))
    return {"path": path, "hash": _pr_hash.sha256(data.encode()).hexdigest(), "entries": len(rows)}
def _pr_resolve():
    parts = _pr_target.split(".")
    for end in range(len(parts)-1, 0, -1):
        name = ".".join(parts[:end])
        try:
            value = _pr_import.import_module(name)
        except ModuleNotFoundError as error:
            if error.name and (name == error.name or name.startswith(error.name + ".")):
                continue
            raise
        for attr in parts[end:]:
            value = getattr(value, attr)
        if not callable(value):
            raise TypeError("declared entrypoint is not callable")
        return value
    raise ImportError("declared entrypoint cannot be resolved")
def call_target(args=(), kwargs=None, *, input_paths=(), environment_keys=()):
    kwargs = {} if kwargs is None else kwargs
    if (type(args) not in (list, tuple) or type(kwargs) is not dict or len(_pr_rows) >= 4
            or type(input_paths) not in (list, tuple) or len(input_paths) > 4
            or type(environment_keys) not in (list, tuple) or len(environment_keys) > 16
            or any(type(k) is not str for k in environment_keys)):
        _pr_more[0] = True
        raise ValueError("invalid call_target inputs")
    target = _pr_resolve()
    row = {"entrypoint": _pr_target,
           "resolved_entrypoint": getattr(target, "__module__", "") + "." +
                                  getattr(target, "__qualname__", ""),
           "arguments": _pr_value({"args": list(args), "kwargs": kwargs}),
           "cwd": _pr_os.getcwd(), "sys_path": list(_pr_sys.path), "start_cwd": _pr_start,
           "inputs": [], "environment": {"python": list(_pr_sys.version_info[:3]),
           "platform": _pr_sys.platform, "variables": {}}, "outcome": "incomplete"}
    try:
        budget = [64, 1048576]
        row["inputs"] = [_pr_snapshot(_pr_os.path.abspath(p), budget) for p in input_paths]
        row["environment"]["variables"] = {k: (None if k not in _pr_os.environ else
            _pr_hash.sha256(_pr_os.environ[k].encode()).hexdigest()) for k in environment_keys}
    except (OSError, ValueError, TypeError):
        _pr_more[0] = True
    _pr_rows.append(row)
    try:
        value = target(*args, **kwargs)
    except BaseException:
        row["outcome"] = "raised"
        raise
    if any(check(value) for check in (_pr_inspect.isawaitable, _pr_inspect.isgenerator,
                                     _pr_inspect.isasyncgen)):
        _pr_more[0] = True
    else:
        row["outcome"] = "returned"
    return value
def record_observation(value):
    _pr_observation["count"] += 1
    _pr_observation["call_count"] = len(_pr_rows)
    try:
        if _pr_observation["count"] != 1:
            raise ValueError("record_observation requires one value")
        text = _pr_json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
        if len(text.encode()) > 2048:
            raise ValueError("observation exceeds 2048 bytes")
        _pr_observation["json"] = text
    except (ValueError, TypeError, OverflowError, RecursionError):
        _pr_observation["error"] = "invalid_observation"
        raise
try:
    exec(compile(_pr_source, "<patchloop-reproduction>", "exec"), globals())
finally:
    try:
        report = _pr_json.dumps({"calls": _pr_rows, "incomplete": _pr_more[0],
                                "observation": _pr_observation},
                               ensure_ascii=True, allow_nan=False, separators=(",", ":"))
        if len(report) > 6000:
            report = '{"calls":[],"incomplete":true}'
        _pr_os.write(2, ("\\n" + _pr_marker + report + "\\n").encode())
    except (ValueError, OverflowError, OSError):
        pass
'''


def valid_call(call, entrypoint):
    return (isinstance(call, dict) and set(call) == {
        "entrypoint", "resolved_entrypoint", "arguments", "cwd", "sys_path", "start_cwd",
        "inputs", "environment", "outcome"}
        and call["entrypoint"] == entrypoint and isinstance(call["resolved_entrypoint"], str)
        and isinstance(call["arguments"], dict)
        and all(isinstance(call[k], str) for k in ("cwd", "start_cwd"))
        and isinstance(call["sys_path"], list)
        and all(isinstance(p, str) for p in call["sys_path"])
        and isinstance(call["inputs"], list) and len(call["inputs"]) <= 4
        and all(isinstance(p, dict) and set(p) == {"path", "hash", "entries"}
                and isinstance(p["path"], str) and isinstance(p["hash"], str)
                and type(p["entries"]) is int for p in call["inputs"])
        and isinstance(call["environment"], dict)
        and call["outcome"] in ("returned", "raised", "incomplete"))


def environment(output):
    """Host-observed execution environment, excluding candidate and clock identities."""
    policy = output.get("execution_policy", {})
    return {key: copy.deepcopy(policy.get(key)) for key in (
        "image_digest", "profile_hash", "dependencies", "thread_environment", "entrypoint",
    )}


def conditions(trace):
    calls = []
    for original in trace["calls"]:
        row = copy.deepcopy(original)
        anchors = [(v["path"], f"$INPUT{i}") for i, v in enumerate(row["inputs"])]
        anchors.append((row["start_cwd"], "$START_CWD"))
        anchors.sort(key=lambda pair: len(pair[0]), reverse=True)

        def normalize(value, anchors=anchors):
            if isinstance(value, str):
                for path, alias in anchors:
                    if value == path or value.startswith((path + "/", path + "\\")):
                        return alias + value[len(path):]
            elif isinstance(value, list):
                return [normalize(v) for v in value]
            elif isinstance(value, dict):
                return {k: normalize(v) for k, v in value.items()}
            return value

        # A return/exception or a changed implementation is an outcome, not input
        # drift. The public callable selection, argument and setup identities remain.
        for key in ("resolved_entrypoint", "outcome"):
            row.pop(key)
        calls.append(normalize(row))
    return {"calls": calls, "execution_environment": trace.get("execution_environment"),
            "incomplete": trace["incomplete"]}


def summary(trace):
    """Keep the concrete scope visible in handoffs without copying full probe bodies."""
    calls = trace["calls"]
    value = conditions(trace)
    preview = canonical_json(value["calls"])
    return {
        "status": "incomplete" if trace["incomplete"] else "called" if calls else "not_called",
        "call_count": len(calls), "conditions_hash": sha256_json(value),
        "actual_conditions": preview[:700], "omitted_condition_chars": max(0, len(preview) - 700),
        "execution_environment_hash": sha256_json(value["execution_environment"]),
    }
