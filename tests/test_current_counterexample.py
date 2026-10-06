"""Current-observation diagnostics use synthetic data, never a provider or Docker."""
from __future__ import annotations

import copy
import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_candidate_review_repair import request as mock_request
from test_candidate_review_repair import seed
from test_checkpoint_continuation import stop_steps
from test_dev_probes import FakeProbe
from test_observation_comparison import resolver

from diagnostics import candidate_review_repair as seeded
from diagnostics import current_counterexample as diagnostic
from diagnostics.checkpoint_continuation import ScriptedClient
from diagnostics.declaration_checkpoint import Source
from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner
from patchloop.dev.contracts import DevLimits, DevModelTurn, PublicTurnDecision, RequestedTool
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.sandbox import LocalSandbox
from patchloop.sandbox.probes import probe_execution_policy
from patchloop.util import canonical_json, sha256_bytes, sha256_json, sha256_text


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr("socket.socket.connect", lambda *_: pytest.fail("network forbidden"))


def calibration(patch="synthetic public candidate"):
    program = "print('public behavior')\nassert False\n"
    return {
        "candidate_diff_hash": sha256_text(patch),
        "question": "Does the current candidate preserve quoted newlines?",
        "python_source": program,
        "source_hash": sha256_text(program),
        "output": {
            "stdout": "public behavior\n", "stderr": "AssertionError\n", "exit_code": 1,
            "setup_checks": {"status": "passed"},
        },
    }


def test_only_current_execution_observations_differ_and_expire():
    record = calibration()
    original = copy.deepcopy(record)
    arms = {arm: diagnostic.feedback(record, arm) for arm in ("A", "B")}
    assert [key for key in arms["A"] if arms["A"][key] != arms["B"][key]] == ["stdout"]
    assert arms["A"]["stdout"] == diagnostic.WITHHELD
    assert json.loads(arms["B"]["stdout"]) == record["output"]
    assert record == original
    for feedback in arms.values():
        seeded.validate_feedback(feedback, record["candidate_diff_hash"])
        assert feedback["python_source"] == record["python_source"]
        assert feedback["execution_receipt_hash"] == sha256_json(record["output"])
        current = seeded.feedback_overlay(
            {"current_diff": {"patch_hash": record["candidate_diff_hash"]}}, feedback,
        )
        assert current["currency"] == "current_candidate"
        changed = seeded.feedback_overlay({"current_diff": {"patch_hash": "new"}}, feedback)
        assert changed["currency"] == "historical_candidate"
        assert changed["observed_on_diff_hash"] == record["candidate_diff_hash"]
        assert "registered check verdicts" in changed["interpretation"]
    with pytest.raises(ContractError):
        diagnostic.feedback(record, "unknown")


