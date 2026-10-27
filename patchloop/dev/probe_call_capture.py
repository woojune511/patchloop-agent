"""Current per-call Python-stream capture; legacy observer programs remain frozen."""

from __future__ import annotations

import re

CHANNEL = "invoke-declared-call-v3"
CAPTURE_BYTES = 4096
REPORT_BYTES = 10000

# Composed with the existing snapshot/resolver and observation framing. These
# streams observe this Python process only, not native fd writes or subprocesses.
CALLS = '''from types import SimpleNamespace as _pr_Result
_pr_remaining = [4096]
class _pr_Stream:
    def __init__(self):
        self.parts, self.truncated = [], False
    def write(self, text):
        raw = text.encode("utf-8")
        kept = raw[:_pr_remaining[0]].decode("utf-8", "ignore")
        if kept:
            self.parts.append(kept)
        _pr_remaining[0] -= len(kept.encode("utf-8"))
        self.truncated |= len(raw) != len(kept.encode("utf-8"))
        return len(text)
    def flush(self):
        pass
    def isatty(self):
        return False
    @property
    def encoding(self):
        return "utf-8"

def observed_target(*, input_paths=(), environment_keys=(), expected_exceptions=()):
    if (type(input_paths) not in (list, tuple) or len(input_paths) > 4
            or type(environment_keys) not in (list, tuple) or len(environment_keys) > 16
            or any(type(k) is not str for k in environment_keys)
            or type(expected_exceptions) is not tuple or len(expected_exceptions) > 4
            or any(not isinstance(t, type) or not issubclass(t, Exception)
                   for t in expected_exceptions)):
        _pr_more[0] = True
        raise ValueError("invalid observed_target settings")
    input_paths, environment_keys = tuple(input_paths), tuple(environment_keys)
    def invoke(*args, **kwargs):
        if len(_pr_rows) >= 4:
            _pr_more[0] = True
            raise ValueError("call limit")
        target = _pr_resolve()
        row = {"entrypoint": _pr_target,
            "resolved_entrypoint": getattr(target, "__module__", "") + "." +
                                   getattr(target, "__qualname__", ""),
            "argv": _pr_value(_pr_sys.argv),
            "arguments": _pr_value({"args": list(args), "kwargs": kwargs}),
            "cwd": _pr_os.getcwd(), "sys_path": list(_pr_sys.path), "start_cwd": _pr_start,
            "inputs": [], "environment": {"python": list(_pr_sys.version_info[:3]),
            "platform": _pr_sys.platform, "variables": {}}, "outcome": "incomplete",
            "call_id": "call-" + str(len(_pr_rows)+1), "bound_parameters": None,
            "exception_policy": [t.__module__ + "." + t.__qualname__ for t in expected_exceptions],
            "capture": {"scope": "python-streams", "status": "incomplete",
                        "stdout": "", "stderr": ""},
            "exception": None, "exit_code": None}
        _pr_rows.append(row)
        try:
            budget = [64, 1048576]
            row["inputs"] = [_pr_snapshot(_pr_os.path.abspath(p), budget) for p in input_paths]
            row["environment"]["variables"] = {k: (None if k not in _pr_os.environ else
                _pr_hash.sha256(_pr_os.environ[k].encode()).hexdigest()) for k in environment_keys}
            try:
                signature = _pr_inspect.signature(target)
            except (ValueError, TypeError):
                signature = None
            if signature is not None:
                row["bound_parameters"] = _pr_value(dict(signature.bind(*args, **kwargs).arguments))
        except (OSError, ValueError, TypeError):
            _pr_more[0] = True
            raise
        out, err = _pr_Stream(), _pr_Stream()
        old = _pr_sys.stdout, _pr_sys.stderr
        value, error = None, None
        _pr_sys.stdout, _pr_sys.stderr = out, err
        try:
            value = target(*args, **kwargs)
            row["outcome"] = "returned"
            if any(check(value) for check in (_pr_inspect.isawaitable, _pr_inspect.isgenerator,
                                             _pr_inspect.isasyncgen)):
                _pr_more[0] = True
        except BaseException as caught:
            error = caught
            row["exception"] = {"type": type(caught).__module__ + "." + type(caught).__qualname__,
                                "message": str(caught)[:256]}
            row["outcome"] = "system_exit" if isinstance(caught, SystemExit) else "raised"
            if isinstance(caught, SystemExit):
                row["exit_code"] = _pr_value(caught.code)
            elif type(caught) not in expected_exceptions:
                _pr_more[0] = True
        finally:
            altered = _pr_sys.stdout is not out or _pr_sys.stderr is not err
            _pr_sys.stdout, _pr_sys.stderr = old
            state = ("incomplete" if altered else
                     "truncated" if out.truncated or err.truncated else "complete")
            row["capture"].update(status=state, stdout="".join(out.parts),
                                  stderr="".join(err.parts))
            _pr_more[0] |= state != "complete"
        if error is not None and not isinstance(error, (Exception, SystemExit)):
            raise error
        return _pr_Result(value=value, stdout=row["capture"]["stdout"],
            stderr=row["capture"]["stderr"], outcome=row["outcome"],
            capture_status=row["capture"]["status"], exception=row["exception"],
            exit_code=row["exit_code"], call_id=row["call_id"])
    return invoke
'''


