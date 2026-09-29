import json
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from diagnostics import prior_decision_sampler as s
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_json
from tests.test_decision_sampler import FakeClient, events
from tests.test_evidence_context_sampler import report_response
from tests.test_prior_decision_design import original


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    views, audit = s.design.project(original())
    cases = {c: (views, {**audit, "source_receipt": {"turn_id": c}})
             for c in ("C1", "C2", "C3", "C4")}
    source = tmp_path / "source.json"
    source.write_text(canonical_json({"source_bindings": {}}))
    monkeypatch.setattr(s.design, "inputs", lambda *args: cases)
    prep = tmp_path / "preparation"
    s.design.prepare(source, "synthetic", prep)

    def forbidden(*args, **kwargs):
        pytest.fail("live provider, credential or action reached")

    monkeypatch.setattr(s.shared, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(s.shared, "create_openai_client", forbidden)
    monkeypatch.setattr("patchloop.dev.tools.DevToolGateway.execute", forbidden)
    root = tmp_path / "plan"
    digest = s.prepare(prep / "packet.json", root)
    plan = s.load_plan(root / "packet.json", digest)
    # Source protection includes the original preparation's parent.
    approval = s.shared.Approval(
        digest, sha256_json(s.hashes()), tmp_path.parent / (tmp_path.name + "-result"),
        s.repository_root() / ".env", Decimal("9"),
        sha256_json(s.shared.protocol_prices(s.protocol())),
        datetime.now(UTC).date().isoformat())
    return plan, approval


def test_exact_sixteen_requests_only_prior_decisions_differ(prepared):
    plan, approval = prepared
    fake = FakeClient(edit_response=report_response)
    result = s.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == "SAMPLES_COLLECTED" and result["sample_count"] == 16
    assert result["provider_free"] and result["tool_executions"] == 0
    assert result["task_acceptance"] == result["safety_state"] == "NOT_RUN"
    assert len(fake.created) == len(fake.counted) == 16
    for cell, sent in zip(plan.cells, fake.created, strict=True):
        assert sha256_json({k: v for k, v in sent.items() if k != "timeout"}) == cell.request_hash
        view = json.loads(sent["input"][1]["content"])
        assert ("turn_decision" in view["evidence"]["recent_attempt_result_next_question"][0]
                ) == (cell.arm == "A")
        assert sent["input"][0]["content"] == s.design.base.QUESTION
        assert sent["tools"] == [s.previous.REPORT]
        assert "new_cipher_" not in canonical_json(sent)
        assert "borderline" not in canonical_json(sent)
    for e in events(approval):
        if e["event_type"] == "sample_recorded":
            public = json.loads(Path(e["payload"]["public_artifact"]["path"]).read_bytes())
            assert public["report_status"] == "VALID"


@pytest.mark.parametrize("mode,terminal", [
    ("count", "COUNT_TIMEOUT_OR_UNKNOWN"), ("transport", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
    ("billing", "PROVIDER_TIMEOUT_OR_UNKNOWN")])
def test_stop_all_on_uncertainty(prepared, mode, terminal):
    plan, approval = prepared

    def edit(r):
        report_response(r)
        if mode == "billing":
            r.usage = None

    fake = FakeClient(edit_response=edit, count_error=mode == "count",
                      create_error=mode == "transport")
    result = s.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == terminal
    assert len(fake.created) == (0 if mode == "count" else 1)


def test_cap_and_preparation_tamper_reject_before_dispatch(prepared):
    plan, approval = prepared
    with pytest.raises(ContractError, match="cap mismatch"):
        s.collect(plan, replace(approval, max_cost_usd=Decimal("10")))
    packet = json.loads(Path(plan.packet["preparation_path"]).read_bytes())
    Path(packet["cases"]["C1"]["views"]["B"]["path"]).write_text("{}")
    with pytest.raises(ContractError, match="source CAS"):
        s.collect(plan, approval)
    assert not approval.result_root.exists()


def test_same_settings_schedule_and_conservative_cost():
    assert s.SCHEDULE == s.previous.SCHEDULE
    assert replace(s.protocol(), kind=s.previous.SCHEMA) == s.previous.protocol()
    assert s.shared.full_reservation(60_000, s.shared.cell_profile(s.protocol(), "A").pricing()
                                    ) * 16 == 8_400_000_000
