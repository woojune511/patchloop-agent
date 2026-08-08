from __future__ import annotations

import inspect
import json
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.contracts import MemoryEntry
from patchloop.errors import ContractError
from patchloop.memory import d102_maintainer_assisted_decisions as d102
from patchloop.memory import d103_exact_candidate_admission as d103
from patchloop.memory import d104_unindexed_sources as d104

ROOT = Path(__file__).resolve().parents[1]


def test_d104_checked_in_gate_exactly_validates() -> None:
    result = d104.validate_d104_source_gate(repository=ROOT)
    gate = json.loads((ROOT / d104.DEFAULT_GATE_PATH).read_text(encoding="utf-8"))
    authority = gate["semantic_body"]["authority"]

    assert result["gate_validation"] == "pass"
    assert result["materialized_rule_source_count"] == 3
    assert result["actual_memory_entry_count"] == 0
    assert result["held_group_count"] == 2
    assert result["memory_index_build_authorized"] is False
    assert result["core_campaign_unlocked"] is False
    assert authority["render_policy_frozen"] is False
    assert authority["rendered_memory_count"] == 0
    assert authority["embedding_count"] == 0
    assert authority["d104_created_index_count"] == 0
    assert authority["retrieval_ready"] is False
    assert authority["memory_effect_established"] is False
    assert authority["negative_transfer_established"] is False
    assert authority["provider_calls_made"] == 0
    assert authority["evaluator_calls_made"] == 0
    assert authority["added_model_cost_usd"] == 0


def test_d104_materializes_exact_three_admitted_sources_and_excludes_holds() -> None:
    result = d104.validate_d104_materialized_sources(repository=ROOT)

    assert [entry["semantic_group_id"] for entry in result["entries"]] == [
        row["semantic_group_id"] for row in d103.EXPECTED_ADMITTED_GROUPS
    ]
    assert result["held_group_ids"] == list(d103.EXPECTED_HELD_GROUPS)
    assert len(result["entries"]) == 3
    assert sum(len(entry["source_run_ids"]) for entry in result["entries"]) == 6
    assert sum(len(entry["source_failure_ids"]) for entry in result["entries"]) == 6
    assert all(entry["validation_count"] == 0 for entry in result["entries"])


def test_d104_sources_are_strict_unindexed_templates_with_future_compatibility() -> None:
    for path in sorted((ROOT / d104.DEFAULT_SOURCE_DIRECTORY).glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        source = d104.D104SourceRecord.model_validate(payload)
        template = source.semantic_body.projected_entry.template.model_dump(mode="json")
        encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

        assert path.read_text(encoding="utf-8") == encoded
        assert "index_version" not in template
        assert "embedding" not in template
        assert "frozen" not in template
        assert source.semantic_body.authority.actual_memory_entry_created is False
        with pytest.raises(ValidationError):
            MemoryEntry.model_validate(template)
        future = {
            "schema_version": "memory-entry-v1",
            "memory_id": template.pop("proposed_memory_id"),
            "index_version": "idx_future_real_version",
            **{key: value for key, value in template.items() if key != "target_schema"},
        }
        assert MemoryEntry.model_validate(future).index_version == "idx_future_real_version"


def test_d104_projection_and_provenance_are_exactly_seal_derived() -> None:
    seal = json.loads((ROOT / d103.DEFAULT_SEAL_PATH).read_text(encoding="utf-8"))
    admitted = seal["semantic_body"]["admitted_entries"]
    sources = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((ROOT / d104.DEFAULT_SOURCE_DIRECTORY).glob("*.json"))
    ]
    by_group = {
        source["semantic_body"]["projected_entry"]["provenance"]["semantic_group_id"]: source
        for source in sources
    }

    for projected in admitted:
        group_id = projected["provenance"]["semantic_group_id"]
        assert by_group[group_id]["semantic_body"]["projected_entry"] == projected


@pytest.mark.parametrize(
    "marker",
    [
        "diff --git a/module.py b/module.py",
        "@@ -1,2 +1,2 @@",
        "```python",
        "reference.patch",
        "private.yaml",
        ".patchloop-hidden/tests/test_acceptance.py",
        "hidden acceptance assertion",
        "OPENAI_API_KEY=sk-proj-exampleSecretValue123456789",
        "github_pat_exampleSecretValue123456789",
        "C:\\Users\\someone\\.env",
        "def leaked_solution():",
        "\u202esecret",
    ],
)
def test_d104_leak_scan_fails_without_echoing_input(marker: str) -> None:
    with pytest.raises(ContractError) as raised:
        d104.validate_d104_text_leak_safe(marker)

    assert marker not in str(raised.value)


@pytest.mark.parametrize(
    "name", [row["proposed_memory_id"] for row in d103.EXPECTED_ADMITTED_GROUPS]
)
def test_d104_materialized_source_tampering_fails_closed(tmp_path: Path, name: str) -> None:
    source_dir = tmp_path / "sources"
    shutil.copytree(ROOT / d104.DEFAULT_SOURCE_DIRECTORY, source_dir)
    selected = source_dir / f"{name}.json"
    selected.write_bytes(selected.read_bytes() + b" ")

    with pytest.raises(ContractError, match="exact bytes drifted"):
        d104.validate_d104_materialized_sources(
            repository=ROOT,
            source_directory=source_dir,
        )


