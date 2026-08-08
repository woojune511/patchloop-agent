from __future__ import annotations

import inspect
import json
import re
import shutil
from pathlib import Path

import pytest

from patchloop.errors import ContractError
from patchloop.memory import d103_exact_candidate_admission as d103
from patchloop.memory import d104_unindexed_sources as d104
from patchloop.memory import d105_renderer_authorization as d105
from patchloop.util import canonical_json, sha256_text

ROOT = Path(__file__).resolve().parents[1]


def _ordered_d104_sources() -> list[d104.D104SourceRecord]:
    gate = json.loads((ROOT / d104.DEFAULT_GATE_PATH).read_text(encoding="utf-8"))
    return [
        d104.D104SourceRecord.model_validate_json(
            (ROOT / descriptor["path"]).read_text(encoding="utf-8")
        )
        for descriptor in gate["semantic_body"]["entries"]
    ]


def _copy_d104_sources(tmp_path: Path) -> Path:
    target = tmp_path / "sources"
    shutil.copytree(ROOT / d104.DEFAULT_SOURCE_DIRECTORY, target)
    return target


def _copy_d105_renders(tmp_path: Path) -> Path:
    target = tmp_path / "renders"
    shutil.copytree(ROOT / d105.DEFAULT_RENDER_DIRECTORY, target)
    return target


def test_d105_checked_in_gate_exactly_validates() -> None:
    result = d105.validate_d105_gate(repository=ROOT)
    gate = json.loads((ROOT / d105.DEFAULT_GATE_PATH).read_text(encoding="utf-8"))
    authority = gate["semantic_body"]["authority"]

    assert result["gate_validation"] == "pass"
    assert authority["render_policy_frozen"] is True
    assert authority["rendered_memory_count"] == 3
    assert authority["index_build_authorization_candidate"] is True
    assert authority["memory_index_build_authorized"] is False
    assert authority["actual_memory_entry_count"] == 0
    assert authority["embedding_count"] == 0
    assert authority["d105_created_index_count"] == 0
    assert authority["memory_index_built"] is False
    assert authority["memory_index_frozen"] is False
    assert authority["retrieval_ready"] is False
    assert authority["core_campaign_unlocked"] is False
    assert authority["analysis_ready"] is False


def test_d105_render_descriptors_bind_exact_d104_source_order() -> None:
    d104_gate = json.loads((ROOT / d104.DEFAULT_GATE_PATH).read_text(encoding="utf-8"))
    d105_gate = json.loads((ROOT / d105.DEFAULT_GATE_PATH).read_text(encoding="utf-8"))
    expected = d104_gate["semantic_body"]["entries"]
    actual = d105_gate["semantic_body"]["entries"]

    assert len(actual) == len(expected) == 3
    assert [entry["order"] for entry in actual] == [1, 2, 3]
    assert [entry["proposed_memory_id"] for entry in actual] == [
        entry["proposed_memory_id"] for entry in expected
    ]
    assert [entry["source_id"] for entry in actual] == [entry["source_id"] for entry in expected]
    assert [entry["source_file_sha256"] for entry in actual] == [
        entry["file_sha256"] for entry in expected
    ]
    assert [entry["semantic_group_id"] for entry in actual] == [
        entry["semantic_group_id"] for entry in expected
    ]
    assert [entry["template_hash"] for entry in actual] == [
        entry["template_hash"] for entry in expected
    ]
    assert [entry["semantic_group_id"] for entry in actual] == [
        row["semantic_group_id"] for row in d103.EXPECTED_ADMITTED_GROUPS
    ]


