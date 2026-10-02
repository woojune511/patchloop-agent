from __future__ import annotations

import json
import shutil
from types import SimpleNamespace

import pytest
import yaml
from test_candidate_review_repair import request as mock_request
from test_selected_tests import call, suite

from diagnostics import candidate_review_repair as seeded
from diagnostics import selected_tests_diagnostic as diagnostic
from patchloop.dev import runner
from patchloop.dev.contracts import DevModelTurn, PublicTurnDecision, RequestedTool
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.util import sha256_bytes, sha256_text


@pytest.mark.parametrize(
    "result,status",
    [
        ({"exit_code": 0, "stdout": '{"violations":[[],[]]}'}, "PASS"),
        ({"exit_code": 0, "stdout": '{"violations":[[[1,2,"L031"]],[]]}'}, "FAIL"),
        ({"exit_code": 0, "stdout": '{"violations":[]}'}, "ERROR"),
        ({"exit_code": 0, "stdout": "[]"}, "ERROR"),
        ({"exit_code": 0, "stdout": "broken"}, "ERROR"),
        ({"exit_code": 1, "stdout": '{"violations":[[],[]]}'}, "ERROR"),
        ({"exit_code": 0, "stdout": '{"violations":[[],[]]}', "cleanup_failed": True}, "ERROR"),
        ({"exit_code": 0, "stdout": '{"violations":[[],[]]}', "truncated": True}, "ERROR"),
    ],
)
def test_example_assessment_distinguishes_failure_from_uncertainty(result, status):
    assert diagnostic.classify_examples(result, {"violations": [[], []]}) == status


def test_frozen_packet_rejects_scope_or_byte_changes(tmp_path, monkeypatch):
    packet = {"scope": "two runs"}
    diagnostic.save(tmp_path, "packet.json", packet)
    digest = sha256_bytes((tmp_path / "packet.json").read_bytes())
    monkeypatch.setattr(diagnostic, "identity", lambda _: packet)
    diagnostic.validate(tmp_path, digest)
    monkeypatch.setattr(diagnostic, "identity", lambda _: {"scope": "three runs"})
    with pytest.raises(ContractError, match="conditions changed"):
        diagnostic.validate(tmp_path, digest)
    with pytest.raises(ContractError, match="packet changed"):
        diagnostic.validate(tmp_path, "sha256:" + "0" * 64)


def test_no_paid_dispatch_without_new_packet_bound_approval(tmp_path, monkeypatch):
    monkeypatch.setattr(diagnostic, "validate", lambda *_: None)
    monkeypatch.setattr(diagnostic, "environment", lambda: pytest.fail("must not dispatch"))
    with pytest.raises(ContractError, match="fresh exact two-run approval"):
        diagnostic.run(tmp_path, "frozen")
    diagnostic.save(
        tmp_path,
        "authorization.json",
        {
            "approved": True,
            "human_message": "old approval",
            "packet_hash": "old",
        },
    )
    with pytest.raises(ContractError, match="does not bind"):
        diagnostic.run(tmp_path, "frozen")


@pytest.mark.parametrize(
    "known,cost,expected_calls", [(False, 1, 1), (True, 3_000_000_001, 1), (True, 3_000_000_000, 2)]
)
def test_allocation_stops_on_uncertainty_and_never_exceeds_two_dispatches(
    tmp_path,
    monkeypatch,
    known,
    cost,
    expected_calls,
):
    monkeypatch.setattr(diagnostic, "LIVE", tmp_path / "live")
    monkeypatch.setattr(diagnostic, "validate", lambda *_: None)
    monkeypatch.setattr(diagnostic, "load_exact_openai_api_key", lambda _: "unused")
    package = SimpleNamespace(
        public=SimpleNamespace(repository=SimpleNamespace(base_commit="base"))
    )
    monkeypatch.setattr(
        diagnostic,
        "environment",
        lambda: (package, SimpleNamespace(image_identity=lambda: "image"), None, "profile"),
    )
    monkeypatch.setattr(diagnostic, "settled", lambda *_: known)
    calls = []

    def dispatch(req, root, label, digest, base):
        calls.append((label, req.max_cost_usd))
        return {"cost_nanos": cost, "runs": [{"artifact_hashes": {}}]}

    monkeypatch.setattr(diagnostic, "dispatch", dispatch)
    diagnostic.save(
        tmp_path,
        "authorization.json",
        {"approved": True, "human_message": "exact scope", "packet_hash": "frozen"},
    )
    diagnostic.save(tmp_path, "calibration.json", {"image": "image", "probe_profile": "profile"})
    diagnostic.save(tmp_path, "public-example.json", {})
    result = diagnostic.run(tmp_path, "frozen")
    assert calls == [
        (label, diagnostic.ROW_CAP) for label in list(diagnostic.SEEDS)[:expected_calls]
    ]
    assert result["allocation"] == "CLOSED" and not result["resume_allowed"]
    with pytest.raises(ContractError, match="no restart"):
        diagnostic.run(tmp_path, "frozen")


