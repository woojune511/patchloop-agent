"""Small synthetic controls for selected-call/focus isolation and bounded observations."""

import copy
import io
import json
import subprocess
import sys
import types

import pytest

from patchloop.dev import probe_invocation, reproduction
from patchloop.errors import ContractError
from patchloop.sandbox import call_path_trace as trace
from patchloop.sandbox import probes
from patchloop.sandbox.execution_feedback import make_request
from patchloop.sandbox.line_trace import LineTrace
from patchloop.sandbox.probes import _OutputCollector
from patchloop.util import sha256_bytes

CALLER = """def focus(mode, paths):
    if mode:
        return helper(paths)
    return 'skip'
def run(mode):
    helper(['initialization'])
    return focus(mode, ['src/project'])
"""
HELPER = """def helper(paths):
    selected = paths[0]
    if selected == 'raise':
        raise ValueError('failure')
    return selected
"""


def fixture(tmp_path, *, scope=None, candidate_focus=False):
    workspace, dependency = tmp_path / "workspace", tmp_path / "dependency"
    workspace.mkdir()
    dependency.mkdir()
    (workspace / "helper.py").write_bytes(HELPER.encode())
    (dependency / "caller.py").write_bytes(CALLER.encode())
    request = {"call_id": "call-1", "focus": {
        "origin": "dependency", "path": "caller.py", "function": "focus"},
        "watches": [{"origin": "workspace", "path": "helper.py", "function": "helper",
                     "lines": [2, 4, 5], "fields": ["paths", "selected"]}]}
    if scope is not None:
        request["scope"] = scope
    if candidate_focus:
        request["focus"] = {key: request["watches"][0][key]
                            for key in ("origin", "path", "function")}
    bound = trace.bind_request(request, workspace, dependency_root=dependency,
                               dependency_files={"caller.py": sha256_bytes(CALLER.encode())},
                               snapshot_hash="snapshot", execution_identity_hash="execution")
    namespace = {"__name__": "call_path_fixture"}
    exec(compile(HELPER, str(workspace / "helper.py"), "exec"), namespace)
    exec(compile(CALLER, str(dependency / "caller.py"), "exec"), namespace)
    return bound, namespace, {"workspace": workspace, "dependency": dependency}


def collector(bound, roots, **kwargs):
    value = trace.CallPathTrace(bound, roots, **kwargs)
    value.write = lambda *_: None
    return value


def test_focus_separates_initialization_and_control_from_failing_call(tmp_path):
    bound, ns, roots = fixture(tmp_path)
    value = collector(bound, roots)
    value.begin("call-1")
    assert ns["run"](False) == "skip"
    value.end("call-1")
    value.begin("call-2")
    ns["run"](True)
    value.end("call-2")
    feedback = trace.public_feedback(bound, value.finish())
    assert feedback["status"] == "complete"
    assert feedback["focus"]["entries"] == 1
    assert feedback["focus"]["events"][0]["values"] == {
        "mode": False, "paths": ["src/project"]}
    assert feedback["focus"]["events"][-1]["value"] == "skip"
    assert feedback["watches"][0]["entries"] == 0
    assert feedback["watches"][0]["not_observed_lines"] == [2, 4, 5]


@pytest.mark.parametrize("scope", [None, "selected_call"])
def test_nested_values_parent_line_return_and_exception(tmp_path, scope):
    bound, ns, roots = fixture(tmp_path, scope=scope)
    value = collector(bound, roots)
    value.begin("call-1")
    with pytest.raises(ValueError, match="failure"):
        ns["focus"](True, ["raise"])
    value.end("call-1")
    feedback = trace.public_feedback(bound, value.finish())
    assert feedback["status"] == "complete"
    watched = feedback["watches"][0]
    assert watched["entries"] == 1
    assert watched["observed_lines"] == [2, 4]
    assert watched["events"][0]["parent_index"] == 0
    assert any(event.get("exception_type") == "ValueError" for event in watched["events"])
    assert any(event["values"].get("selected") == "raise" for event in watched["events"])


@pytest.mark.parametrize("scope", [None, "selected_call"])
@pytest.mark.parametrize("completed", [False, True])
def test_candidate_no_hit_requires_complete_selected_call_window(tmp_path, scope, completed):
    bound, ns, roots = fixture(tmp_path, scope=scope, candidate_focus=True)
    value = collector(bound, roots)
    ns["helper"](["before"])
    value.begin("call-2")
    ns["helper"](["other call"])
    value.end("call-2")
    value.begin("call-1")
    assert ns["focus"](False, ["src/project"]) == "skip"
    if completed:
        value.end("call-1")
        ns["helper"](["after"])
    report = value.finish()
    feedback = trace.public_feedback(bound, report)
    complete = scope == "selected_call" and completed
    assert feedback["status"] == ("complete" if complete else "unknown")
    assert feedback["reason"] == (None if complete else
                                  "focus_not_observed" if completed else "call_incomplete")
    assert feedback["focus"]["entries"] == feedback["watches"][0]["entries"] == 0
    assert feedback["watches"][0]["not_observed_lines"] == ([2, 4, 5] if complete else None)
    assert feedback["watches"][0]["observation"] == ("not_observed" if complete else "unknown")
    if scope is None:
        assert "scope" not in bound and "scope" not in report
        assert feedback["scope"] == "selected_call_focus_launch_thread"
    else:
        assert bound["scope"] == report["scope"] == "selected_call"
        assert feedback["scope"] == "selected_call_launch_thread"


