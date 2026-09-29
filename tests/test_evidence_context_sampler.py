import json
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from diagnostics import decision_sampler as shared
from diagnostics import evidence_context_sampler as s
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_json
from tests.test_decision_sampler import FakeClient, events
from tests.test_evidence_context_design import source


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    views, receipt = s.design.project(source())
    cases = {c: (views, {**receipt, "turn_id": c}) for c in ("C1", "C2", "C3", "C4")}
    monkeypatch.setattr(s.design, "load_sources", lambda: (cases, {}))

    def forbidden(*args, **kwargs):
        pytest.fail("credential, provider or tool execution reached")

    monkeypatch.setattr(shared, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(shared, "create_openai_client", forbidden)
    monkeypatch.setattr("patchloop.dev.tools.DevToolGateway.execute", forbidden)
    prep = tmp_path / "preparation"
    s.design.prepare(prep)
    root = tmp_path / "plan"
    digest = s.prepare(prep / "packet.json", root)
    plan = s.load_plan(root / "packet.json", digest)
    approval = shared.Approval(
        digest, sha256_json(s.hashes()), tmp_path / "result", s.repository_root() / ".env",
        Decimal("9"), sha256_json(shared.protocol_prices(s.protocol())),
        datetime.now(UTC).date().isoformat())
    return plan, approval


def report_response(response):
    response.model = s.MODEL
    response.output[1].name = "record_assessment"
    response.output[1].arguments = canonical_json({"assessment": "Public evidence is limited."})


def test_sixteen_reports_no_execution_chaining_or_rubric(prepared):
    plan, approval = prepared
    fake = FakeClient(edit_response=report_response)
    result = s.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == "SAMPLES_COLLECTED"
    assert result["sample_count"] == len(fake.created) == len(fake.counted) == 16
    assert result["provider_free"] and result["tool_executions"] == 0
    assert result["task_acceptance"] == result["safety_state"] == "NOT_RUN"
    assert result["completed_comparison_blocks"] == 8
    for cell, sent in zip(plan.cells, fake.created, strict=True):
        assert sha256_json({k: v for k, v in sent.items() if k != "timeout"}) == cell.request_hash
        assert sent["tools"] == [s.REPORT] and not sent["parallel_tool_calls"]
        assert sent["input"][0]["content"] == s.design.QUESTION
        assert "new_cipher_" not in canonical_json(sent)
        assert "Primary supported assessment" not in canonical_json(sent)
    rows = [e["payload"] for e in events(approval) if e["event_type"] == "sample_recorded"]
    for row in rows:
        public = json.loads(Path(row["public_artifact"]["path"]).read_bytes())
        assert public["report_status"] == "VALID" and public["error_code"] is None
        assert public["report"]["assessment"] == "Public evidence is limited."
        assert not {"arm", "cost_nanos", "latency"} & public.keys()
        encrypted = Path(row["report_continuation_artifact"]["path"]).read_text()
        assert "PLAINTEXT_REASONING_SENTINEL" not in encrypted
        assert "new_cipher_" in encrypted and row["continuation_ref"] is None


@pytest.mark.parametrize("mode,terminal,calls", [
    ("count", "COUNT_TIMEOUT_OR_UNKNOWN", 0),
    ("transport", "PROVIDER_TIMEOUT_OR_UNKNOWN", 1),
    ("billing", "PROVIDER_TIMEOUT_OR_UNKNOWN", 1),
    ("continuation", "PROVIDER_CONTINUATION_ERROR", 1),
])
def test_uncertainty_stops_without_retry(prepared, mode, terminal, calls):
    plan, approval = prepared

    def edit(response):
        report_response(response)
        if mode == "billing":
            response.usage = None
        if mode == "continuation":
            response.output[0].encrypted_content = None

    fake = FakeClient(edit_response=edit, count_error=mode == "count",
                      create_error=mode == "transport")
    result = s.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == terminal and len(fake.created) == calls
    assert result["sample_count"] == 0


@pytest.mark.parametrize("mode", ["wrong_name", "extra_field", "empty", "incomplete"])
def test_invalid_report_is_retained_not_corrected(prepared, mode):
    plan, approval = prepared

    def edit(response):
        report_response(response)
        if mode == "wrong_name":
            response.output[1].name = "run_check"
        elif mode == "extra_field":
            response.output[1].arguments = '{"assessment":"claim","extra":1}'
        elif mode == "empty":
            response.output[1].arguments = '{"assessment":" "}'
        else:
            response.status = "incomplete"

    fake = FakeClient(edit_response=edit)
    result = s.collect(plan, approval, adapter_factory=fake.factory)
    assert result["sample_count"] == 16 and len(fake.created) == 16
    for event in events(approval):
        if event["event_type"] == "sample_recorded":
            public = json.loads(Path(event["payload"]["public_artifact"]["path"]).read_bytes())
            assert public["report_status"] == "NOT_ASSESSABLE" and public["report"] is None


def test_approval_and_tampering_reject_before_provider(prepared):
    plan, approval = prepared
    with pytest.raises(ContractError, match="cap mismatch"):
        s.collect(plan, replace(approval, max_cost_usd=Decimal("10")))
    with pytest.raises(ContractError, match="wrong credential"):
        s.collect(plan, replace(approval,
                               credential_file=approval.credential_file.with_name("other.env")))
    path = Path(plan.packet["preparation_path"])
    packet = json.loads(path.read_bytes())
    artifact = Path(packet["cases"]["C4"]["views"]["B"]["path"])
    artifact.write_text("{}")
    with pytest.raises(ContractError, match="artifact changed"):
        s.collect(plan, approval)
    assert not approval.result_root.exists()


def test_full_reservations_and_counterbalanced_pairs():
    price = shared.cell_profile(s.protocol(), "A").pricing()
    assert shared.full_reservation(60_000, price) * len(s.SCHEDULE) == 8_400_000_000
    for case in ("C1", "C2", "C3", "C4"):
        first = [a for c, a, n in s.SCHEDULE if c == case and n == 1]
        second = [a for c, a, n in s.SCHEDULE if c == case and n == 2]
        assert first == second[::-1] and set(first) == {"A", "B"}