def test_dispatch_supplies_only_seed_and_common_notice(tmp_path, monkeypatch):
    (tmp_path / "A1.patch").write_text("public patch", encoding="utf-8")
    captured = {}
    monkeypatch.setattr(seeded, "run_seeded", lambda req, **kwargs: captured.update(kwargs))
    diagnostic.dispatch(diagnostic.request(tmp_path / "state"), tmp_path, "A1", "packet", "base")
    assert captured["review"] is None and captured["source_code"] == []
    assert set(captured) == {
        "seed_patch",
        "seed_hash",
        "base_commit",
        "source_code",
        "review",
        "experiment_hash",
        "source_run_id",
        "branch",
    }


@pytest.mark.parametrize(
    "billing,terminal,expected",
    [
        (None, "EVALUATOR_FAIL", True),
        (None, "COST_CAP_REACHED", True),
        ("UNKNOWN", "EVALUATOR_PASS", False),
        (None, "COUNT_TIMEOUT_OR_UNKNOWN", False),
        (None, "PROVIDER_TIMEOUT_OR_UNKNOWN", False),
        (None, "EVALUATOR_ERROR", False),
    ],
)
def test_settlement_matches_sparse_terminal_billing_contract(tmp_path, billing, terminal, expected):
    row = {"run_id": "run_dev_fixture", "terminal": terminal}
    if billing is not None:
        row["billing_state"] = billing
    assert diagnostic.settled({"completed_repetitions": 1, "runs": [row]}, tmp_path) is expected


@pytest.mark.parametrize("repair", [True, False], ids=["repair-seed", "preserve-seed"])
def test_seeded_selection_delivery_repair_or_preservation_and_isolated_evaluation(
    tmp_path,
    monkeypatch,
    gateway_factory,
    smoke_package,
    repair,
):
    task = tmp_path / "task"
    shutil.copytree(repository_root() / "tasks/smoke/csv-quoted-newline", task)
    public = yaml.safe_load((task / "public.yaml").read_text())
    public["test_suites"] = [suite().model_dump()]
    (task / "public.yaml").write_text(yaml.safe_dump(public), encoding="utf-8")
    gateway, _, workspace = gateway_factory()
    mutation = MockDevAdapter(smoke_package.public.task_id).mutation
    path = workspace / mutation.path
    content = path.read_text()
    path.write_text(
        "# Saved public candidate.\n"
        + (content if repair else content.replace(mutation.old_text, mutation.new_text)),
        encoding="utf-8",
        newline="",
    )
    patch = gateway.current_diff.patch
    inputs = []

    class SelectedSeedMock(MockDevAdapter):
        def _next_action(self, context, tools):
            inputs.append(json.loads(context))
            step = len(inputs)
            if step == 1 or (repair and step == 4):
                return DevModelTurn(tool_calls=[call(action_id=f"selected-{step}")])
            if repair and step == 2:
                return DevModelTurn(
                    tool_calls=[
                        RequestedTool(
                            name="read_file",
                            action_id="read-current",
                            arguments={"path": mutation.path, "start_line": 1, "end_line": 80},
                            turn_decision=PublicTurnDecision(
                                mode="inspect",
                                basis="Read current source.",
                                evidence_goal="Locate the parser lifetime.",
                            ),
                        )
                    ]
                )
            if repair and step == 3:
                return DevModelTurn(
                    tool_calls=[
                        RequestedTool(
                            name="replace_text",
                            action_id="repair-current",
                            arguments={
                                "path": mutation.path,
                                "old_text": mutation.old_text,
                                "new_text": mutation.new_text,
                                "occurrence": 1,
                                "hypothesis": mutation.hypothesis,
                                "expected_behavior": mutation.expected_behavior,
                                "causal_revision": None,
                            },
                            turn_decision=PublicTurnDecision(
                                mode="mutate", basis="Keep parser state."
                            ),
                        )
                    ]
                )
            return super()._next_action(context, tools)

    monkeypatch.setattr(runner, "MockDevAdapter", SelectedSeedMock)
    req = mock_request(tmp_path / "branch").model_copy(update={"task": task / "public.yaml"})
    run = seeded.run_seeded(
        req,
        seed_patch=patch,
        seed_hash=sha256_text(patch),
        base_commit=smoke_package.public.repository.base_commit,
        source_code=[],
        review=None,
        experiment_hash="sha256:" + "a" * 64,
        source_run_id="run_dev_saved",
        branch="uncued",
    )["runs"][0]
    assert run["terminal"] == "EVALUATOR_PASS" and run["evaluator"]["safety_state"] == "NOT_RUN"
    assert run["accepted_mutations"] == int(repair)
    assert inputs[0]["remaining_budget"]["accepted_mutations"] == 3
    journal = DevJournal(req.state_root, run["run_id"])
    from patchloop.artifacts import ArtifactStore

    store = ArtifactStore(req.state_root / "artifacts")
    delivered = []
    for event in journal.events():
        if event["event_type"] != "turn_started":
            continue
        items = runner._load_active_model_input(
            event["payload"], store, context_policy="segmented-v1"
        )
        state = reconstruct_state(items, context_policy="segmented-v1")
        assert state[seeded.FIELD]["reference_source"]["source_code"] == []
        assert diagnostic.TARGET not in json.dumps(state)
        assert "source_run_id" not in state[seeded.FIELD]
        delivered.extend(
            json.loads(item["output"])
            for item in items
            if item.get("type") == "function_call_output"
            and item["call_id"].startswith("selected-")
        )
    assert delivered and all(r["output"]["test_status"] == "PASS" for r in delivered)
