from __future__ import annotations

import copy
from pathlib import Path

import pytest

from patchloop.contracts import MemoryCondition, Phase
from patchloop.errors import ContractError
from patchloop.memory import d110_index_freeze_execution as d110
from patchloop.memory import retrieval as memory_retrieval
from patchloop.util import canonical_json, sha256_text

ROOT = Path(__file__).resolve().parents[1]
FIXED_START = "2026-08-06T13:00:00.123456Z"


@pytest.fixture(scope="module")
def exact_d109_context() -> dict:
    return d110._load_exact_d109(ROOT, verify_live_runtime=False)


@pytest.fixture(scope="module")
def exact_pre_index() -> tuple[dict, bytes]:
    return d110._load_exact_pre_index(ROOT)


def _prepare_temp_execution_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    exact_d109_context: dict,
    pre_content: bytes,
) -> None:
    portable_pre = tmp_path / d110.d109.DEFAULT_PORTABLE_INDEX_PATH
    runtime_index = tmp_path / d110.DEFAULT_RUNTIME_INDEX_PATH
    approval_path = tmp_path / d110.DEFAULT_APPROVAL_PATH
    for path in (portable_pre, runtime_index, approval_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    portable_pre.write_bytes(pre_content)
    runtime_index.write_bytes(pre_content)
    approval = d110.build_d110_approval_receipt(
        repository=ROOT,
        _d109_context=exact_d109_context,
    )
    approval_path.write_bytes(d110._pretty_json(approval))
    monkeypatch.setattr(
        d110,
        "_load_exact_d109",
        lambda repository, verify_live_runtime: exact_d109_context,
    )
    monkeypatch.setattr(
        d110,
        "_implementation_bindings",
        lambda repository: [
            {
                "path": path.as_posix(),
                "file_bytes": index + 1,
                "file_sha256": "sha256:" + f"{index + 1:064x}",
            }
            for index, path in enumerate(d110.D110_IMPLEMENTATION_PATHS)
        ],
    )


def test_d110_approval_binds_exact_candidate_and_keeps_later_actions_closed(
    exact_d109_context: dict,
) -> None:
    approval = d110.build_d110_approval_receipt(
        repository=ROOT,
        _d109_context=exact_d109_context,
    )
    body = approval["semantic_body"]
    assert body["d109_candidate"] == {
        "path": "reports/memory-development/d109-index-freeze-authorization-candidate.json",
        "schema_version": "memory-index-freeze-authorization-candidate-d109-v1",
        "candidate_id": d110.EXPECTED_CANDIDATE_ID,
        "semantic_body_hash": d110.EXPECTED_CANDIDATE_BODY_SHA,
        "file_bytes": d110.EXPECTED_CANDIDATE_BYTES,
        "file_sha256": d110.EXPECTED_CANDIDATE_FILE_SHA,
    }
    scope = body["authorized_scope"]
    assert scope["freeze_execution_count"] == 1
    assert scope["automatic_retry_authorized"] is False
    assert scope["provider_calls_authorized"] == 0
    assert scope["evaluator_calls_authorized"] == 0
    assert scope["retrieval_authorized"] is False
    assert scope["runtime_memory_injection_authorized"] is False
    assert scope["core_campaign_authorized"] is False
    assert scope["analysis_authorized"] is False
    assert body["reviewer_identity_authenticated"] is False
    assert body["cryptographic_signature_verified"] is False


def test_d110_rehashed_approval_scope_tamper_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exact_d109_context: dict,
) -> None:
    approval = d110.build_d110_approval_receipt(
        repository=ROOT,
        _d109_context=exact_d109_context,
    )
    tampered = copy.deepcopy(approval)
    tampered["semantic_body"]["authorized_scope"]["retrieval_authorized"] = True
    body_hash = sha256_text(canonical_json(tampered["semantic_body"]))
    tampered["semantic_body_hash"] = body_hash
    tampered["receipt_id"] = f"d110approval_{body_hash.removeprefix('sha256:')}"
    path = tmp_path / "approval.json"
    path.write_bytes(d110._pretty_json(tampered))
    monkeypatch.setattr(
        d110,
        "_load_exact_d109",
        lambda repository, verify_live_runtime: exact_d109_context,
    )
    with pytest.raises(d110.D110ExecutionError, match="approval drifted"):
        d110.validate_d110_approval_receipt(path, repository=tmp_path)


