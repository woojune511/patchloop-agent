import builtins
import copy
import hashlib
import json

import pytest

from patchloop.sandbox.exception_frames import (
    MAX_EXCEPTIONS,
    MAX_FRAMES,
    MAX_FRAMES_PER_EXCEPTION,
    MAX_PACKET_BYTES,
    MAX_TRACEBACK_SCAN,
    ExceptionFrames,
    public,
)


def _load(path, source, **globals_):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    namespace = {"__name__": "public_fixture", **globals_}
    exec(compile(source, str(path), "exec"), namespace)
    return namespace


def _caught(callback):
    try:
        callback()
    except Exception as error:
        return error
    raise AssertionError("fixture did not fail")


def _digest(path):
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _simple(tmp_path, source="def fail():\n    raise RuntimeError('failure')\n"):
    root = tmp_path / "public"
    path = root / "target.py"
    namespace = _load(path, source)
    return ExceptionFrames({"workspace": root}), _caught(namespace["fail"]), path


def test_two_exception_chain_retains_all_eleven_public_frames(tmp_path):
    dependency = tmp_path / "dependency"
    report_path = dependency / "report.py"
    report = _load(
        report_path,
        "def r0(): return r1()\n"
        "def r1(): return r2()\n"
        "def r2(): return r3()\n"
        "def r3():\n"
        "    source_secret = 'not-a-diagnostic-field'\n"
        "    raise FileNotFoundError('report.md')\n",
    )
    workspace = tmp_path / "workspace"
    target_path = workspace / "target.py"
    target = _load(
        target_path,
        "def u0(): return u1()\n"
        "def u1(): return u2()\n"
        "def u2(): return u3()\n"
        "def u3(): return u4()\n"
        "def u4(): raise AttributeError('__enter__')\n"
        "def entry():\n"
        "    try: u0()\n"
        "    except Exception: report()\n",
        report=report["r0"],
    )
    error = _caught(target["entry"])
    before = (error.__traceback__, error.__context__, error.args)
    collector = ExceptionFrames(
        {"workspace": workspace, "dependency": dependency},
        {"report.py": _digest(report_path)},
    )
    packet = collector.capture(error)
    assert packet["status"] == "complete"
    escaped, context = packet["exceptions"]
    assert [row["relation"] for row in packet["exceptions"]] == ["escaped", "context"]
    assert [row["type"] for row in packet["exceptions"]] == [
        "builtins.FileNotFoundError", "builtins.AttributeError"
    ]
    assert [row["message"] for row in packet["exceptions"]] == ["report.md", "__enter__"]
    assert [len(escaped["frames"]), len(context["frames"])] == [5, 6]
    assert escaped["frames"][-1] == {
        "origin": "dependency", "path": "report.py", "function": "r3",
        "line": 6, "file_hash": _digest(report_path),
    }
    assert context["frames"][-1] == {
        "origin": "workspace", "path": "target.py", "function": "u4",
        "line": 5, "file_hash": _digest(target_path),
    }
    assert escaped["excluded_frame_count"] == 1
    assert len(_json(packet).encode("utf-8")) <= MAX_PACKET_BYTES
    assert "not-a-diagnostic-field" not in _json(packet)
    assert str(tmp_path) not in _json(packet)
    assert (error.__traceback__, error.__context__, error.args) == before
    detached = public(packet)
    assert detached == packet
    detached["exceptions"][0]["frames"].clear()
    assert len(packet["exceptions"][0]["frames"]) == 5


def test_effective_chain_prefers_cause_and_honors_suppressed_context(tmp_path):
    collector, error, _ = _simple(tmp_path)
    cause = ValueError("explicit cause")
    error.__context__ = KeyError("hidden context")
    error.__cause__ = cause
    packet = collector.capture(error)
    assert [row["relation"] for row in packet["exceptions"]] == ["escaped", "cause"]
    assert packet["exceptions"][1]["message"] == "explicit cause"
    assert "hidden context" not in _json(packet)
    error.__cause__ = None
    error.__suppress_context__ = True
    assert len(collector.capture(error)["exceptions"]) == 1