def test_d105_three_model_facing_renders_are_exact_deterministic_ascii_lf() -> None:
    validation = d105.validate_d105_rendered_entries(repository=ROOT)
    descriptors = validation["entries"]
    sources = _ordered_d104_sources()

    assert len(descriptors) == len(sources) == 3
    assert sorted(path.suffix for path in (ROOT / d105.DEFAULT_RENDER_DIRECTORY).iterdir()) == [
        ".txt",
        ".txt",
        ".txt",
    ]
    for descriptor, source in zip(descriptors, sources, strict=True):
        rendered_path = ROOT / descriptor["path"]
        content = rendered_path.read_bytes()
        expected = d105.encode_d105_render(d105.render_d105_entry(source))

        assert content == expected
        assert len(content) == descriptor["file_bytes"]
        assert content.endswith(b"\n")
        assert b"\r" not in content
        assert content.decode("ascii").encode("ascii") == content


def test_d105_public_renderer_rejects_identity_drift_and_rehashed_provenance_text() -> None:
    source = _ordered_d104_sources()[0]
    identity_drift = source.model_copy(deep=True)
    identity_drift.semantic_body.projected_entry.template.failure_pattern.description = (
        "A changed description."
    )
    with pytest.raises(ContractError, match="identity drifted"):
        d105.render_d105_entry(identity_drift)

    payload = source.model_dump(mode="json")
    projected = payload["semantic_body"]["projected_entry"]
    projected["template"]["failure_pattern"]["description"] = (
        "Use run_secret123 as model-visible guidance."
    )
    projected["template_hash"] = sha256_text(canonical_json(projected["template"]))
    body_hash = sha256_text(canonical_json(payload["semantic_body"]))
    payload["semantic_body_hash"] = body_hash
    payload["source_id"] = f"d104src_{body_hash.removeprefix('sha256:')}"
    rehashed = d104.D104SourceRecord.model_validate(payload)
    with pytest.raises(ContractError, match="model-excluded provenance"):
        d105.render_d105_entry(rehashed)


@pytest.mark.parametrize(
    "pattern",
    [
        r"sha256:",
        r"\bd104src_[0-9a-f]+\b",
        r"\bmemgrp_[0-9a-f]+\b",
        r"\brun_[a-z0-9_]+\b",
        r"\bfail_[a-z0-9_]+\b",
        r"\b(?:source|failure|template|decision)_id\b",
        r"\bprivate(?:\.|[/\\]|[_ -](?:test|assertion))",
        r"\bhidden(?:[/\\]|[_ -](?:test|acceptance|assertion))",
        r"\breference(?:\.patch|[/\\]|[_ -](?:patch|solution))",
        r"diff\s+--git",
        r"(?m)^\s*@@(?:\s|$)",
        r"```",
        r"(?m)^\s*(?:async\s+)?def\s+[A-Za-z_]\w*\s*\(",
        r"(?m)^\s*class\s+[A-Za-z_]\w*",
    ],
)
def test_d105_model_facing_renders_exclude_provenance_and_leak_shapes(
    pattern: str,
) -> None:
    combined = "\n".join(
        path.read_text(encoding="ascii")
        for path in sorted((ROOT / d105.DEFAULT_RENDER_DIRECTORY).glob("*.txt"))
    )

    assert re.search(pattern, combined, flags=re.IGNORECASE) is None


@pytest.mark.parametrize("mutation", ["missing", "extra", "tampered"])
def test_d105_rejects_inexact_d104_source_set(tmp_path: Path, mutation: str) -> None:
    source_directory = _copy_d104_sources(tmp_path)
    paths = sorted(source_directory.glob("*.json"))
    if mutation == "missing":
        paths[0].unlink()
    elif mutation == "extra":
        (source_directory / "extra.json").write_text("{}\n", encoding="utf-8")
    else:
        paths[0].write_bytes(paths[0].read_bytes() + b" ")

    with pytest.raises(ContractError):
        d105.validate_d105_rendered_entries(
            repository=ROOT,
            source_directory=source_directory,
        )


