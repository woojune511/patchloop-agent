from __future__ import annotations

import csv
import json
from pathlib import Path

from patchloop.contracts import DatasetRole
from patchloop.dataset import require_dataset_role
from patchloop.repository import ALLOWED_REMOTE_REPOSITORIES
from patchloop.task_loader import load_task_package

LOGURU_TASK = Path("tasks/dev-train/loguru-invalid-format-feedback")
ANYIO_TASK = Path("tasks/dev-train/anyio-interrupt-runner-cleanup")
TOX_TASK = Path("tasks/dev-train/tox-cross-section-empty-substitution")


def test_loguru_candidate_has_pinned_real_repository_provenance() -> None:
    package = load_task_package(LOGURU_TASK)

    assert package.public.task_id == "loguru-invalid-format-feedback"
    assert package.public.repository.url == "https://github.com/Delgan/loguru.git"
    assert package.public.repository.base_commit == "2abeb0fa6d7be4b0455c6e0b580b1e9dab19005e"
    assert package.public.repository.url in ALLOWED_REMOTE_REPOSITORIES
    assert package.public.constraints.allowed_paths == ["loguru/_handler.py"]
    assert package.public.constraints.max_diff_lines == 60
    assert package.environment is not None
    assert package.environment.image_digest == (
        "sha256:181bd51aa34ebe84d749819dfbe9a2d3d215ff8f6406d897d790f876bc5f36db"
    )
    assert package.environment.evaluator_image.endswith(f"@{package.environment.image_digest}")


def test_loguru_public_contract_excludes_evaluator_only_material() -> None:
    package = load_task_package(LOGURU_TASK)
    public_text = (LOGURU_TASK / "public.yaml").read_text(encoding="utf-8")

    assert "test_invalid_format_feedback.py" not in public_text
    assert "_make_key_error" not in public_text
    assert "reference.patch" not in public_text
    assert package.private.reference_patch.sha256 not in public_text
    assert ".patchloop-hidden" not in "\n".join(
        argument for check in package.public.visible_checks for argument in check.command
    )


def test_loguru_candidate_is_traceable_to_swe_rebench_row() -> None:
    with Path("data/benchmark-candidate-ledger.csv").open(encoding="utf-8", newline="") as handle:
        rows = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    candidate = rows["delgan__loguru-1451"]
    assert candidate["benchmark_revision"] == "ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b"
    assert candidate["base_commit"] == "2abeb0fa6d7be4b0455c6e0b580b1e9dab19005e"
    assert candidate["pr_url"] == "https://github.com/Delgan/loguru/pull/1451"
    assert candidate["status"] == "admitted"


def test_anyio_candidate_has_pinned_real_repository_provenance() -> None:
    package = load_task_package(ANYIO_TASK)

    assert package.public.task_id == "anyio-interrupt-runner-cleanup"
    assert package.public.repository.url == "https://github.com/agronholm/anyio.git"
    assert package.public.repository.base_commit == "cb245dba9883516f2ed4c23899de157183a1cb50"
    assert package.public.repository.url in ALLOWED_REMOTE_REPOSITORIES
    assert package.public.constraints.allowed_paths == ["src/anyio/**"]
    assert package.public.constraints.max_changed_files == 1
    assert package.public.constraints.max_diff_lines == 50
    assert package.environment is not None
    assert package.environment.image_digest == (
        "sha256:063bb968109c70a3fe617d9d30287a3a43d549eb1091b27a030a9af2a74c2320"
    )
    assert package.environment.evaluator_image.endswith(f"@{package.environment.image_digest}")


def test_anyio_public_contract_excludes_evaluator_only_material() -> None:
    package = load_task_package(ANYIO_TASK)
    public_text = (ANYIO_TASK / "public.yaml").read_text(encoding="utf-8")

    assert "test_interrupt_runner_cleanup.py" not in public_text
    assert "OutcomeException" not in public_text
    assert "reference.patch" not in public_text
    assert package.private.reference_patch.sha256 not in public_text
    assert ".patchloop-hidden" not in "\n".join(
        argument for check in package.public.visible_checks for argument in check.command
    )