def test_d104_missing_or_extra_source_fails_closed(tmp_path: Path) -> None:
    source_dir = tmp_path / "sources"
    shutil.copytree(ROOT / d104.DEFAULT_SOURCE_DIRECTORY, source_dir)
    (source_dir / "extra.txt").write_text("unexpected\n", encoding="utf-8")

    with pytest.raises(ContractError, match="file set"):
        d104.validate_d104_materialized_sources(
            repository=ROOT,
            source_directory=source_dir,
        )


def test_d104_source_schema_rejects_index_and_unknown_fields() -> None:
    path = next(iter(sorted((ROOT / d104.DEFAULT_SOURCE_DIRECTORY).glob("*.json"))))
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["semantic_body"]["projected_entry"]["template"]["index_version"] = "pending"

    with pytest.raises(ValidationError):
        d104.D104SourceRecord.model_validate(payload)


def test_d104_gate_authority_tampering_fails_closed(tmp_path: Path) -> None:
    gate = tmp_path / "gate.json"
    payload = json.loads((ROOT / d104.DEFAULT_GATE_PATH).read_text(encoding="utf-8"))
    payload["semantic_body"]["authority"]["memory_index_build_authorized"] = True
    gate.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ContractError, match="exact bytes drifted"):
        d104.validate_d104_source_gate(gate, repository=ROOT)


def test_d104_gate_refuses_a_noncanonical_source_directory() -> None:
    with pytest.raises(ContractError, match="canonical source directory"):
        d104.build_d104_source_gate(
            repository=ROOT,
            source_directory=ROOT / ".d104-noncanonical-source",
        )


def test_d104_rejects_source_directory_alias_before_resolving(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    alias = (tmp_path / "source-alias").absolute()
    inspected: list[Path] = []

    def classify_linklike(path: Path) -> bool:
        inspected.append(path)
        return path == alias

    monkeypatch.setattr(d104, "_is_linklike", classify_linklike)
    with pytest.raises(ContractError, match="source directory cannot contain a link or junction"):
        d104.validate_d104_materialized_sources(
            repository=ROOT,
            source_directory=alias,
        )

    assert inspected[-1] == alias


def test_d104_rejects_linklike_source_directory_parent_before_resolving(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    parent_alias = (tmp_path / "parent-alias").absolute()
    source_directory = parent_alias / "sources"
    inspected: list[Path] = []

    def classify_linklike(path: Path) -> bool:
        inspected.append(path)
        return path == parent_alias

    monkeypatch.setattr(d104, "_is_linklike", classify_linklike)
    with pytest.raises(ContractError, match="source directory cannot contain a link or junction"):
        d104.validate_d104_materialized_sources(
            repository=ROOT,
            source_directory=source_directory,
        )

    assert parent_alias in inspected
    assert source_directory not in inspected


def test_d104_rejects_a_linklike_repository_root_before_resolving(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_alias = (ROOT.parent / "repository-alias").absolute()
    inspected: list[Path] = []

    def classify_linklike(path: Path) -> bool:
        inspected.append(path)
        return path == repository_alias

    monkeypatch.setattr(d104, "_is_linklike", classify_linklike)
    with pytest.raises(ContractError, match="repository root cannot contain a link or junction"):
        d104.validate_d104_materialized_sources(repository=repository_alias)

    assert repository_alias in inspected


def test_d104_materialization_refuses_a_directory_outside_repository(tmp_path: Path) -> None:
    with pytest.raises(ContractError, match="source directory must stay within the repository"):
        d104.materialize_d104_sources(
            repository=ROOT,
            source_directory=tmp_path,
        )


def test_d104_exact_writer_allows_retry_and_refuses_conflict(tmp_path: Path) -> None:
    output = tmp_path / "source.json"

    first = d104.write_d104_new_exact(output, b"exact\n")
    retry = d104.write_d104_new_exact(output, b"exact\n")

    assert first["created"] is True
    assert retry["idempotent_retry"] is True
    with pytest.raises(ContractError, match="different exact bytes"):
        d104.write_d104_new_exact(output, b"different\n")


def test_d104_rebuild_is_deterministic_and_preserves_predecessors() -> None:
    rebuilt = d104.encode_d104_gate(d104.build_d104_source_gate(repository=ROOT))

    assert rebuilt == (ROOT / d104.DEFAULT_GATE_PATH).read_bytes()
    assert d102.validate_d102_decision_candidate_gate(repository=ROOT)["gate_validation"] == "pass"
    assert d103.validate_d103_exact_admission_gate(repository=ROOT)["gate_validation"] == "pass"


def test_d104_path_does_not_connect_legacy_index_or_provider_runtime() -> None:
    source = inspect.getsource(d104)

    assert "patchloop.memory.store" not in source
    assert "build_index_from_failures" not in source
    assert "freeze_index" not in source
    assert "sentence_transformers" not in source
    assert "import openai" not in source.lower()
    assert "from openai" not in source.lower()
