from __future__ import annotations

import json
from pathlib import Path

import pytest

from diagnostics import closure_policy_sampler as sampler
from diagnostics import selected_probe_continuation as continuation
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import canonical_json
from tests import test_closure_policy_sampler as fixtures
from tests.test_decision_sampler import FakeClient


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    return fixtures.prepared.__wrapped__(tmp_path, monkeypatch)


def record(prepared, name="run_probe"):
    def response(r):
        r.model = sampler.MODEL
        r.output[1].name = name
        r.output[1].arguments = canonical_json({
            "question": "Does the public behavior hold?", "python_source": "assert True",
            "turn_decision": {"mode": "verify", "basis": "Saved fixture only",
                              "memory_update": None, "plan_update": None}})
    fake = FakeClient(edit_response=response)
    sampler.collect(prepared.plan, prepared.grant, adapter_factory=fake.factory)
    # Fixture-only metadata makes the saved-response loader exercise its live path.
    path = prepared.grant.result_root / "envelope.json"
    envelope = json.loads(path.read_bytes())
    envelope["provider_free"] = False
    path.write_text(canonical_json(envelope), encoding="utf-8")
    return prepared.grant.result_root, fake


def test_real_saved_encrypted_order_and_usage_preserved(prepared):
    root, fake = record(prepared)
    cell, turn, binding = continuation.saved_response(root, prepared.plan)
    assert cell.arm == "B" and cell.sample_number == 2
    assert turn.response_id == fake.responses_returned[2].id
    assert turn.input_tokens == 100 and turn.output_tokens == 20
    assert turn.provider_continuation[0].encrypted_content == "new_cipher_3"
    assert turn.provider_continuation[1].action_id == turn.tool_calls[0].action_id
    assert binding["usage"]["billing_known"]
    assert len(fake.created) == 4  # Loading the saved response made no extra call.


def test_wrong_selected_action_rejected(prepared):
    root, _ = record(prepared, name="read_file")
    with pytest.raises(ContractError, match="not one probe"):
        continuation.saved_response(root, prepared.plan)


def test_unsettled_collection_rejected(prepared):
    root, _ = record(prepared)
    path = root / "result.json"
    result = json.loads(path.read_bytes())
    result["total_cost_known"] = False
    path.write_text(canonical_json(result), encoding="utf-8")
    with pytest.raises(ContractError, match="not settled"):
        continuation.saved_response(root, prepared.plan)


def test_cipher_integrity_failure_is_not_replaced_with_synthetic_state(prepared):
    root, _ = record(prepared)
    env = json.loads((root / "envelope.json").read_bytes())
    events = DevJournal(root, env["run_id"]).events()
    sample = next(e["payload"] for e in events if e["event_type"] == "sample_recorded"
                  and e["payload"]["arm"] == "B" and e["payload"]["sample_number"] == 2)
    Path(sample["continuation_ref"]["artifact"]["path"]).write_bytes(b"damaged")
    with pytest.raises(Exception, match="continuation"):
        continuation.saved_response(root, prepared.plan)


def test_capture_signal_bypasses_provider_exception_handlers():
    assert issubclass(continuation.BoundaryCaptured, BaseException)
    assert not issubclass(continuation.BoundaryCaptured, Exception)
