"""Public dependency receipts are allowed provenance, not preparation path disclosure."""
from __future__ import annotations

import copy
import json

import pytest
from test_dev_probe_observation_v28 import _result
from test_dev_probes import FakeProbe, probe_call
from test_prepared_probe_dependencies import DependencyProbe, write_bundle

from diagnostics.public_probe_delivery import audit_preparation_delivery, audit_run
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact, ProbeDependencyIdentity
from patchloop.dev import runner
from patchloop.dev.contracts import DevModelTurn, DevRunRequest
from patchloop.dev.conversation import SEGMENT_RULES, reconstruct_state
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.probe_observation import project_probe_result
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.sandbox.probes import probe_execution_policy, probe_profile, probe_profile_hash
from patchloop.util import canonical_json, sha256_bytes, sha256_json

IDENTITY = ProbeDependencyIdentity(
    manifest_hash=sha256_json("dependency manifest"), content_hash=sha256_json("public wheels"),
    source_roots=["src"],
)
SOURCE_HASH = sha256_json("prepared source")
SOURCE_PATH = "C:\\operator\\source\\prepared-source.json"
DEPENDENCY_PATH = "C:\\operator\\dependencies\\prepared-probe-dependencies.json"


def _receipt(status="passed", *, dependencies=IDENTITY):
    raw = _result(status=status)
    policy = probe_execution_policy(effective_timeout_seconds=30, row_deadline_limited=False,
                                    cleanup_status="confirmed", profile=probe_profile(dependencies))
    raw["output"].update(execution_policy=policy, execution_policy_hash=sha256_json(policy),
                         profile_hash=probe_profile_hash(dependencies))
    return raw


def _native(raw, *, archived=False):
    exchange = {"type": "function_call_output", "call_id": raw["action_id"],
                "output": canonical_json(project_probe_result(raw))}
    return [SEGMENT_RULES.archive(exchanges=[exchange])] if archived else [exchange]


def _audit(native, raw, *, dependencies=IDENTITY):
    return audit_preparation_delivery(
        native, probe_results={raw["action_id"]: raw},
        probe_dependencies=dependencies.model_dump() if dependencies else None,
        probe_profile_hash=probe_profile_hash(dependencies), prepared_source_hash=SOURCE_HASH,
        preparation_paths=[SOURCE_PATH, DEPENDENCY_PATH],
    )


@pytest.mark.parametrize("archived", [False, True])
@pytest.mark.parametrize("status", ["passed", "failed", "timeout"])
def test_verified_receipts_survive_native_delivery_and_public_handoff(status, archived):
    raw = _receipt(status)
    native = _native(raw, archived=archived)
    before = copy.deepcopy((native, raw))
    rows = _audit(native, raw)
    assert (native, raw) == before
    assert rows == [{"action_id": raw["action_id"], "native_index": 0,
                     "location": "quoted_public_exchange" if archived else "function_call_output",
                     "execution_status": "completed" if status == "passed" else status,
                     "dependency_identity_verified": True}]


@pytest.mark.parametrize("field", ["status", "stdout", "diff_hash", "execution_policy_hash"])
def test_changed_public_receipt_fails_even_with_a_known_digest(field):
    raw = _receipt()
    changed = copy.deepcopy(raw)
    changed["output"][field] = "changed"
    with pytest.raises(ContractError, match="durable public receipt"):
        _audit(_native(changed, archived=True), raw)


@pytest.mark.parametrize("fault", ["manifest", "content", "profile", "policy_hash", "missing"])
def test_durable_receipt_must_also_match_admitted_dependency_identity(fault):
    raw = _receipt()
    policy = raw["output"]["execution_policy"]
    if fault in {"manifest", "content"}:
        policy["dependencies"][f"{fault}_hash"] = sha256_json("different")
        raw["output"]["execution_policy_hash"] = sha256_json(policy)
    elif fault == "profile":
        raw["output"]["profile_hash"] = sha256_json("different")
    elif fault == "policy_hash":
        raw["output"]["execution_policy_hash"] = sha256_json("different")
    else:
        del raw["output"]["execution_policy"]
    with pytest.raises(ContractError, match="policy"):
        _audit(_native(raw), raw)


@pytest.mark.parametrize("fault", ["missing", "wrong_call", "wrong_tool"])
def test_unbound_receipts_cannot_whitelist_dependency_hashes(fault):
    raw = _receipt()
    native = _native(raw)
    if fault == "missing":
        with pytest.raises(ContractError, match="preceding durable receipt"):
            audit_preparation_delivery(native, probe_results={})
        return
    if fault == "wrong_call":
        native[0]["call_id"] = "another-call"
    else:
        changed = copy.deepcopy(raw)
        changed["tool"] = "read_file"
        native = _native(changed)
    with pytest.raises(ContractError, match="receipt"):
        _audit(native, raw)


@pytest.mark.parametrize("location", ["text", "arbitrary_json", "stdout", "annotation",
                                     "archive_observation", "unregistered_archive"])
