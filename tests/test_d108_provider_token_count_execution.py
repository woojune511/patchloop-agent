from __future__ import annotations

import copy
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from patchloop.errors import ContractError
from patchloop.memory import d108_provider_token_count_execution as d108
from patchloop.util import canonical_json, sha256_text

ROOT = Path(__file__).resolve().parents[1]


class _RawResponse:
    def __init__(self, input_tokens: int, request_id: str) -> None:
        self._parsed = SimpleNamespace(
            object="response.input_tokens",
            input_tokens=input_tokens,
        )
        self.request_id = request_id
        self.status_code = 200
        self.retries_taken = 0

    def parse(self) -> SimpleNamespace:
        return self._parsed


class _CountMethod:
    def __init__(self, counts: list[int], fail_at: int | None = None) -> None:
        self.counts = counts
        self.fail_at = fail_at
        self.calls: list[dict] = []

    def count(self, **payload):
        self.calls.append(copy.deepcopy(payload))
        call_number = len(self.calls)
        if self.fail_at == call_number:
            raise RuntimeError("synthetic count failure")
        return _RawResponse(self.counts[call_number - 1], f"req_test_{call_number}")


class _FakeClient:
    def __init__(self, counts: list[int], fail_at: int | None = None) -> None:
        method = _CountMethod(counts, fail_at=fail_at)
        self.method = method
        self.max_retries = 0
        self.base_url = "https://api.openai.com/v1/"
        self.timeout = SimpleNamespace(connect=5.0, read=600.0, write=600.0, pool=600.0)
        self.responses = SimpleNamespace(
            input_tokens=SimpleNamespace(with_raw_response=method)
        )


def _paths(prefix: str) -> tuple[tempfile.TemporaryDirectory, dict[str, Path]]:
    root = ROOT / ".patchloop"
    root.mkdir(exist_ok=True)
    temporary = tempfile.TemporaryDirectory(prefix=prefix, dir=root)
    directory = Path(temporary.name)
    return temporary, {
        "approval_path": d108.DEFAULT_APPROVAL_PATH,
        "journal_path": directory / "execution.jsonl",
        "provider_receipt_path": directory / "provider-receipt.json",
        "completion_gate_path": directory / "completion-gate.json",
    }


@pytest.fixture(autouse=True)
def _provider_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret-never-rendered")
    for name in (
        "OPENAI_BASE_URL",
        "OPENAI_API_BASE",
        "OPENAI_ORG_ID",
        "OPENAI_ORGANIZATION",
        "OPENAI_PROJECT",
    ):
        monkeypatch.delenv(name, raising=False)


def _no_call_deep_validator(_repository: Path) -> None:
    return None


def test_d108_approval_receipt_has_exact_narrow_scope() -> None:
    receipt = d108.build_d108_approval_receipt(repository=ROOT)
    scope = receipt["semantic_body"]["authorized_scope"]

    assert scope["provider_input_token_count_calls"] == 2
    assert scope["call_order"] == ["baseline", "with_memory"]
    assert scope["provider_generation_calls"] == 0
    assert scope["sdk_transport_max_retries"] == 0
    assert scope["automatic_retry_authorized"] is False
    assert scope["index_freeze_authorized"] is False
    assert scope["retrieval_experiment_authorized"] is False
    assert scope["runtime_memory_injection_authorized"] is False
    assert scope["core_campaign_authorized"] is False


def test_d108_fake_execution_calls_exact_pair_and_seals_receipt() -> None:
    temporary, paths = _paths("d108-success-")
    client = _FakeClient([2_000, 2_731])
    try:
        result = d108.execute_d108_provider_token_counts(
            repository=ROOT,
            client_factory=lambda _key: client,
            deep_source_validator=_no_call_deep_validator,
            **paths,
        )

        assert len(client.method.calls) == 2
        assert [request["input"] for request in client.method.calls]
        assert result["baseline_input_tokens"] == 2_000
        assert result["with_memory_input_tokens"] == 2_731
        assert result["memory_delta_tokens"] == 731
        assert result["provider_input_token_count_calls_made"] == 2
        assert result["provider_generation_calls_made"] == 0
        assert result["automatic_retry_used"] is False
        assert result["provider_exact_budget_validated"] is True
        assert result["index_freeze_authorized"] is False
        assert result["retrieval_ready"] is False
        assert result["core_campaign_unlocked"] is False

        validated = d108.validate_d108_completion_gate(
            paths["completion_gate_path"], repository=ROOT
        )
        assert validated["memory_delta_tokens"] == 731
        assert validated["index_freeze_authorization_candidate_ready"] is True
        assert validated["index_freeze_authorized"] is False
    finally:
        temporary.cleanup()