def test_d110_post_transform_changes_exact_five_pointers_and_hash(
    exact_pre_index: tuple[dict, bytes],
) -> None:
    pre, _ = exact_pre_index
    post = d110.build_d110_post_freeze_index(pre, execution_started_at=FIXED_START)
    result = d110.validate_d110_post_freeze_index(
        pre,
        post,
        execution_started_at=FIXED_START,
    )
    assert result["mutation_paths"] == list(d110.ALLOWED_MUTATION_POINTERS)
    assert d110._json_diff_paths(pre, post) == sorted(d110.ALLOWED_MUTATION_POINTERS)
    assert post["frozen"] is True
    assert post["frozen_at"] == FIXED_START
    assert post["authority"]["index_freeze_authorized"] is True
    assert post["authority"]["memory_index_frozen"] is True
    assert post["authority"]["retrieval_experiment_authorized"] is False
    assert post["authority"]["runtime_memory_injection_count"] == 0
    assert post["authority"]["core_campaign_unlocked"] is False
    without_hash = {key: value for key, value in post.items() if key != "content_hash"}
    assert post["content_hash"] == sha256_text(canonical_json(without_hash))


def test_d110_post_transform_rejects_preexisting_frozen_at(
    exact_pre_index: tuple[dict, bytes],
) -> None:
    pre, _ = exact_pre_index
    tampered = copy.deepcopy(pre)
    tampered["frozen_at"] = "2026-08-06T00:00:00Z"
    with pytest.raises(d110.D110ExecutionError, match="already has frozen_at"):
        d110.build_d110_post_freeze_index(tampered, execution_started_at=FIXED_START)


def test_d110_post_validator_rejects_rehashed_unapproved_field(
    exact_pre_index: tuple[dict, bytes],
) -> None:
    pre, _ = exact_pre_index
    post = d110.build_d110_post_freeze_index(pre, execution_started_at=FIXED_START)
    post["authority"]["retrieval_ready"] = True
    without_hash = {key: value for key, value in post.items() if key != "content_hash"}
    post["content_hash"] = sha256_text(canonical_json(without_hash))
    with pytest.raises(d110.D110ExecutionError, match="five-pointer whitelist"):
        d110.validate_d110_post_freeze_index(
            pre,
            post,
            execution_started_at=FIXED_START,
        )


def test_d110_post_validator_rejects_unapproved_index_identity(
    exact_pre_index: tuple[dict, bytes],
) -> None:
    pre, _ = exact_pre_index
    tampered_pre = copy.deepcopy(pre)
    tampered_pre["index_version"] = "idx_not_approved"
    without_hash = {
        key: value for key, value in tampered_pre.items() if key != "content_hash"
    }
    tampered_pre["content_hash"] = sha256_text(canonical_json(without_hash))
    with pytest.raises(d110.D110ExecutionError, match="index ID drifted"):
        d110.build_d110_post_freeze_index(
            tampered_pre,
            execution_started_at=FIXED_START,
        )


def test_d110_new_output_path_rejects_linklike_existing_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    linked_parent = tmp_path / "linked-parent"
    linked_parent.mkdir()
    monkeypatch.setattr(d110, "_is_linklike", lambda path: path == linked_parent)
    with pytest.raises(d110.D110ExecutionError, match="link or junction"):
        d110._resolved(
            linked_parent / "new" / "artifact.json",
            repository=tmp_path,
            label="new artifact",
            must_exist=False,
        )


def test_d110_atomic_index_then_binary_lf_marker(
    tmp_path: Path,
    exact_pre_index: tuple[dict, bytes],
) -> None:
    pre, pre_content = exact_pre_index
    post = d110.build_d110_post_freeze_index(pre, execution_started_at=FIXED_START)
    post_content = d110._pretty_json(post)
    marker_content = (post["content_hash"] + "\n").encode("ascii")
    target_dir = tmp_path / "indexes" / d110.EXPECTED_INDEX_ID
    target_dir.mkdir(parents=True)
    target = target_dir / "index.json"
    marker = target_dir / "FROZEN"
    staged = tmp_path / "freeze-state" / "index.json.staged"
    target.write_bytes(pre_content)

    d110._atomic_replace_index(
        target,
        staged,
        expected_pre_content=pre_content,
        post_content=post_content,
        marker_path=marker,
    )
    assert target.read_bytes() == post_content
    assert not marker.exists()
    d110._create_marker(marker, marker_content)
    assert marker.read_bytes() == marker_content
    assert marker.read_bytes().endswith(b"\n")
    assert b"\r\n" not in marker.read_bytes()
    assert sorted(path.name for path in target_dir.iterdir()) == ["FROZEN", "index.json"]


