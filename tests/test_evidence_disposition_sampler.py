import copy
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from diagnostics import decision_sampler as shared
from diagnostics import evidence_disposition_sampler as s
from patchloop.dev.conversation import assemble_model_input
from patchloop.dev.tools import dev_tool_schemas
from patchloop.errors import ContractError
from patchloop.util import sha256_json
from tests.test_decision_sampler import FakeClient


def request():
    names = ["read_file", "search_files", "run_probe", "finish_task", "stop_task"]
    state = {
        "public_task": {"task_id": "synthetic"}, "workflow_gate": "ready_to_submit",
        "remaining_visible_check_ids": [], "current_diff": {"patch_hash": "current"},
        "visible_check_status": [{"status": "PASS", "diff_hash": "current"}],
        "available_tool_names": names,
    }
    return {**shared.SETTINGS, "model": s.MODEL, "reasoning": {"effort": "xhigh"},
            "input": assemble_model_input(system_prompt="public instructions", state=state,
                                          history=[], context_policy="segmented-v1"),
            "tools": dev_tool_schemas(finish_enabled=True, check_ids=[],
                                       allowed_tools=names, read_paths=[])}


def test_only_system_instruction_changes_without_task_hint_or_score():
    original = request()
    before = copy.deepcopy(original)
    pair = s.project(original)
    assert original == before == pair["A"]
    assert pair["B"]["input"][1:] == original["input"][1:]
    restored = copy.deepcopy(pair["B"])
    restored["input"][0]["content"] = original["input"][0]["content"]
    assert restored == original
    assert not any(word in s.INSTRUCTION for word in ("HfApi", "wrapped_name", "C1", "endpoint"))


@pytest.mark.parametrize("change", ["remaining", "stale_check", "no_probe"])
def test_submission_and_choice_gates(change):
    import json
    original = request()
    item = original["input"][-1]
    view = json.loads(item["content"])
    if change == "remaining":
        view["state"]["remaining_visible_check_ids"] = ["other"]
    elif change == "stale_check":
        view["state"]["visible_check_status"][0]["diff_hash"] = "old"
    else:
        original["tools"] = [t for t in original["tools"] if t["name"] != "run_probe"]
    item["content"] = json.dumps(view)
    with pytest.raises(ContractError):
        s.project(original)


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    loaded = {case: (s.project(request()),
                    {"turn_id": case, "max_parallel_reads": 4, "targeted_read_paths": []},
                    {"task_content_hash": "public", "turn_id": case})
              for case in ("C1", "C2", "C3")}
    monkeypatch.setattr(s, "sources", lambda: (loaded, {}))

    def forbidden(*args, **kwargs):
        pytest.fail("live provider, credential or tool execution reached")

    monkeypatch.setattr(shared, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(shared, "create_openai_client", forbidden)
    monkeypatch.setattr("patchloop.dev.tools.DevToolGateway.execute", forbidden)
    design = tmp_path / "design"
    digest = s.prepare(design)
    plan = s.load_plan(design / "packet.json", digest)
    approval = shared.Approval(
        digest, sha256_json(s.hashes()), tmp_path / "results",
        s.repository_root() / ".env", Decimal("8"),
        sha256_json(shared.protocol_prices(s.protocol())), datetime.now(UTC).date().isoformat())
    return plan, approval


def test_twelve_mock_responses_no_tools_no_chaining(prepared):
    plan, approval = prepared
    fake = FakeClient(edit_response=lambda r: setattr(r, "model", s.MODEL))
    result = s.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == "SAMPLES_COLLECTED"
    assert result["provider_free"] and result["sample_count"] == 12
    assert result["tool_executions"] == 0 and result["task_acceptance"] == "NOT_RUN"
    assert len(fake.counted) == len(fake.created) == 12
    for cell, sent in zip(plan.cells, fake.created, strict=True):
        assert sha256_json({k: v for k, v in sent.items() if k != "timeout"}) == cell.request_hash
        assert "new_cipher_" not in str(sent)


def test_transport_uncertainty_stops_all_cells(prepared):
    plan, approval = prepared
    fake = FakeClient(create_error=True)
    result = s.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == "PROVIDER_TIMEOUT_OR_UNKNOWN"
    assert len(fake.created) == 1 and result["sample_count"] == 0


def test_packet_and_cap_changes_reject_before_provider(prepared):
    from dataclasses import replace
    plan, approval = prepared
    with pytest.raises(ContractError, match="cap mismatch"):
        s.collect(plan, replace(approval, max_cost_usd=Decimal("9")))
    plan.packet_path.write_text("{}")
    with pytest.raises(ContractError, match="packet changed"):
        s.collect(plan, approval)


def test_full_reservations_and_balanced_pairs():
    price = shared.cell_profile(s.protocol(), "A").pricing()
    assert shared.full_reservation(60_000, price) * len(s.SCHEDULE) == 6_300_000_000
    for i in range(0, len(s.SCHEDULE), 2):
        first, second = s.SCHEDULE[i:i+2]
        assert first[0] == second[0] and first[2] == second[2]
        assert {first[1], second[1]} == {"A", "B"}
