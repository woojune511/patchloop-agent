"""Inserted into the frozen public caller program before its entrypoint call."""

helper_calls = []
helper_counts = {"file_info_from_modpath": 0, "_spec_from_modpath": 0}
helper_selected = dict.fromkeys(helper_counts, 0)
helper_overflow = 0


def helper_scalar(value):
    if value is None or type(value) in (bool, int, float, str):
        return value
    if isinstance(value, (list, tuple)) and all(type(v) is str for v in value):
        return list(value)[:8]
    if type(value).__name__ == "ModuleSpec" and isinstance(value, tuple) and len(value) == 5:
        return {"name": value[0], "type": value[1].name,
                "location": value[2], "search_locations": helper_scalar(value[4])}
    return "<non-scalar>"


def helper_trace(frame, event, arg):
    global helper_overflow
    name = frame.f_code.co_name
    if (event != "call" or name not in helper_counts
            or not frame.f_code.co_filename.replace("\\", "/").endswith("/astroid/modutils.py")):
        return None
    helper_counts[name] += 1
    modpath = frame.f_locals.get("modpath")
    if not isinstance(modpath, (list, tuple)) or not any(p in ("src", "project") for p in modpath):
        return None
    helper_selected[name] += 1
    if len(helper_calls) >= 12:
        helper_overflow += 1
        return None
    parent = frame.f_back
    row = {"function": name, "file": frame.f_code.co_filename,
           "first_line": frame.f_code.co_firstlineno,
           "caller": {"function": parent.f_code.co_name,
                      "file": parent.f_code.co_filename, "line": parent.f_lineno},
           "arguments": {k: helper_scalar(frame.f_locals[k]) for k in
                         ("modpath", "path", "context_file", "context") if k in frame.f_locals},
           "lines": [], "states": [], "exceptions": [], "returned": False}
    helper_calls.append(row)

    def observe_helper(current, kind, result):
        global helper_overflow
        if kind == "line":
            if len(row["lines"]) >= 64:
                helper_overflow += 1
                return None
            row["lines"].append(current.f_lineno)
            state = {k: helper_scalar(current.f_locals[k]) for k in
                     ("context", "location", "found_spec") if k in current.f_locals}
            if state and (not row["states"] or state != row["states"][-1]["values"]):
                if len(row["states"]) >= 8:
                    helper_overflow += 1
                else:
                    row["states"].append({"line": current.f_lineno, "values": state})
        elif kind == "exception":
            if len(row["exceptions"]) < 4:
                row["exceptions"].append({"line": current.f_lineno, "type": result[0].__name__})
            else:
                helper_overflow += 1
        elif kind == "return":
            row["returned"] = True
            row["return_line"] = current.f_lineno
            row["return"] = helper_scalar(result)
        return observe_helper

    return observe_helper