def test_d110_index_marker_crash_window_is_partial_and_not_rolled_back(
    tmp_path: Path,
    exact_pre_index: tuple[dict, bytes],
) -> None:
    pre, pre_content = exact_pre_index
    post = d110.build_d110_post_freeze_index(pre, execution_started_at=FIXED_START)
    post_content = d110._pretty_json(post)
    target_dir = tmp_path / "indexes" / d110.EXPECTED_INDEX_ID
    target_dir.mkdir(parents=True)
    target = target_dir / "index.json"
    marker = target_dir / "FROZEN"
    staged = tmp_path / "freeze-state" / "index.json.staged"
    target.write_bytes(pre_content)

    def crash(stage: str) -> None:
        if stage == "after_index_replaced":
            raise RuntimeError("injected crash after index replace")

    with pytest.raises(RuntimeError, match="injected crash"):
        d110._atomic_replace_index(
            target,
            staged,
            expected_pre_content=pre_content,
            post_content=post_content,
            marker_path=marker,
            fault_injector=crash,
        )
    assert target.read_bytes() == post_content
    assert not marker.exists()


def test_d110_journal_exclusive_create_consumes_one_use(tmp_path: Path) -> None:
    path = tmp_path / "execution.jsonl"
    first = d110._ExecutionJournal(path)
    first.open()
    first.append(
        "FreezeExecutionClaimed",
        {"approval_action_id": d110.APPROVAL_ACTION_ID},
        recorded_at=FIXED_START,
    )
    first.close()
    second = d110._ExecutionJournal(path)
    with pytest.raises(d110.D110ExecutionError, match="already exists"):
        second.open()
    loaded = d110._load_journal(path)
    assert loaded["record_count"] == 1


def test_d110_full_executor_freezes_exact_copy_once_and_keeps_retrieval_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exact_d109_context: dict,
    exact_pre_index: tuple[dict, bytes],
) -> None:
    _, pre_content = exact_pre_index
    _prepare_temp_execution_repository(
        tmp_path,
        monkeypatch,
        exact_d109_context=exact_d109_context,
        pre_content=pre_content,
    )

    result = d110.execute_d110_index_freeze(repository=tmp_path)
    assert result["memory_index_frozen"] is True
    assert result["retrieval_ready"] is False
    assert result["runtime_memory_injection_count"] == 0
    assert result["core_campaign_unlocked"] is False
    assert (tmp_path / d110.d109.DEFAULT_PORTABLE_INDEX_PATH).read_bytes() == pre_content
    assert (tmp_path / d110.DEFAULT_RUNTIME_MARKER_PATH).read_bytes() == (
        result["content_hash"] + "\n"
    ).encode("ascii")
    portable_only = d110.validate_d110_completion_gate(repository=tmp_path)
    assert portable_only["memory_index_frozen_at_execution"] is True
    assert portable_only["current_runtime_memory_index_frozen"] is None
    assert portable_only["memory_index_frozen"] is None
    with pytest.raises(d110.D110ExecutionError, match="already consumed"):
        d110.execute_d110_index_freeze(repository=tmp_path)


