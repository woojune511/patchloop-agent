from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from patchloop.errors import ContractError
from patchloop.evals import heldout_ac_preregistration as prereg
from patchloop.evals import heldout_ac_suite, runner
from patchloop.util import canonical_json, load_unique_yaml, sha256_bytes, sha256_text

ROOT = Path(__file__).resolve().parents[1]
SUITE_PATH = ROOT / "experiments/heldout-ac-suite-20260814-v1.yaml"
PLAN_PATH = ROOT / "experiments/heldout-ac-suite-20260814-v1.plan.yaml"
SUITE_CONTENT_HASH = "sha256:1d023e8837e99889d76acf6f3a2d970261cb7aa4b3e978c84cef2ef5cf517aaa"
SUITE_FILE_SHA256 = "sha256:27157e26881cc277a9026e51d22a6f21fbf5bbb8f6c1c09eaa89aec607e52534"
PLAN_CONTENT_HASH = "sha256:b2058c48de3f2b4d13df872d7fd19a325c3a76ffb5ef24974310409100cb8885"


def _payload(path: Path) -> dict[str, Any]:
    value = load_unique_yaml(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _seal_and_write(path: Path, payload: dict[str, Any]) -> None:
    payload["content_hash"] = sha256_text(
        canonical_json({key: value for key, value in payload.items() if key != "content_hash"})
    )
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _set_path(payload: dict[str, Any], path: tuple[Any, ...], value: Any) -> None:
    cursor: Any = payload
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value


def test_exact_execution_closed_suite_and_plan_load() -> None:
    suite = heldout_ac_suite.load_heldout_ac_suite(SUITE_PATH, repository=ROOT)
    plan, planned_suite = heldout_ac_suite.load_heldout_ac_suite_plan(PLAN_PATH, repository=ROOT)

    assert suite == planned_suite
    assert suite.schema_version == "heldout-ac-suite-v1"
    assert suite.suite_id == "core-ac-fixed-bundle-heldout-20260814-v1"
    assert suite.status == "execution-closed"
    assert suite.content_hash == SUITE_CONTENT_HASH
    assert not isinstance(suite, runner.ExperimentSuite)
    assert "experiment_id" not in type(suite).model_fields
    assert "approved_execution_hash" not in type(suite).model_fields
    suite_source = SUITE_PATH.read_text(encoding="utf-8")
    assert "public.yaml" not in suite_source
    assert "private.yaml" not in suite_source
    assert len(SUITE_PATH.read_bytes()) == 13_348
    assert sha256_bytes(SUITE_PATH.read_bytes()) == SUITE_FILE_SHA256
    assert len(suite.tasks) == 12
    assert len(suite.schedule) == 48
    assert suite.runtime.max_cumulative_input_tokens == 4_000_000
    assert suite.runtime.max_cumulative_output_tokens == 500_000
    assert suite.runtime.max_total_tokens == 4_500_000
    assert suite.cost.full_schedule_reserve_usd == 252.0
    assert suite.cost.hard_cap_usd == 275.0
    assert plan.status == "offline-contract-only"
    assert plan.content_hash == PLAN_CONTENT_HASH
    assert plan.grants_execution_authority is False


def test_suite_authority_is_closed_and_prerequisites_remain_unsatisfied() -> None:
    suite = heldout_ac_suite.load_heldout_ac_suite(SUITE_PATH, repository=ROOT)
    plan, _ = heldout_ac_suite.load_heldout_ac_suite_plan(PLAN_PATH, repository=ROOT)
    gate = suite.execution_gate.model_dump(mode="python")

    assert all(
        value is False
        for key, value in gate.items()
        if key.endswith(("_authorized", "_present"))
        or key
        in {
            "pricing_refreshed_for_candidate",
            "heldout_task_spec_or_outcome_access_authorized",
        }
    )
    assert gate["authorized_cost_usd"] == 0.0
    assert type(gate["authorized_cost_usd"]) is float
    assert all(
        type(value) is int and value == 0
        for key, value in gate.items()
        if key.startswith("authorized_") and key.endswith(("_calls", "_runs"))
    )
    requirements = plan.requirements
    assert requirements.dedicated_source_qualification_required is True
    assert requirements.refreshed_pricing_binding_required is True
    assert requirements.exact_execution_candidate_required is True
    assert requirements.separate_explicit_paid_approval_required is True
    assert requirements.may_open_heldout_task_specs_or_outcomes is False
    assert requirements.may_make_provider_evaluator_agent_docker_or_sdk_calls is False
    assert requirements.may_reserve_or_spend_cost is False


def test_suite_loader_does_not_open_task_files_or_call_execution_surfaces(monkeypatch) -> None:
    observed: list[Path] = []
    original_read_bytes = Path.read_bytes

    def tracked(path: Path) -> bytes:
        observed.append(path.resolve())
        return original_read_bytes(path)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("execution surface must not be called")

    monkeypatch.setattr(Path, "read_bytes", tracked)
    monkeypatch.setattr(runner, "load_task_package", forbidden)
    monkeypatch.setattr(runner.subprocess, "run", forbidden)

    heldout_ac_suite.load_heldout_ac_suite(SUITE_PATH, repository=ROOT)

    assert observed
    assert all("tasks" not in path.relative_to(ROOT).parts for path in observed)
    allowed = {
        SUITE_PATH.resolve(),
        (ROOT / prereg.PREREGISTRATION_PATH).resolve(),
        (ROOT / prereg.DATASET_MANIFEST_PATH).resolve(),
        *(ROOT / row["path"] for row in prereg.PREDECESSOR_BINDINGS),
    }
    assert set(observed) == {path.resolve() for path in allowed}


def test_generic_experiment_loader_rejects_dedicated_heldout_suite() -> None:
    with pytest.raises(ContractError, match="experiment contract validation failed"):
        runner.load_suite(SUITE_PATH)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("runtime", "max_model_calls"), "240"),
        (("runtime", "max_total_tokens"), 4_499_999),
        (("cost", "full_schedule_reserve_usd"), 252),
        (("cost", "hard_cap_usd"), 276.0),
        (("execution_gate", "provider_execution_authorized"), True),
        (("execution_gate", "authorized_provider_calls"), 1),
        (("execution_gate", "authorized_cost_usd"), 0),
        (("schedule", 0, "condition"), "no_memory"),
        (("tasks", 0, "role"), "core-same-repo"),
    ],
)
def test_suite_rejects_type_semantic_or_preregistration_drift(
    tmp_path: Path,
    path: tuple[Any, ...],
    value: Any,
) -> None:
    payload = _payload(SUITE_PATH)
    _set_path(payload, path, value)
    selected = tmp_path / "suite.yaml"
    _seal_and_write(selected, payload)

    with pytest.raises(ContractError):
        heldout_ac_suite.load_heldout_ac_suite(selected, repository=ROOT)


