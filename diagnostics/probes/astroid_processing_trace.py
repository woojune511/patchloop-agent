"""Observe the fixed public caller without replacing target functions, Python 3.9.

A return event also closes an unwinding frame; it does not mean processing passed.
"""

import json as _pt_json
import os as _pt_os
import posixpath as _pt_path
import sys as _pt_sys

_pt_files = {
    "expand_modules": "/pylint/lint/expand_modules.py",
    "file_info_from_modpath": "/astroid/modutils.py",
    "is_namespace": "/astroid/modutils.py",
    "is_directory": "/astroid/modutils.py",
    "get_module_files": "/astroid/modutils.py",
    "file_build": "/astroid/builder.py",
    "_check_file": "/pylint/lint/pylinter.py",
    "check_astroid_module": "/pylint/lint/pylinter.py",
    "_check_astroid_module": "/pylint/lint/pylinter.py",
}
_pt_fields = {
    "expand_modules": ("files_or_modules",),
    "file_info_from_modpath": ("modpath", "context_file"),
    "is_namespace": ("specobj",),
    "is_directory": ("specobj",),
    "get_module_files": ("src_directory", "list_all"),
    "file_build": ("path", "modname"),
    "_check_file": ("file",),
    "check_astroid_module": ("ast_node",),
    "_check_astroid_module": ("node",),
}
_pt_active = False
_pt_report = None
_pt_previous = None
_pt_max_calls = 128
_pt_max_bytes = 8000


def _pt_overflow(kind):
    _pt_report["overflow"] = True
    _pt_report["counts"][kind] = _pt_report["counts"].get(kind, 0) + 1


def _pt_value(value, depth=0):
    if value is None or type(value) in (bool, int, float):
        return value
    if type(value) is str:
        if len(value) > 256:
            _pt_overflow("truncated_values")
        return value[:256]
    if depth >= 5:
        _pt_overflow("truncated_values")
        return "<depth-limit>"
    kind = type(value).__name__
    if kind == "Module":
        fields = object.__getattribute__(value, "__dict__")
        body = fields.get("body")
        return {"type": kind, "name": _pt_value(fields.get("name"), depth + 1),
                "file": _pt_value(fields.get("file"), depth + 1),
                "body_length": len(body) if type(body) is list else None,
                "package": fields.get("package") if type(fields.get("package")) is bool else None}
    if kind == "ModuleType":
        return object.__getattribute__(value, "_name_")
    if isinstance(value, tuple) and kind in ("ModuleSpec", "FileItem"):
        return {key: _pt_value(value[index], depth + 1)
                for index, key in enumerate(type(value)._fields)
                if key not in ("origin", "modpath") and value[index] is not None}
    if type(value) in (list, tuple):
        if len(value) > 12:
            _pt_overflow("truncated_values")
        return [_pt_value(item, depth + 1) for item in value[:12]]
    if type(value) is dict:
        if len(value) > 12:
            _pt_overflow("truncated_values")
        return {key: _pt_value(item, depth + 1) for key, item in list(value.items())[:12]
                if type(key) is str}
    return {"type": kind}


def _pt_under(value, root):
    if type(value) is not str:
        return False
    path = _pt_path.normpath(_pt_path.join(root, value.replace("\\", "/")))
    return path == root or path.startswith(root + "/")


def _pt_select(frame, name, root):
    values = frame.f_locals
    if name == "expand_modules":
        return any(_pt_under(value, root) for value in values.get("files_or_modules", ()))
    if name == "file_info_from_modpath":
        return any(part in ("src", "project", "regularpkg")
                   for part in values.get("modpath", ()))
    if name in ("is_namespace", "is_directory"):
        parent = frame.f_back
        return (parent is not None and parent.f_code.co_name == "expand_modules"
                and parent.f_code.co_filename.replace("\\", "/").endswith(
                    _pt_files["expand_modules"]))
    if name == "get_module_files":
        return _pt_under(values.get("src_directory"), root)
    if name == "file_build":
        return _pt_under(values.get("path"), root)
    key = {"_check_file": "file", "check_astroid_module": "ast_node",
           "_check_astroid_module": "node"}[name]
    value = _pt_value(values.get(key))
    return type(value) is dict and _pt_under(value.get("filepath", value.get("file")), root)


def _pt_state(frame, row):
    values = frame.f_locals
    if row["function"] == "expand_modules":
        fields = ("filepath", "modname", "is_namespace", "is_directory", "has_init")
        if not all(key in values for key in fields):
            return
    elif row["function"] == "get_module_files":
        fields = ("directory", "dirnames", "filenames")
        if not all(key in values for key in fields):
            return
    else:
        return
    state = {key: _pt_value(values[key]) for key in fields}
    if row["states"] and row["states"][-1]["values"] == state:
        return
    if len(row["states"]) >= 8:
        _pt_overflow("dropped_states")
    else:
        row["states"].append({"line": frame.f_lineno, "values": state})