def test_d110_full_executor_crash_after_index_commit_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exact_d109_context: dict,
    exact_pre_index: tuple[dict, bytes],
) -> None:
    _, pre_content = exact_pre_index
    _prepare_temp_execution_repository(
        tmp_path,
        monkeypatch,
        exact_d109_context=exact_d109_context,
        pre_content=pre_content,
    )

    def crash(stage: str) -> None:
        if stage == "after_index_replaced":
            raise RuntimeError("injected full-executor crash")

    with pytest.raises(d110.D110ExecutionError, match="index-mutation-issued"):
        d110.execute_d110_index_freeze(
            repository=tmp_path,
            _fault_injector=crash,
        )
    assert (tmp_path / d110.DEFAULT_RUNTIME_INDEX_PATH).read_bytes() != pre_content
    assert not (tmp_path / d110.DEFAULT_RUNTIME_MARKER_PATH).exists()
    journal = d110._load_journal(tmp_path / d110.DEFAULT_JOURNAL_PATH)
    assert journal["records"][-1]["event_type"] == "FreezeExecutionFailed"
    assert (tmp_path / d110.DEFAULT_EXECUTION_LOCK_PATH).exists()
    assert not (tmp_path / d110.DEFAULT_COMPLETION_GATE_PATH).exists()
    with pytest.raises(d110.D110ExecutionError, match="execution lock already exists"):
        d110.execute_d110_index_freeze(repository=tmp_path)


def test_d110_completion_gate_failure_is_journaled_and_not_retried(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exact_d109_context: dict,
    exact_pre_index: tuple[dict, bytes],
) -> None:
    _, pre_content = exact_pre_index
    _prepare_temp_execution_repository(
        tmp_path,
        monkeypatch,
        exact_d109_context=exact_d109_context,
        pre_content=pre_content,
    )

    def crash(stage: str) -> None:
        if stage == "after_completion_gate_write":
            raise RuntimeError("injected completion-gate crash")

    with pytest.raises(d110.D110ExecutionError, match="completion-gate"):
        d110.execute_d110_index_freeze(
            repository=tmp_path,
            _fault_injector=crash,
        )
    journal = d110._load_journal(tmp_path / d110.DEFAULT_JOURNAL_PATH)
    assert journal["records"][-1]["event_type"] == "FreezeExecutionFailed"
    assert not (tmp_path / d110.DEFAULT_EXECUTION_LOCK_PATH).exists()
    assert (tmp_path / d110.DEFAULT_COMPLETION_GATE_PATH).exists()
    with pytest.raises(d110.D110ExecutionError, match="eight journal records"):
        d110.validate_d110_completion_gate(repository=tmp_path)
    with pytest.raises(d110.D110ExecutionError, match="already consumed"):
        d110.execute_d110_index_freeze(repository=tmp_path)


def test_d110_frozen_index_still_blocks_retrieval_before_embedding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exact_pre_index: tuple[dict, bytes],
) -> None:
    pre, _ = exact_pre_index
    post = d110.build_d110_post_freeze_index(pre, execution_started_at=FIXED_START)
    index_path = tmp_path / "index.json"
    index_path.write_bytes(d110._pretty_json(post))
    monkeypatch.setattr(
        memory_retrieval,
        "_query_embedding",
        lambda *args, **kwargs: pytest.fail("embedding must not run before authorization"),
    )
    with pytest.raises(ContractError, match="later explicit authorization gate"):
        memory_retrieval.retrieve_memory(
            run_id="run_d110_retrieval_closed",
            query="test query",
            phase=Phase.REVIEW,
            condition=MemoryCondition.STRUCTURED,
            index_path=index_path,
        )


def test_d110_checked_in_approval_or_completion_state_is_exact(
    monkeypatch: pytest.MonkeyPatch,
    exact_d109_context: dict,
) -> None:
    monkeypatch.setattr(
        d110,
        "_load_exact_d109",
        lambda repository, verify_live_runtime: exact_d109_context,
    )
    approval = d110.validate_d110_approval_receipt(repository=ROOT)
    assert approval["self_attested"] is True
    gate = ROOT / d110.DEFAULT_COMPLETION_GATE_PATH
    if gate.exists():
        result = d110.validate_d110_completion_gate(
            repository=ROOT,
            verify_live_runtime=True,
        )
        assert result["memory_index_frozen"] is True
        assert result["retrieval_ready"] is False
        assert result["core_campaign_unlocked"] is False


def test_d110_implementation_does_not_call_legacy_or_external_boundaries() -> None:
    source = (ROOT / "patchloop/memory/d110_index_freeze_execution.py").read_text(
        encoding="utf-8"
    )
    assert "store.freeze_index(" not in source
    assert "responses.create(" not in source
    assert "responses.input_tokens" not in source
    assert "retrieve_memory(" not in source
    assert "evaluate_task(" not in source
