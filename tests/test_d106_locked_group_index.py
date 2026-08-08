from __future__ import annotations

import inspect
import json
import math
from pathlib import Path

import pytest

from patchloop.contracts import MemoryCondition, Phase
from patchloop.errors import ContractError
from patchloop.memory import d104_unindexed_sources as d104
from patchloop.memory import d105_renderer_authorization as d105
from patchloop.memory import d106_locked_group_index as d106
from patchloop.memory import store as memory_store
from patchloop.memory.retrieval import retrieve_memory
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def _portable_index_path() -> Path:
    gate = json.loads((ROOT / d106.DEFAULT_GATE_PATH).read_text(encoding="utf-8"))
    return ROOT / gate["semantic_body"]["index"]["path"]


def _portable_index() -> dict:
    return json.loads(_portable_index_path().read_text(encoding="utf-8"))


def test_d106_exact_d105_approval_receipt_is_narrow_and_valid() -> None:
    receipt = d106.validate_d106_approval_receipt(repository=ROOT)
    payload = json.loads((ROOT / d106.DEFAULT_RECEIPT_PATH).read_text(encoding="utf-8"))
    scope = payload["semantic_body"]["authorized_scope"]

    assert receipt["self_attested"] is True
    assert receipt["reviewer_identity_authenticated"] is False
    assert receipt["cryptographic_signature_verified"] is False
    assert payload["semantic_body"]["d105_gate"]["gate_id"] == d106.EXPECTED_D105_GATE_ID
    assert payload["semantic_body"]["d105_gate"]["file_sha256"] == d106.EXPECTED_D105_FILE_SHA
    assert scope["pinned_snapshot_download"] is True
    assert scope["locked_snapshot_preflight"] is True
    assert scope["group_aware_builder_implementation"] is True
    assert scope["actual_unfrozen_index_count"] == 1
    assert scope["index_freeze_authorized"] is False
    assert scope["retrieval_experiment_authorized"] is False
    assert scope["core_campaign_authorized"] is False


def test_d106_snapshot_manifest_records_exact_safetensors_runtime_files() -> None:
    preflight = json.loads((ROOT / d106.DEFAULT_PREFLIGHT_PATH).read_text(encoding="utf-8"))
    snapshot = preflight["semantic_body"]["snapshot"]

    assert [row["path"] for row in snapshot["files"]] == [
        row["path"] for row in d106.SNAPSHOT_FILES
    ]
    assert len(snapshot["files"]) == 10
    assert all(
        not row["path"].endswith((".bin", ".onnx", ".h5", ".ot"))
        for row in snapshot["files"]
    )
    safetensors = next(row for row in snapshot["files"] if row["path"] == "model.safetensors")
    assert safetensors["lfs_sha256"] == (
        "53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db"
    )
    assert safetensors["local_sha256"] == f"sha256:{safetensors['lfs_sha256']}"