def test_seeded_pair_actual_inputs_have_no_inherited_check_credit_and_reach_evaluation(
    tmp_path, monkeypatch, gateway_factory, smoke_package,
):
    patch_text = seed(gateway_factory)
    record = calibration(patch_text)
    inputs, schemas, results = {}, {}, {}
    original_hooks = {key: getattr(runner, key) for key in ("_build_context", "DevToolGateway")}
    probe = FakeProbe(status="passed")
    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda **_: probe)

    for arm in ("A", "B"):
        inputs[arm], schemas[arm] = [], []

        class RepairMock(MockDevAdapter):
            step = 0

            def _next_action(self, context, tools, selected_arm=arm):
                state = json.loads(context)
                inputs[selected_arm].append(state)
                schemas[selected_arm].append(tools)
                self.step += 1
                if self.step == 1:
                    call = RequestedTool(
                        name="read_file", action_id="read-current",
                        arguments={"path": self.mutation.path, "start_line": 1, "end_line": 80},
                        turn_decision=PublicTurnDecision(mode="inspect", basis="Inspect candidate.",
                                                        evidence_goal="Locate parser behavior."),
                    )
                elif self.step == 2:
                    call = RequestedTool(
                        name="replace_text", action_id="repair-current",
                        arguments={"path": self.mutation.path, "old_text": self.mutation.old_text,
                                   "new_text": self.mutation.new_text, "occurrence": 1,
                                   "hypothesis": self.mutation.hypothesis,
                                   "expected_behavior": self.mutation.expected_behavior,
                                   "causal_revision": None},
                        turn_decision=PublicTurnDecision(mode="mutate", basis="Preserve CSV rows."),
                    )
                else:
                    return super()._next_action(context, tools)
                return DevModelTurn(tool_calls=[call])

        monkeypatch.setattr(runner, "MockDevAdapter", RepairMock)
        root = tmp_path / arm
        request = mock_request(root).model_copy(update={
            "limits": DevLimits(max_model_calls=40, max_tool_actions=100,
                                max_accepted_mutations=4, wall_time_seconds=1800),
            "retained_source_chars": 24_000,
            "evaluation_reserve_seconds": 330, "enable_probes": True,
        })
        result = seeded.run_seeded(
            request, seed_patch=patch_text, seed_hash=sha256_text(patch_text),
            base_commit=smoke_package.public.repository.base_commit, source_code=[], review=None,
            experiment_hash="sha256:" + "a" * 64, source_run_id="run_dev_fixture", branch=arm,
            public_feedback=diagnostic.feedback(record, arm),
        )["runs"][0]
        results[arm] = result
        assert result["terminal"] == "EVALUATOR_PASS", result
        assert result["evaluator"]["safety_state"] == "NOT_RUN"
        assert result["accepted_mutations"] == 1
        first, last = inputs[arm][0], inputs[arm][-1]
        assert first[seeded.FEEDBACK_FIELD]["currency"] == "current_candidate"
        assert last[seeded.FEEDBACK_FIELD]["currency"] == "historical_candidate"
        assert first["remaining_budget"]["accepted_mutations"] == 3
        assert last["remaining_budget"]["accepted_mutations"] == 2
        assert first["remaining_budget"]["model_calls"] == 40
        assert first["remaining_budget"]["evaluation_reserve_seconds"] == 330
        assert all(row["status"] == "NOT_RUN" for row in first["visible_check_status"])
        assert "finish_task" not in first["available_tool_names"]
        events = DevJournal(root, result["run_id"]).events()
        assert any(event["event_type"] == "evaluator_finished" for event in events)
        assert not any(event["event_type"] == "action_started"
                       and event["payload"]["tool"] == "run_probe" for event in events)
        assert all(getattr(runner, key) is value for key, value in original_hooks.items())

    first_a, first_b = copy.deepcopy(inputs["A"][0]), copy.deepcopy(inputs["B"][0])
    first_a[seeded.FEEDBACK_FIELD]["stdout"] = first_b[seeded.FEEDBACK_FIELD]["stdout"]
    # Startup time is measured independently; it is not an experimental intervention.
    first_a["remaining_budget"] = first_b["remaining_budget"]
    assert first_a == first_b
    assert schemas["A"][0] == schemas["B"][0]
    assert results["A"]["accepted_mutations"] == results["B"]["accepted_mutations"]
    assert probe.calls == 0


def test_request_has_equal_fresh_limits_and_selected_configuration(tmp_path, monkeypatch):
    old = SimpleNamespace(prepared_source_path=str(tmp_path / "source"),
                          prepared_probe_dependencies_path=str(tmp_path / "dependencies"))
    monkeypatch.setattr(diagnostic.DevJournal, "load_envelope", lambda _: old)
    plan = {"source": {"root": str(tmp_path / "prior"), "run_id": "run_dev_fixture",
                       "public_path": str(tmp_path / "public.yaml")},
            "model": "gpt-5.4-mini-2026-03-17", "env_file": str(tmp_path / "unused.env"),
            "task": str(tmp_path / "public.yaml")}
    a, b = (diagnostic.request(plan, tmp_path / arm) for arm in ("A", "B"))
    assert a.model == "gpt-5.4-mini-2026-03-17" and a.reasoning_effort == "xhigh"
    assert a.max_output_tokens == 25_000 and a.retained_source_chars == 24_000
    assert a.limits.max_model_calls == 40 and a.limits.max_tool_actions == 100
    assert a.limits.max_accepted_mutations == 4 and a.limits.wall_time_seconds == 1800
    assert a.evaluation_reserve_seconds == 330 and a.max_cost_usd == Decimal("1.20")
    assert a.enable_probes and a.probe_policy == a.probe_recheck == "none"
    assert a.repeat == 1 and a.resume_run_id is None
    assert a.model_dump(exclude={"state_root"}) == b.model_dump(exclude={"state_root"})
    assert len(diagnostic.ORDER) * diagnostic.ROW_CAP == diagnostic.CAP == Decimal("2.40")