def test_selected_call_captures_watches_before_focus_and_nested_entry_exit(tmp_path):
    bound, ns, roots = fixture(tmp_path, scope="selected_call")
    value = collector(bound, roots)
    value.begin("call-1")
    assert ns["run"](True) == "src/project"
    value.end("call-1")
    value.begin("call-2")
    ns["run"](True)
    value.end("call-2")
    feedback = trace.public_feedback(bound, value.finish())
    assert feedback["status"] == "complete"
    events = feedback["watches"][0]["events"]
    assert feedback["watches"][0]["entries"] == 2
    entries = [item for item in events if item["event"] == "call"]
    exits = [item for item in events if item["event"] == "return"]
    assert [item["values"]["paths"] for item in entries] == [
        ["initialization"], ["src/project"]]
    assert [item["parent_index"] for item in entries] == [None, 0]
    assert [item["values"]["selected"] for item in exits] == ["initialization", "src/project"]
    assert [item["value"] for item in exits] == ["initialization", "src/project"]


def test_selected_call_bounds_observations_without_changing_values(tmp_path):
    bound, ns, roots = fixture(tmp_path, scope="selected_call")
    value = collector(bound, roots)
    paths = ["x" * 400] * 12
    value.begin("call-1")
    assert ns["focus"](True, paths) == "x" * 400
    value.end("call-1")
    feedback = trace.public_feedback(bound, value.finish())
    assert feedback["status"] == "complete" and paths == ["x" * 400] * 12
    events = feedback["watches"][0]["events"]
    assert events[0]["values"]["paths"] == ["x" * 128 + "..."] * 8 + ["<remaining-items>"]
    assert events[-1]["value"] == "x" * 128 + "..."


@pytest.mark.parametrize("failure", ["missing_call", "drift", "limit", "trace_limit", "tamper"])
def test_selected_call_gaps_and_bounds_stay_unknown(tmp_path, monkeypatch, failure):
    bound, ns, roots = fixture(tmp_path, scope="selected_call", candidate_focus=True)
    value = collector(bound, roots)
    if failure != "missing_call":
        value.begin("call-1")
        if failure == "limit":
            monkeypatch.setattr(trace, "MAX_EVENTS", 1)
            ns["helper"](["src/project"])
        else:
            if failure == "trace_limit":
                monkeypatch.setattr(trace, "MAX_TRACE_EVENTS", 1)
            ns["focus"](False, ["src/project"])
        if failure == "tamper":
            saved = sys.gettrace()
            sys.settrace(None)
            sys.settrace(saved)
        value.end("call-1")
    if failure == "drift":
        (roots["workspace"] / "helper.py").write_text(HELPER + "# changed\n")
    feedback = trace.public_feedback(bound, value.finish())
    assert feedback["status"] == "unknown"
    assert feedback["watches"][0]["observation"] == "unknown"
    assert feedback["watches"][0]["not_observed_lines"] is None


def test_selected_call_scope_is_host_only_and_bound_to_report(tmp_path):
    bound, ns, roots = fixture(tmp_path, scope="selected_call")
    assert "scope" not in trace.schema()["properties"]
    assert "scope" not in trace.selection_schema()["properties"]
    raw = {"call_id": bound["call_id"], "scope": "selected_call",
           "focus": {key: bound["focus"][key] for key in ("origin", "path", "function")},
           "watches": [{key: bound["watches"][0][key]
                        for key in ("origin", "path", "function", "lines", "fields")}]}
    assert trace.validate_request(raw) == raw
    for invalid in (None, False, "focus", "all_calls", []):
        with pytest.raises(ValueError, match="request"):
            trace.validate_request({**raw, "scope": invalid})
    value = collector(bound, roots)
    value.begin("call-1")
    ns["focus"](False, [])
    value.end("call-1")
    report = value.finish()
    for key, replacement in (("scope", None), ("scope", "focus"),
                             ("request_hash", "sha256:" + "0" * 64)):
        bad = {**report, key: replacement}
        assert trace.public_feedback(bound, bad)["reason"] == "invalid_report"
    del report["scope"]
    assert trace.public_feedback(bound, report)["status"] == "unknown"