def test_d108_failed_first_call_is_not_retried_and_cannot_resume() -> None:
    temporary, paths = _paths("d108-failure-")
    client = _FakeClient([2_000, 2_731], fail_at=1)
    try:
        with pytest.raises(d108.D108ExecutionError, match="no retry or receipt"):
            d108.execute_d108_provider_token_counts(
                repository=ROOT,
                client_factory=lambda _key: client,
                deep_source_validator=_no_call_deep_validator,
                **paths,
            )
        assert len(client.method.calls) == 1
        assert paths["journal_path"].is_file()
        assert not paths["provider_receipt_path"].exists()
        assert not paths["completion_gate_path"].exists()

        second = _FakeClient([2_000, 2_731])
        with pytest.raises(d108.D108ExecutionError, match="journal already exists"):
            d108.execute_d108_provider_token_counts(
                repository=ROOT,
                client_factory=lambda _key: second,
                deep_source_validator=_no_call_deep_validator,
                **paths,
            )
        assert not second.method.calls
    finally:
        temporary.cleanup()


def test_d108_failed_second_call_retains_first_count_but_writes_no_receipt() -> None:
    temporary, paths = _paths("d108-second-failure-")
    client = _FakeClient([2_000, 2_731], fail_at=2)
    try:
        with pytest.raises(d108.D108ExecutionError, match="no retry or receipt"):
            d108.execute_d108_provider_token_counts(
                repository=ROOT,
                client_factory=lambda _key: client,
                deep_source_validator=_no_call_deep_validator,
                **paths,
            )
        assert len(client.method.calls) == 2
        journal = paths["journal_path"].read_text(encoding="utf-8")
        assert journal.count("ProviderInputTokenCountCallCompleted") == 1
        assert journal.count("ProviderInputTokenCountCallFailed") == 1
        assert not paths["provider_receipt_path"].exists()
        assert not paths["completion_gate_path"].exists()
    finally:
        temporary.cleanup()


def test_d108_custom_routing_is_rejected_before_client_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    temporary, paths = _paths("d108-custom-routing-")
    constructed = False

    def factory(_key: str) -> _FakeClient:
        nonlocal constructed
        constructed = True
        return _FakeClient([2_000, 2_731])

    try:
        monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
        with pytest.raises(d108.D108ExecutionError, match="custom OpenAI routing"):
            d108.execute_d108_provider_token_counts(
                repository=ROOT,
                client_factory=factory,
                deep_source_validator=_no_call_deep_validator,
                **paths,
            )
        assert constructed is False
        assert not paths["journal_path"].exists()
    finally:
        temporary.cleanup()


def test_d108_delta_over_budget_writes_no_receipt_or_gate() -> None:
    temporary, paths = _paths("d108-over-budget-")
    client = _FakeClient([2_000, 4_001])
    try:
        with pytest.raises(ContractError):
            d108.execute_d108_provider_token_counts(
                repository=ROOT,
                client_factory=lambda _key: client,
                deep_source_validator=_no_call_deep_validator,
                **paths,
            )
        assert len(client.method.calls) == 2
        assert paths["journal_path"].is_file()
        assert not paths["provider_receipt_path"].exists()
        assert not paths["completion_gate_path"].exists()
    finally:
        temporary.cleanup()


def test_d108_strict_receipt_rejects_unknown_field() -> None:
    plan, _ = d108._load_exact_plan(ROOT)
    receipt = d108._build_provider_receipt(
        plan,
        [
            {"object": "response.input_tokens", "input_tokens": 2_000},
            {"object": "response.input_tokens", "input_tokens": 2_731},
        ],
    )
    receipt["semantic_body"]["calls"][0]["unexpected"] = True
    body_hash = sha256_text(canonical_json(receipt["semantic_body"]))
    receipt["semantic_body_hash"] = body_hash
    receipt["receipt_id"] = f"d107countreceipt_{body_hash.removeprefix('sha256:')}"

    with pytest.raises(d108.D108ExecutionError, match="field set"):
        d108.validate_strict_provider_receipt(receipt, plan)


def test_d108_source_has_no_generation_freeze_or_retrieval_call_path() -> None:
    source = (
        ROOT / "patchloop/memory/d108_provider_token_count_execution.py"
    ).read_text(encoding="utf-8")

    assert ".responses.create(" not in source
    assert "freeze_index(" not in source
    assert "retrieve_memory(" not in source
    assert "OPENAI_API_KEY" in source
    assert "error_message_persisted" in source