def test_chain_cycle_and_length_are_explicit(tmp_path):
    collector, error, _ = _simple(tmp_path)
    child = ValueError("child")
    error.__cause__ = child
    child.__cause__ = error
    cycle = collector.capture(error)
    assert cycle["status"] == "partial"
    assert cycle["omissions"] == {"chain_cycle": 1}
    assert len(cycle["exceptions"]) == 2
    cursor = error
    for index in range(MAX_EXCEPTIONS + 1):
        cursor.__cause__ = ValueError(index)
        cursor = cursor.__cause__
    limited = collector.capture(error)
    assert len(limited["exceptions"]) == MAX_EXCEPTIONS
    assert limited["omissions"] == {"chain_limit": 1}


def test_frame_limit_retains_innermost_failure_and_scan_limit_is_partial(tmp_path):
    collector, error, path = _simple(
        tmp_path,
        "def recur(n):\n"
        "    if n: return recur(n - 1)\n"
        "    raise RuntimeError('failure')\n"
        "def fail(): return recur(20)\n",
    )
    limited = collector.capture(error)
    frames = limited["exceptions"][0]["frames"]
    assert limited["status"] == "partial"
    assert len(frames) == MAX_FRAMES_PER_EXCEPTION
    assert frames[-1]["line"] == 3
    assert limited["omissions"] == {"frame_limit": 10}
    deep = _load(path, path.read_text(encoding="utf-8"))
    scanned = collector.capture(_caught(lambda: deep["recur"](MAX_TRACEBACK_SCAN + 1)))
    assert scanned["status"] == "partial"
    assert scanned["omissions"]["traceback_limit"] == 1
    assert sum(len(row["frames"]) for row in scanned["exceptions"]) <= MAX_FRAMES


def test_byte_and_message_limits_reduce_only_diagnostic_details(tmp_path):
    names = ["함" * 100 + str(index) for index in range(MAX_FRAMES_PER_EXCEPTION)]
    definitions = [f"def {name}(): return {names[index + 1]}()"
                   for index, name in enumerate(names[:-1])]
    definitions.extend([
        f"def {names[-1]}(): raise RuntimeError('긴' * 1000)",
        f"def fail(): return {names[0]}()",
    ])
    collector, error, _ = _simple(tmp_path, "\n".join(definitions) + "\n")
    packet = collector.capture(error)
    assert len(_json(packet).encode("utf-8")) <= MAX_PACKET_BYTES
    assert packet["status"] == "partial"
    assert packet["omissions"]["message_limit"] == 1
    assert packet["omissions"]["packet_byte_limit"] > 0
    assert error.args == ("긴" * 1000,)
    assert packet["exceptions"][0]["frames"][-1]["function"] == names[-1]


def test_long_frame_label_is_omitted_instead_of_silently_truncated(tmp_path):
    name = "f" * 129
    collector, error, _ = _simple(
        tmp_path, f"def {name}(): raise RuntimeError('failure')\ndef fail(): return {name}()\n"
    )
    packet = collector.capture(error)
    assert packet["status"] == "partial"
    assert packet["omissions"] == {"frame_text_limit": 1}
    assert [frame["function"] for frame in packet["exceptions"][0]["frames"]] == ["fail"]