@pytest.mark.parametrize("failure", [
    "missing_call", "missing_focus", "tamper", "drift", "limit", "trace_limit",
])
def test_unknown_never_claims_not_observed(tmp_path, monkeypatch, failure):
    bound, ns, roots = fixture(tmp_path)
    value = collector(bound, roots)
    if failure != "missing_call":
        value.begin("call-1")
        if failure == "limit":
            monkeypatch.setattr(trace, "MAX_EVENTS", 1)
        if failure == "trace_limit":
            monkeypatch.setattr(trace, "MAX_TRACE_EVENTS", 1)
        if failure != "missing_focus":
            ns["focus"](True, ["src/project"])
        if failure == "tamper":
            saved = sys.gettrace()
            sys.settrace(None)
            sys.settrace(saved)  # Even a restored tracer must report the observation gap.
        value.end("call-1")
    if failure == "drift":
        (roots["workspace"] / "helper.py").write_text(HELPER + "# changed\n")
    feedback = trace.public_feedback(bound, value.finish())
    assert feedback["status"] == "unknown"
    assert feedback["watches"][0]["not_observed_lines"] is None
    assert feedback["watches"][0]["observation"] == "unknown"


def test_composes_with_trusted_changed_line_collector(tmp_path):
    bound, ns, roots = fixture(tmp_path)
    line_request = make_request("diff", [{"path": "helper.py",
        "file_hash": sha256_bytes(HELPER.encode()), "changed_lines": [2, 4, 5]}],
        execution_identity=None, omitted_file_count=0, deleted_line_count=0)
    lines = LineTrace(line_request, str(roots["workspace"]))
    emitted = []
    lines.write = lambda _fd, data: emitted.append(data)
    value = collector(bound, roots, line_trace=lines)
    lines.start()
    try:
        value.begin("call-1")
        ns["run"](False)
        value.end("call-1")
        assert sys.gettrace() is lines.trace
        feedback = trace.public_feedback(bound, value.finish())
    finally:
        lines.finish()
    assert feedback["status"] == "complete"
    assert feedback["watches"][0]["entries"] == 0
    report = json.loads(emitted[0][emitted[0].index(b"{"):])
    assert report["files"][0]["executed"] == [2, 5]


def test_initialization_events_do_not_spend_focus_allowance(tmp_path, monkeypatch):
    bound, ns, roots = fixture(tmp_path)
    line_request = make_request("diff", [{"path": "helper.py",
        "file_hash": sha256_bytes(HELPER.encode()), "changed_lines": [2, 4, 5]}],
        execution_identity=None, omitted_file_count=0, deleted_line_count=0)
    lines = LineTrace(line_request, str(roots["workspace"]))
    lines.write = lambda *_: None
    value = collector(bound, roots, line_trace=lines)
    monkeypatch.setattr(trace, "MAX_TRACE_EVENTS", 8)
    lines.start()
    try:
        value.begin("call-1")
        for _ in range(32):
            ns["helper"](["initialization"])
        assert value.trace_events == 0
        assert ns["focus"](False, []) == "skip"
        value.end("call-1")
        feedback = trace.public_feedback(bound, value.finish())
    finally:
        lines.finish()
    assert feedback["status"] == "complete"
    assert 0 < value.trace_events <= 8
    assert feedback["focus"]["entries"] == 1
    assert feedback["watches"][0]["entries"] == 0


def test_binding_rejects_private_unprepared_and_outside_function(tmp_path):
    bound, _, roots = fixture(tmp_path)
    raw = {"call_id": bound["call_id"],
           "focus": {key: bound["focus"][key] for key in ("origin", "path", "function")},
           "watches": [{key: bound["watches"][0][key]
                        for key in ("origin", "path", "function", "lines", "fields")}]}
    for path in ("../helper.py", "/helper.py", ".env/helper.py", "a\\helper.py"):
        invalid = copy.deepcopy(raw)
        invalid["watches"][0]["path"] = path
        with pytest.raises(ValueError):
            trace.validate_request(invalid)
    with pytest.raises(ValueError, match="allowlist"):
        trace.bind_request(raw, roots["workspace"], dependency_root=roots["dependency"])
    raw["watches"][0]["lines"] = [6]
    with pytest.raises(ValueError, match="outside"):
        trace.bind_request(raw, roots["workspace"], dependency_root=roots["dependency"],
                           dependency_files={"caller.py": sha256_bytes(CALLER.encode())})


