from __future__ import annotations

import json
from pathlib import Path

from patchloop.agent import workflow_causal_alternative_rapid_activation_qualification as q
from patchloop.util import sha256_bytes

REPOSITORY = Path(__file__).resolve().parents[1]


def test_superseded_activation_v1_is_preserved_byte_for_byte() -> None:
    raw = (REPOSITORY / q.QUALIFICATION_PATH).read_bytes()
    value = json.loads(raw)

    assert raw == q.qualification_bytes(value)
    assert len(raw) == 10_595
    assert sha256_bytes(raw) == (
        "sha256:526c957b55e1598c9d02fbdb666985aa5bcdc5c43f1165911de829988ffce253"
    )
    assert value["content_hash"] == (
        "sha256:7df7b1be0a0ef388806870d81322d81943d758774e213dfa86ab6f62357f5371"
    )
    assert value["schema_version"] == ("lean-causal-alternative-rapid-activation-qualification-v1")
    assert value["source_transition"]["observed_changed_paths"] == ["patchloop/contracts.py"]
    assert value["runtime_activation_authorized"] is False
    assert value["paid_execution_authorized"] is False