@pytest.fixture
def calibration_case(tmp_path, monkeypatch):
    record = calibration()
    candidate = "synthetic public candidate"
    source_root = tmp_path / "source"
    source_root.mkdir()
    public = tmp_path / "public.yaml"
    public.write_text("public fixture", encoding="utf-8")
    source = Source(source_root, "run_dev_fixture", "sha256:journal", "sha256:envelope",
                    public, sha256_bytes(public.read_bytes()))
    boundary = ArtifactStore(source_root / "artifacts").put_json({"request": {"input": [{
        "content": canonical_json({"state": {"current_diff": {
            "patch": candidate, "patch_hash": record["candidate_diff_hash"],
        }}}),
    }]}})
    old = SimpleNamespace(base_commit="b" * 40, probe_dependencies=None)
    monkeypatch.setattr(diagnostic.replay, "audit", lambda *_: {
        "candidate_diff_hash": record["candidate_diff_hash"],
    })
    monkeypatch.setattr(diagnostic.DevJournal, "events", lambda _: [{
        "sequence": 5, "payload": {"artifact": boundary.model_dump(mode="json")},
    }])
    monkeypatch.setattr(diagnostic.DevJournal, "load_envelope", lambda _: old)
    original_program = {key: record[key] for key in ("python_source", "question")}
    monkeypatch.setattr(diagnostic.probe_replay, "prepare", lambda *_: original_program)
    policy = probe_execution_policy(effective_timeout_seconds=30.0,
                                   row_deadline_limited=False, cleanup_status="confirmed")
    record["output"].update({
        "source_hash": record["source_hash"], "status": "failed", "timed_out": False,
        "truncated": False, "cleanup_failed": False, "deadline_exhausted": False,
        "image_digest": runner.probe_profile(None)["image_digest"],
        "profile_hash": runner.probe_profile_hash(None), "execution_policy": policy,
        "execution_policy_hash": sha256_json(policy),
    })
    record.update({
        "schema": "current-counterexample-calibration-v1", "source": source.record(),
        "cut_sequence": 5, "target_action_id": "original-probe", "candidate_patch": candidate,
        "base_commit": old.base_commit, "official": False,
        "public_program_origin": "source_agent_action",
        "observed_diff_hash_before": record["candidate_diff_hash"],
        "observed_diff_hash_after": record["candidate_diff_hash"],
        "execution_identity": {"run_id": "run_dev_probe", "action_id": "probe",
                               "input_hash": sha256_json({"question": record["question"],
                                   "python_source": record["python_source"],
                                   "diff_hash": record["candidate_diff_hash"]})},
        "protected_files": {str(public): sha256_bytes(public.read_bytes())},
    })
    path = tmp_path / "calibration.json"
    path.write_text(canonical_json(record), encoding="utf-8")
    case = {key: record[key] for key in ("source", "cut_sequence", "target_action_id")}
    case["calibration"] = {"path": str(path), "hash": sha256_bytes(path.read_bytes())}
    assert diagnostic.load_calibration(case)[0] == record
    return case, record


@pytest.mark.parametrize("changed", ["receipt_hash", "program", "candidate", "receipt_source",
                                    "timeout", "cleanup", "policy", "protected_file", "setup",
                                    "execution_binding"])