@pytest.mark.parametrize("mutation", ["missing", "extra", "tampered"])
def test_d105_rejects_inexact_render_set(tmp_path: Path, mutation: str) -> None:
    render_directory = _copy_d105_renders(tmp_path)
    paths = sorted(render_directory.glob("*.txt"))
    if mutation == "missing":
        paths[0].unlink()
    elif mutation == "extra":
        (render_directory / "extra.txt").write_text("unexpected\n", encoding="ascii")
    else:
        paths[0].write_bytes(paths[0].read_bytes() + b" ")

    with pytest.raises(ContractError):
        d105.validate_d105_rendered_entries(
            repository=ROOT,
            render_directory=render_directory,
        )


def test_d105_provider_input_delta_accepts_exact_2000_token_boundary() -> None:
    assert d105.MEMORY_TOKEN_LIMIT == 2_000
    assert d105.validate_d105_provider_budget_delta(100_000, 102_000) == 2_000


@pytest.mark.parametrize(
    ("before", "after"),
    [
        (100_000, 102_001),
        (100_000, 99_999),
        (-1, 0),
        (0, -1),
    ],
)
def test_d105_provider_input_delta_rejects_over_limit_or_negative_counts(
    before: int,
    after: int,
) -> None:
    with pytest.raises(ContractError):
        d105.validate_d105_provider_budget_delta(before, after)


@pytest.mark.parametrize(
    ("before", "after"),
    [(True, 1), (1, True), (1.0, 2), (1, 2.0)],
)
def test_d105_provider_input_delta_requires_json_integers(
    before: object,
    after: object,
) -> None:
    with pytest.raises(ContractError):
        d105.validate_d105_provider_budget_delta(before, after)  # type: ignore[arg-type]


def test_d105_token_policy_does_not_claim_unobserved_provider_validation() -> None:
    gate = json.loads((ROOT / d105.DEFAULT_GATE_PATH).read_text(encoding="utf-8"))
    policy = gate["semantic_body"]["token_budget_policy"]

    assert policy == {
        "max_memory_delta_tokens": 2_000,
        "provider_exact_budget_validated": False,
        "counter": "responses.input_tokens.count",
        "same_request_shape_required": True,
    }
    boundary = gate["semantic_body"]["token_budget_evidence_boundary"]
    assert boundary["baseline_selected_memory_value"] is None
    assert boundary["allowed_context_diff_json_pointers"] == ["/selected_memory"]
    assert boundary["canonical_context_deep_diff_required"] is True
    assert boundary["request_equal_after_context_slot_normalization"] is True


def test_d105_embedding_candidate_is_exactly_pinned_but_not_executed() -> None:
    gate = json.loads((ROOT / d105.DEFAULT_GATE_PATH).read_text(encoding="utf-8"))
    candidate = gate["semantic_body"]["embedding_authorization_candidate"]

    assert d105.EMBEDDING_MODEL_ID == "sentence-transformers/all-MiniLM-L6-v2"
    assert re.fullmatch(r"[0-9a-f]{40}", d105.EMBEDDING_MODEL_REVISION)
    assert candidate == {
        "model_id": d105.EMBEDDING_MODEL_ID,
        "revision": d105.EMBEDDING_MODEL_REVISION,
        "normalize_embeddings": True,
        "trust_remote_code": False,
    }


@pytest.mark.parametrize("revision", ["", "main", "v1", "a" * 39, "A" * 40])
def test_d105_embedding_candidate_rejects_nonimmutable_revision(
    monkeypatch: pytest.MonkeyPatch,
    revision: str,
) -> None:
    monkeypatch.setattr(d105, "EMBEDDING_MODEL_REVISION", revision)

    with pytest.raises(ContractError, match="revision"):
        d105.build_d105_render_authorization_gate(repository=ROOT)


