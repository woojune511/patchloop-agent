from __future__ import annotations

import re
from pathlib import Path

from patchloop.memory import d108_provider_token_count_execution as d108

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = (
    d108.DEFAULT_APPROVAL_PATH,
    d108.DEFAULT_JOURNAL_PATH,
    d108.DEFAULT_PROVIDER_RECEIPT_PATH,
    d108.DEFAULT_COMPLETION_GATE_PATH,
)


def test_d108_checked_in_completion_gate_exactly_rebuilds() -> None:
    result = d108.validate_d108_completion_gate(repository=ROOT)

    assert result["baseline_input_tokens"] == 2_193
    assert result["with_memory_input_tokens"] == 2_895
    assert result["memory_delta_tokens"] == 702
    assert result["maximum_memory_delta_tokens"] == 2_000
    assert result["provider_input_token_count_calls_made"] == 2
    assert result["provider_generation_calls_made"] == 0
    assert result["automatic_retry_used"] is False
    assert result["provider_exact_budget_validated"] is True
    assert result["index_freeze_authorization_candidate_ready"] is True
    assert result["index_freeze_authorized"] is False
    assert result["retrieval_ready"] is False
    assert result["core_campaign_unlocked"] is False


def test_d108_portable_artifacts_contain_no_secret_shaped_value() -> None:
    secret_pattern = re.compile(rb"(?i)(?:sk-[a-z0-9_-]{8,}|bearer\s+[a-z0-9._-]+)")

    for relative in ARTIFACTS:
        content = (ROOT / relative).read_bytes()
        assert b"OPENAI_API_KEY" not in content
        assert secret_pattern.search(content) is None
