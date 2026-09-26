from __future__ import annotations

import copy
import json
import shutil

import pytest
import yaml

from diagnostics import declaration_context as diagnostic
from diagnostics.segmented_input_audit import verify_turn
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev import runner
from patchloop.dev.context import source_lines
from patchloop.dev.contracts import DevModelTurn, DevRunRequest, PublicTurnDecision, RequestedTool
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway
from patchloop.errors import ContractError
from patchloop.git_execution import run_git
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root
from patchloop.util import directory_hash, sha256_bytes, sha256_json

EXPERIMENT = "sha256:" + "b" * 64
FIELD_SOURCE = '''buffer_mode: str = "ordinary"
"""Choose how values are represented.

This setting concerns a representation.
Its spelling alone supplies no capability.
Existing callers may choose the same value.
Documentation is source, not a test result.
DECLARATION_TAIL
"""
'''


def raw_result(text, query="buffer_mode", path="settings.py"):
    lines = source_lines(text)
    spans = [DevToolGateway._span(path, max(1, n - 2), min(len(lines), n + 2),
                                 "\n".join(lines[max(0, n - 3):n + 2]),
                                 sha256_bytes(text.encode()))
             for n, line in enumerate(lines, 1) if query in line][:20]
    return {"query": query, "path_glob": "**/*.py", "searched_file_count": 1,
            "spans": spans, "truncated": False}


@pytest.mark.parametrize("wrapper,newline", [("module", "\n"), ("class", "\r\n"),
                                            ("nested-class", "\n")])
def test_complete_literal_documentation_preserves_original_lines(wrapper, newline):
    source = FIELD_SOURCE
    if wrapper != "module":
        source = "class Options:\n" + "\n".join("    " + s for s in source.splitlines())
    if wrapper == "nested-class":
        source = "class Outer:\n" + "\n".join("    " + s for s in source.splitlines())
    source = source.replace("\n", newline)
    original = raw_result(source)
    before = copy.deepcopy(original)
    expanded, receipt = diagnostic.expand_search_result(original, lambda _: source.encode())
    assert original == before and receipt["changes"]
    assert "DECLARATION_TAIL" in expanded["spans"][0]["content"]
    assert len(expanded["spans"]) == len(original["spans"])
    assert {k: v for k, v in expanded.items() if k != "spans"} == {
        k: v for k, v in original.items() if k != "spans"}
    for old, new in zip(original["spans"], expanded["spans"], strict=True):
        assert new["start_line"] <= old["start_line"] <= old["end_line"] <= new["end_line"]
        assert old["content"] in new["content"]
        assert new["file_hash"] == old["file_hash"]
    assert receipt["expanded_output_hash"] == sha256_json(expanded)


@pytest.mark.parametrize("source", [
    'buffer_mode = (\n    "ordinary"\n)\n"""first\nsecond\nthird\ntail\n"""\n',
    'buffer_mode: str\n# Comment between declaration and documentation.\n' +
    '"""first\nsecond\nthird\ntail\n"""\n',
    'buffer_mode = alias = 1\n"""first\nsecond\nthird\ntail\n"""\n',
])
def test_multiline_and_annotated_declarations(source):
    expanded, receipt = diagnostic.expand_search_result(
        raw_result(source), lambda _: source.encode())
    assert receipt["changes"] and "tail" in expanded["spans"][0]["content"]


@pytest.mark.parametrize("source,path", [
    ("def f():\n" + "\n".join("    " + x for x in FIELD_SOURCE.splitlines()), "settings.py"),
    ('other = buffer_mode\n"""not the queried declaration"""\n', "settings.py"),
    ('other = "buffer_mode"\n"""not the queried declaration"""\n', "settings.py"),
    ('buffer_mode = 1\nother = 2\n"""belongs to other"""\n', "settings.py"),
    ('buffer_mode = 1\nf"not literal {buffer_mode}"\n', "settings.py"),
    ('buffer_mode, other = 1, 2\n"""unsupported unpacking"""\n', "settings.py"),
    ('buffer_mode =\n"""invalid Python"""\n', "settings.py"),
    (FIELD_SOURCE, "settings.txt"),
])
def test_unsupported_source_keeps_the_search_result(source, path):
    original = raw_result(source, path=path)
    expanded, receipt = diagnostic.expand_search_result(original, lambda _: source.encode())
    assert expanded == original and not receipt["changes"]