def test_anyio_candidate_is_traceable_to_swe_rebench_row() -> None:
    with Path("data/benchmark-candidate-ledger.csv").open(encoding="utf-8", newline="") as handle:
        rows = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    candidate = rows["agronholm__anyio-1121"]
    assert candidate["benchmark_revision"] == "ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b"
    assert candidate["base_commit"] == "cb245dba9883516f2ed4c23899de157183a1cb50"
    assert candidate["pr_url"] == "https://github.com/agronholm/anyio/pull/1121"
    assert candidate["status"] == "admitted"


def test_anyio_admission_evidence_records_hardened_reference_and_bad_gold() -> None:
    package = load_task_package(ANYIO_TASK)
    entry = require_dataset_role(
        task_id=package.public.task_id,
        task_version=package.public.task_version,
        public_spec_hash=package.public_spec_hash,
        allowed_roles={DatasetRole.MEMORY_DEVELOPMENT},
    )
    assert entry.admission_evidence is not None
    assert entry.admission_evidence.reference_pass_runs == 3
    assert entry.admission_evidence.rejected_bad_patches == 5

    evidence = json.loads(
        Path("reports/docker-gate/research-anyio-interrupt-runner-cleanup.json").read_text(
            encoding="utf-8"
        )
    )
    assert evidence["harness_git_commit"] == "45949f2065905dcdd35c8c7820d2e549ff221eba"
    assert evidence["reference_policy"]["kind"] == "hardened-upstream"
    assert evidence["reference_hidden_stability_runs"] == 20
    assert evidence["reference_hidden_stability_failures"] == 0
    assert evidence["upstream_regression_test_count"] == 32
    cases = {case["name"]: case for case in evidence["cases"]}
    assert all(cases[f"reference-{index}"]["observed_success"] for index in range(1, 4))
    assert cases["upstream-gold-outcome-regression"]["observed_success"] is False


def test_tox_candidate_has_pinned_real_repository_provenance() -> None:
    package = load_task_package(TOX_TASK)

    assert package.public.task_id == "tox-cross-section-empty-substitution"
    assert package.public.repository.url == "https://github.com/tox-dev/tox.git"
    assert package.public.repository.base_commit == "02e9ed73da6a0f97f9167e957e1168d6116942ce"
    assert package.public.repository.url in ALLOWED_REMOTE_REPOSITORIES
    assert package.public.constraints.allowed_paths == ["src/tox/config/loader/ini/**"]
    assert package.public.constraints.max_changed_files == 2
    assert package.public.constraints.max_diff_lines == 80
    assert package.environment is not None
    assert package.environment.image_digest == (
        "sha256:ffd1129e4be4692becf5011c874858918864d586267002a2917195726542de57"
    )
    assert package.environment.evaluator_image.endswith(f"@{package.environment.image_digest}")


def test_tox_public_contract_excludes_evaluator_only_material() -> None:
    package = load_task_package(TOX_TASK)
    public_text = (TOX_TASK / "public.yaml").read_text(encoding="utf-8")

    assert "test_cross_section_empty_semantics.py" not in public_text
    assert "_resolve_section_proxy" not in public_text
    assert "reference.patch" not in public_text
    assert package.private.reference_patch.sha256 not in public_text
    assert ".patchloop-hidden" not in "\n".join(
        argument for check in package.public.visible_checks for argument in check.command
    )


def test_tox_candidate_is_traceable_to_swe_rebench_row() -> None:
    with Path("data/benchmark-candidate-ledger.csv").open(encoding="utf-8", newline="") as handle:
        rows = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    candidate = rows["tox-dev__tox-3810"]
    assert candidate["benchmark_revision"] == "ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b"
    assert candidate["benchmark_split"] == "2026_02"
    assert candidate["base_commit"] == "02e9ed73da6a0f97f9167e957e1168d6116942ce"
    assert candidate["pr_url"] == "https://github.com/tox-dev/tox/pull/3810"
    assert candidate["f2p"] == "1"
    assert candidate["p2p"] == "29"
    assert candidate["proposed_lane"] == "memory-development"
    assert candidate["status"] == "screening"


def test_same_repository_candidates_are_not_labeled_cross_repo() -> None:
    with Path("data/benchmark-candidate-ledger.csv").open(encoding="utf-8", newline="") as handle:
        rows = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    assert rows["tox-dev__tox-3904"]["proposed_lane"] == "core-same-repo"
    assert rows["agronholm__anyio-1134"]["proposed_lane"] == "core-same-repo"