def test_known_digest_is_forbidden_outside_verified_policy_fields(location):
    raw = _receipt()
    digest = IDENTITY.manifest_hash
    native = _native(raw)
    if location == "stdout":
        raw["output"]["stdout"] = digest
        native = _native(raw)
    elif location == "annotation":
        value = json.loads(native[0]["output"])
        value["plan_update_result"] = {"plan": digest}
        native[0]["output"] = canonical_json(value)
    elif location in {"archive_observation", "unregistered_archive"}:
        native = _native(raw, archived=True)
        archive = json.loads(native[0]["content"])
        if location == "archive_observation":
            archive["observations"] = [{"field": "plan", "value": digest}]
        else:
            archive["kind"] = "not_a_public_archive"
        native[0]["content"] = canonical_json(archive)
    else:
        native.append({"role": "developer", "content": digest if location == "text" else
                       canonical_json({"output": {"execution_policy": {
                           "dependencies": IDENTITY.model_dump()}}})})
    with pytest.raises(ContractError, match="outside a verified"):
        _audit(native, raw)


@pytest.mark.parametrize("secret", [SOURCE_HASH, SOURCE_PATH, DEPENDENCY_PATH,
                                    SOURCE_PATH.lower().replace("\\", "/")])
@pytest.mark.parametrize("archived", [False, True])
def test_source_identity_and_escaped_preparation_paths_stay_absent(secret, archived):
    raw = _receipt()
    raw["output"]["stderr"] = secret
    with pytest.raises(ContractError, match="actual model input"):
        _audit(_native(raw, archived=archived), raw)


def test_omitted_option_and_pre_execution_failure_need_no_dependency_receipt():
    raw = _receipt(dependencies=None)
    assert _audit(_native(raw), raw, dependencies=None)[0]["dependency_identity_verified"] is False
    raw.update(status="failed", output={})
    assert _audit(_native(raw), raw)[0]["execution_status"] == "not_run"
    assert _audit([], raw) == []  # Historical receipts need not remain in every later segment.


@pytest.mark.parametrize("context_policy", ["append-v1", "segmented-v1"])
@pytest.mark.parametrize("prepared", [False, True])
def test_actual_mock_inputs_probe_failures_handoffs_and_isolated_evaluation(
    tmp_path, monkeypatch, smoke_package, context_policy, prepared,
):
    bundle = write_bundle(tmp_path / "prepared", smoke_package.public) if prepared else None
    backends = []

    class SequenceProbe(DependencyProbe if prepared else FakeProbe):
        def run_probe(self, *args, **kwargs):
            self.status = "passed" if self.calls == 1 else "failed"
            return super().run_probe(*args, **kwargs)

    def backend(**kwargs):
        instance = SequenceProbe(**kwargs) if prepared else SequenceProbe()
        backends.append(instance)
        return instance

    class ProbeThenMock(MockDevAdapter):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.probes = 0

        def next_turn(self, context, tools):
            if self.probes < 3:
                self.probes += 1
                return DevModelTurn(tool_calls=[probe_call(f"probe-{self.probes}")])
            return super().next_turn(context, tools)

    monkeypatch.setattr(runner, "DockerProbeSandbox", backend)
    monkeypatch.setattr(runner, "MockDevAdapter", ProbeThenMock)
    request = DevRunRequest(
        provider="mock", model="mock-dev", enable_probes=True, planning_policy="brief-v1",
        task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml",
        context_policy=context_policy, state_root=tmp_path / "state",
        prepared_probe_dependencies=bundle,
    )
    result, = runner.run_dev(request)["runs"]
    assert result["terminal"] == "EVALUATOR_PASS" and result["cost_nanos"] == 0
    assert result["evaluator"]["safety_state"] == "NOT_RUN"
    assert sum(b.calls for b in backends) == 3
    journal = DevJournal(request.state_root, result["run_id"])
    before = journal.path.read_bytes()
    audit = audit_run(request.state_root, result["run_id"])
    assert audit["actual_inputs_verified"] == result["call_counts"]["model"] == 7
    deliveries = [p for row in audit["inputs"] for p in row["probe_deliveries"]]
    assert {p["action_id"] for p in deliveries} == {"probe-1", "probe-2", "probe-3"}
    assert {p["execution_status"] for p in deliveries} == {"failed", "completed"}
    assert all(p["dependency_identity_verified"] is prepared for p in deliveries)
    if context_policy == "segmented-v1":
        assert {p["execution_status"] for p in deliveries
                if p["location"] == "quoted_public_exchange"} == {"failed", "completed"}
    store = ArtifactStore(request.state_root / "artifacts")
    for event in journal.events():
        if event["event_type"] != "turn_started":
            continue
        turn = event["payload"]
        native = runner._load_active_model_input(turn, store, context_policy=context_policy)
        actual = reconstruct_state(native, context_policy=context_policy)
        canonical = json.loads(store.read_bytes(Artifact.model_validate(turn["context_artifact"])))
        for field in ("public_task", "current_diff", "visible_check_status"):
            assert actual[field] == canonical[field]
    assert actual["current_diff"]["patch"]
    assert all(c["status"] == "PASS" for c in actual["visible_check_status"])
    assert journal.path.read_bytes() == before
    (tmp_path / "audit.json").write_text(canonical_json({
        "result": result, "context_policy": context_policy, "prepared": prepared,
        "journal_hash": sha256_bytes(before), "audit": audit,
    }), encoding="utf-8")


@pytest.mark.parametrize("partial_store", [False, True])
def test_missing_run_audit_does_not_create_directories(tmp_path, partial_store):
    root = tmp_path / "missing"
    if partial_store:
        (root / "runs").mkdir(parents=True)
        (root / "artifacts").mkdir()
    before = list(tmp_path.rglob("*"))
    with pytest.raises(ContractError, match="existing"):
        audit_run(root, "run_dev_absent")
    assert list(tmp_path.rglob("*")) == before
