"""One public caller, with bounded observational wrappers and an invalid child."""

import contextlib
import functools
import hashlib
import importlib
import io
import json
import os
import sys
from pathlib import Path

LAYOUT = "__LAYOUT__"
work = Path("/tmp/namespace-selection")
root = work / "inputs"
project = root / "src/project"
project.mkdir(parents=True)
(root / "src/__init__.py").write_text("", encoding="utf-8")
(project / "file.py").write_text("__CHILD_SOURCE__", encoding="utf-8")
if LAYOUT == "package":
    (project / "__init__.py").write_text("", encoding="utf-8")
for label in ("home", "cache"):
    (work / label).mkdir()
os.environ["HOME"] = str(work / "home")
os.environ["XDG_CACHE_HOME"] = str(work / "cache")
os.chdir(root)

from astroid import builder, modutils  # noqa: E402 -- HOME/cache precede caller imports.
from pylint.lint import Run  # noqa: E402

pylinter = importlib.import_module("pylint.lint.pylinter")
target = "src/project/file.py" if LAYOUT == "direct" else "src/project"
events = []
patches = []
search_paths = []
overflow = False
expanding = 0
stack = []


def clean(value):
    return str(value).replace(str(root), "<inputs>")


def inventory():
    result = []
    for path in sorted(root.rglob("*")):
        item = {
            "path": path.relative_to(root).as_posix(),
            "mode": path.stat().st_mode,
            "kind": "dir" if path.is_dir() else "file",
        }
        if path.is_file():
            item["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        result.append(item)
    return result


def path_id(paths):
    global overflow
    if paths is None:
        return None
    values = [clean(v) for v in paths]
    if len(values) > 24 or any(len(v) > 250 for v in values):
        overflow = True
    values = [v[:250] for v in values[:24]]
    if values in search_paths:
        return search_paths.index(values)
    if len(search_paths) >= 8:
        overflow = True
        return -1
    search_paths.append(values)
    return len(search_paths) - 1


def emit(value):
    global overflow
    if len(events) >= 48:
        overflow = True
    else:
        events.append(value)


def wrap(obj, name, label):
    original = getattr(obj, name)

    @functools.wraps(original)
    def observed(*args, **kwargs):
        global expanding
        is_expand = label == "expand"
        is_parse = label in {"get_ast", "file_build"}
        active = (
            is_expand
            or expanding > 0
            or (is_parse and os.path.abspath(str(args[1])).startswith(str(root) + os.sep))
        )
        if not active:
            return original(*args, **kwargs)
        if is_expand:
            expanding += 1
            inputs = {
                "targets": list(args[0]),
                "cwd": clean(os.getcwd()),
                "sys_path_id": path_id(sys.path),
            }
        elif is_parse:
            inputs = {
                "filepath": clean(args[1]),
                "modname": args[2] if len(args) > 2 else kwargs.get("modname"),
            }
        elif label == "module_files":
            inputs = {"directory": clean(args[0]), "list_all": kwargs.get("list_all", False)}
        elif label == "namespace":
            spec = args[0]
            inputs = {
                "type": str(spec.type),
                "location": clean(spec.location),
                "search_locations_id": path_id(spec.submodule_search_locations),
            }
        else:
            inputs = {
                "input": args[0] if isinstance(args[0], list) else clean(args[0]),
                "path_id": path_id(kwargs.get("path", args[1] if len(args) > 1 else None)),
            }
        row = {
            "id": len(events),
            "parent_id": stack[-1] if stack else None,
            "function": label,
            "input": inputs,
            "outcome": "entered",
        }
        emit(row)
        stack.append(row["id"])
        try:
            result = original(*args, **kwargs)
        except BaseException as error:
            row.update(outcome="raised", exception=type(error).__name__, message=clean(error)[:400])
            raise
        else:
            row["outcome"] = "returned"
            if is_expand:
                modules, errors = result
                row["selected"] = [
                    {"path": clean(m["path"]), "name": m["name"], "isarg": m["isarg"]}
                    for m in modules
                ]
                row["errors"] = [
                    {"key": e["key"], "mod": e["mod"], "error": clean(e["ex"])[:400]}
                    for e in errors
                ]
            elif label == "file_info":
                row["spec"] = {
                    "type": str(result.type),
                    "location": clean(result.location),
                    "search_locations_id": path_id(result.submodule_search_locations),
                }
            elif label == "namespace":
                row["is_namespace"] = bool(result)
            elif label == "module_files":
                row["files"] = [clean(v) for v in result]
            elif label == "modpath":
                row["modpath"] = list(result)
            else:
                row["returned_ast"] = result is not None
            return result
        finally:
            stack.pop()
            if is_expand:
                expanding -= 1

    patches.append((obj, name, original))
    setattr(obj, name, observed)


before = inventory()
wrap(pylinter, "expand_modules", "expand")
wrap(modutils, "modpath_from_file", "modpath")
wrap(modutils, "file_info_from_modpath", "file_info")
wrap(modutils, "is_namespace", "namespace")
wrap(modutils, "get_module_files", "module_files")
wrap(pylinter.PyLinter, "get_ast", "get_ast")
wrap(builder.AstroidBuilder, "file_build", "file_build")
stdout, stderr = io.StringIO(), io.StringIO()
outcome, exit_code, exception = "returned", None, None
sys.argv = ["<namespace-selection>", target]
try:
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            Run([target])
        except SystemExit as error:
            outcome, exit_code = "system_exit", error.code
        except BaseException as error:
            outcome = "raised"
            exception = {"type": type(error).__name__, "message": clean(error)[:500]}
finally:
    for obj, name, original in reversed(patches):
        setattr(obj, name, original)
after = inventory()
payload = {
    "layout": LAYOUT,
    "target": target,
    "events": events,
    "search_paths": search_paths,
    "overflow": overflow,
    "inputs_before": before,
    "inputs_after": after,
    "environment": {
        "cwd": clean(os.getcwd()),
        "HOME": os.environ["HOME"],
        "XDG_CACHE_HOME": os.environ["XDG_CACHE_HOME"],
    },
    "outcome": outcome,
    "exit_code": exit_code,
    "exception": exception,
    "stdout": stdout.getvalue(),
    "stderr": stderr.getvalue(),
}
encoded = json.dumps(payload, sort_keys=True)
assert len(encoded.encode()) < 11000, "bounded observation overflow"
print("SELECTION_DIAGNOSTIC=" + encoded)