def test_only_public_roots_and_exact_prepared_dependencies_are_exposed(tmp_path):
    outside = tmp_path / "private" / "secret_module.py"
    hidden = _load(outside, "def secret_function(): raise RuntimeError('failure')\n")
    collector = ExceptionFrames({"workspace": tmp_path / "public"})
    packet = collector.capture(_caught(hidden["secret_function"]))
    assert packet["status"] == "unavailable"
    assert packet["exceptions"][0]["frames"] == []
    assert packet["exceptions"][0]["excluded_frame_count"] == 2
    assert "secret_module" not in _json(packet)
    assert "secret_function" not in _json(packet)
    for manifest, reason in [({}, "dependency_not_prepared"),
                             ({"secret_module.py": "sha256:" + "0" * 64}, "source_hash_mismatch")]:
        bounded = ExceptionFrames({"dependency": outside.parent}, manifest)
        packet = bounded.capture(_caught(hidden["secret_function"]))
        assert packet["status"] == "unavailable"
        assert packet["omissions"] == {reason: 1}
        assert packet["exceptions"][0]["frames"] == []


def test_parent_traversal_cannot_turn_an_outside_file_into_a_public_frame(tmp_path):
    root = tmp_path / "public"
    root.mkdir()
    namespace = {}
    exec(compile("def fail(): raise RuntimeError('failure')\n",
                 str(root / ".." / "secret.py"), "exec"), namespace)
    packet = ExceptionFrames({"workspace": root}).capture(_caught(namespace["fail"]))
    assert packet["status"] == "unavailable"
    assert packet["omissions"] == {"unsafe_public_path": 1}
    assert "secret.py" not in _json(packet)


def test_capture_does_not_render_custom_exception_or_argument(tmp_path):
    calls = []

    class CustomError(Exception):
        def __str__(self):
            calls.append("str")
            raise AssertionError("must not render custom exception")

    class CustomArgument:
        def __repr__(self):
            calls.append("repr")
            raise AssertionError("must not render custom argument")

    root = tmp_path / "public"
    namespace = _load(root / "target.py", "def fail(): raise error\n",
                      error=CustomError(CustomArgument()))
    packet = ExceptionFrames({"workspace": root}).capture(_caught(namespace["fail"]))
    assert calls == []
    assert packet["status"] == "partial"
    assert packet["omissions"] == {"message_unavailable": 1}
    assert packet["exceptions"][0]["message"] is None
    assert packet["exceptions"][0]["message_source"] == "omitted"
    assert len(packet["exceptions"][0]["frames"]) == 1


@pytest.mark.skipif(not hasattr(builtins, "ExceptionGroup"), reason="Python without groups")
def test_exception_group_tree_is_explicitly_unsupported(tmp_path):
    collector, error, _ = _simple(
        tmp_path,
        "def fail():\n"
        "    raise ExceptionGroup('group', [ValueError('child-secret'), TypeError('nested')])\n",
    )
    packet = collector.capture(error)
    assert packet["status"] == "partial"
    assert packet["omissions"]["exception_group_unsupported"] == 2
    assert len(packet["exceptions"]) == 1
    assert "child-secret" not in _json(packet)
    assert packet["exceptions"][0]["frames"][-1]["line"] == 2


@pytest.mark.parametrize("path", ["/private.py", "C:/private.py", "../private.py", ".",
                                 "a/../b.py", "a//b.py", "a\\b.py"])
def test_public_reader_rejects_noncanonical_relative_paths(tmp_path, path):
    collector, error, _ = _simple(tmp_path)
    packet = collector.capture(error)
    packet["exceptions"][0]["frames"][0]["path"] = path
    assert public(packet)["omissions"] == {"invalid_packet": 1}


def test_public_reader_rejects_extra_fields_and_inconsistent_status_without_mutation(tmp_path):
    collector, error, _ = _simple(tmp_path)
    packet = collector.capture(error)
    packet["exceptions"][0]["frames"][0]["locals"] = {"secret": "never forward"}
    before = copy.deepcopy(packet)
    assert public(packet)["omissions"] == {"invalid_packet": 1}
    assert packet == before
    packet = collector.capture(error)
    packet["status"] = "partial"
    assert public(packet)["omissions"] == {"invalid_packet": 1}
    assert public(None)["omissions"] == {"not_available": 1}
    assert collector.capture(None)["omissions"] == {"not_exception": 1}