def observer(legacy):
    """Keep v1/v2 exact; replace only the call implementation for fresh v3 cases."""
    prefix, rest = legacy.split("def call_target(", 1)
    suffix = "def record_observation(" + rest.split("def record_observation(", 1)[1]
    suffix = suffix.replace("if len(report) > 6000:",
                            'if len(report.encode("utf-8")) > 10000:', 1)
    # UTF-8, rather than ASCII escapes, lets bounded captured diagnostics fit the
    # existing 12K process-output limit. Oversized reports remain incomplete.
    suffix = suffix.replace("ensure_ascii=True, allow_nan=False",
                            "ensure_ascii=False, allow_nan=False")
    # Compact only fixed host indentation, never authored source or legacy bytes.
    # All block indents in these fixed fragments are multiples of four spaces;
    # continuation indentation inside parentheses has no semantic significance.
    return "\n".join(" " * ((len(line) - len(line.lstrip())) // 4) + line.lstrip()
                     for line in (prefix + CALLS + suffix).splitlines() if line.strip()) + "\n"


def stable_observer(legacy):
    """Fresh v4 launch state; v3's observer and saved program bytes stay exact."""
    setup = '''_pr_start = _pr_os.getcwd()
_pr_sys.argv=["<patchloop-reproduction>"]
_pr_work=[]
def reproduction_workspace():
 if not _pr_work:
  p=_pr_os.path.join(_pr_start,"patchloop-case")
  _pr_os.mkdir(p)
  _pr_work.append(p)
 return _pr_work[0]
'''
    source = observer(legacy).replace("_pr_start = _pr_os.getcwd()\n", setup, 1)
    # A sandbox starts with a fresh writable cwd. Exclusive mkdir never reuses
    # or deletes someone else's directory; repeat calls in this execution share
    # only the directory just created here. Authored argv overrides remain real.
    # Shorten fixed private symbols to retain the existing 8K observer allowance.
    for old, new in (
        ("_pr_observation", "_pr_obs"), ("_pr_remaining", "_pr_left"),
        ("_pr_inspect", "_pr_i"), ("_pr_value", "_pr_v"),
        ("_pr_rows", "_pr_r"), ("_pr_more", "_pr_m"),
        ("_pr_Stream", "_pr_S"), ("_pr_json", "_pr_j"),
    ):
        source = source.replace(old, new)
    return source


def diagnostic_observer(legacy):
    """v5 adds a separate trusted diagnostic hook; v1-v4 bytes stay frozen."""
    source = stable_observer(legacy)
    anchor = '   row["outcome"] = "system_exit"'
    hook = ('   try:_patchloop_exception_capture(caught,row["call_id"],row["exception"])\n'
            '   except BaseException:pass\n')
    if source.count(anchor) != 1:
        raise ValueError("exception observer hook location is unavailable")
    source = source.replace(anchor, hook + anchor, 1)
    # Keep the existing observer allowance even at the maximum entrypoint length.
    # Only private host identifiers change; authored source and prior versions do not.
    for old, new in (("_pr_start", "_pr_st"), ("_pr_work", "_pr_w"),
                     ("_pr_snapshot", "_pr_ss"), ("_pr_resolve", "_pr_rs"),
                     ("_pr_hash", "_pr_h"), ("_pr_import", "_pr_im"), ("budget", "b")):
        source = source.replace(old, new)
    return source


def behavior_observer(legacy):
    """v7 separates generated state and identifies failures before target entry."""
    source = diagnostic_observer(legacy)
    old = '''_pr_w=[]
def reproduction_workspace():
 if not _pr_w:
  p=_pr_os.path.join(_pr_st,"patchloop-case")
  _pr_os.mkdir(p)
  _pr_w.append(p)
 return _pr_w[0]
'''
    new = '''_pr_dirs={}
def _pr_dir(name):
 if name not in _pr_dirs:
  p=_pr_os.path.join(_pr_st,name)
  _pr_os.mkdir(p)
  _pr_dirs[name]=p
 return _pr_dirs[name]
def reproduction_workspace():
 return _pr_dir("patchloop-case")
def reproduction_outputs():
 return _pr_dir("patchloop-outputs")
def _pr_input(p,b):
 p=_pr_os.path.abspath(p)
 paths=[_pr_os.path.normcase(_pr_os.path.realpath(v)) for v in
        (p,_pr_os.path.join(_pr_st,"patchloop-outputs"))]
 try:
  overlap=_pr_os.path.commonpath(paths) in paths
 except ValueError:
  overlap=False
 if overlap:
  raise ValueError("input path overlaps reproduction_outputs")
 return _pr_ss(p,b)
def _pr_error(e):
 return {"type":type(e).__module__+"."+type(e).__qualname__,"message":str(e)[:256]}
'''
    # These replacements apply only to the fresh observer. Saved v1-v6 program
    # bytes retain their original directory, capture and recovery semantics.
    if source.count(old) != 1:
        raise ValueError("behavior observer workspace location is unavailable")
    source = source.replace(old, new, 1)
    source = source.replace('  target = _pr_rs()\n', '', 1)
    resolved = ('getattr(target, "__module__", "") + "." +\n'
                '        getattr(target, "__qualname__", "")')
    source = source.replace('"resolved_entrypoint": ' + resolved,
                            '"resolved_entrypoint": "", "target_started": False', 1)
    source = source.replace('  try:\n   b = [64, 1048576]',
                            '  try:\n   target = _pr_rs()\n'
                            '   row["resolved_entrypoint"] = (' + resolved + ')\n'
                            '   b = [64, 1048576]', 1)
    source = source.replace('_pr_ss(_pr_os.path.abspath(p), b)', '_pr_input(p,b)', 1)
    source = source.replace('  except (OSError, ValueError, TypeError):\n',
                            '  except BaseException as caught:\n'
                            '   row["exception"] = _pr_error(caught)\n', 1)
    source = source.replace('   value = target(*args, **kwargs)',
                            '   row["target_started"] = True\n'
                            '   value = target(*args, **kwargs)', 1)
    source = source.replace(
        '{"type": type(caught).__module__ + "." + type(caught).__qualname__,\n'
        '        "message": str(caught)[:256]}', '_pr_error(caught)', 1)
    # Keep the 8K allowance, including the maximum entrypoint and optional call
    # path hooks, by shortening fixed host symbols only. Never rewrite user code.
    names = {
        "_pr_os": "_o", "_pr_sys": "_s", "_pr_j": "_j",
        "_pr_im": "_im", "_pr_i": "_i", "_pr_h": "_h",
        "_pr_st": "_st", "_pr_dirs": "_ds", "_pr_dir": "_d",
        "_pr_input": "_in", "_pr_error": "_e", "_pr_obs": "_ob",
        "_pr_left": "_l", "_pr_Result": "_R", "_pr_ss": "_ss",
        "_pr_rs": "_rs", "_pr_v": "_v", "_pr_r": "_r",
        "_pr_m": "_m", "_pr_S": "_S",
    }
    source = re.sub(r"\b_pr_[A-Za-z]+\b", lambda match: names.get(match[0], match[0]), source)
    for old, new in ((" = ", "="), (", ", ","), (": ", ":"), (" + ", "+")):
        source = source.replace(old, new)
    # Keep the two fixed invocation lines available to the optional call-path
    # transform, which must set the phase after its own begin hook succeeds.
    return source.replace('   row["target_started"]=True',
                          '   row["target_started"] = True', 1).replace(
                              '   value=target(*args,**kwargs)',
                              '   value = target(*args, **kwargs)', 1)


def valid(call):
    capture = call.get("capture")
    error = call.get("exception")
    return (
        isinstance(call.get("call_id"), str)
        and call["call_id"] in {f"call-{i}" for i in range(1, 5)}
        and (call.get("bound_parameters") is None or isinstance(call["bound_parameters"], dict))
        and isinstance(call.get("exception_policy"), list)
        and len(call["exception_policy"]) <= 4
        and all(isinstance(item, str) for item in call["exception_policy"])
        and (error is None or isinstance(error, dict) and set(error) == {"type", "message"}
             and all(isinstance(value, str) for value in error.values()))
        and (call.get("exit_code") is None or type(call["exit_code"]) in (str, int))
        and isinstance(capture, dict)
        and set(capture) == {"scope", "status", "stdout", "stderr"}
        and capture["scope"] == "python-streams"
        and capture["status"] in {"complete", "incomplete", "truncated"}
        and all(isinstance(capture[key], str) for key in ("stdout", "stderr"))
        and sum(len(capture[key].encode("utf-8")) for key in ("stdout", "stderr")) <= CAPTURE_BYTES
    )


def incomplete(calls):
    """Known missing capture or unexpected exceptions never gain equality credit."""
    return (len({call["call_id"] for call in calls}) != len(calls)
            or sum(len(call["capture"][key].encode("utf-8"))
                   for call in calls for key in ("stdout", "stderr")) > CAPTURE_BYTES
            or any(call["capture"]["status"] != "complete"
                   or call["outcome"] == "incomplete"
                   or call["outcome"] == "raised" and (
                       not call["exception"]
                       or call["exception"]["type"] not in call["exception_policy"])
                   for call in calls))