def test_source_preflight_rejects_bad_targets_without_export_or_execution(tmp_path, monkeypatch):
    _, _, roots = fixture(tmp_path)
    workspace = roots["workspace"]
    subprocess.run(["git", "init", str(workspace)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(workspace), "add", "helper.py"],
                   check=True, capture_output=True)
    sandbox = probes.DockerProbeSandbox()
    monkeypatch.setattr(probes, "_snapshot", lambda *_a, **_k: pytest.fail("exported snapshot"))
    monkeypatch.setattr(sandbox, "run_probe", lambda *_a, **_k: pytest.fail("executed probe"))
    raw = {"call_id": "call-1", "focus": {
        "origin": "workspace", "path": "helper.py", "function": "helper"},
        "watches": [{"origin": "workspace", "path": "helper.py", "function": "helper",
                     "lines": [2], "fields": ["paths"]}]}
    for edit in ({"function": "not_present"}, {"lines": [30]}, {"path": "untracked.py"}):
        (workspace / "untracked.py").write_bytes(HELPER.encode())
        rejected = copy.deepcopy(raw)
        rejected["watches"][0].update(edit)
        with pytest.raises(ContractError, match="source request"):
            sandbox.validate_call_path(workspace, rejected)
    # A valid correction is still statically admitted; no launch has occurred.
    accepted = sandbox.validate_call_path(workspace, raw)
    assert accepted["focus"]["file_hash"] == sha256_bytes(HELPER.encode())


def test_source_preflight_binds_only_prepared_dependency_members(tmp_path, monkeypatch):
    _, _, roots = fixture(tmp_path)
    sandbox = probes.DockerProbeSandbox()
    identity = types.SimpleNamespace(source_roots=[])
    site_packages = tmp_path / "site-packages"
    site_packages.mkdir()
    (site_packages / "caller.py").write_bytes(CALLER.encode())
    sandbox.dependencies = types.SimpleNamespace(path=tmp_path / "manifest.json", identity=identity)
    descriptor = {"files": {"caller.py": sha256_bytes(CALLER.encode())}}
    monkeypatch.setattr(probes, "read_descriptor", lambda _path: (descriptor, identity))
    raw = {"call_id": "call-1", "focus": {
        "origin": "dependency", "path": "caller.py", "function": "focus"},
        "watches": [{"origin": "dependency", "path": "caller.py", "function": "run",
                     "lines": [6], "fields": ["mode"]}]}
    assert sandbox.validate_call_path(roots["workspace"], raw)["focus"]["file_hash"] == (
        sha256_bytes(CALLER.encode()))
    descriptor["files"] = {}
    with pytest.raises(ContractError, match="allowlist"):
        sandbox.validate_call_path(roots["workspace"], raw)


def test_report_frames_do_not_pollute_public_streams_and_foreign_data_is_unknown(tmp_path):
    bound, ns, roots = fixture(tmp_path)
    value = collector(bound, roots)
    value.begin("call-1")
    ns["focus"](False, [])
    value.end("call-1")
    report = value.finish()
    framing = trace.marker(bound) + json.dumps(report).encode() + b"\n"
    output = _OutputCollector()
    output.enable_call_path(bound)
    output.drain(io.BytesIO(b"original diagnostic\n" + framing), "stderr")
    assert output.public_text() == ("", "original diagnostic\n")
    assert output.call_path_report == report
    report["rows"][0]["events"][0]["values"]["unrequested"] = "bad"
    assert trace.public_feedback(bound, report)["status"] == "unknown"
    duplicate = _OutputCollector()
    duplicate.enable_call_path(bound)
    duplicate.drain(io.BytesIO(framing + framing), "stderr")
    assert duplicate.call_path_report is None


@pytest.mark.parametrize("channel", [probe_invocation.CAPTURE_CHANNEL, probe_invocation.CHANNEL])
def test_optional_observer_keeps_default_bytes_and_original_capture(tmp_path, monkeypatch, channel):
    monkeypatch.setattr(sys, "argv", sys.argv.copy())
    bound, ns, roots = fixture(tmp_path)
    module = types.ModuleType("call_path_fixture")
    module.run = ns["run"]
    monkeypatch.setitem(sys.modules, "call_path_fixture", module)
    binding = {"case_id": "sha256:" + "c" * 64,
               "definition": {"entrypoint": "call_path_fixture.run",
                              "observation_channel": channel}}
    source = "result = observed_target()(False)\nrecord_observation(result.value)"
    plain = reproduction.program(source, binding)
    assert plain == reproduction.program(source, binding, call_path=False)
    wrapped = reproduction.program(source, binding, call_path=True)
    assert wrapped != plain
    value = collector(bound, roots)
    namespace = {"_patchloop_call_path_begin": value.begin,
                 "_patchloop_call_path_end": value.end}
    exec(wrapped, namespace)
    assert namespace["result"].stdout == namespace["result"].stderr == ""
    assert namespace["result"].value == "skip"
    assert trace.public_feedback(bound, value.finish())["status"] == "complete"
    binding["definition"]["observation_channel"] = probe_invocation.LEGACY_CHANNEL
    with pytest.raises(ContractError, match="captured"):
        reproduction.program(source, binding, call_path=True)