def test_whole_block_limits_keep_every_original_hit():
    long = 'buffer_mode = 1\n"""\n' + "line\n" * 41 + '"""\n'
    original = raw_result(long)
    expanded, receipt = diagnostic.expand_search_result(original, lambda _: long.encode())
    assert expanded == original and receipt["omitted"]
    original = raw_result(FIELD_SOURCE)
    large = "x" * (24_000 - len(original["spans"][0]["content"]))
    original["spans"].append(DevToolGateway._span("other.txt", 1, 1, large, "opaque"))
    expanded, receipt = diagnostic.expand_search_result(original, lambda _: FIELD_SOURCE.encode())
    assert expanded == original and receipt["omitted"]


def test_multiple_hits_expand_a_declaration_only_once():
    source = FIELD_SOURCE.replace("a representation", "buffer_mode representation")
    original = raw_result(source)
    expanded, receipt = diagnostic.expand_search_result(original, lambda _: source.encode())
    assert len(receipt["changes"]) == 1
    assert len(expanded["spans"]) == len(original["spans"])


@pytest.mark.parametrize("fault", ["source", "content", "range", "size"])
def test_inconsistent_source_fails_closed(fault):
    original = raw_result(FIELD_SOURCE)
    source = FIELD_SOURCE.encode()
    if fault == "source":
        source += b"# changed\n"
    elif fault == "content":
        original["spans"][0]["content"] = "invented"
    elif fault == "range":
        original["spans"][0]["start_line"] = 0
    else:
        source = b"x" * 1_000_001
    with pytest.raises(ContractError):
        diagnostic.expand_search_result(original, lambda _: source)


def search_call(action_id="search", query="buffer_mode", path="mini_data_utils/settings.py"):
    return RequestedTool(name="search_files", action_id=action_id,
                         arguments={"query": query, "path_glob": path},
                         turn_decision=PublicTurnDecision(
                             mode="inspect", basis="Inspect settings.",
                             evidence_goal="Read the declared meaning."))


def test_expansion_replay_cache_and_mutation_evidence(gateway_factory):
    original, journal, workspace = gateway_factory()
    path = workspace / "mini_data_utils/settings.py"
    path.write_text(FIELD_SOURCE, encoding="utf-8")
    run_git(workspace, "add", "--", "mini_data_utils/settings.py")
    run_git(workspace, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "-qm", "synthetic setting")
    cls = diagnostic.gateway_type(experiment_hash=EXPERIMENT)
    kwargs = dict(workspace=workspace, journal=journal, public_task=original.public_task,
                  sandbox=original.sandbox, limits=original.limits)
    gateway = cls(**kwargs)
    result = gateway.execute(search_call())
    assert result.status == "succeeded"
    assert "DECLARATION_TAIL" in result.output["spans"][0]["content"]
    assert result.output["evidence_gain"]["new_covered_line_count"] == 9
    journal.append("tool_batch_finished", {"turn_id": "first", "action_ids": ["search"]})
    restored = cls(**kwargs)
    replay = restored.execute(search_call())
    assert replay.replayed and replay.output == result.output
    cached = restored.execute(search_call("cached"))
    assert cached.evidence_cache_hit and "DECLARATION_TAIL" in cached.output["spans"][0]["content"]
    second = restored.execute(search_call("later", query="mode"))
    assert "DECLARATION_TAIL" not in second.output["spans"][0]["content"]
    mutation = RequestedTool(name="replace_text", action_id="edit-expanded-source", arguments={
        "path": "mini_data_utils/settings.py", "old_text": "DECLARATION_TAIL",
        "new_text": "UPDATED_TAIL", "occurrence": 1, "hypothesis": "Update public documentation.",
        "expected_behavior": "Documentation changes on the observed source.",
        "causal_revision": None,
    }, turn_decision=PublicTurnDecision(mode="mutate", basis="Use the observed exact line."))
    assert restored.execute(mutation).status == "succeeded"
    with pytest.raises(ContractError, match="identity"):
        diagnostic.gateway_type(experiment_hash="sha256:" + "c" * 64)(**kwargs)


