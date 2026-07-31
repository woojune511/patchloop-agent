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