def test_changed_calibration_is_rejected_before_execution(calibration_case, changed):
    case, record = calibration_case
    if changed == "program":
        record["python_source"] += "print('extra hint')\n"
        record["source_hash"] = sha256_text(record["python_source"])
    elif changed == "candidate":
        record["candidate_patch"] += "changed"
    elif changed == "receipt_source":
        record["output"]["source_hash"] = "different"
    elif changed == "timeout":
        record["output"]["timed_out"] = True
    elif changed == "cleanup":
        record["output"]["cleanup_failed"] = True
    elif changed == "policy":
        record["output"]["execution_policy_hash"] = "different"
    elif changed == "protected_file":
        Path(next(iter(record["protected_files"]))).write_text("changed", encoding="utf-8")
    elif changed == "setup":
        record["output"]["setup_checks"]["status"] = "not_checked"
    elif changed == "execution_binding":
        record["execution_identity"]["input_hash"] = "different"
    path = Path(case["calibration"]["path"])
    path.write_text(canonical_json(record) + "\n", encoding="utf-8")
    if changed != "receipt_hash":
        case["calibration"]["hash"] = sha256_bytes(path.read_bytes())
    with pytest.raises(ContractError):
        diagnostic.load_calibration(case)


def test_wrong_approval_stops_before_environment_or_provider(tmp_path, monkeypatch):
    path = tmp_path / "manifest.json"
    path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(diagnostic, "environment", lambda *_: pytest.fail("preflight reached"))
    with pytest.raises(ContractError, match="USD 2.40"):
        diagnostic.collect(path, sha256_bytes(path.read_bytes()), Decimal("1.20"))
    with pytest.raises(ContractError, match="manifest changed"):
        diagnostic.collect(path, "wrong", Decimal("2.40"))


@pytest.mark.parametrize("failure", [None, "count", "transport", "usage", "first_input"])
def test_actual_sdk_count_dispatch_billing_and_group_stop(
    tmp_path, monkeypatch, gateway_factory, smoke_package, failure,
):
    patch_text = seed(gateway_factory)
    record = calibration(patch_text)
    client = ScriptedClient(stop_steps() * 2,
                            failure=None if failure == "first_input" else failure)
    original_adapter = diagnostic.OpenAIResponsesAdapter

    class SyntheticAdapter(original_adapter):
        def __init__(self, config, **_):
            super().__init__(config, api_key="synthetic", client=client)

    monkeypatch.setattr(diagnostic, "OpenAIResponsesAdapter", SyntheticAdapter)
    monkeypatch.setattr(runner, "load_exact_openai_api_key", lambda _: "synthetic")
    monkeypatch.setattr(runner, "_live_task_is_admitted", lambda *_: None)
    monkeypatch.setattr(runner, "_live_source_preflight", lambda *_, **__: None)
    monkeypatch.setattr(runner, "_live_sandbox_preflight", lambda *_, **__: LocalSandbox())
    monkeypatch.setattr(runner, "_require_tracked_clean_paths", lambda *_: None)
    monkeypatch.setattr(runner, "_resolve_task_file", resolver(runner._resolve_task_file))
    monkeypatch.setattr(diagnostic, "normalized", lambda _: {"fixture": "first-input"})
    called = []

    def run_seeded(plan, arm, root):
        called.append(arm)
        request = mock_request(root).model_copy(update={
            "provider": "openai", "model": "gpt-5.4-mini-2026-03-17",
            "env_file": tmp_path / "absent.env", "max_cost_usd": Decimal("1.20"),
            "reasoning_effort": "xhigh",
        })
        try:
            return seeded.run_seeded(
                request, seed_patch=patch_text, seed_hash=sha256_text(patch_text),
                base_commit=smoke_package.public.repository.base_commit,
                source_code=[], review=None,
                experiment_hash="sha256:" + "a" * 64, source_run_id="run_dev_fixture", branch=arm,
                public_feedback=diagnostic.feedback(record, arm),
            )
        except Exception as exc:
            pytest.fail(f"Synthetic SDK fixture failed before its expected terminal: {exc}")

    plan = {"case": {}, "result_root": str(tmp_path / "live"), "row_cap_nanos": 1_200_000_000,
            "new_cap_nanos": 2_400_000_000,
            "first_request_hashes": {arm: sha256_json({"fixture": "first-input"})
                                     for arm in ("A", "B")}}
    if failure == "first_input":
        plan["first_request_hashes"]["A"] = "different-first-input"
    manifest = tmp_path / "plan" / "manifest.json"
    manifest.parent.mkdir()
    monkeypatch.setattr(diagnostic, "validate", lambda *_: plan)
    monkeypatch.setattr(diagnostic, "environment", lambda *_: {"status": "READY"})
    monkeypatch.setattr(diagnostic, "run_seeded", run_seeded)
    if failure is None:
        monkeypatch.setattr(diagnostic, "load_calibration", lambda _: (record, None))
        monkeypatch.setattr(runner, "DockerProbeSandbox",
                            lambda **_: pytest.fail("probe forbidden"))
    else:
        monkeypatch.setattr(diagnostic, "audit_candidate",
                            lambda *_: pytest.fail("audit forbidden"))
    result = diagnostic.collect(manifest, "synthetic-approval", Decimal("2.40"))
    if failure is None:
        assert called == ["A", "B"] and result["stop_reason"] is None, result
        assert result["billing_known"] and result["new_cost_nanos"] > 0
        assert result["new_cost_nanos"] == sum(row["new_cost_nanos"] for row in result["rows"])
        assert len(client.counted) == len(client.created) == 2
        assert all(row["input_counts"] == row["dispatches"] == 1 for row in result["rows"])
        assert all(row["public_audit"]["verdict"] == "NOT_RUN" for row in result["rows"])
        assert all(row["result"]["terminal"] == "AGENT_STOPPED" for row in result["rows"])
        return
    assert called == ["A"]
    before_dispatch = failure in {"count", "first_input"}
    expected = "COUNT_TIMEOUT_OR_UNKNOWN" if before_dispatch else "PROVIDER_TIMEOUT_OR_UNKNOWN"
    assert result["stop_reason"] == expected, result
    assert result["rows"][0]["result"]["terminal"] == expected
    assert result["rows"][0]["stop_remaining"]
    assert result["billing_known"] is before_dispatch
    assert result["new_cost_nanos"] == (0 if before_dispatch else None)
    assert len(client.counted) == (0 if failure == "first_input" else 1)
    assert len(client.created) == (0 if before_dispatch else 1)


