from __future__ import annotations

import ast
import inspect
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from patchloop.errors import ContractError
from patchloop.evals import heldout_ac_preregistration as prereg
from patchloop.util import load_unique_yaml, sha256_bytes, sha256_json

ROOT = Path(__file__).resolve().parents[1]


def _allowed_relative_paths() -> list[Path]:
    return [
        prereg.PREREGISTRATION_PATH,
        prereg.DATASET_MANIFEST_PATH,
        *(Path(row["path"]) for row in prereg.PREDECESSOR_BINDINGS),
    ]


def _copy_closed_contract(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    for relative in _allowed_relative_paths():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    return root


def _payload(root: Path) -> dict[str, Any]:
    value = load_unique_yaml((root / prereg.PREREGISTRATION_PATH).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _seal_and_write(root: Path, payload: dict[str, Any]) -> None:
    payload["content_hash"] = sha256_json(
        {key: value for key, value in payload.items() if key != "content_hash"}
    )
    (root / prereg.PREREGISTRATION_PATH).write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _set_path(payload: dict[str, Any], path: tuple[Any, ...], value: Any) -> None:
    cursor: Any = payload
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value


def test_exact_preregistration_loads_as_design_only() -> None:
    summary = prereg.load_heldout_ac_preregistration(repository=ROOT)

    assert summary == {
        "schema_version": "heldout-ac-preregistration-v1",
        "preregistration_id": "core-ac-fixed-bundle-heldout-20260814-v1",
        "status": "design-only",
        "content_hash": ("sha256:3b75f049649850b7561f310229e1e5429f72ea24024e835ccf4910fb2c901f74"),
        "file_bytes": 31_338,
        "file_sha256": ("sha256:f6d9d015329823f3f888aac5f15296b2ddefda9e45b5d5501b8d94587bb11d8f"),
        "task_count": 12,
        "expected_runs": 48,
        "provider_calls_authorized": False,
        "added_model_cost_usd": 0,
    }


def test_validator_reads_only_the_closed_six_file_set(monkeypatch) -> None:
    observed: list[Path] = []
    original = Path.read_bytes

    def tracked(path: Path) -> bytes:
        observed.append(path.resolve())
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", tracked)

    prereg.load_heldout_ac_preregistration(repository=ROOT)

    assert set(observed) == {(ROOT / relative).resolve() for relative in _allowed_relative_paths()}
    assert len(observed) == 6


def test_validator_is_read_only(tmp_path: Path) -> None:
    root = _copy_closed_contract(tmp_path)
    before = {
        path.relative_to(root): (path.stat().st_size, sha256_bytes(path.read_bytes()))
        for path in root.rglob("*")
        if path.is_file()
    }

    prereg.load_heldout_ac_preregistration(repository=root)

    after = {
        path.relative_to(root): (path.stat().st_size, sha256_bytes(path.read_bytes()))
        for path in root.rglob("*")
        if path.is_file()
    }
    assert after == before


def test_module_has_no_execution_or_writer_surface() -> None:
    source = inspect.getsource(prereg)
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    forbidden = {
        "patchloop.task_loader",
        "patchloop.runtime",
        "patchloop.evals.runner",
        "patchloop.agent.runner",
        "patchloop.sandbox",
        "patchloop.environment",
        "openai",
        "subprocess",
        "socket",
        "urllib",
        "requests",
    }
    assert imported.isdisjoint(forbidden)
    assert prereg.__all__ == [
        "DATASET_MANIFEST_PATH",
        "DESIGN_BASE_COMMIT",
        "CONTENT_HASH",
        "FILE_BYTES",
        "FILE_SHA256",
        "PREDECESSOR_BINDINGS",
        "PREREGISTRATION_ID",
        "PREREGISTRATION_PATH",
        "SCHEMA_VERSION",
        "STATUS",
        "HeldoutACPreregistrationError",
        "load_heldout_ac_preregistration",
    ]
    assert not any(
        name.startswith(("run_", "evaluate_", "write_", "create_", "materialize_"))
        for name, value in vars(prereg).items()
        if callable(value)
    )


def test_generic_experiment_loader_rejects_preregistration() -> None:
    from patchloop.evals.runner import load_suite

    with pytest.raises(ContractError, match="experiment contract validation failed"):
        load_suite(ROOT / prereg.PREREGISTRATION_PATH)


def test_predecessor_bindings_match_current_immutable_bytes() -> None:
    assert len(prereg.PREDECESSOR_BINDINGS) == 4
    for binding in prereg.PREDECESSOR_BINDINGS:
        content = (ROOT / binding["path"]).read_bytes()
        assert len(content) == binding["file_bytes"]
        assert sha256_bytes(content) == binding["file_sha256"]


def test_every_authority_and_observed_activity_field_is_closed() -> None:
    payload = _payload(ROOT)
    authority = payload["authority"]

    assert authority["authorized_cost_usd"] == 0.0
    assert type(authority["authorized_cost_usd"]) is float
    assert all(
        type(value) is bool and value is False
        for key, value in authority.items()
        if key.endswith("_authorized")
    )
    assert all(
        type(value) is int and value == 0
        for key, value in authority.items()
        if key.startswith("authorized_") and key.endswith(("_calls", "_runs"))
    )


def test_duplicate_yaml_key_is_rejected_before_interpretation(tmp_path: Path) -> None:
    root = _copy_closed_contract(tmp_path)
    selected = root / prereg.PREREGISTRATION_PATH
    source = selected.read_text(encoding="utf-8")
    selected.write_text(
        source.replace(
            "status: design-only\n",
            "status: design-only\nstatus: design-only\n",
            1,
        ),
        encoding="utf-8",
    )

    with pytest.raises(prereg.HeldoutACPreregistrationError, match="unreadable"):
        prereg.load_heldout_ac_preregistration(repository=root)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("provenance", "design_base_commit"), "f" * 40),
        (("provenance", "heldout_task_specs_opened_for_design"), True),
        (("provenance", "heldout_run_outcomes_opened_for_design"), True),
        (("provenance", "predecessors", 0, "file_bytes"), 3_115),
        (("dataset", "task_count"), 11),
        (("dataset", "tasks", 0, "private_spec_hash"), "sha256:" + "f" * 64),
        (("treatment", "conditions"), ["structured", "no_memory"]),
        (("treatment", "query_embedding_or_similarity_used"), True),
        (("schedule_design", "expected_runs"), 47),
        (("runtime", "max_cumulative_input_tokens"), 3_999_999),
        (("runtime", "max_tool_calls"), "400"),
        (("cost", "full_schedule_reserve_usd"), 252),
        (("cost", "hard_cap_usd"), 276.0),
        (("outcomes", "typed_agent_terminal_failures_score_zero"), False),
        (("outcomes", "evaluator_completed_non_pass_rows_are_eligible_zero"), False),
        (("analysis", "descriptive_stability_interval", "samples"), 10_000),
        (
            (
                "analysis",
                "descriptive_stability_interval",
                "endpoints",
                "lower_endpoint_formula",
            ),
            "(39*m_sorted[2499]+m_sorted[2500])/960",
        ),
        (("analysis", "paired_sign_flip_sensitivity", "sign_vectors_enumerated"), 924),
        (("analysis", "paired_sign_flip_sensitivity", "schedule_orientation_randomized"), True),
        (("analysis", "independent_task_clusters"), 24),
        (("exclusions", "post_outcome_exclusions_allowed"), True),
        (("stopping", "row_retry_allowed"), True),
        (("authority", "provider_execution_authorized"), True),
        (("authority", "authorized_provider_calls"), 1),
        (("authority", "authorized_cost_usd"), 0),
        (("next_gate", "grants_execution_authority"), True),
    ],
)
def test_exact_design_contract_rejects_semantic_or_type_drift(
    tmp_path: Path,
    path: tuple[Any, ...],
    value: Any,
) -> None:
    root = _copy_closed_contract(tmp_path)
    payload = _payload(root)
    _set_path(payload, path, value)
    _seal_and_write(root, payload)

    with pytest.raises(prereg.HeldoutACPreregistrationError):
        prereg.load_heldout_ac_preregistration(repository=root)