def test_public_boundary_and_private_hidden_hit_are_preserved(gateway_factory):
    original, journal, workspace = gateway_factory()
    hidden = workspace / ".patchloop-hidden/settings.py"
    hidden.parent.mkdir()
    hidden.write_text(FIELD_SOURCE, encoding="utf-8")
    run_git(workspace, "add", "--", ".patchloop-hidden/settings.py")
    gateway = diagnostic.gateway_type(experiment_hash=EXPERIMENT)(
        workspace=workspace, journal=journal, public_task=original.public_task,
        sandbox=original.sandbox, limits=original.limits)
    assert gateway.execute(search_call(path="**/*.py")).output["spans"] == []
    with pytest.raises(ContractError):
        gateway._tracked_path(".patchloop-hidden/settings.py")


@pytest.mark.parametrize("fault", ["policy", "repeat", "resume", "root", "hash"])
def test_invalid_run_admission_precedes_runner(tmp_path, monkeypatch, fault):
    request = DevRunRequest(provider="mock", model="mock", state_root=tmp_path / "run",
                            task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml")
    kwargs = {"policy": diagnostic.POLICY, "experiment_hash": EXPERIMENT}
    if fault == "policy":
        kwargs["policy"] = "unknown"
    elif fault == "repeat":
        request = request.model_copy(update={"repeat": 2})
    elif fault == "resume":
        request = request.model_copy(update={"resume_run_id": "run_dev_saved"})
    elif fault == "root":
        request.state_root.mkdir()
    else:
        kwargs["experiment_hash"] = "bad"
    monkeypatch.setattr(runner, "run_dev", lambda _: pytest.fail("must not enter runner"))
    with pytest.raises(ContractError):
        diagnostic.run(request, **kwargs)


def test_omission_uses_the_exact_existing_runner(monkeypatch):
    request = object()
    monkeypatch.setattr(runner, "run_dev", lambda value: (value, runner.DevToolGateway))
    assert diagnostic.run(request) == (request, DevToolGateway)


def test_scoped_gateway_is_restored_when_the_runner_raises(tmp_path, monkeypatch):
    request = DevRunRequest(provider="mock", model="mock", state_root=tmp_path / "run",
                            task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml")

    def fail(_):
        assert runner.DevToolGateway is not DevToolGateway
        raise RuntimeError("interrupted before provider execution")

    monkeypatch.setattr(runner, "run_dev", fail)
    with pytest.raises(RuntimeError, match="interrupted"):
        diagnostic.run(request, policy=diagnostic.POLICY, experiment_hash=EXPERIMENT)
    assert runner.DevToolGateway is DevToolGateway


@pytest.mark.parametrize("context_policy", ["append-v1", "segmented-v1"])
def test_mock_search_edit_check_submit_evaluation_and_actual_inputs(tmp_path, monkeypatch,
                                                                  context_policy):
    fixtures = tmp_path / "fixtures"
    snapshot = fixtures / "mini-data-utils"
    shutil.copytree(repository_root() / "fixtures/repositories/mini-data-utils", snapshot)
    target = snapshot / "mini_data_utils/csvlite.py"
    target.write_bytes(FIELD_SOURCE.encode() + b"\n" + target.read_bytes())
    task = tmp_path / "task"
    shutil.copytree(repository_root() / "tasks/smoke/csv-quoted-newline", task)
    public = yaml.safe_load((task / "public.yaml").read_text(encoding="utf-8"))
    public["repository"]["base_commit"] = directory_hash(snapshot)
    (task / "public.yaml").write_text(yaml.safe_dump(public), encoding="utf-8")
    original_init = WorkspaceManager.__init__

    def fixture_init(self, fixture_root, workspace_root, **kwargs):
        original_init(self, fixtures, workspace_root, **kwargs)

    monkeypatch.setattr(WorkspaceManager, "__init__", fixture_init)
    monkeypatch.setattr("socket.socket.connect", lambda *_: pytest.fail("network forbidden"))

    states, schemas, native = {}, {}, {}

    class SearchMock(MockDevAdapter):
        step = 0

        def _next_action(self, context, tools):
            schemas[arm].append(copy.deepcopy(tools))
            self.step += 1
            if self.step == 1:
                # Read the parser independently in the same ordinary read batch.
                # That range excludes the synthetic declaration, so A still lacks its tail.
                return DevModelTurn(tool_calls=[
                    search_call(path="mini_data_utils/csvlite.py"),
                    RequestedTool(name="read_file", action_id="read-parser", arguments={
                        "path": self.mutation.path,
                        "start_line": len(source_lines(FIELD_SOURCE)) + 2, "end_line": 80,
                    }, turn_decision=PublicTurnDecision(
                        mode="inspect", basis="Inspect the parser.",
                        evidence_goal="Obtain the exact parser replacement anchor.",
                    )),
                ])
            return super()._next_action(context, tools)

    monkeypatch.setattr(runner, "MockDevAdapter", SearchMock)
    for arm, policy in [("A", "none"), ("B", diagnostic.POLICY)]:
        schemas[arm] = []
        root = tmp_path / arm
        request = DevRunRequest(provider="mock", model="mock", state_root=root,
                                task=task / "public.yaml", context_policy=context_policy,
                                planning_policy="brief-v1", repair_recheck=True)
        result = diagnostic.run(request, policy=policy, experiment_hash=EXPERIMENT)["runs"][0]
        assert result["terminal"] == "EVALUATOR_PASS", result
        assert runner.DevToolGateway is DevToolGateway
        journal = DevJournal(root, result["run_id"])
        events, store = journal.events(), ArtifactStore(root / "artifacts")
        states[arm], native[arm] = [], []
        for event in events:
            if event["event_type"] != "turn_started":
                continue
            items = json.loads(store.read_bytes(Artifact.model_validate(
                event["payload"]["model_input_artifact"])))
            state = reconstruct_state(items, context_policy=context_policy)
            states[arm].append(state)
            native[arm].append(items)
            if context_policy == "segmented-v1":
                assert verify_turn(event, events, store, actual_input=items)["verified"]
        assert len(states[arm]) == 4
        assert states[arm][-1]["current_diff"]["patch"]
        assert states[arm][-1]["visible_check_status"][0]["status"] == "PASS"
        assert all(state["public_task"] == states[arm][0]["public_task"] for state in states[arm])
        assert sum(e["event_type"] == diagnostic.EVENT for e in events) == (arm == "B")
        assert any(e["event_type"] == "evaluator_finished" for e in events)
    assert schemas["A"] == schemas["B"]
    initial = []
    for arm in ("A", "B"):
        state = copy.deepcopy(states[arm][0])
        state["remaining_budget"].pop("active_wall_time_seconds")
        if "segment_handoff" in state:
            state["segment_handoff"].pop("segment_id")
        initial.append(state)
    assert initial[0] == initial[1]
    assert states["A"][1]["working_plan"]["plan"]["text"] == (
        states["B"][1]["working_plan"]["plan"]["text"])
    assert native["A"][0][0] == native["B"][0][0]
    a = json.dumps(native["A"][1])
    b = json.dumps(native["B"][1])
    # Inspect actual native delivery, including source bodies behind current-state references.
    assert "DECLARATION_TAIL" not in a and "DECLARATION_TAIL" in b