def test_post_run_audit_uncertainty_closes_peer_but_preserves_known_billing(tmp_path, monkeypatch):
    plan = {"result_root": str(tmp_path / "live"), "new_cap_nanos": 2_400_000_000,
            "first_request_hashes": {"A": "first-a", "B": "first-b"}}
    manifest = tmp_path / "plan" / "manifest.json"
    manifest.parent.mkdir()
    calls = []

    def row(_, arm, *__):
        calls.append(arm)
        return {"row": arm, "status": "EXECUTED", "billing_known": True,
                "new_cost_nanos": 123, "stop_remaining": False,
                "result": {"terminal": "EVALUATOR_PASS"}}

    def audit(*_):
        raise ContractError("synthetic incomplete audit")

    monkeypatch.setattr(diagnostic, "validate", lambda *_: plan)
    monkeypatch.setattr(diagnostic, "environment", lambda *_: {"status": "READY"})
    monkeypatch.setattr(diagnostic, "run_row", row)
    monkeypatch.setattr(diagnostic, "audit_candidate", audit)
    result = diagnostic.collect(manifest, "synthetic-approval", Decimal("2.40"))
    assert calls == ["A"] and result["stop_reason"] == "PUBLIC_AUDIT_UNCERTAIN"
    assert result["billing_known"] and result["new_cost_nanos"] == 123
    assert result["rows"][0]["public_audit"]["verdict"] == "NOT_ASSESSABLE"
    assert result["allocation"] == "CLOSED" and not result["automatic_followup"]
    with pytest.raises(ContractError, match="fresh output|no resume"):
        diagnostic.collect(manifest, "synthetic-approval", Decimal("2.40"))