def test_unknown_top_level_field_is_rejected(tmp_path: Path) -> None:
    root = _copy_closed_contract(tmp_path)
    payload = _payload(root)
    payload["execution_authority"] = False
    _seal_and_write(root, payload)

    with pytest.raises(prereg.HeldoutACPreregistrationError, match="fields differ"):
        prereg.load_heldout_ac_preregistration(repository=root)


def test_content_hash_is_verified_excluding_only_itself(tmp_path: Path) -> None:
    root = _copy_closed_contract(tmp_path)
    payload = _payload(root)
    payload["content_hash"] = "sha256:" + "0" * 64
    (root / prereg.PREREGISTRATION_PATH).write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )

    with pytest.raises(prereg.HeldoutACPreregistrationError, match="content hash mismatch"):
        prereg.load_heldout_ac_preregistration(repository=root)


def test_dataset_manifest_byte_drift_is_rejected(tmp_path: Path) -> None:
    root = _copy_closed_contract(tmp_path)
    manifest = root / prereg.DATASET_MANIFEST_PATH
    manifest.write_bytes(manifest.read_bytes() + b"\n")

    with pytest.raises(
        prereg.HeldoutACPreregistrationError, match="manifest byte identity drifted"
    ):
        prereg.load_heldout_ac_preregistration(repository=root)


def test_predecessor_byte_drift_is_rejected(tmp_path: Path) -> None:
    root = _copy_closed_contract(tmp_path)
    predecessor = root / prereg.PREDECESSOR_BINDINGS[0]["path"]
    predecessor.write_bytes(predecessor.read_bytes() + b"\n")

    with pytest.raises(prereg.HeldoutACPreregistrationError, match="predecessor bytes drifted"):
        prereg.load_heldout_ac_preregistration(repository=root)


@pytest.mark.parametrize("mutation", ["swap_blocks", "flip_orientation", "wrong_wave"])
def test_schedule_must_match_the_deterministic_counterbalanced_projection(
    tmp_path: Path,
    mutation: str,
) -> None:
    root = _copy_closed_contract(tmp_path)
    payload = _payload(root)
    rows = payload["schedule"]
    if mutation == "swap_blocks":
        rows[:4] = rows[2:4] + rows[:2]
        for order, row in enumerate(rows, 1):
            row["order"] = order
    elif mutation == "flip_orientation":
        rows[0]["condition"], rows[1]["condition"] = (
            rows[1]["condition"],
            rows[0]["condition"],
        )
    else:
        rows[0]["wave"] = 2
        rows[12]["wave"] = 1
    projection_fields = payload["schedule_design"]["projection_fields"]
    projection = [{field: row[field] for field in projection_fields} for row in rows]
    encoded = (
        __import__("json")
        .dumps(
            projection,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        .encode("utf-8")
    )
    payload["schedule_design"]["projection_bytes"] = len(encoded)
    payload["schedule_design"]["projection_sha256"] = sha256_bytes(encoded)
    _seal_and_write(root, payload)

    with pytest.raises(prereg.HeldoutACPreregistrationError):
        prereg.load_heldout_ac_preregistration(repository=root)