def test_suite_unknown_field_is_rejected_even_when_resealed(tmp_path: Path) -> None:
    payload = _payload(SUITE_PATH)
    payload["execution_authority"] = False
    selected = tmp_path / "suite.yaml"
    _seal_and_write(selected, payload)

    with pytest.raises(ContractError, match="contract validation failed"):
        heldout_ac_suite.load_heldout_ac_suite(selected, repository=ROOT)


def test_suite_content_hash_is_verified(tmp_path: Path) -> None:
    payload = _payload(SUITE_PATH)
    payload["content_hash"] = "sha256:" + "0" * 64
    selected = tmp_path / "suite.yaml"
    selected.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    with pytest.raises(ContractError, match="content_hash"):
        heldout_ac_suite.load_heldout_ac_suite(selected, repository=ROOT)


def test_suite_duplicate_yaml_key_is_rejected(tmp_path: Path) -> None:
    source = SUITE_PATH.read_text(encoding="utf-8")
    selected = tmp_path / "suite.yaml"
    selected.write_text(
        source.replace(
            "status: execution-closed\n",
            "status: execution-closed\nstatus: execution-closed\n",
            1,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ContractError, match="YAML validation failed"):
        heldout_ac_suite.load_heldout_ac_suite(selected, repository=ROOT)


def test_plan_rejects_suite_file_binding_drift_even_when_resealed(tmp_path: Path) -> None:
    payload = _payload(PLAN_PATH)
    payload["suite"]["file_bytes"] += 1
    selected = tmp_path / "plan.yaml"
    _seal_and_write(selected, payload)

    with pytest.raises(ContractError, match="file binding drifted"):
        heldout_ac_suite.load_heldout_ac_suite_plan(selected, repository=ROOT)


def test_plan_cannot_relax_offline_authority_even_when_resealed(tmp_path: Path) -> None:
    payload = _payload(PLAN_PATH)
    payload["requirements"]["may_make_provider_evaluator_agent_docker_or_sdk_calls"] = True
    selected = tmp_path / "plan.yaml"
    _seal_and_write(selected, payload)

    with pytest.raises(ContractError, match="plan validation failed"):
        heldout_ac_suite.load_heldout_ac_suite_plan(selected, repository=ROOT)