def test_non_submission_never_executes_operator_audit(tmp_path, monkeypatch):
    monkeypatch.setattr(diagnostic, "load_calibration", lambda _: (calibration(), None))
    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda **_: pytest.fail("probe forbidden"))
    row = {"row": "A", "result": {"run_id": "run_dev_unsubmitted"}}
    result = diagnostic.audit_candidate({"case": {}}, row, tmp_path / "A",
                                        DevJournal(tmp_path, "run_dev_group"))
    assert result == {"verdict": "NOT_RUN", "reason": "no submitted candidate",
                      "agent_verification_credit": False}


@pytest.mark.parametrize("drift_after_first", [False, True])
def test_group_sums_new_cost_and_rechecks_frozen_controls_before_each_row(
    tmp_path, monkeypatch, drift_after_first,
):
    plan = {"case": {}, "env_file": str(tmp_path / "absent.env"),
            "result_root": str(tmp_path / "live"), "new_cap_nanos": 2_400_000_000,
            "git_commit": "frozen-commit", "runtime_hash": "frozen-runtime",
            "task": str(tmp_path / "public.yaml"), "source": {"public_path": "original"},
            "first_request_hashes": {"A": "first-a", "B": "first-b"}}
    manifest = tmp_path / "plan" / "manifest.json"
    manifest.parent.mkdir()
    calls, admissions = [], []

    def controls(*_):
        admissions.append(len(calls))
        value = {key: item for key, item in plan.items() if key != "first_request_hashes"}
        if calls and drift_after_first:
            value["runtime_hash"] = "changed-runtime"
        return value

    def row(_, arm, *__):
        calls.append(arm)
        return {"row": arm, "status": "EXECUTED", "billing_known": True,
                "new_cost_nanos": 100 if arm == "A" else 200, "stop_remaining": False,
                "result": {"terminal": "AGENT_STOPPED"}}

    monkeypatch.setattr(diagnostic, "validate", lambda *_: plan)
    monkeypatch.setattr(diagnostic, "controls", controls)
    monkeypatch.setattr(runner, "_require_tracked_clean_paths", lambda *_: None)
    monkeypatch.setattr(diagnostic.live, "check_environment", lambda *_: {"status": "READY"})
    monkeypatch.setattr(diagnostic, "run_row", row)
    monkeypatch.setattr(diagnostic, "audit_candidate", lambda *_: {"verdict": "NOT_RUN"})
    result = diagnostic.collect(manifest, "synthetic-approval", Decimal("2.40"))
    assert admissions == [0, 1]
    assert calls == (["A"] if drift_after_first else ["A", "B"])
    assert result["new_cost_nanos"] == (100 if drift_after_first else 300)
    assert result["billing_known"]
    assert result["stop_reason"] == ("PREFLIGHT_FAILED" if drift_after_first else None)


def test_first_request_normalization_changes_only_clock_and_segment_identity():
    state = {"remaining_budget": {"active_wall_time_seconds": 1470,
                                  "total_active_wall_time_seconds": 1800,
                                  "model_calls": 40},
             "segment_handoff": {"segment_id": "fresh-id", "reason": "initial"},
             seeded.FEEDBACK_FIELD: {"stdout": "real observation"}}
    request = {"timeout": 12, "model": "same-model", "input": [{
        "role": "developer", "content": canonical_json({"state": state}),
    }]}
    original = copy.deepcopy(request)
    value = diagnostic.normalized(request)
    projected = json.loads(value["input"][-1]["content"])["state"]
    assert projected["remaining_budget"]["model_calls"] == 40
    assert projected["segment_handoff"]["reason"] == "initial"
    assert projected[seeded.FEEDBACK_FIELD]["stdout"] == "real observation"
    projected["remaining_budget"]["active_wall_time_seconds"] = 1470
    projected["remaining_budget"]["total_active_wall_time_seconds"] = 1800
    projected["segment_handoff"]["segment_id"] = "fresh-id"
    value["input"][-1]["content"] = canonical_json({"state": projected})
    value["timeout"] = 12
    assert value == original == request
