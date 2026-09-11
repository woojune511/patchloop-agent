from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_model_state_sampler import MultiClient, snapshot
from test_model_state_sampler import factorial as _factorial

from diagnostics import decision_sampler as shared
from diagnostics import model_state_review as review
from diagnostics import model_state_sampler as sampler
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.model import MOCK_MUTATIONS
from patchloop.sandbox import LocalSandbox, SandboxResult
from patchloop.util import canonical_json

factorial = _factorial


def replacement_public():
    mutation = MOCK_MUTATIONS["csv-quoted-newline"]
    return {
        "anonymous_sample_id": "anonymous_1",
        "case_id": "C1",
        "error_code": None,
        "tool_calls": [
            {
                "name": "replace_text",
                "action_id": "sampled_mutation",
                "arguments": {
                    "path": mutation.path,
                    "old_text": mutation.old_text,
                    "new_text": mutation.new_text,
                    "hypothesis": "Public CSV line splitting loses multiline quote state.",
                    "expected_behavior": "Preserve public CSV records and quoted newlines.",
                    "turn_decision": {
                        "mode": "mutate",
                        "basis": "Observed public parser",
                        "memory_update": None,
                    },
                },
            }
        ],
    }


def hydrated(factorial, root, sandbox=None, case="C1"):
    plan, _, package = factorial
    payload = json.loads(
        next(c for c in plan.cells if c.case_id == case and c.arm == "B").request_json
    )["input"][1]["content"]
    payload = json.loads(payload)
    source_events, _ = sampler.source_events(plan.source_root)
    cutoff = plan.packet["cases"][case]["cutoff_event_hash"]
    index = next(i for i, e in enumerate(source_events) if e["event_hash"] == cutoff)
    gateway = review.gateway_at(
        plan,
        case,
        payload,
        source_events[:index],
        root / "evidence",
        root / "workspace" / "repo",
        package.public,
        sandbox or LocalSandbox(),
        ExecutionDeadline.from_remaining(30),
    )
    return gateway, payload, ArtifactStore(root / "assessment")


@pytest.mark.parametrize("violation", ["anchor", "scope", "unobserved", "untracked"])
def test_rejected_candidate_has_no_check_and_restores_checkpoint(factorial, tmp_path, violation):
    gateway, payload, store = hydrated(factorial, tmp_path / "review")
    public = replacement_public()
    args = public["tool_calls"][0]["arguments"]
    if violation == "anchor":
        args["old_text"] = "absent exact anchor"
    elif violation == "scope":
        args["new_text"] += "\n" + "# exceeds complete scope\n" * 30
    elif violation == "unobserved":
        gateway.spans.clear()
    else:
        (gateway.workspace / "untracked.txt").write_text("untracked")
    before = snapshot(gateway.workspace)
    baseline = gateway.current_diff.patch_hash
    row = review.assess_sample(public, payload, gateway, store, {}, "C1")
    assert row["mutation_admission"] == "FAIL" and row["checks"] == []
    assert gateway.current_diff.patch_hash == baseline
    # Git may refresh its index stat cache; tracked worktree bytes must not change.
    assert {p: b for p, b in before.items() if ".git" not in p.parts} == {
        p: b for p, b in snapshot(gateway.workspace).items() if ".git" not in p.parts
    }
    assert row["mutation_quality"] == "NOT_ASSESSED"


def test_candidate_hash_cache_and_public_regression_not_prose(factorial, tmp_path):
    cache = {}
    for index in range(2):
        gateway, payload, store = hydrated(factorial, tmp_path / f"review{index}")
        row = review.assess_sample(replacement_public(), payload, gateway, store, cache, "C1")
        assert row["mutation_admission"] == "PASS"
        assert row["mutation_quality"] == "PUBLIC_CHECKS_PASS"
        assert row["check_cache_hit"] is (index == 1)
        assert row["diagnostic_tool_executions"] == (3 if index == 0 else 1)
        assert all(c["diff_hash"] == row["candidate_hash"] for c in row["checks"])
        assert row["task_acceptance"] == row["hidden_evaluator"] == "NOT_RUN"
    # A persuasive expectation is not accepted as semantic evidence.
    gateway, payload, store = hydrated(factorial, tmp_path / "wrong")
    payload["visible_check_status"][0]["status"] = "PASS"
    public = replacement_public()
    public["tool_calls"][0]["arguments"]["new_text"] = "def parse_rows(text):\n    return []\n"
    row = review.assess_sample(public, payload, gateway, store, cache, "C1")
    assert row["mutation_admission"] == "PASS" and row["mutation_quality"] == "PUBLIC_CHECKS_FAIL"
    assert row["new_regressions"] == ["simple"]
    assert row["check_cache_hit"] is False


@pytest.mark.parametrize(
    "name,args,valid",
    [
        (
            "read_file",
            {"path": "mini_data_utils/csvlite.py", "start_line": 1, "end_line": 40},
            True,
        ),
        ("read_file", {"path": "not-tracked.py", "start_line": 1, "end_line": 40}, False),
        ("search_files", {"query": "parse_rows", "path_glob": "**/*.py"}, True),
    ],
)
def test_inspection_validity_is_not_mutation_failure(factorial, tmp_path, name, args, valid):
    gateway, payload, store = hydrated(factorial, tmp_path / "inspection")
    public = replacement_public()
    public["tool_calls"] = [
        {
            "name": name,
            "action_id": "inspect",
            "arguments": {
                **args,
                "turn_decision": {
                    "mode": "inspect",
                    "basis": "Public owner",
                    "evidence_goal": "Locate parser",
                },
            },
        }
    ]
    row = review.assess_sample(public, payload, gateway, store, {}, "C1")
    assert row["inspection_valid"] is valid
    assert row["mutation_admission"] == "NOT_RUN" and row["mutation_quality"] == "NOT_ASSESSED"
    assert row["checks"] == []