def test_d105_gate_authority_or_embedding_tampering_fails_closed(tmp_path: Path) -> None:
    original = json.loads((ROOT / d105.DEFAULT_GATE_PATH).read_text(encoding="utf-8"))
    cases = []
    authority = json.loads(json.dumps(original))
    authority["semantic_body"]["authority"]["memory_index_build_authorized"] = True
    cases.append(authority)
    embedding = json.loads(json.dumps(original))
    embedding["semantic_body"]["embedding_authorization_candidate"]["revision"] = "main"
    cases.append(embedding)

    for index, payload in enumerate(cases):
        gate_path = tmp_path / f"tampered-{index}.json"
        gate_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        with pytest.raises(ContractError, match="exact bytes drifted"):
            d105.validate_d105_gate(gate_path, repository=ROOT)


def test_d105_module_has_no_direct_model_provider_index_or_retrieval_api_use() -> None:
    source = inspect.getsource(d105)
    gate = json.loads((ROOT / d105.DEFAULT_GATE_PATH).read_text(encoding="utf-8"))
    boundary = gate["semantic_body"]["evidence_boundary"]

    assert "patchloop.memory.store" not in source
    assert "patchloop.memory.retrieval" not in source
    assert "SentenceTransformer" not in source
    assert "sentence_transformers" not in source
    assert "import openai" not in source.lower()
    assert "from openai" not in source.lower()
    assert boundary["package_initialization_imported_legacy_retrieval_and_store_modules"] is True
    assert boundary["legacy_memory_store_or_retrieval_api_called"] is False
    assert boundary["public_submitted_patch_bodies_read_by_inherited_validator"] is True
    assert boundary["public_patch_text_copied_into_renders"] is False
    assert boundary["new_rule_semantics_authored_from_patch_text"] is False


def test_d105_rebuild_and_materialization_are_exact_and_idempotent() -> None:
    checked_in_gate = (ROOT / d105.DEFAULT_GATE_PATH).read_bytes()
    checked_in_renders = {
        path.name: path.read_bytes()
        for path in sorted((ROOT / d105.DEFAULT_RENDER_DIRECTORY).glob("*.txt"))
    }

    rebuilt = d105.encode_d105_gate(d105.build_d105_render_authorization_gate(repository=ROOT))
    preflight = d105.preflight_d105_publication(repository=ROOT)

    assert rebuilt == checked_in_gate
    assert preflight == d105.build_d105_render_authorization_gate(repository=ROOT)
    assert checked_in_renders == {
        path.name: path.read_bytes()
        for path in sorted((ROOT / d105.DEFAULT_RENDER_DIRECTORY).glob("*.txt"))
    }


def test_d105_dependency_lock_rejects_duplicate_selected_package(tmp_path: Path) -> None:
    shutil.copy2(ROOT / "pyproject.toml", tmp_path / "pyproject.toml")
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    lock += '\n[[package]]\nname = "sentence-transformers"\nversion = "5.6.0"\n'
    (tmp_path / "uv.lock").write_text(lock, encoding="utf-8")

    with pytest.raises(ContractError, match="duplicated or incomplete"):
        d105._locked_dependencies(tmp_path)  # noqa: SLF001


def test_d105_gate_rejects_lexical_alias_for_canonical_source_directory() -> None:
    alias = d104.DEFAULT_SOURCE_DIRECTORY / "missing" / ".."

    with pytest.raises(ContractError, match="exact canonical source directory"):
        d105.build_d105_render_authorization_gate(
            repository=ROOT,
            source_directory=alias,
        )


def test_d105_exact_writer_allows_retry_and_refuses_conflict(tmp_path: Path) -> None:
    output = tmp_path / "render.txt"

    first = d105.write_d105_new_exact(output, b"exact\n")
    retry = d105.write_d105_new_exact(output, b"exact\n")

    assert first["created"] is True
    assert retry["idempotent_retry"] is True
    with pytest.raises(ContractError, match="different exact bytes"):
        d105.write_d105_new_exact(output, b"different\n")


def test_d105_materialization_refuses_output_outside_repository(tmp_path: Path) -> None:
    with pytest.raises(ContractError, match="must stay within the repository"):
        d105.materialize_d105_renders(
            repository=ROOT,
            render_directory=tmp_path,
        )
