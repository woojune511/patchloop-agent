"""Nested-fork restoration and input-only intervention, without a provider."""
import copy
import json
from pathlib import Path

import pytest
from test_checkpoint_continuation import call, stop_steps
from test_mutation_advice_checkpoint import source as source  # noqa: F401

from diagnostics import checkpoint_continuation as continuation
from diagnostics import cleanup_information_checkpoint as cleanup
from diagnostics import mutation_advice_checkpoint as original
from diagnostics.declaration_checkpoint import Source
from patchloop.contracts import Artifact
from patchloop.dev.model import MOCK_MUTATIONS
from patchloop.errors import ContractError
from patchloop.util import sha256_bytes


@pytest.fixture(scope="module")
def failed_source(source, tmp_path_factory):
    root = tmp_path_factory.mktemp("failed-check-source")
    packet = original.prepare(source, root / "original-packet")
    branch = continuation.restore(Path(packet["packet"]), packet["packet_hash"], root / "fork", "A")
    mutation = MOCK_MUTATIONS["csv-quoted-newline"]
    args = {k: getattr(mutation, k) for k in
            ("path", "old_text", "hypothesis", "expected_behavior")}
    args.update(new_text=mutation.old_text.replace("return rows", "return []"),
                occurrence=1, causal_revision=None)
    client = continuation.ScriptedClient([
        [call("replace_text", args, "mutate")],
        [call("run_check", {"check_id": "existing-unit-tests"}, "verify")],
        *stop_steps(),
    ])
    result = continuation.rehearse(branch, client)
    assert result["result"]["terminal"] == "AGENT_STOPPED"
    return Source(branch.root, branch.journal.run_id,
                  sha256_bytes(branch.journal.path.read_bytes()),
                  sha256_bytes(branch.journal.envelope_path.read_bytes()),
                  source.public_path, source.public_hash)


@pytest.mark.parametrize("arm", ["A", "B"])
def test_nested_failed_checkpoint_exact_delivery(failed_source, tmp_path, monkeypatch, arm):
    supplement = {"origin": "synthetic_operator", "observations": ["fixture only"]}
    monkeypatch.setattr(cleanup, "observation", lambda packet: supplement)
    packet = cleanup.prepare(failed_source, {"path": str(tmp_path / "evidence/result.json")},
                             tmp_path / "packet")
    cleanup.validate(Path(packet["packet"]), packet["packet_hash"])
    branch = continuation.restore(Path(packet["packet"]), packet["packet_hash"],
                                  tmp_path / arm, arm)
    client = continuation.ScriptedClient([
        [call("read_file", {"path": "mini_data_utils/csvlite.py", "start_line": 1,
                            "end_line": 90}, "inspect")], *stop_steps()])
    result = continuation.rehearse(branch, client)
    assert result["first_state_restored"] and result["result"]["terminal"] == "AGENT_STOPPED"
    assert {k: v for k, v in client.created[0].items() if k != "timeout"} == branch.selected
    initial = json.loads(branch.selected["input"][-1]["content"])["state"]
    assert ("operator_caller_observation" in initial) == (arm == "B")
    later = json.loads(client.created[1]["input"][-1]["content"])["state"]
    assert "operator_caller_observation" not in later
    assert result["result"]["accepted_mutations"] == 1
    assert result["new_billed_cost_nanos"] == 0


def test_nested_reference_metadata_rejected(failed_source):
    loaded = cleanup.load(failed_source)
    pair = next(iter(loaded.store.references.values()))
    bad = Artifact.model_validate({**pair[0], "size_bytes": pair[0]["size_bytes"] + 1})
    with pytest.raises(ContractError, match="source CAS path|metadata changed"):
        loaded.store.read_bytes(bad)


def test_restore_rejects_wrong_preimage(failed_source, tmp_path):
    mutation = copy.deepcopy(cleanup.load(failed_source).mutation)
    target = tmp_path / mutation["mutation_target_path"]
    target.parent.mkdir(parents=True)
    target.write_text("wrong source")
    with pytest.raises(ContractError, match="preimage changed"):
        cleanup.restore_candidate(tmp_path, mutation)
    assert target.read_text() == "wrong source"


def test_observation_excludes_other_candidate_and_rejects_rescue(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from patchloop.artifacts import ArtifactStore
    from patchloop.dev.state import DevJournal
    from patchloop.util import canonical_json

    mutation = {"mutation_expected_worktree_diff_hash": "first-diff"}
    envelope = SimpleNamespace(runtime_hash="runtime", probe_image_digest="image",
                               probe_profile_hash="profile",
                               probe_dependencies=SimpleNamespace(model_dump=lambda **kw: {}))
    fake_source = SimpleNamespace(root=tmp_path, run_id="run_dev_source")
    monkeypatch.setattr(cleanup.Source, "from_record", lambda _: fake_source)
    monkeypatch.setattr(cleanup, "load", lambda _: SimpleNamespace(
        mutation=mutation, source=fake_source))
    monkeypatch.setattr(DevJournal, "load_envelope", lambda _: envelope)
    store = ArtifactStore(tmp_path / "artifacts")
    journal = DevJournal(tmp_path, "run_dev_cleanupprobe")
    program = (Path(cleanup.__file__).parent / "probes/anyio_cleanup_trace.py").read_text()
    programs = {str(flag): f"TRACE = {flag!r}\n" + program for flag in (False, True)}
    journal.append("cleanup_probe_prepared", {
        "remove_caller_cancel": False, "runtime_hash": "runtime",
        "mutations": {"B1": mutation, "B2": "DO_NOT_PROJECT_OTHER_PATCH"},
        "programs": {k: store.put_text(v).model_dump(mode="json") for k, v in programs.items()}})
    rows = []
    for flag in (False, True):
        observation = {"events": [], "outcome": "diagnostic_watchdog_exit", "records": []}
        receipt = {"source_hash": sha256_bytes(programs[str(flag)].encode()),
                   "stdout": canonical_json(observation), "stderr": "", "status": "passed",
                   "exit_code": 0, "image_digest": "image", "profile_hash": "profile",
                   "execution_policy": {"dependencies": {}},
                   **dict.fromkeys(("cleanup_failed", "timed_out", "truncated",
                                    "deadline_exhausted"), False)}
        rows.append({"row": "B1", "trace": flag, "diff_hash": "first-diff",
                     "observation": observation,
                     "receipt": store.put_json(receipt).model_dump(mode="json")})
    rows.append({"row": "B2", "observation": "DO_NOT_PROJECT_OTHER_PATCH"})
    result = {"remove_caller_cancel": False, "rows": rows}
    journal.append("cleanup_observation_completed", {
        "artifact": store.put_json(result).model_dump(mode="json")})
    path = tmp_path / "result.json"
    path.write_text(canonical_json(result))
    packet = {"source": {}, "evidence": {"path": str(path),
              "hash": sha256_bytes(path.read_bytes()),
              "journal_hash": sha256_bytes(journal.path.read_bytes())}}
    supplement = cleanup.observation(packet)
    assert len(supplement["measurements"]) == 2
    assert "DO_NOT_PROJECT_OTHER_PATCH" not in canonical_json(supplement)
    result["remove_caller_cancel"] = True
    path.write_text(canonical_json(result))
    packet["evidence"]["hash"] = sha256_bytes(path.read_bytes())
    with pytest.raises(ContractError, match="probe result binding changed"):
        cleanup.observation(packet)