def _pt_error(frame, event, error):
    _pt_report["counts"]["callback_errors"] += 1
    if len(_pt_report["callback_errors"]) < 4:
        _pt_report["callback_errors"].append({"event": event,
            "function": frame.f_code.co_name, "line": frame.f_lineno,
            "type": type(error).__name__})
    else:
        _pt_overflow("dropped_errors")


def _pt_trace(frame, event, arg):
    if not _pt_active or event != "call":
        return None
    name = frame.f_code.co_name
    suffix = _pt_files.get(name)
    if suffix is None:
        return None
    filename = frame.f_code.co_filename.replace("\\", "/")
    if not filename.endswith(suffix) or (suffix.startswith("/astroid/")
                                        and not filename.startswith("/workspace/")):
        return None
    try:
        counts = _pt_report["counts"]
        counts["matched_calls"] += 1
        cwd = _pt_os.getcwd().replace("\\", "/")
        root = next(("/tmp/patchloop-case/" + case for case in ("failing", "control")
                     if cwd == "/tmp/patchloop-case/" + case), None)
        if root is None or not _pt_select(frame, name, root):
            counts["excluded_calls"] += 1
            return None
        counts["selected_calls"] += 1
        if len(_pt_report["calls"]) >= _pt_max_calls:
            _pt_overflow("dropped_calls")
            return None
        arguments = {key: _pt_value(frame.f_locals[key])
                     for key in _pt_fields[name] if key in frame.f_locals}
        if name in ("check_astroid_module", "_check_astroid_module"):
            key = _pt_fields[name][0]
            arguments[key] = {field: arguments[key][field] for field in ("file", "body_length")}
        row = {"phase": root.rsplit("/", 1)[1],
               "function": name, "arguments": arguments,
               "states": [], "exceptions": [], "return_seen": False}
        _pt_report["calls"].append(row)
        counts["recorded_calls"] += 1
    except Exception as error:
        _pt_error(frame, event, error)
        return None

    def _pt_local(current, kind, value):
        if not _pt_active:
            return None
        try:
            if kind in ("line", "return"):
                _pt_state(current, row)
            if kind == "exception":
                if len(row["exceptions"]) >= 4:
                    _pt_overflow("dropped_exceptions")
                else:
                    row["exceptions"].append({"line": current.f_lineno,
                                              "type": value[0].__name__})
            elif kind == "return":
                row["return_seen"] = True
                row["return_value"] = _pt_value(value)
                counts["closed_calls"] += 1
        except Exception as error:
            _pt_error(current, kind, error)
        return _pt_local

    return _pt_local


def install_processing_trace(max_calls=128, max_bytes=8000):
    """Install in the calling thread; existing tracing is restored by finish."""
    global _pt_active, _pt_report, _pt_previous, _pt_max_calls, _pt_max_bytes
    if _pt_active:
        raise RuntimeError("processing trace already installed")
    if not 1 <= max_calls <= 128 or not 1024 <= max_bytes <= 8000:
        raise ValueError("processing trace limits exceed the bounded contract")
    _pt_previous = _pt_sys.gettrace()
    _pt_max_calls, _pt_max_bytes = max_calls, max_bytes
    _pt_report = {"schema_version": "astroid-processing-trace-v1", "complete": False,
        "overflow": False, "counts": dict.fromkeys(("matched_calls", "excluded_calls",
            "selected_calls", "recorded_calls", "closed_calls", "dropped_calls",
            "callback_errors"), 0), "callback_errors": [], "calls": []}
    _pt_active = True
    _pt_sys.settrace(_pt_trace)


def finish_processing_trace():
    """Return bounded JSON data; complete means selected observation, not repair."""
    global _pt_active
    if not _pt_active:
        raise RuntimeError("processing trace is not installed")
    replaced = _pt_sys.gettrace() is not _pt_trace
    _pt_active = False
    _pt_sys.settrace(_pt_previous)
    counts = _pt_report["counts"]
    _pt_report["trace_replaced"] = replaced
    _pt_report["complete"] = not (replaced or _pt_report["overflow"]
        or counts["callback_errors"] or counts["recorded_calls"] != counts["closed_calls"])
    for row in _pt_report["calls"]:
        for key in ("states", "exceptions"):
            if not row[key]:
                del row[key]
    while len(_pt_json.dumps(_pt_report, separators=(",", ":")).encode()) > _pt_max_bytes:
        _pt_report["complete"] = False
        _pt_overflow("byte_dropped_calls")
        _pt_report["calls"].pop()
    return _pt_report