def test_frozen_read_mask_is_respected_without_a_new_action_policy(factorial, tmp_path):
    gateway, payload, store = hydrated(factorial, tmp_path / "inspection")
    public = replacement_public()
    public["tool_calls"] = [
        {
            "name": "read_file",
            "action_id": "inspect",
            "arguments": {
                "path": "mini_data_utils/csvlite.py",
                "start_line": 1,
                "end_line": 40,
                "turn_decision": {
                    "mode": "inspect",
                    "basis": "Public owner",
                    "evidence_goal": "Locate parser",
                },
            },
        }
    ]
    row = review.assess_sample(public, payload, gateway, store, {}, "C1", read_paths=("other.py",))
    assert row["batch_valid"] is False and row["diagnostic_tool_executions"] == 0


class CleanupFailure:
    backend = "mock"
    supports_execution_deadline = True
    calls = 0

    def run_check(self, workspace, check, *, deadline, execution_identity):
        self.calls += 1
        return SandboxResult(
            check.command,
            0,
            "public-output",
            "",
            1,
            False,
            False,
            13,
            execution_policy={"cleanup_status": "failed"},
            cleanup_failed=True,
        )


def test_cleanup_failure_preserves_policy_candidate_and_stops_checks(factorial, tmp_path):
    sandbox = CleanupFailure()
    gateway, payload, store = hydrated(factorial, tmp_path / "failed", sandbox)
    cache = {}
    row = review.assess_sample(replacement_public(), payload, gateway, store, cache, "C1")
    assert row["infrastructure_error"] and row["checks"][0]["status"] == "ERROR"
    assert sandbox.calls == 1 and not cache
    assert Path(row["candidate_artifact"]["path"]).is_file()
    evidence = review.read_json(store, row["checks"][0]["evidence"])
    assert evidence["output"]["execution_policy"]["cleanup_status"] == "failed"
    assert row["mutation_quality"] == "NOT_ASSESSED"


def test_blind_freeze_then_unblind_preserves_originals_and_cache(factorial, tmp_path, monkeypatch):
    plan, approval, package = factorial
    fake = MultiClient()

    def mutation(response):
        call = replacement_public()["tool_calls"][0]
        response.output[1].name = call["name"]
        response.output[1].arguments = canonical_json(call["arguments"])

    fake.edit_response = mutation
    sampler.collect(plan, approval, adapter_factory=fake.factory)
    originals = snapshot(plan.source_root, plan.packet_path.parent, approval.result_root)
    assessment = tmp_path / "blind"
    with pytest.raises(shared.ContractError, match="missing artifact store"):
        review.report(plan, approval.result_root, assessment)
    result = review.evaluate(
        plan,
        approval.result_root,
        assessment,
        tmp_path / "clones",
        Path(package.root),
        sandbox=LocalSandbox(),
    )
    assert result["terminal"] == "BLIND_OBSERVATIONS_FROZEN", result
    assert len(result["observations"]) == 16 and result["unassessed_samples"] == 0
    store = sampler.readonly_store(assessment)
    rows = [review.read_json(store, ref) for ref in result["observations"]]
    assert all("condition" not in r and "model" not in r and "input_tokens" not in r for r in rows)
    assert all(r["mutation_quality"] == "PUBLIC_CHECKS_PASS" for r in rows)
    assert sum(r["diagnostic_tool_executions"] for r in rows) == 20
    frozen = snapshot(assessment)
    unblinded = review.report(plan, approval.result_root, assessment)
    assert {r["condition"] for r in unblinded["rows"]} == set("ABCD")
    assert len(unblinded["rows"]) == 16 and unblinded["task_acceptance"] == "NOT_RUN"
    assert frozen == snapshot(assessment)
    assert originals == snapshot(plan.source_root, plan.packet_path.parent, approval.result_root)
    for data in frozen.values():
        for secret in (
            b"PLAINTEXT_REASONING_SENTINEL",
            b"PRIVATE_SPEC_SENTINEL",
            b"REFERENCE_PATCH_SENTINEL",
        ):
            assert secret not in data
    assert all(r["original_agent_check_credit"] is False for r in unblinded["rows"])
    with pytest.raises(shared.ContractError):
        review.evaluate(
            plan,
            approval.result_root,
            assessment,
            tmp_path / "new-clones",
            Path(package.root),
            sandbox=LocalSandbox(),
        )


def test_task_mismatch_and_missing_docker_reject_before_clone(factorial, tmp_path, monkeypatch):
    plan, approval, package = factorial
    sampler.collect(plan, approval, adapter_factory=MultiClient().factory)
    output, scratch = tmp_path / "blind", tmp_path / "clones"
    monkeypatch.setattr(
        review,
        "load_task_package",
        lambda _: package.model_copy(update={"task_content_hash": "changed"}),
    )
    with pytest.raises(shared.ContractError, match="task package mismatch"):
        review.evaluate(plan, approval.result_root, output, scratch, Path(package.root))
    assert not output.exists() and not scratch.exists()
    monkeypatch.setattr(review, "load_task_package", lambda _: package)

    def no_docker(*args, **kwargs):
        raise shared.ContractError("Docker unavailable; no start/pull/build")

    monkeypatch.setattr(review, "_live_sandbox_preflight", no_docker)
    with pytest.raises(shared.ContractError, match="Docker unavailable"):
        review.evaluate(plan, approval.result_root, output, scratch, Path(package.root))
    assert not output.exists() and not scratch.exists()
