from __future__ import annotations

from copy import deepcopy
from datetime import date
from pathlib import Path

import pytest
import yaml

from patchloop.agent.review import (
    load_public_review_contract,
    normalize_public_issue_text,
    public_review_contract_content_hash,
    public_review_coverage_target_id,
    public_review_requirement_id,
)
from patchloop.contracts import PublicReviewContract, RunManifest, ToolCall
from patchloop.errors import ContractError
from patchloop.runtime import build_manifest
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_json

REVIEW_CONTRACT_CASES = {
    "hf-hub-xet-endpoint-propagation": 5,
    "pdm-ignore-active-venv-resolution": 6,
    "pyfakefs-makedirs-parent-traversal": 8,
}


def _task_dir(task_id: str) -> Path:
    return Path("tasks/dev-train") / task_id


def _review_path(task_id: str) -> Path:
    return Path("experiments/review-contracts") / f"{task_id}.yaml"


def _review_v2_path(task_id: str) -> Path:
    return Path("experiments/review-contracts-v2") / f"{task_id}.yaml"


def _payload(task_id: str) -> dict:
    value = yaml.safe_load(
        _review_path(task_id).read_text(encoding="utf-8")
    )
    assert isinstance(value, dict)
    return value


def _write_payload(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "public-review.yaml"
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path


def _rehash(payload: dict) -> dict:
    payload["content_hash"] = public_review_contract_content_hash(
        payload
    )
    return payload


def _coverage_target(
    requirement_id: str,
    *,
    evidence_kind: str = "current_diff_inspection",
    description: str = "Inspect endpoint propagation in the current diff.",
    path: str | None = "src/huggingface_hub/utils/_xet.py",
    anchor: str | None = "parse_xet_file_data_from_response",
    check_ids: list[str] | None = None,
) -> dict:
    target = {
        "coverage_target_id": public_review_coverage_target_id(
            requirement_id,
            description=description,
            evidence_kind=evidence_kind,
            path=path,
            anchor=anchor,
            check_ids=check_ids,
        ),
        "description": description,
        "evidence_kind": evidence_kind,
    }
    if path is not None:
        target["path"] = path
    if anchor is not None:
        target["anchor"] = anchor
    if check_ids is not None:
        target["check_ids"] = check_ids
    return target


def _v2_payload() -> dict:
    payload = _payload("hf-hub-xet-endpoint-propagation")
    payload["schema_version"] = "public-review-contract-v2"
    for index, requirement in enumerate(payload["requirements"]):
        requirement_id = requirement["requirement_id"]
        if index % 2:
            requirement["coverage_targets"] = [
                _coverage_target(
                    requirement_id,
                    evidence_kind="passing_validation",
                    description=f"Validate public endpoint behavior case {index}.",
                    path=None,
                    anchor=None,
                    check_ids=["upstream-xet-regression"],
                )
            ]
        else:
            requirement["coverage_targets"] = [
                _coverage_target(
                    requirement_id,
                    description=f"Inspect public endpoint code path {index}.",
                )
            ]
    return _rehash(payload)


@pytest.mark.parametrize(
    ("task_id", "requirement_count"),
    REVIEW_CONTRACT_CASES.items(),
)
def test_checked_in_public_review_contracts_bind_exact_public_excerpts(
    task_id: str,
    requirement_count: int,
) -> None:
    package = load_task_package(_task_dir(task_id))

    contract = load_public_review_contract(
        _review_path(task_id),
        task=package.public,
        public_spec_hash=package.public_spec_hash,
    )

    normalized_issue = normalize_public_issue_text(
        package.public.issue.description
    )
    assert len(contract.requirements) == requirement_count
    assert contract.public_spec_hash == package.public_spec_hash
    assert contract.content_hash == public_review_contract_content_hash(
        contract.model_dump(mode="json")
    )
    for requirement in contract.requirements:
        assert requirement.source_excerpt in normalized_issue
        assert requirement.requirement_id == public_review_requirement_id(
            requirement.source_excerpt
        )


def test_v1_review_contract_dump_and_hash_exclude_coverage_targets() -> None:
    task_id = "hf-hub-xet-endpoint-propagation"
    package = load_task_package(_task_dir(task_id))
    payload = _payload(task_id)

    contract = load_public_review_contract(
        _review_path(task_id),
        task=package.public,
        public_spec_hash=package.public_spec_hash,
    )

    assert contract.model_dump(mode="json") == payload
    assert contract.content_hash == (
        "sha256:2d3f31bd6a6f429cfc305229e029a99bd7459a0f97291c3e804c58eb7b013a2e"
    )
    assert all(
        "coverage_targets" not in requirement
        for requirement in contract.model_dump(mode="json")["requirements"]
    )


def test_v1_review_contract_rejects_even_empty_coverage_targets(
    tmp_path: Path,
) -> None:
    task_id = "hf-hub-xet-endpoint-propagation"
    package = load_task_package(_task_dir(task_id))
    payload = _payload(task_id)
    payload["requirements"][0]["coverage_targets"] = []
    path = _write_payload(tmp_path, _rehash(payload))

    with pytest.raises(
        ContractError,
        match="public review contract validation failed",
    ):
        load_public_review_contract(
            path,
            task=package.public,
            public_spec_hash=package.public_spec_hash,
        )


def test_v2_review_contract_binds_public_inspection_and_validation_targets(
    tmp_path: Path,
) -> None:
    task_id = "hf-hub-xet-endpoint-propagation"
    package = load_task_package(_task_dir(task_id))
    payload = _v2_payload()
    path = _write_payload(tmp_path, payload)

    contract = load_public_review_contract(
        path,
        task=package.public,
        public_spec_hash=package.public_spec_hash,
    )

    assert contract.schema_version == "public-review-contract-v2"
    assert sum(
        len(requirement.coverage_targets)
        for requirement in contract.requirements
    ) == len(contract.requirements)
    assert contract.model_dump(mode="json") == payload


def test_v2_coverage_target_id_hashes_all_normalized_canonical_fields() -> None:
    requirement_id = "req-64fd5304816b"
    baseline = public_review_coverage_target_id(
        requirement_id,
        description="Inspect endpoint propagation.",
        evidence_kind="current_diff_inspection",
        path="src/huggingface_hub/utils/_xet.py",
        anchor="parse_xet_file_data_from_response",
        check_ids=[],
    )

    assert baseline == public_review_coverage_target_id(
        requirement_id,
        description="  Inspect   endpoint propagation.  ",
        evidence_kind="current_diff_inspection",
        path=r"src\huggingface_hub\utils\_xet.py",
        anchor=" parse_xet_file_data_from_response ",
        check_ids=[],
    )
    assert baseline != public_review_coverage_target_id(
        requirement_id,
        description="Inspect endpoint propagation.",
        evidence_kind="current_diff_inspection",
        path="src/huggingface_hub/file_download.py",
        anchor="parse_xet_file_data_from_response",
        check_ids=[],
    )
    assert baseline != public_review_coverage_target_id(
        requirement_id,
        description="Inspect endpoint propagation.",
        evidence_kind="current_diff_inspection",
        path="src/huggingface_hub/utils/_xet.py",
        anchor="get_hf_file_metadata",
        check_ids=[],
    )
    validation = public_review_coverage_target_id(
        requirement_id,
        description="Validate endpoint propagation.",
        evidence_kind="passing_validation",
        check_ids=["z-check", "a-check"],
    )
    assert validation == public_review_coverage_target_id(
        requirement_id,
        description="Validate endpoint propagation.",
        evidence_kind="passing_validation",
        check_ids=["a-check", "z-check"],
    )


def test_v2_review_contract_requires_targets_for_every_requirement(
    tmp_path: Path,
) -> None:
    package = load_task_package(
        _task_dir("hf-hub-xet-endpoint-propagation")
    )
    payload = _v2_payload()
    payload["requirements"][0].pop("coverage_targets")
    path = _write_payload(tmp_path, _rehash(payload))

    with pytest.raises(
        ContractError,
        match="public review contract validation failed",
    ):
        load_public_review_contract(
            path,
            task=package.public,
            public_spec_hash=package.public_spec_hash,
        )


@pytest.mark.parametrize("missing_field", ["path", "anchor"])
def test_v2_inspection_target_requires_public_path_and_exact_anchor(
    tmp_path: Path,
    missing_field: str,
) -> None:
    package = load_task_package(
        _task_dir("hf-hub-xet-endpoint-propagation")
    )
    payload = _v2_payload()
    payload["requirements"][0]["coverage_targets"][0].pop(missing_field)
    path = _write_payload(tmp_path, _rehash(payload))

    with pytest.raises(
        ContractError,
        match="public review contract validation failed",
    ):
        load_public_review_contract(
            path,
            task=package.public,
            public_spec_hash=package.public_spec_hash,
        )


def test_v2_validation_target_requires_nonempty_check_ids(
    tmp_path: Path,
) -> None:
    package = load_task_package(
        _task_dir("hf-hub-xet-endpoint-propagation")
    )
    payload = _v2_payload()
    payload["requirements"][1]["coverage_targets"][0]["check_ids"] = []
    path = _write_payload(tmp_path, _rehash(payload))

    with pytest.raises(
        ContractError,
        match="public review contract validation failed",
    ):
        load_public_review_contract(
            path,
            task=package.public,
            public_spec_hash=package.public_spec_hash,
        )


def test_v2_review_contract_rejects_noncanonical_target_id(
    tmp_path: Path,
) -> None:
    package = load_task_package(
        _task_dir("hf-hub-xet-endpoint-propagation")
    )
    payload = _v2_payload()
    payload["requirements"][0]["coverage_targets"][0][
        "coverage_target_id"
    ] = "cov-000000000000"
    path = _write_payload(tmp_path, _rehash(payload))

    with pytest.raises(
        ContractError,
        match="coverage target ID does not match",
    ):
        load_public_review_contract(
            path,
            task=package.public,
            public_spec_hash=package.public_spec_hash,
        )


def test_v2_review_contract_rejects_duplicate_target_ids(
    tmp_path: Path,
) -> None:
    package = load_task_package(
        _task_dir("hf-hub-xet-endpoint-propagation")
    )
    payload = _v2_payload()
    payload["requirements"][1]["coverage_targets"] = [
        deepcopy(payload["requirements"][0]["coverage_targets"][0])
    ]
    path = _write_payload(tmp_path, _rehash(payload))

    with pytest.raises(
        ContractError,
        match="public review contract validation failed",
    ):
        load_public_review_contract(
            path,
            task=package.public,
            public_spec_hash=package.public_spec_hash,
        )


def test_v2_inspection_target_must_reference_an_allowed_public_path(
    tmp_path: Path,
) -> None:
    package = load_task_package(
        _task_dir("hf-hub-xet-endpoint-propagation")
    )
    payload = _v2_payload()
    requirement = payload["requirements"][0]
    requirement["coverage_targets"] = [
        _coverage_target(
            requirement["requirement_id"],
            description="Inspect a public but out-of-scope code path.",
            path="src/huggingface_hub/constants.py",
            anchor="ENDPOINT",
        )
    ]
    path = _write_payload(tmp_path, _rehash(payload))

    with pytest.raises(
        ContractError,
        match="path is not public and allowed",
    ):
        load_public_review_contract(
            path,
            task=package.public,
            public_spec_hash=package.public_spec_hash,
        )


def test_v2_validation_target_must_reference_visible_checks(
    tmp_path: Path,
) -> None:
    package = load_task_package(
        _task_dir("hf-hub-xet-endpoint-propagation")
    )
    payload = _v2_payload()
    requirement = payload["requirements"][1]
    requirement["coverage_targets"] = [
        _coverage_target(
            requirement["requirement_id"],
            evidence_kind="passing_validation",
            description="Validate an unknown public check.",
            path=None,
            anchor=None,
            check_ids=["unknown-check"],
        )
    ]
    path = _write_payload(tmp_path, _rehash(payload))

    with pytest.raises(
        ContractError,
        match="unknown visible check",
    ):
        load_public_review_contract(
            path,
            task=package.public,
            public_spec_hash=package.public_spec_hash,
        )


def test_v2_review_contract_limits_targets_across_requirements(
    tmp_path: Path,
) -> None:
    package = load_task_package(
        _task_dir("hf-hub-xet-endpoint-propagation")
    )
    payload = _v2_payload()
    for requirement_index, requirement in enumerate(payload["requirements"]):
        requirement["coverage_targets"] = [
            _coverage_target(
                requirement["requirement_id"],
                description=(
                    f"Inspect public code path {requirement_index}-{target_index}."
                ),
                anchor=f"public_anchor_{requirement_index}_{target_index}",
            )
            for target_index in range(5)
        ]
    path = _write_payload(tmp_path, _rehash(payload))

    with pytest.raises(
        ContractError,
        match="public review contract validation failed",
    ):
        load_public_review_contract(
            path,
            task=package.public,
            public_spec_hash=package.public_spec_hash,
        )


def test_v2_review_contract_leak_scans_coverage_targets_without_echoing(
    tmp_path: Path,
) -> None:
    package = load_task_package(
        _task_dir("hf-hub-xet-endpoint-propagation")
    )
    payload = _v2_payload()
    marker = "reference.patch"
    requirement = payload["requirements"][0]
    requirement["coverage_targets"] = [
        _coverage_target(
            requirement["requirement_id"],
            description=f"Inspect data from {marker}.",
        )
    ]
    path = _write_payload(tmp_path, _rehash(payload))

    with pytest.raises(
        ContractError,
        match="public review contract leak scan failed",
    ) as captured:
        load_public_review_contract(
            path,
            task=package.public,
            public_spec_hash=package.public_spec_hash,
        )
    assert marker not in str(captured.value)


def test_public_review_contract_rejects_duplicate_requirement_ids(
    tmp_path: Path,
) -> None:
    task_id = "pdm-ignore-active-venv-resolution"
    package = load_task_package(_task_dir(task_id))
    payload = _payload(task_id)
    payload["requirements"].append(
        deepcopy(payload["requirements"][0])
    )
    path = _write_payload(tmp_path, _rehash(payload))

    with pytest.raises(
        ContractError,
        match="public review contract validation failed",
    ):
        load_public_review_contract(
            path,
            task=package.public,
            public_spec_hash=package.public_spec_hash,
        )


def test_public_review_contract_rejects_unknown_requirement_id(
    tmp_path: Path,
) -> None:
    task_id = "hf-hub-xet-endpoint-propagation"
    package = load_task_package(_task_dir(task_id))
    payload = _payload(task_id)
    payload["requirements"][0]["requirement_id"] = "req-000000000000"
    path = _write_payload(tmp_path, _rehash(payload))

    with pytest.raises(
        ContractError,
        match="requirement ID does not match",
    ):
        load_public_review_contract(
            path,
            task=package.public,
            public_spec_hash=package.public_spec_hash,
        )


def test_public_review_contract_rejects_unknown_fields(
    tmp_path: Path,
) -> None:
    task_id = "hf-hub-xet-endpoint-propagation"
    package = load_task_package(_task_dir(task_id))
    payload = _payload(task_id)
    payload["requirements"][0]["unsupported"] = True
    path = _write_payload(tmp_path, _rehash(payload))

    with pytest.raises(
        ContractError,
        match="public review contract validation failed",
    ):
        load_public_review_contract(
            path,
            task=package.public,
            public_spec_hash=package.public_spec_hash,
        )


def test_public_review_contract_rejects_mismatched_public_hash(
    tmp_path: Path,
) -> None:
    task_id = "pyfakefs-makedirs-parent-traversal"
    package = load_task_package(_task_dir(task_id))
    payload = _payload(task_id)
    payload["public_spec_hash"] = "sha256:" + ("f" * 64)
    path = _write_payload(tmp_path, _rehash(payload))

    with pytest.raises(
        ContractError,
        match="public spec hash mismatch",
    ):
        load_public_review_contract(
            path,
            task=package.public,
            public_spec_hash=package.public_spec_hash,
        )


@pytest.mark.parametrize(
    "private_marker",
    [
        "private.yaml",
        "reference.patch",
        ".patchloop-hidden/secret.py",
        "hidden/test_acceptance.py",
        "ghp_" + ("a" * 36),
        "github_pat_" + ("b" * 48),
        "AKIA" + ("C" * 16),
        "AWS_ACCESS_KEY_ID=ASIA" + ("D" * 16),
        "AWS_SECRET_ACCESS_KEY=" + ("e" * 40),
        "AWS_SESSION_TOKEN=" + ("f" * 80),
    ],
)
def test_public_review_contract_rejects_private_markers_without_echoing(
    tmp_path: Path,
    private_marker: str,
) -> None:
    task_id = "pdm-ignore-active-venv-resolution"
    package = load_task_package(_task_dir(task_id))
    payload = _payload(task_id)
    payload["requirements"][0]["source_excerpt"] = private_marker
    payload["requirements"][0]["requirement_id"] = (
        public_review_requirement_id(private_marker)
    )
    path = _write_payload(tmp_path, _rehash(payload))

    with pytest.raises(
        ContractError,
        match="public review contract leak scan failed",
    ) as captured:
        load_public_review_contract(
            path,
            task=package.public,
            public_spec_hash=package.public_spec_hash,
        )
    assert private_marker not in str(captured.value)


@pytest.mark.parametrize(
    "public_example",
    [
        "ghp_short",
        "github_pat_<redacted>",
        "AWS_ACCESS_KEY_ID=<redacted>",
        "AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}",
        "AWS_SESSION_TOKEN=example",
    ],
)
def test_public_review_contract_allows_noncredential_documentation_markers(
    tmp_path: Path,
    public_example: str,
) -> None:
    task_id = "pdm-ignore-active-venv-resolution"
    package = load_task_package(_task_dir(task_id))
    public_task = package.public.model_copy(deep=True)
    public_task.issue.description = (
        f"{public_task.issue.description} {public_example}"
    )
    public_spec_hash = sha256_json(public_task.model_dump(mode="json"))
    payload = _payload(task_id)
    payload["public_spec_hash"] = public_spec_hash
    payload["requirements"][0].update(
        {
            "requirement_id": public_review_requirement_id(public_example),
            "source_excerpt": public_example,
        }
    )
    path = _write_payload(tmp_path, _rehash(payload))

    contract = load_public_review_contract(
        path,
        task=public_task,
        public_spec_hash=public_spec_hash,
    )

    assert contract.requirements[0].source_excerpt == public_example


def test_public_review_contract_requires_exact_normalized_issue_substring(
    tmp_path: Path,
) -> None:
    task_id = "pyfakefs-makedirs-parent-traversal"
    package = load_task_package(_task_dir(task_id))
    payload = _payload(task_id)
    excerpt = "A requirement that is not present in the public issue."
    payload["requirements"][0]["source_excerpt"] = excerpt
    payload["requirements"][0]["requirement_id"] = (
        public_review_requirement_id(excerpt)
    )
    path = _write_payload(tmp_path, _rehash(payload))

    with pytest.raises(
        ContractError,
        match="not in the public issue description",
    ):
        load_public_review_contract(
            path,
            task=package.public,
            public_spec_hash=package.public_spec_hash,
        )


def test_public_review_contract_rejects_non_json_yaml_scalar(
    tmp_path: Path,
) -> None:
    task_id = "hf-hub-xet-endpoint-propagation"
    package = load_task_package(_task_dir(task_id))
    payload = _payload(task_id)
    payload["requirements"][0]["source_excerpt"] = date(2020, 1, 1)
    path = _write_payload(tmp_path, payload)

    with pytest.raises(
        ContractError,
        match="only JSON-compatible values",
    ):
        load_public_review_contract(
            path,
            task=package.public,
            public_spec_hash=package.public_spec_hash,
        )


def test_manifest_builder_revalidates_public_review_provenance() -> None:
    task_id = "pdm-ignore-active-venv-resolution"
    package = load_task_package(_task_dir(task_id))
    payload = _payload(task_id)
    excerpt = "private.yaml"
    payload["requirements"][0].update(
        {
            "requirement_id": public_review_requirement_id(excerpt),
            "source_excerpt": excerpt,
        }
    )
    contract = PublicReviewContract.model_validate(_rehash(payload))

    with pytest.raises(ContractError, match="leak scan failed"):
        build_manifest(
            package,
            corrective_validation=True,
            public_review_contract=contract,
        )


def test_manifest_embeds_review_contract_without_changing_legacy_dump() -> None:
    task_id = "pdm-ignore-active-venv-resolution"
    package = load_task_package(_task_dir(task_id))
    contract = load_public_review_contract(
        _review_path(task_id),
        task=package.public,
        public_spec_hash=package.public_spec_hash,
    )
    legacy = build_manifest(package, run_id="run_review_contract_legacy")

    assert "public_review_contract" not in legacy.model_dump(mode="json")

    payload = legacy.model_dump(mode="json")
    payload.update(
        {
            "tool_schema_version": "v4",
            "context_policy_version": "phase-evidence-v7",
            "public_review_contract": contract.model_dump(mode="json"),
        }
    )
    manifest = RunManifest.model_validate(payload)

    assert manifest.public_review_contract == contract
    assert manifest.model_dump(mode="json")[
        "public_review_contract"
    ]["content_hash"] == contract.content_hash


def test_saturation_manifest_requires_and_embeds_public_review_contract() -> None:
    task_id = "pdm-ignore-active-venv-resolution"
    package = load_task_package(_task_dir(task_id))
    contract = load_public_review_contract(
        _review_path(task_id),
        task=package.public,
        public_spec_hash=package.public_spec_hash,
    )

    manifest = build_manifest(
        package,
        run_id="run_saturation_review_contract",
        saturation_context_validation=True,
        public_review_contract=contract,
    )

    assert manifest.tool_schema_version == "v4"
    assert manifest.context_policy_version == "phase-evidence-v8"
    assert manifest.public_review_contract == contract
    assert manifest.model_dump(mode="json")[
        "public_review_contract"
    ]["content_hash"] == contract.content_hash
    with pytest.raises(ContractError, match="require a public review contract"):
        build_manifest(
            package,
            saturation_context_validation=True,
        )


def test_tool_call_accepts_v4_without_changing_default() -> None:
    default = ToolCall(
        tool="review_task",
        action_id="review-default",
        run_id="run_review_default",
        input_hash="sha256:" + ("a" * 64),
    )
    current = ToolCall(
        tool="review_task",
        tool_schema_version="v4",
        action_id="review-v4",
        run_id="run_review_v4",
        input_hash="sha256:" + ("b" * 64),
    )

    assert default.tool_schema_version == "v1"
    assert current.tool_schema_version == "v4"


def test_hf_hub_v2_sidecar_is_pinned_without_replacing_v1() -> None:
    task_id = "hf-hub-xet-endpoint-propagation"
    package = load_task_package(_task_dir(task_id))

    legacy = load_public_review_contract(
        _review_path(task_id),
        task=package.public,
        public_spec_hash=package.public_spec_hash,
    )
    coverage = load_public_review_contract(
        _review_v2_path(task_id),
        task=package.public,
        public_spec_hash=package.public_spec_hash,
    )

    assert legacy.schema_version == "public-review-contract-v1"
    assert legacy.content_hash == (
        "sha256:2d3f31bd6a6f429cfc305229e029a99bd7459a0f97291c3e"
        "804c58eb7b013a2e"
    )
    assert coverage.schema_version == "public-review-contract-v2"
    assert coverage.content_hash == (
        "sha256:51c6c4ace6bb46a5919cc7cfe13088e456088a0f5ed9d87b"
        "67eb75b5a7221cce"
    )
    targets = [
        target
        for requirement in coverage.requirements
        for target in requirement.coverage_targets
    ]
    assert len(targets) == 8
    assert {target.evidence_kind for target in targets} == {
        "current_diff_inspection",
        "passing_validation",
    }