def test_d106_snapshot_validator_rejects_missing_extra_and_hash_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = b"exact-small-file\n"
    metadata = (
        {
            "path": "config.json",
            "bytes": len(content),
            "git_blob_sha1": d106._git_blob_sha1(content),  # noqa: SLF001
            "lfs_sha256": None,
        },
    )
    monkeypatch.setattr(d106, "SNAPSHOT_FILES", metadata)
    (tmp_path / "config.json").write_bytes(content)

    assert d106.validate_d106_snapshot_files(tmp_path)["required_file_count"] == 1
    (tmp_path / "extra.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ContractError, match="file set"):
        d106.validate_d106_snapshot_files(tmp_path)
    (tmp_path / "extra.json").unlink()
    (tmp_path / "config.json").write_bytes(b"drift")
    with pytest.raises(ContractError, match="byte count|blob hash"):
        d106.validate_d106_snapshot_files(tmp_path)


def test_d106_checked_in_preflight_is_portably_valid_and_not_provider_evidence() -> None:
    result = d106.validate_d106_preflight_report(repository=ROOT)
    payload = json.loads((ROOT / d106.DEFAULT_PREFLIGHT_PATH).read_text(encoding="utf-8"))
    body = payload["semantic_body"]

    assert result["schema_version"] == d106.PREFLIGHT_SCHEMA_VERSION
    assert len(result["vector_checks"]) == 3
    assert body["offline_reload"]["fresh_local_model_load_count"] == 2
    assert body["offline_reload"]["local_embedding_encode_call_count"] == 2
    assert body["offline_reload"]["network_socket_blocked"] is False
    assert body["tokenization"]["all_renders_fit_without_truncation"] is True
    assert body["authority"]["provider_calls_made"] == 0
    assert body["authority"]["memory_index_built"] is False


def test_d106_index_is_exactly_one_entry_per_group_in_d105_order() -> None:
    index = _portable_index()
    d104_evidence = d104.validate_d104_materialized_sources(repository=ROOT)
    d105_evidence = d105.validate_d105_rendered_entries(repository=ROOT)
    entries = index["entries"]

    assert index["schema_version"] == "memory-index-v1"
    assert index["index_version"].startswith("idxgrp_")
    assert len(entries) == len(index["embeddings"]) == 3
    assert [entry["memory_id"] for entry in entries] == [
        row["proposed_memory_id"] for row in d104_evidence["entries"]
    ]
    assert [row["semantic_group_id"] for row in index["group_provenance"]] == [
        row["semantic_group_id"] for row in d104_evidence["entries"]
    ]
    assert [row["render_file_sha256"] for row in index["group_provenance"]] == [
        row["file_sha256"] for row in d105_evidence["entries"]
    ]
    assert set(index["held_group_ids"]) == set(d106.HELD_GROUP_IDS)
    assert not set(index["held_group_ids"]) & {
        row["semantic_group_id"] for row in index["group_provenance"]
    }


def test_d106_index_embeds_exact_d105_text_and_preserves_provenance_out_of_band() -> None:
    index = _portable_index()
    for entry, provenance in zip(index["entries"], index["group_provenance"], strict=True):
        memory_id = entry["memory_id"]
        render = index["model_facing_text"][memory_id]
        render_path = (
            ROOT
            / "reports"
            / "memory-development"
            / "rendered"
            / "d105"
            / f"{memory_id}.txt"
        )
        assert render.encode("ascii") == render_path.read_bytes()
        assert provenance["memory_id"] == memory_id
        assert provenance["semantic_group_id"] not in render
        assert provenance["source_id"] not in render
        assert all(source_id not in render for source_id in provenance["source_failure_ids"])


def test_d106_vectors_are_finite_normalized_float32_384() -> None:
    index = _portable_index()
    assert index["embedding"]["dtype"] == "float32"
    assert index["embedding"]["dimension"] == 384
    for vector in index["embeddings"].values():
        assert len(vector) == 384
        assert all(math.isfinite(value) for value in vector)
        assert math.isclose(math.sqrt(sum(value * value for value in vector)), 1.0, abs_tol=1e-5)


def test_d106_rebuild_from_stored_vectors_has_same_deterministic_id_and_bytes() -> None:
    checked_in = _portable_index()
    rebuilt = d106.build_d106_group_index(checked_in["embeddings"], repository=ROOT)

    assert rebuilt["index_version"] == checked_in["index_version"]
    assert d106._pretty_json(rebuilt) == _portable_index_path().read_bytes()  # noqa: SLF001


def test_d106_index_remains_unfrozen_and_not_retrievable() -> None:
    index_path = _portable_index_path()
    index = _portable_index()

    assert index["frozen"] is False
    assert index["authority"]["index_freeze_authorized"] is False
    assert index["authority"]["retrieval_experiment_authorized"] is False
    assert not (index_path.parent / "FROZEN").exists()
    with pytest.raises(ContractError, match="frozen index"):
        retrieve_memory(
            run_id="run_d106_guard",
            query="public issue",
            phase=Phase.REPRODUCE,
            condition=MemoryCondition.STRUCTURED,
            index_path=index_path,
        )


def test_d106_group_index_freeze_requires_later_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    index = _portable_index()
    index_id = index["index_version"]
    root = tmp_path / "indexes"
    target = root / index_id
    target.mkdir(parents=True)
    (target / "index.json").write_text(json.dumps(index), encoding="utf-8")
    monkeypatch.setattr(memory_store, "index_root", lambda: root)

    with pytest.raises(ContractError, match="later explicit authorization"):
        memory_store.freeze_index(index_id, d106.MODEL_REVISION)
    assert not (target / "FROZEN").exists()


def test_d106_module_never_calls_legacy_builder_renderer_retrieval_or_provider() -> None:
    source = inspect.getsource(d106)

    assert "build_index_from_failures(" not in source
    assert "entry_embedding_text(" not in source
    assert "freeze_index(" not in source
    assert "retrieve_memory(" not in source
    assert "import openai" not in source.lower()
    assert "from openai" not in source.lower()


def test_d106_completion_gate_closes_freeze_retrieval_and_core() -> None:
    result = d106.validate_d106_completion_gate(repository=ROOT)
    gate = json.loads((ROOT / d106.DEFAULT_GATE_PATH).read_text(encoding="utf-8"))
    authority = gate["semantic_body"]["authority"]

    assert result["actual_memory_entry_count"] == 3
    assert result["embedding_count"] == 3
    assert result["memory_index_built"] is True
    assert result["memory_index_frozen"] is False
    assert result["retrieval_ready"] is False
    assert result["core_campaign_unlocked"] is False
    assert authority["provider_calls_made"] == 0
    assert authority["evaluator_calls_made"] == 0
    assert authority["added_model_cost_usd"] == 0
    assert (
        gate["semantic_body"]["evidence_boundary"]["provider_exact_token_budget_validated"]
        is False
    )


def test_d106_portable_and_runtime_index_match_when_runtime_copy_is_present() -> None:
    index = _portable_index()
    runtime_path = (
        ROOT
        / ".patchloop"
        / "memory"
        / "indexes"
        / index["index_version"]
        / "index.json"
    )
    if not runtime_path.exists():
        pytest.skip("ignored runtime copy is not required for portable validation")

    assert runtime_path.read_bytes() == _portable_index_path().read_bytes()
    assert sha256_bytes(runtime_path.read_bytes()) == sha256_bytes(
        _portable_index_path().read_bytes()
    )
    assert not (runtime_path.parent / "FROZEN").exists()
