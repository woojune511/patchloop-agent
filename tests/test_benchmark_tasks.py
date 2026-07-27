from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import pytest

from patchloop.contracts import DatasetRole
from patchloop.dataset import require_dataset_role
from patchloop.errors import ContractError
from patchloop.repository import ALLOWED_REMOTE_REPOSITORIES
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_bytes

LOGURU_TASK = Path("tasks/dev-train/loguru-invalid-format-feedback")
ANYIO_TASK = Path("tasks/dev-train/anyio-interrupt-runner-cleanup")
TOX_TASK = Path("tasks/dev-train/tox-cross-section-empty-substitution")
HF_HUB_TASK = Path("tasks/dev-train/hf-hub-xet-endpoint-propagation")
HF_TASK = Path(
    "tasks/same-repo-heldout/hf-hub-custom-tqdm-class-contract"
)
PDM_TASK = Path("tasks/dev-train/pdm-ignore-active-venv-resolution")
PYFAKEFS_TASK = Path("tasks/dev-train/pyfakefs-makedirs-parent-traversal")
PYFAKEFS_CAPABILITY_TASK = Path(
    "tasks/same-repo-heldout/pyfakefs-file-wrapper-io-capabilities"
)
MOTO_TASK = Path("tasks/dev-validation/moto-query-scanned-count")
BABEL_TASK = Path("tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes")
SQLGLOT_TASK = Path(
    "tasks/cross-repo-heldout/sqlglot-duckdb-ignore-nulls-modifier-order"
)
PDM_TARGET_TASK = Path(
    "tasks/same-repo-heldout/pdm-target-project-options-loading"
)
ANYIO_PROCESS_TASK = Path(
    "tasks/same-repo-heldout/anyio-extensionless-entrypoint-worker-main"
)
PARAM_TASK = Path(
    "tasks/cross-repo-heldout/param-shared-rx-fanout-cache"
)
MTPLX_TASK = Path(
    "tasks/cross-repo-heldout/mtplx-mixed-content-tool-call-stream"
)
FUSESOC_TASK = Path(
    "tasks/cross-repo-heldout/fusesoc-retained-parse-error-diagnostics"
)
TOX_DOTTED_TASK = Path(
    "tasks/same-repo-heldout/tox-dotted-version-factor-base-python"
)
DAGSTER_TASK = Path(
    "tasks/cross-repo-heldout/dagster-subset-partition-definition-selection"
)
KUBEFLOW_TASK = Path(
    "tasks/cross-repo-heldout/kubeflow-exit-handler-after-dependencies"
)
LOGURU_TIMEZONE_TASK = Path(
    "tasks/same-repo-heldout/loguru-post-2038-local-timezone-fallback"
)


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
    assert candidate["status"] == "admitted"


def test_same_repository_candidates_are_not_labeled_cross_repo() -> None:
    with Path("data/benchmark-candidate-ledger.csv").open(encoding="utf-8", newline="") as handle:
        rows = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    assert rows["tox-dev__tox-3904"]["proposed_lane"] == "core-same-repo"
    assert rows["agronholm__anyio-1134"]["proposed_lane"] == "core-same-repo"


def test_tox_architecture_candidate_is_excluded_by_dependency_contract() -> None:
    with Path("data/benchmark-candidate-ledger.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    candidate = rows["tox-dev__tox-3904"]
    assert candidate["status"] == "excluded"
    assert candidate["environment_image"].endswith(
        "@sha256:c07d892532885ac2fc4d26e2014555455c7ce9a6ce32884d0eaa6759ba72a3c7"
    )
    assert "direct python-discovery dependency" in candidate["notes"]
    assert "binary dependency policy" in candidate["notes"]
    assert "182/182" in candidate["notes"]


def test_tox_admission_evidence_binds_submitted_source_and_bad_boundaries() -> None:
    package = load_task_package(TOX_TASK)
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
        Path("reports/docker-gate/research-tox-cross-section-empty-substitution.json").read_text(
            encoding="utf-8"
        )
    )
    assert evidence["harness_git_commit"] == "255ea88072f89adf9643c59105366f225e7ca379"
    assert evidence["upstream_regression_test_count"] == 29
    assert evidence["independent_hidden_test_count"] == 6
    assert evidence["admission_checks"]["submitted_source_binding"] == "pass"
    cases = {case["name"]: case for case in evidence["cases"]}
    assert all(cases[f"reference-{index}"]["observed_success"] for index in range(1, 4))
    assert "regression:upstream-show-config-regression" in cases["global-factor-empty"][
        "failed_checks"
    ]
    assert cases["forbidden-test-edit"]["failed_checks"] == [
        "hidden:cross-section-empty-semantics",
        "policy:scope",
        "policy:test_tampering",
    ]


def test_hf_hub_candidate_has_pinned_real_repository_provenance() -> None:
    package = load_task_package(HF_HUB_TASK)

    assert package.public.task_id == "hf-hub-xet-endpoint-propagation"
    assert package.public.repository.url == "https://github.com/huggingface/huggingface_hub.git"
    assert package.public.repository.base_commit == "6f9b87ecda5025259c69a1eb0ae6f8ee80d05d33"
    assert package.public.repository.url in ALLOWED_REMOTE_REPOSITORIES
    assert package.public.constraints.allowed_paths == [
        "src/huggingface_hub/file_download.py",
        "src/huggingface_hub/hf_api.py",
        "src/huggingface_hub/utils/_xet.py",
    ]
    assert package.public.constraints.max_changed_files == 3
    assert package.public.constraints.max_diff_lines == 80
    assert package.public.constraints.public_api_changes_allowed is True
    assert package.environment is not None
    assert package.environment.image_digest == (
        "sha256:c698facf4c9a9e636b8dc114aa9bda6a17ee5f89fe3efd43f39a6543540e891f"
    )
    assert package.environment.evaluator_image.endswith(f"@{package.environment.image_digest}")
    assert package.public.visible_checks[0].environment["PYTHONPATH"] == "/workspace/src"


def test_hf_hub_public_contract_excludes_evaluator_only_material() -> None:
    package = load_task_package(HF_HUB_TASK)
    public_text = (HF_HUB_TASK / "public.yaml").read_text(encoding="utf-8")

    assert "test_xet_endpoint_propagation.py" not in public_text
    assert "parse_xet_file_data_from_response" not in public_text
    assert "reference.patch" not in public_text
    assert package.private.reference_patch.sha256 not in public_text
    assert ".patchloop-hidden" not in "\n".join(
        argument for check in package.public.visible_checks for argument in check.command
    )


def test_hf_hub_candidate_is_traceable_to_swe_rebench_v2_row() -> None:
    with Path("data/benchmark-candidate-ledger.csv").open(encoding="utf-8", newline="") as handle:
        rows = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    candidate = rows["huggingface__huggingface_hub-3180"]
    assert candidate["benchmark_revision"] == "475dd5e8703bb5fb22dd3c60b5d038b019eba1e0"
    assert candidate["benchmark_split"] == "train"
    assert candidate["base_commit"] == "6f9b87ecda5025259c69a1eb0ae6f8ee80d05d33"
    assert candidate["pr_url"] == "https://github.com/huggingface/huggingface_hub/pull/3180"
    assert candidate["changed_files"] == "3"
    assert candidate["f2p"] == "2"
    assert candidate["p2p"] == "15"
    assert candidate["proposed_lane"] == "memory-development"
    assert candidate["status"] == "admitted"


def test_hf_hub_admission_evidence_binds_source_api_and_bad_boundaries() -> None:
    package = load_task_package(HF_HUB_TASK)
    entry = require_dataset_role(
        task_id=package.public.task_id,
        task_version=package.public.task_version,
        public_spec_hash=package.public_spec_hash,
        allowed_roles={DatasetRole.MEMORY_DEVELOPMENT},
    )
    assert entry.admission_evidence is not None
    assert entry.admission_evidence.reference_pass_runs == 3
    assert entry.admission_evidence.rejected_bad_patches == 6

    evidence = json.loads(
        Path("reports/docker-gate/research-hf-hub-xet-endpoint-propagation.json").read_text(
            encoding="utf-8"
        )
    )
    assert evidence["harness_git_commit"] == "ebf05dd5327df011e7ec20ede3c3f01d14054007"
    assert evidence["upstream_regression_test_count"] == 15
    assert evidence["independent_hidden_test_count"] == 8
    assert evidence["admission_checks"]["submitted_source_binding"] == "pass"
    assert evidence["admission_checks"]["exact_public_signature_delta"] == "pass"
    cases = {case["name"]: case for case in evidence["cases"]}
    assert all(cases[f"reference-{index}"]["observed_success"] for index in range(1, 4))
    for case_name in (
        "parser-only",
        "missing-hf-api-forwarding",
        "missing-download-forwarding",
        "unguarded-substring-replace",
        "hardcoded-default-endpoint",
    ):
        assert cases[case_name]["failed_checks"] == ["hidden:xet-endpoint-propagation"]
    assert cases["forbidden-test-edit"]["failed_checks"] == [
        "hidden:xet-endpoint-propagation",
        "policy:scope",
        "policy:test_tampering",
    ]


def test_pdm_candidate_has_pinned_real_repository_provenance() -> None:
    package = load_task_package(PDM_TASK)

    assert package.public.task_id == "pdm-ignore-active-venv-resolution"
    assert package.public.repository.url == "https://github.com/pdm-project/pdm.git"
    assert package.public.repository.base_commit == "881cd4e38d31663ae67bdae227ec1ccdfd5e2c77"
    assert package.public.repository.url in ALLOWED_REMOTE_REPOSITORIES
    assert package.public.constraints.allowed_paths == ["src/pdm/project/core.py"]
    assert package.public.constraints.max_changed_files == 1
    assert package.public.constraints.max_diff_lines == 60
    assert package.public.constraints.public_api_changes_allowed is False
    assert package.environment is not None
    assert package.environment.image_digest == (
        "sha256:a822ad3888e56650c18e9506f8d7882c145ed83d47d518e541e3e44406a929a0"
    )
    assert package.environment.evaluator_image.endswith(f"@{package.environment.image_digest}")
    assert package.public.visible_checks[0].environment["PYTHONPATH"] == "/workspace/src"


def test_pdm_public_contract_excludes_evaluator_only_material() -> None:
    package = load_task_package(PDM_TASK)
    public_text = (PDM_TASK / "public.yaml").read_text(encoding="utf-8")

    assert "test_ignore_active_venv_resolution.py" not in public_text
    assert "is_path_relative_to" not in public_text
    assert "ensure_boolean" not in public_text
    assert "reference.patch" not in public_text
    assert package.private.reference_patch.sha256 not in public_text
    assert ".patchloop-hidden" not in "\n".join(
        argument for check in package.public.visible_checks for argument in check.command
    )


def test_pdm_candidate_is_traceable_to_swe_rebench_v2_row() -> None:
    with Path("data/benchmark-candidate-ledger.csv").open(encoding="utf-8", newline="") as handle:
        rows = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    candidate = rows["pdm-project__pdm-2781"]
    assert candidate["benchmark_revision"] == "475dd5e8703bb5fb22dd3c60b5d038b019eba1e0"
    assert candidate["benchmark_split"] == "train"
    assert candidate["base_commit"] == "881cd4e38d31663ae67bdae227ec1ccdfd5e2c77"
    assert candidate["pr_url"] == "https://github.com/pdm-project/pdm/pull/2781"
    assert candidate["changed_files"] == "2"
    assert candidate["f2p"] == "1"
    assert candidate["p2p"] == "37"
    assert candidate["proposed_lane"] == "memory-development"
    assert candidate["status"] == "admitted"


def test_pdm_admission_evidence_binds_resolution_semantics_and_bad_boundaries() -> None:
    package = load_task_package(PDM_TASK)
    entry = require_dataset_role(
        task_id=package.public.task_id,
        task_version=package.public.task_version,
        public_spec_hash=package.public_spec_hash,
        allowed_roles={DatasetRole.MEMORY_DEVELOPMENT},
    )
    assert entry.role == DatasetRole.MEMORY_DEVELOPMENT
    assert entry.admission_evidence is not None
    assert entry.admission_evidence.reference_pass_runs == 3
    assert entry.admission_evidence.rejected_bad_patches == 7

    evidence = json.loads(
        Path("reports/docker-gate/research-pdm-ignore-active-venv-resolution.json").read_text(
            encoding="utf-8"
        )
    )
    assert evidence["harness_git_commit"] == "035d7c7f4be10966cfd6a9cf839c029f93614167"
    assert evidence["reference_policy"]["kind"] == "normalized-upstream-production-only"
    assert evidence["reference_pass_count"] == 3
    assert evidence["base_noop_rejection_count"] == 1
    assert evidence["known_bad_patch_rejection_count"] == 7
    assert evidence["upstream_regression_test_count"] == 36
    assert evidence["benchmark_p2p_declared_count"] == 37
    assert evidence["independent_hidden_test_count"] == 10
    for check_id in (
        "submitted_source_binding",
        "false_like_flag_semantics",
        "active_prefix_sources",
        "path_component_boundary",
        "benchmark_test_patch_accounting",
    ):
        assert evidence["admission_checks"][check_id] == "pass"


def test_pyfakefs_capability_task_has_pinned_real_repository_contract() -> None:
    package = load_task_package(PYFAKEFS_CAPABILITY_TASK)

    assert package.public.task_id == "pyfakefs-file-wrapper-io-capabilities"
    assert package.public.split == "same-repo-heldout"
    assert package.public.repository.url == "https://github.com/pytest-dev/pyfakefs.git"
    assert package.public.repository.base_commit == (
        "a3685da29db2f185d4793f185ca07dfe36f3d9a9"
    )
    assert package.public.constraints.allowed_paths == ["pyfakefs/fake_file.py"]
    assert package.public.constraints.max_changed_files == 1
    assert package.public.constraints.max_diff_lines == 60
    assert package.public.constraints.dependency_changes_allowed is False
    assert package.public.constraints.public_api_changes_allowed is True
    assert package.private.schema_version == "task-private-v2"
    assert package.environment is not None
    assert package.environment.evaluator_image.endswith(
        "@sha256:02c69afcbf763a1ede2637197e0979327f7b29392f2fedeead6e2a17e8746a91"
    )


def test_pyfakefs_capability_public_contract_excludes_evaluator_material() -> None:
    package = load_task_package(PYFAKEFS_CAPABILITY_TASK)
    public_text = (PYFAKEFS_CAPABILITY_TASK / "public.yaml").read_text(
        encoding="utf-8"
    )

    assert "reference.patch" not in public_text
    assert "test_file_wrapper_io_capabilities.py" not in public_text
    assert "benchmark test" not in public_text.lower()
    assert package.private.reference_patch.sha256 not in public_text
    assert package.private.hidden_artifacts[0].sha256 not in public_text
    assert ".patchloop-hidden" not in "\n".join(
        argument for check in package.public.visible_checks for argument in check.command
    )


def test_pyfakefs_capability_admission_is_traceable_to_frozen_rebench_row() -> None:
    with Path("data/benchmark-candidate-ledger.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    candidate = rows["pytest-dev__pyfakefs-1269"]
    assert candidate["benchmark_family"] == "SWE-rebench-leaderboard"
    assert candidate["benchmark_revision"] == (
        "ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b"
    )
    assert candidate["benchmark_split"] == "test"
    assert candidate["upstream_repository"] == "pytest-dev/pyfakefs"
    assert candidate["base_commit"] == (
        "a3685da29db2f185d4793f185ca07dfe36f3d9a9"
    )
    assert candidate["pr_url"] == "https://github.com/pytest-dev/pyfakefs/pull/1269"
    assert candidate["license_spdx"] == "Apache-2.0"
    assert candidate["gold_patch_lines"] == "58"
    assert candidate["test_patch_lines"] == "34"
    assert candidate["changed_files"] == "1"
    assert candidate["f2p"] == "1"
    assert candidate["p2p"] == "431"
    assert candidate["proposed_lane"] == "core-same-repo"
    assert candidate["status"] == "admitted"
    assert candidate["environment_image"].endswith(
        "@sha256:02c69afcbf763a1ede2637197e0979327f7b29392f2fedeead6e2a17e8746a91"
    )
    assert "row 653" in candidate["notes"]
    assert "passed 3/3 official runs" in candidate["notes"]
    assert "dynamic-interface equivalent passed 1/1" in candidate["notes"]
    assert "431 visible tests with 161 skips" in candidate["notes"]
    assert "all 15 cases made zero model/API calls" in candidate["notes"]


def test_pyfakefs_capability_reference_is_exact_production_patch() -> None:
    package = load_task_package(PYFAKEFS_CAPABILITY_TASK)
    reference_path = (
        PYFAKEFS_CAPABILITY_TASK / package.private.reference_patch.path
    )
    patch_text = reference_path.read_text(encoding="utf-8")
    patch_lines = patch_text.splitlines()

    assert package.private.reference_patch.sha256 == (
        "sha256:21f7350ac6a344e0a076a91491e41f0a08f223c32be5f4354c4db1ccc460fa7d"
    )
    assert sha256_bytes(reference_path.read_bytes()) == (
        package.private.reference_patch.sha256
    )
    assert sum(
        line.startswith("+") and not line.startswith("+++") for line in patch_lines
    ) == 11
    assert sum(
        line.startswith("-") and not line.startswith("---") for line in patch_lines
    ) == 3
    assert {
        line.removeprefix("diff --git a/").split(" b/", maxsplit=1)[0]
        for line in patch_lines
        if line.startswith("diff --git a/")
    } == {"pyfakefs/fake_file.py"}
    assert "pyfakefs/tests/" not in patch_text
    assert "CHANGES.md" not in patch_text


def test_pyfakefs_capability_oracle_and_patch_inventory_are_explicit() -> None:
    package = load_task_package(PYFAKEFS_CAPABILITY_TASK)
    hidden_path = (
        PYFAKEFS_CAPABILITY_TASK / "hidden/test_file_wrapper_io_capabilities.py"
    )
    hidden_text = hidden_path.read_text(encoding="utf-8")
    bad_names = sorted(
        path.name for path in (PYFAKEFS_CAPABILITY_TASK / "bad").glob("*.patch")
    )
    equivalent_path = (
        PYFAKEFS_CAPABILITY_TASK
        / "equivalent/dynamic-capability-interface.patch"
    )

    assert hidden_text.count("\ndef test_") == 10
    for marker in (
        '("r", True, False)',
        '("w", False, True)',
        '("a", False, True)',
        '("x", False, True)',
        '("r+", True, True)',
        '("a+b", True, True)',
        "TextIOWrapper",
        "handle.readable = lambda: True",
        "handle.readable = lambda: False",
        "actual_read_from_write_only",
        "actual_write_to_read_only",
    ):
        assert marker in hidden_text
    assert [artifact.path for artifact in package.private.hidden_artifacts] == [
        "hidden/test_file_wrapper_io_capabilities.py"
    ]
    assert package.private.hidden_artifacts[0].sha256 == (
        "sha256:3a3e796931d0bfd751d6303947f82cfc293c3ee79155321a22c2008eae2a7d2f"
    )
    assert sha256_bytes(hidden_path.read_bytes()) == (
        package.private.hidden_artifacts[0].sha256
    )
    assert bad_names == [
        "always-readable.patch",
        "always-writable.patch",
        "capability-properties.patch",
        "forbidden-test-edit.patch",
        "inverted-capabilities.patch",
        "methods-without-dispatch.patch",
        "mirrored-capabilities.patch",
        "noop.patch",
        "primary-mode-only.patch",
        "readable-only.patch",
        "underlying-buffer-capabilities.patch",
    ]
    assert (PYFAKEFS_CAPABILITY_TASK / "bad/noop.patch").read_bytes() == b"\n"
    assert sha256_bytes(equivalent_path.read_bytes()) == (
        "sha256:9ae6bb6a86a82244b4f11e647f8815312fe0af4aaa1c3ea9dcf46008a4a0c1f8"
    )
    equivalent_text = equivalent_path.read_text(encoding="utf-8")
    assert 'if name == "readable"' in equivalent_text
    assert "def readable" not in equivalent_text

    audit_text = (PYFAKEFS_CAPABILITY_TASK / "audit.md").read_text(
        encoding="utf-8"
    )
    assert "Admission state: admitted" in audit_text
    assert "ten pytest functions collecting 29 cases" in audit_text
    assert "one no-op, nine semantic partials" in audit_text
    assert "implementation-independent positive control" in audit_text
    assert "Medium under `dataset-manifest-v1`" in audit_text
    assert "sixth `core-same-repo` task" in audit_text
    assert "Exact upstream reference: 3/3 full SCRR passes" in audit_text
    assert "Model/API calls and model cost: 0 and USD 0" in audit_text


def test_pyfakefs_capability_private_v2_rejects_hidden_oracle_mutation(
    tmp_path: Path,
) -> None:
    copied_task = tmp_path / PYFAKEFS_CAPABILITY_TASK.name
    shutil.copytree(PYFAKEFS_CAPABILITY_TASK, copied_task)
    hidden_path = copied_task / "hidden/test_file_wrapper_io_capabilities.py"
    hidden_path.write_text(
        hidden_path.read_text(encoding="utf-8") + "\n# unbound mutation\n",
        encoding="utf-8",
    )

    with pytest.raises(ContractError, match="hidden artifact hash mismatch"):
        load_task_package(copied_task)


def test_pyfakefs_capability_lineage_is_distinct_from_memory_development() -> None:
    development = load_task_package(PYFAKEFS_TASK)
    held_out = load_task_package(PYFAKEFS_CAPABILITY_TASK)
    audit_text = (PYFAKEFS_CAPABILITY_TASK / "audit.md").read_text(
        encoding="utf-8"
    )

    assert held_out.public.repository.url == development.public.repository.url
    assert held_out.public.repository.base_commit != (
        development.public.repository.base_commit
    )
    assert held_out.public.task_id != development.public.task_id
    assert set(held_out.public.constraints.allowed_paths).isdisjoint(
        development.public.constraints.allowed_paths
    )
    assert "pytest-dev-pyfakefs-pr-1269" in audit_text
    assert "PR #991" in audit_text
    assert "`pyfakefs/fake_file.py`" in audit_text
    assert "`pyfakefs/fake_os.py`" in audit_text


def test_pyfakefs_capability_admission_evidence_binds_all_boundaries() -> None:
    package = load_task_package(PYFAKEFS_CAPABILITY_TASK)
    entry = require_dataset_role(
        task_id=package.public.task_id,
        task_version=package.public.task_version,
        public_spec_hash=package.public_spec_hash,
        allowed_roles={DatasetRole.CORE_SAME_REPO},
    )
    assert entry.role == DatasetRole.CORE_SAME_REPO
    assert entry.failure_pattern_id == (
        "file-wrapper-capability-query-hits-operation-guard"
    )
    assert entry.solution_lineage_id == "pytest-dev-pyfakefs-pr-1269"
    assert entry.admission_evidence is not None
    assert entry.admission_evidence.reference_pass_runs == 3
    assert entry.admission_evidence.rejected_bad_patches == 10

    evidence_path = Path(
        "reports/docker-gate/research-pyfakefs-file-wrapper-io-capabilities.json"
    )
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert sha256_bytes(evidence_path.read_bytes()) == (
        entry.admission_evidence.sha256
    )
    assert evidence["task_id"] == package.public.task_id
    assert evidence["task_version"] == package.public.task_version
    assert evidence["dataset_role"] == entry.role.value
    assert evidence["split"] == package.public.split
    assert evidence["public_spec_hash"] == package.public_spec_hash
    assert evidence["private_spec_hash"] == package.private_spec_hash
    assert evidence["source"]["base_commit"] == package.public.repository.base_commit
    assert evidence["evaluator_image"] == package.environment.evaluator_image
    assert evidence["evaluator_image_digest"] == package.environment.image_digest
    assert evidence["harness_git_commit"] == (
        "b50b4314aa7fd209737db46f15b38aee056bbd80"
    )
    assert evidence["reference_policy"]["kind"] == (
        "exact-upstream-production-only"
    )
    assert evidence["reference_policy"]["rejected_benchmark_production_patch"] is (
        False
    )
    assert evidence["source"]["benchmark_production_patch_sha256"] == (
        package.private.reference_patch.sha256
    )
    assert evidence["source"]["benchmark_gold_patch_sha256"] == (
        "sha256:477352e8cb5b51653d1ac2afbde24dadf329cbc46afb98ce8a983cd2b457d9e6"
    )
    assert evidence["source"]["benchmark_test_patch_sha256"] == (
        "sha256:39edf7cfec5497ae55af6ccb0b6ba3f6c0d606cc00543bfd9a074f352594e47a"
    )
    assert evidence["source"]["private_hidden_artifact_sha256"] == (
        package.private.hidden_artifacts[0].sha256
    )
    assert evidence["source"]["base_source_blob_sha1"] == {
        "pyfakefs/fake_file.py": "2cc3f1eda46008fafa8fafbaa19af716b50f6ff6"
    }
    assert evidence["source"]["accepted_source_blob_sha1"] == {
        "pyfakefs/fake_file.py": "293b39340acd8e75ccc1902e2bf86b5c84f64336"
    }
    assert evidence["reference_pass_count"] == 3
    assert evidence["equivalent_solution_pass_count"] == 1
    assert evidence["base_noop_rejection_count"] == 1
    assert evidence["known_bad_patch_rejection_count"] == 10
    assert evidence["semantic_bad_patch_rejection_count"] == 9
    assert evidence["independent_hidden_test_count"] == 29
    assert evidence["independent_hidden_test_function_count"] == 10
    assert evidence["benchmark_f2p_declared_count"] == 1
    assert evidence["benchmark_p2p_declared_count"] == 431
    assert evidence["upstream_regression_test_count"] == 431
    assert evidence["upstream_regression_collected_count"] == 592
    assert evidence["upstream_regression_skip_count"] == 161
    assert evidence["official_run_count"] == 15
    assert evidence["observed_timeout_count"] == 0
    assert evidence["observed_output_truncation_count"] == 0
    assert evidence["api_calls"] == 0
    assert evidence["model_cost_usd"] == 0
    assert evidence["runtime"]["working_directory"] == "/workspace"
    assert evidence["runtime"]["network"] == "none"
    assert evidence["runtime"]["root_filesystem"] == "read-only"
    assert evidence["runtime"]["workspace_mount"] == "read-only"

    expected_failed_checks = {
        "reference-1": [],
        "reference-2": [],
        "reference-3": [],
        "equivalent-dynamic-capability-interface": [],
        "base-noop": ["hidden:file-wrapper-io-capabilities"],
        "always-readable": [
            "regression:upstream-file-wrapper-regression",
            "hidden:file-wrapper-io-capabilities",
        ],
        "always-writable": ["hidden:file-wrapper-io-capabilities"],
        "capability-properties": ["hidden:file-wrapper-io-capabilities"],
        "inverted-capabilities": [
            "regression:upstream-file-wrapper-regression",
            "hidden:file-wrapper-io-capabilities",
        ],
        "methods-without-dispatch": ["hidden:file-wrapper-io-capabilities"],
        "mirrored-capabilities": ["hidden:file-wrapper-io-capabilities"],
        "primary-mode-only": [
            "regression:upstream-file-wrapper-regression",
            "hidden:file-wrapper-io-capabilities",
        ],
        "readable-only": ["hidden:file-wrapper-io-capabilities"],
        "underlying-buffer-capabilities": [
            "regression:upstream-file-wrapper-regression",
            "hidden:file-wrapper-io-capabilities",
        ],
        "forbidden-test-edit": [
            "hidden:file-wrapper-io-capabilities",
            "policy:scope",
            "policy:test_tampering",
        ],
    }
    expected_run_ids = {
        "run_b9902d125f9a4a9e",
        "run_41bba6a0e480483c",
        "run_d0a0277614f04b49",
        "run_1bf5034e9a2a48fb",
        "run_6b26a5042d6048dc",
        "run_272aef3e9f8b45df",
        "run_8e37f09772804bbb",
        "run_2eba08c5e18444b7",
        "run_a6035f0254c644d5",
        "run_ebee495659fb4b84",
        "run_30af1e08c34644a1",
        "run_2fe623b9d2b84d4a",
        "run_43325244972e44ff",
        "run_4d3a7746a3eb4e5a",
        "run_722a1d4381a74127",
    }
    cases = {case["name"]: case for case in evidence["cases"]}
    assert set(cases) == set(expected_failed_checks)
    assert {case["run_id"] for case in cases.values()} == expected_run_ids
    assert all(case["official"] for case in cases.values())
    assert all(
        case["observed_success"] is case["expected_success"]
        for case in cases.values()
    )
    for name, failed_checks in expected_failed_checks.items():
        case = cases[name]
        assert case["failed_checks"] == failed_checks
        patch_path = PYFAKEFS_CAPABILITY_TASK / case["patch"]
        assert sha256_bytes(patch_path.read_bytes()) == case["patch_sha256"]
        for key in ("manifest_sha256", "result_sha256", "provenance_sha256"):
            digest = case[key]
            assert digest.startswith("sha256:")
            assert len(digest) == 71
    for index in range(1, 4):
        assert cases[f"reference-{index}"]["patch_sha256"] == (
            package.private.reference_patch.sha256
        )

    assert evidence["admission_checks"]["base_visible_checks"] == "pass"
    assert evidence["admission_checks"]["base_hidden_acceptance"] == "fail"
    for check_id in (
        "reference_scrr_three_repetitions",
        "dynamic_interface_equivalent_solution",
        "known_bad_boundaries",
        "upstream_regression_oracle",
        "independent_hidden_acceptance",
        "submitted_source_binding",
        "complete_text_and_binary_mode_matrix",
        "text_io_wrapper_construction",
        "binary_text_io_write_through",
        "disallowed_read_and_write_errors_preserved",
        "update_mode_operations_preserved",
        "readable_iterator_behavior_preserved",
        "capability_override_controls_internal_guards",
        "exact_upstream_production_lineage",
        "benchmark_changelog_hunk_excluded",
        "benchmark_test_patch_excluded",
        "private_v2_hidden_artifact_bound",
        "visible_test_read_only",
        "hidden_oracle_read_only",
        "test_tampering_path_recognition",
        "same_repository_solution_lineage_is_distinct",
        "public_private_separation",
        "no_new_dependency",
        "intentional_public_api_extension",
        "network_disabled_evaluator",
        "read_only_root_filesystem",
        "read_only_submitted_workspace",
        "external_image_default_user_disclosed",
        "immutable_source_commit",
        "immutable_evaluator_image",
        "exact_sha_shallow_checkout",
    ):
        assert evidence["admission_checks"][check_id] == "pass"


def test_pdm_admission_case_inventory_is_content_addressed() -> None:
    package = load_task_package(PDM_TASK)
    evidence = json.loads(
        Path(
            "reports/docker-gate/research-pdm-ignore-active-venv-resolution.json"
        ).read_text(encoding="utf-8")
    )

    cases = {case["name"]: case for case in evidence["cases"]}
    assert len(cases) == 11
    assert len({case["run_id"] for case in cases.values()}) == 11
    assert all(case["official"] for case in cases.values())
    assert all(cases[f"reference-{index}"]["observed_success"] for index in range(1, 4))
    assert {
        cases[f"reference-{index}"]["patch_sha256"] for index in range(1, 4)
    } == {package.private.reference_patch.sha256}
    assert cases["base-noop"]["failed_checks"] == [
        "hidden:ignore-active-venv-resolution"
    ]
    for case_name in (
        "outer-guard-only",
        "direct-only-filter",
        "raw-env-truthiness",
        "skip-associated-venvs",
        "string-prefix-containment",
        "virtual-env-only",
    ):
        assert cases[case_name]["failed_checks"] == ["hidden:ignore-active-venv-resolution"]
    assert cases["forbidden-test-edit"]["failed_checks"] == [
        "hidden:ignore-active-venv-resolution",
        "policy:scope",
        "policy:test_tampering",
    ]


def test_pyfakefs_candidate_has_pinned_real_repository_provenance() -> None:
    package = load_task_package(PYFAKEFS_TASK)

    assert package.public.task_id == "pyfakefs-makedirs-parent-traversal"
    assert package.public.repository.url == "https://github.com/pytest-dev/pyfakefs.git"
    assert package.public.repository.base_commit == "7285b671883b8a06fc26466582a8a45baf508bf7"
    assert package.public.repository.url in ALLOWED_REMOTE_REPOSITORIES
    assert package.public.constraints.allowed_paths == ["pyfakefs/fake_os.py"]
    assert package.public.constraints.max_changed_files == 1
    assert package.public.constraints.max_diff_lines == 50
    assert package.public.constraints.public_api_changes_allowed is False
    assert package.environment is not None
    assert package.environment.image_digest == (
        "sha256:6de3b39018eec22728567f44dfbdc3cbd31322c384f6ee3d7f328ef38165d57c"
    )
    assert package.environment.evaluator_image.endswith(f"@{package.environment.image_digest}")
    assert package.public.visible_checks[0].environment["PYTHONPATH"] == "/workspace"


def test_pyfakefs_public_contract_excludes_evaluator_only_material() -> None:
    package = load_task_package(PYFAKEFS_TASK)
    public_text = (PYFAKEFS_TASK / "public.yaml").read_text(encoding="utf-8")

    assert "test_makedirs_parent_traversal.py" not in public_text
    assert "reference.patch" not in public_text
    assert package.private.reference_patch.sha256 not in public_text
    assert ".patchloop-hidden" not in "\n".join(
        argument for check in package.public.visible_checks for argument in check.command
    )


def test_pyfakefs_candidate_is_traceable_to_swe_rebench_v2_row() -> None:
    with Path("data/benchmark-candidate-ledger.csv").open(encoding="utf-8", newline="") as handle:
        rows = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    candidate = rows["pytest-dev__pyfakefs-991"]
    assert candidate["benchmark_revision"] == "475dd5e8703bb5fb22dd3c60b5d038b019eba1e0"
    assert candidate["benchmark_split"] == "train"
    assert candidate["base_commit"] == "7285b671883b8a06fc26466582a8a45baf508bf7"
    assert candidate["pr_url"] == "https://github.com/pytest-dev/pyfakefs/pull/991"
    assert candidate["changed_files"] == "2"
    assert candidate["f2p"] == "1"
    assert candidate["p2p"] == "517"
    assert candidate["proposed_lane"] == "memory-development"
    assert candidate["status"] == "admitted"


def test_pyfakefs_admission_evidence_binds_traversal_and_bad_boundaries() -> None:
    package = load_task_package(PYFAKEFS_TASK)
    entry = require_dataset_role(
        task_id=package.public.task_id,
        task_version=package.public.task_version,
        public_spec_hash=package.public_spec_hash,
        allowed_roles={DatasetRole.MEMORY_DEVELOPMENT},
    )
    assert entry.role == DatasetRole.MEMORY_DEVELOPMENT
    assert entry.admission_evidence is not None
    assert entry.admission_evidence.reference_pass_runs == 3
    assert entry.admission_evidence.rejected_bad_patches == 8

    evidence = json.loads(
        Path("reports/docker-gate/research-pyfakefs-makedirs-parent-traversal.json").read_text(
            encoding="utf-8"
        )
    )
    assert evidence["harness_git_commit"] == "64b2f46700d2f98793ae876a8c6cf6caccd8836d"
    assert evidence["reference_policy"]["kind"] == "normalized-upstream-production-only"
    assert evidence["reference_pass_count"] == 3
    assert evidence["base_noop_rejection_count"] == 1
    assert evidence["known_bad_patch_rejection_count"] == 8
    assert evidence["upstream_regression_test_count"] == 517
    assert evidence["benchmark_p2p_declared_count"] == 517
    assert evidence["independent_hidden_test_count"] == 12
    for check_id in (
        "submitted_source_binding",
        "posix_windows_component_order",
        "nested_and_bytes_path_semantics",
        "exist_ok_and_invalid_parent_semantics",
        "leaf_intermediate_mode_separation",
        "benchmark_test_patch_accounting",
    ):
        assert evidence["admission_checks"][check_id] == "pass"

    cases = {case["name"]: case for case in evidence["cases"]}
    assert len(cases) == 12
    assert len({case["run_id"] for case in cases.values()}) == 12
    assert all(case["official"] for case in cases.values())
    assert all(cases[f"reference-{index}"]["observed_success"] for index in range(1, 4))
    assert {
        cases[f"reference-{index}"]["patch_sha256"] for index in range(1, 4)
    } == {package.private.reference_patch.sha256}
    assert cases["base-noop"]["failed_checks"] == ["hidden:makedirs-parent-traversal"]
    for case_name in ("single-parent-string-only", "parent-mode-propagation"):
        assert cases[case_name]["failed_checks"] == ["hidden:makedirs-parent-traversal"]
    for case_name in (
        "normalize-before-create",
        "ignore-exist-ok",
        "stop-after-parent-creation",
        "swallow-nondirectory-when-exist-ok",
        "uncaught-parent-exists",
    ):
        assert cases[case_name]["failed_checks"] == [
            "regression:upstream-fake-os-regression",
            "hidden:makedirs-parent-traversal",
        ]
    assert cases["forbidden-test-edit"]["failed_checks"] == [
        "hidden:makedirs-parent-traversal",
        "policy:scope",
        "policy:test_tampering",
    ]


def test_moto_candidate_has_pinned_real_repository_provenance() -> None:
    package = load_task_package(MOTO_TASK)

    assert package.public.task_id == "moto-query-scanned-count"
    assert package.public.split == "dev-validation"
    assert package.public.repository.url == "https://github.com/getmoto/moto.git"
    assert (
        package.public.repository.base_commit
        == "624de34d82a1b2c521727b14a2173380e196f1d8"
    )
    assert package.public.repository.url in ALLOWED_REMOTE_REPOSITORIES
    assert package.public.constraints.allowed_paths == ["moto/dynamodb/models/table.py"]
    assert package.public.constraints.max_changed_files == 1
    assert package.public.constraints.max_diff_lines == 120
    assert package.environment is not None
    assert package.environment.image_digest == (
        "sha256:dfdf957ab30b8829e8b6bbfd693b00fab88b7979d3c856362fd5d66c489a1fee"
    )
    assert package.environment.evaluator_image.endswith(f"@{package.environment.image_digest}")
    assert package.public.visible_checks[0].environment["PYTHONPATH"] == "/workspace"


def test_moto_public_contract_excludes_evaluator_only_material() -> None:
    package = load_task_package(MOTO_TASK)
    public_text = (MOTO_TASK / "public.yaml").read_text(encoding="utf-8")

    assert "test_query_scanned_count.py" not in public_text
    assert "reference.patch" not in public_text
    assert package.private.reference_patch.sha256 not in public_text
    assert ".patchloop-hidden" not in "\n".join(
        argument for check in package.public.visible_checks for argument in check.command
    )


def test_moto_candidate_is_traceable_to_swe_rebench_v2_row() -> None:
    with Path("data/benchmark-candidate-ledger.csv").open(encoding="utf-8", newline="") as handle:
        rows = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    candidate = rows["getmoto__moto-7208"]
    assert candidate["benchmark_revision"] == "475dd5e8703bb5fb22dd3c60b5d038b019eba1e0"
    assert candidate["benchmark_split"] == "train"
    assert candidate["base_commit"] == "624de34d82a1b2c521727b14a2173380e196f1d8"
    assert candidate["pr_url"] == "https://github.com/getmoto/moto/pull/7208"
    assert candidate["changed_files"] == "3"
    assert candidate["f2p"] == "3"
    assert candidate["p2p"] == "173"
    assert candidate["proposed_lane"] == "development-validation"
    assert candidate["status"] == "admitted"


def test_moto_oracle_and_bad_patch_inventory_are_explicit() -> None:
    hidden_text = (MOTO_TASK / "hidden/test_query_scanned_count.py").read_text(encoding="utf-8")
    bad_names = sorted(path.name for path in (MOTO_TASK / "bad").glob("*.patch"))

    assert hidden_text.count("\ndef test_") == 9
    assert bad_names == [
        "cursor-subtraction-without-limit.patch",
        "forbidden-test-edit.patch",
        "index-uses-table-count.patch",
        "key-results-before-page.patch",
        "limit-without-cursor.patch",
        "noop.patch",
        "partition-total-only.patch",
        "post-filter-result-count.patch",
    ]


def test_moto_admission_evidence_binds_query_stage_boundaries() -> None:
    package = load_task_package(MOTO_TASK)
    entry = require_dataset_role(
        task_id=package.public.task_id,
        task_version=package.public.task_version,
        public_spec_hash=package.public_spec_hash,
        allowed_roles={DatasetRole.DEVELOPMENT_VALIDATION},
    )
    assert entry.role == DatasetRole.DEVELOPMENT_VALIDATION
    assert entry.admission_evidence is not None
    assert entry.admission_evidence.reference_pass_runs == 3
    assert entry.admission_evidence.rejected_bad_patches == 7

    evidence = json.loads(
        Path("reports/docker-gate/research-moto-query-scanned-count.json").read_text(
            encoding="utf-8"
        )
    )
    assert evidence["harness_git_commit"] == "b4cc0ec8d2dffad907f31ed8ffac220ed0353c38"
    assert evidence["reference_policy"]["kind"] == "normalized-upstream-production-only"
    assert evidence["reference_pass_count"] == 3
    assert evidence["base_noop_rejection_count"] == 1
    assert evidence["known_bad_patch_rejection_count"] == 7
    assert evidence["semantic_bad_patch_rejection_count"] == 6
    assert evidence["upstream_regression_test_count"] == 182
    assert evidence["benchmark_p2p_declared_count"] == 173
    assert evidence["benchmark_p2p_concrete_count"] == 179
    assert evidence["non_p2p_network_test_deselection_count"] == 9
    assert evidence["independent_hidden_test_count"] == 9
    for check_id in (
        "submitted_source_binding",
        "partition_and_empty_query_accounting",
        "filter_stage_accounting",
        "range_and_index_accounting",
        "limit_and_exclusive_start_key_accounting",
        "projection_and_ordering_stability",
        "benchmark_p2p_network_independence",
        "non_p2p_network_exclusions_disclosed",
    ):
        assert evidence["admission_checks"][check_id] == "pass"

    cases = {case["name"]: case for case in evidence["cases"]}
    assert len(cases) == 11
    assert len({case["run_id"] for case in cases.values()}) == 11
    assert all(case["official"] for case in cases.values())
    assert all(cases[f"reference-{index}"]["observed_success"] for index in range(1, 4))
    assert {
        cases[f"reference-{index}"]["patch_sha256"] for index in range(1, 4)
    } == {package.private.reference_patch.sha256}
    assert cases["base-noop"]["failed_checks"] == ["hidden:query-scanned-count"]
    for case_name in (
        "partition-total-only",
        "key-results-before-page",
        "limit-without-cursor",
        "post-filter-result-count",
        "index-uses-table-count",
        "cursor-subtraction-without-limit",
    ):
        assert cases[case_name]["failed_checks"] == ["hidden:query-scanned-count"]
    assert cases["forbidden-test-edit"]["failed_checks"] == [
        "hidden:query-scanned-count",
        "policy:scope",
        "policy:test_tampering",
    ]


def test_babel_candidate_has_pinned_real_repository_provenance() -> None:
    package = load_task_package(BABEL_TASK)

    assert package.public.task_id == "babel-strict-grouped-decimal-trailing-zeroes"
    assert package.public.split == "dev-validation"
    assert package.public.repository.url == "https://github.com/python-babel/babel.git"
    assert (
        package.public.repository.base_commit
        == "aca7663728e08e9d60b192b11fa6626a60974929"
    )
    assert package.public.repository.url in ALLOWED_REMOTE_REPOSITORIES
    assert package.public.constraints.allowed_paths == ["babel/numbers.py"]
    assert package.public.constraints.max_changed_files == 1
    assert package.public.constraints.max_diff_lines == 60
    assert package.environment is not None
    assert package.environment.image_digest == (
        "sha256:864e84fc4bdf09252f7fda4f85665cc05155a7b1d75847d61c67325abce7ef5a"
    )
    assert package.environment.evaluator_image.endswith(f"@{package.environment.image_digest}")
    assert package.public.visible_checks[0].environment["PYTHONPATH"] == "/workspace"


def test_babel_public_contract_excludes_evaluator_only_material() -> None:
    package = load_task_package(BABEL_TASK)
    public_text = (BABEL_TASK / "public.yaml").read_text(encoding="utf-8")

    assert "test_strict_grouped_decimal.py" not in public_text
    assert "_remove_trailing_zeros_after_decimal" not in public_text
    assert "reference.patch" not in public_text
    assert package.private.reference_patch.sha256 not in public_text
    assert ".patchloop-hidden" not in "\n".join(
        argument for check in package.public.visible_checks for argument in check.command
    )


def test_babel_candidate_is_traceable_to_swe_rebench_v2_row() -> None:
    with Path("data/benchmark-candidate-ledger.csv").open(encoding="utf-8", newline="") as handle:
        rows = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    candidate = rows["python-babel__babel-1042"]
    assert candidate["benchmark_revision"] == "475dd5e8703bb5fb22dd3c60b5d038b019eba1e0"
    assert candidate["benchmark_split"] == "train"
    assert candidate["base_commit"] == "aca7663728e08e9d60b192b11fa6626a60974929"
    assert candidate["pr_url"] == "https://github.com/python-babel/babel/pull/1042"
    assert candidate["changed_files"] == "2"
    assert candidate["f2p"] == "1"
    assert candidate["p2p"] == "131"
    assert candidate["proposed_lane"] == "development-validation"
    assert candidate["status"] == "admitted"


def test_babel_oracle_and_bad_patch_inventory_are_explicit() -> None:
    hidden_text = (BABEL_TASK / "hidden/test_strict_grouped_decimal.py").read_text(
        encoding="utf-8"
    )
    bad_names = sorted(path.name for path in (BABEL_TASK / "bad").glob("*.patch"))

    assert hidden_text.count("\ndef test_") == 16
    assert bad_names == [
        "dot-decimal-only.patch",
        "forbidden-test-edit.patch",
        "noop.patch",
        "normalize-returned-decimal.patch",
        "positive-only.patch",
        "remove-all-fraction-zeroes.patch",
        "single-zero-trim.patch",
        "suffix-zero-bypass.patch",
        "western-group-only.patch",
    ]


def test_babel_admission_evidence_binds_locale_scale_and_strictness() -> None:
    package = load_task_package(BABEL_TASK)
    entry = require_dataset_role(
        task_id=package.public.task_id,
        task_version=package.public.task_version,
        public_spec_hash=package.public_spec_hash,
        allowed_roles={DatasetRole.DEVELOPMENT_VALIDATION},
    )
    assert entry.role == DatasetRole.DEVELOPMENT_VALIDATION
    assert entry.admission_evidence is not None
    assert entry.admission_evidence.reference_pass_runs == 3
    assert entry.admission_evidence.rejected_bad_patches == 8

    evidence = json.loads(
        Path(
            "reports/docker-gate/research-babel-strict-grouped-decimal-trailing-zeroes.json"
        ).read_text(encoding="utf-8")
    )
    assert evidence["harness_git_commit"] == "313af714025fb67852f696ae732e33a1ffd62815"
    assert evidence["reference_policy"]["kind"] == "normalized-upstream-production-only"
    assert evidence["runtime_data_policy"]["kind"] == "pinned-image-generated-cldr-overlay"
    assert evidence["reference_pass_count"] == 3
    assert evidence["base_noop_rejection_count"] == 1
    assert evidence["known_bad_patch_rejection_count"] == 8
    assert evidence["semantic_bad_patch_rejection_count"] == 7
    assert evidence["upstream_regression_test_count"] == 132
    assert evidence["benchmark_f2p_declared_count"] == 1
    assert evidence["benchmark_p2p_declared_count"] == 131
    assert evidence["independent_hidden_test_count"] == 16
    for check_id in (
        "submitted_source_binding",
        "dot_comma_arabic_decimal_symbols",
        "western_indian_narrow_space_grouping",
        "negative_and_internal_zero_semantics",
        "one_to_three_trailing_zero_runs",
        "decimal_scale_preservation",
        "malformed_and_wrong_locale_rejection",
        "non_strict_compatibility",
        "generated_cldr_data_provenance",
        "utf8_public_api_verifier",
    ):
        assert evidence["admission_checks"][check_id] == "pass"

    cases = {case["name"]: case for case in evidence["cases"]}
    assert len(cases) == 12
    assert len({case["run_id"] for case in cases.values()}) == 12
    assert all(case["official"] for case in cases.values())
    assert all(cases[f"reference-{index}"]["observed_success"] for index in range(1, 4))
    assert {
        cases[f"reference-{index}"]["patch_sha256"] for index in range(1, 4)
    } == {package.private.reference_patch.sha256}
    assert cases["base-noop"]["failed_checks"] == [
        "hidden:strict-grouped-decimal-trailing-zeroes"
    ]
    for case_name in (
        "dot-decimal-only",
        "positive-only",
        "single-zero-trim",
        "normalize-returned-decimal",
        "remove-all-fraction-zeroes",
        "suffix-zero-bypass",
        "western-group-only",
    ):
        assert cases[case_name]["failed_checks"] == [
            "hidden:strict-grouped-decimal-trailing-zeroes"
        ]
    assert cases["forbidden-test-edit"]["failed_checks"] == [
        "hidden:strict-grouped-decimal-trailing-zeroes",
        "policy:scope",
        "policy:test_tampering",
    ]


def test_sqlglot_candidate_has_pinned_real_repository_provenance() -> None:
    package = load_task_package(SQLGLOT_TASK)

    assert package.public.task_id == "sqlglot-duckdb-ignore-nulls-modifier-order"
    assert package.public.split == "cross-repo-heldout"
    assert package.public.repository.url == "https://github.com/tobymao/sqlglot.git"
    assert (
        package.public.repository.base_commit
        == "0e8d0824c40ac46c5e7275180cf2eaae6810f805"
    )
    assert package.public.repository.url in ALLOWED_REMOTE_REPOSITORIES
    assert package.public.constraints.allowed_paths == [
        "sqlglot/dialects/duckdb.py",
        "sqlglot/generator.py",
        "sqlglot/parser.py",
    ]
    assert package.public.constraints.max_changed_files == 3
    assert package.public.constraints.max_diff_lines == 80
    assert package.environment is not None
    assert package.environment.image_digest == (
        "sha256:43c43d77e3bed15361140767e3f3fd84811e0bad5b58f6afcba83f79b8e58303"
    )
    assert package.environment.evaluator_image.endswith(f"@{package.environment.image_digest}")
    assert package.public.visible_checks[0].environment["PYTHONPATH"] == "/workspace"


def test_sqlglot_public_contract_excludes_evaluator_only_material() -> None:
    package = load_task_package(SQLGLOT_TASK)
    public_text = (SQLGLOT_TASK / "public.yaml").read_text(encoding="utf-8")

    assert "test_duckdb_ignore_nulls_modifier_order.py" not in public_text
    assert "_parse_lambda" not in public_text
    assert "_embed_ignore_nulls" not in public_text
    assert "reference.patch" not in public_text
    assert package.private.reference_patch.sha256 not in public_text
    assert ".patchloop-hidden" not in "\n".join(
        argument for check in package.public.visible_checks for argument in check.command
    )


def test_sqlglot_candidate_is_traceable_to_swe_rebench_row() -> None:
    with Path("data/benchmark-candidate-ledger.csv").open(encoding="utf-8", newline="") as handle:
        rows = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    candidate = rows["tobymao__sqlglot-7187"]
    assert candidate["benchmark_revision"] == "ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b"
    assert candidate["benchmark_split"] == "2026_03"
    assert candidate["base_commit"] == "0e8d0824c40ac46c5e7275180cf2eaae6810f805"
    assert candidate["pr_url"] == "https://github.com/tobymao/sqlglot/pull/7187"
    assert candidate["changed_files"] == "4"
    assert candidate["f2p"] == "1"
    assert candidate["p2p"] == "38"
    assert candidate["proposed_lane"] == "core-cross-repo"
    assert candidate["status"] == "admitted"


def test_sqlglot_staging_oracle_and_bad_patch_inventory_are_explicit() -> None:
    hidden_text = (
        SQLGLOT_TASK / "hidden/test_duckdb_ignore_nulls_modifier_order.py"
    ).read_text(encoding="utf-8")
    bad_names = sorted(path.name for path in (SQLGLOT_TASK / "bad").glob("*.patch"))

    assert hidden_text.count("\ndef test_") == 21
    assert bad_names == [
        "forbidden-test-edit.patch",
        "generator-only.patch",
        "global-order-change.patch",
        "ignore-only.patch",
        "missing-duckdb-policy.patch",
        "missing-having-max-policy.patch",
        "missing-shared-generator-policy.patch",
        "noop.patch",
        "parser-only.patch",
    ]


def test_sqlglot_admission_evidence_binds_modifier_order_boundaries() -> None:
    package = load_task_package(SQLGLOT_TASK)
    entry = require_dataset_role(
        task_id=package.public.task_id,
        task_version=package.public.task_version,
        public_spec_hash=package.public_spec_hash,
        allowed_roles={DatasetRole.CORE_CROSS_REPO},
    )
    assert entry.role == DatasetRole.CORE_CROSS_REPO
    assert entry.admission_evidence is not None
    assert entry.admission_evidence.reference_pass_runs == 3
    assert entry.admission_evidence.rejected_bad_patches == 8

    evidence = json.loads(
        Path(
            "reports/docker-gate/research-sqlglot-duckdb-ignore-nulls-modifier-order.json"
        ).read_text(encoding="utf-8")
    )
    assert evidence["harness_git_commit"] == "89f47025e3a8b92fc04dce99893eefa801755b33"
    assert evidence["reference_policy"]["kind"] == "exact-upstream-production-only"
    assert evidence["reference_pass_count"] == 3
    assert evidence["base_noop_rejection_count"] == 1
    assert evidence["known_bad_patch_rejection_count"] == 8
    assert evidence["semantic_bad_patch_rejection_count"] == 7
    assert evidence["upstream_regression_test_count"] == 39
    assert evidence["benchmark_f2p_declared_count"] == 1
    assert evidence["benchmark_p2p_declared_count"] == 38
    assert evidence["independent_hidden_test_count"] == 21
    for check_id in (
        "submitted_source_binding",
        "symmetric_ignore_respect_function_matrix",
        "prefix_form_duckdb_canonicalization",
        "argument_window_ast_separation",
        "offset_default_named_window_and_frame_stability",
        "bigquery_having_order_limit_negative_transfer_guard",
        "exact_reference_lineage",
        "contamination_and_localization_disclosure",
        "public_private_separation",
    ):
        assert evidence["admission_checks"][check_id] == "pass"

    cases = {case["name"]: case for case in evidence["cases"]}
    assert len(cases) == 12
    assert len({case["run_id"] for case in cases.values()}) == 12
    assert all(case["official"] for case in cases.values())
    assert all(cases[f"reference-{index}"]["observed_success"] for index in range(1, 4))
    assert {
        cases[f"reference-{index}"]["patch_sha256"] for index in range(1, 4)
    } == {package.private.reference_patch.sha256}
    assert cases["base-noop"]["failed_checks"] == [
        "hidden:duckdb-ignore-nulls-modifier-order"
    ]
    for case_name in (
        "parser-only",
        "generator-only",
        "global-order-change",
        "ignore-only",
        "missing-duckdb-policy",
        "missing-shared-generator-policy",
        "missing-having-max-policy",
    ):
        assert cases[case_name]["failed_checks"] == [
            "hidden:duckdb-ignore-nulls-modifier-order"
        ]
    assert cases["forbidden-test-edit"]["failed_checks"] == [
        "hidden:duckdb-ignore-nulls-modifier-order",
        "policy:scope",
        "policy:test_tampering",
    ]


def test_pdm_target_task_has_pinned_real_repository_provenance() -> None:
    package = load_task_package(PDM_TARGET_TASK)

    assert package.public.task_id == "pdm-target-project-options-loading"
    assert package.public.split == "same-repo-heldout"
    assert package.public.repository.url == "https://github.com/pdm-project/pdm.git"
    assert (
        package.public.repository.base_commit
        == "e96d535bb1bd64ac21575cf3490d64f737c6a668"
    )
    assert package.public.repository.url in ALLOWED_REMOTE_REPOSITORIES
    assert package.public.constraints.allowed_paths == ["src/pdm/core.py"]
    assert package.public.constraints.max_changed_files == 1
    assert package.public.constraints.max_diff_lines == 60
    assert package.environment is not None
    assert package.environment.image_digest == (
        "sha256:7a012a5bfd460d638b74d3de84426cd1fa2141aec3914c4f9171071491f5ac93"
    )
    assert package.environment.evaluator_image.endswith(f"@{package.environment.image_digest}")
    assert package.public.visible_checks[0].environment["PYTHONPATH"] == "/workspace/src"


def test_pdm_target_public_contract_excludes_evaluator_only_material() -> None:
    package = load_task_package(PDM_TARGET_TASK)
    public_text = (PDM_TARGET_TASK / "public.yaml").read_text(encoding="utf-8")

    assert "test_target_project_options.py" not in public_text
    assert "_inject_cli_args" not in public_text
    assert "ensure_project" not in public_text
    assert "reference.patch" not in public_text
    assert package.private.reference_patch.sha256 not in public_text
    assert ".patchloop-hidden" not in "\n".join(
        argument for check in package.public.visible_checks for argument in check.command
    )


def test_pdm_target_task_is_traceable_to_swe_rebench_row() -> None:
    with Path("data/benchmark-candidate-ledger.csv").open(encoding="utf-8", newline="") as handle:
        rows = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    candidate = rows["pdm-project__pdm-3759"]
    assert candidate["benchmark_revision"] == "ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b"
    assert candidate["benchmark_split"] == "2026_03"
    assert candidate["base_commit"] == "e96d535bb1bd64ac21575cf3490d64f737c6a668"
    assert candidate["pr_url"] == "https://github.com/pdm-project/pdm/pull/3759"
    assert candidate["changed_files"] == "2"
    assert candidate["f2p"] == "1"
    assert candidate["p2p"] == "63"
    assert candidate["proposed_lane"] == "core-same-repo"
    assert candidate["status"] == "admitted"
    assert candidate["environment_image"].endswith(
        "@sha256:7a012a5bfd460d638b74d3de84426cd1fa2141aec3914c4f9171071491f5ac93"
    )


def test_pdm_target_oracle_and_bad_patch_inventory_are_explicit() -> None:
    hidden_text = (PDM_TARGET_TASK / "hidden/test_target_project_options.py").read_text(
        encoding="utf-8"
    )
    bad_names = sorted(path.name for path in (PDM_TARGET_TASK / "bad").glob("*.patch"))

    assert hidden_text.count("\n    def test_") == 11
    assert bad_names == [
        "caller-fallback-when-target-missing.patch",
        "caller-options-after-selection.patch",
        "environment-only-selection.patch",
        "forbidden-test-edit.patch",
        "ignore-explicit-object.patch",
        "inject-without-reparse.patch",
        "install-command-only.patch",
        "noop.patch",
        "project-selection-no-injection.patch",
        "short-separated-only.patch",
        "upstream-pr-extractor.patch",
    ]


def test_pdm_target_admission_evidence_rejects_original_benchmark_fix() -> None:
    package = load_task_package(PDM_TARGET_TASK)
    entry = require_dataset_role(
        task_id=package.public.task_id,
        task_version=package.public.task_version,
        public_spec_hash=package.public_spec_hash,
        allowed_roles={DatasetRole.CORE_SAME_REPO},
    )
    assert entry.role == DatasetRole.CORE_SAME_REPO
    assert entry.admission_evidence is not None
    assert entry.admission_evidence.reference_pass_runs == 3
    assert entry.admission_evidence.rejected_bad_patches == 10
    development_package = load_task_package(PDM_TASK)
    development_entry = require_dataset_role(
        task_id=development_package.public.task_id,
        task_version=development_package.public.task_version,
        public_spec_hash=development_package.public_spec_hash,
        allowed_roles={DatasetRole.MEMORY_DEVELOPMENT},
    )
    assert entry.solution_lineage_id != development_entry.solution_lineage_id

    evidence = json.loads(
        Path(
            "reports/docker-gate/research-pdm-target-project-options-loading.json"
        ).read_text(encoding="utf-8")
    )
    assert evidence["harness_git_commit"] == "ad25a8a95806d7e15597b03325af9de9108940b2"
    assert (
        evidence["reference_policy"]["kind"]
        == "hardened-maintainer-followup-production-only"
    )
    assert evidence["reference_policy"]["rejected_benchmark_production_patch"] is True
    assert evidence["reference_pass_count"] == 3
    assert evidence["base_noop_rejection_count"] == 1
    assert evidence["known_bad_patch_rejection_count"] == 10
    assert evidence["semantic_bad_patch_rejection_count"] == 9
    assert evidence["upstream_regression_test_count"] == 63
    assert evidence["benchmark_f2p_declared_count"] == 1
    assert evidence["benchmark_p2p_declared_count"] == 63
    assert evidence["network_dependent_p2p_deselection_count"] == 1
    assert evidence["independent_hidden_test_count"] == 11
    for check_id in (
        "submitted_source_binding",
        "real_cli_short_long_and_attached_forms",
        "repeated_project_option_last_wins",
        "environment_project_selection",
        "explicit_project_object_precedence",
        "global_project_isolation",
        "cross_command_config_injection",
        "target_without_option_has_no_caller_fallback",
        "hardened_followup_lineage",
        "upstream_benchmark_production_patch_rejected",
        "network_dependent_p2p_deselection_disclosed",
        "same_repository_solution_lineage_is_distinct",
        "public_private_separation",
    ):
        assert evidence["admission_checks"][check_id] == "pass"

    cases = {case["name"]: case for case in evidence["cases"]}
    assert len(cases) == 14
    assert len({case["run_id"] for case in cases.values()}) == 14
    assert all(case["official"] for case in cases.values())
    assert all(cases[f"reference-{index}"]["observed_success"] for index in range(1, 4))
    assert {
        cases[f"reference-{index}"]["patch_sha256"] for index in range(1, 4)
    } == {package.private.reference_patch.sha256}
    assert cases["base-noop"]["failed_checks"] == ["hidden:target-project-options"]
    assert cases["upstream-pr-extractor"]["patch_sha256"] == (
        evidence["source"]["benchmark_production_patch_sha256"]
    )
    assert cases["upstream-pr-extractor"]["failed_checks"] == [
        "hidden:target-project-options"
    ]
    assert cases["caller-options-after-selection"]["failed_checks"] == [
        "regression:upstream-project-regression",
        "hidden:target-project-options",
    ]
    assert cases["ignore-explicit-object"]["failed_checks"] == [
        "regression:upstream-project-regression",
        "hidden:target-project-options",
    ]
    assert cases["install-command-only"]["failed_checks"] == [
        "regression:upstream-project-regression",
        "hidden:target-project-options",
    ]
    assert cases["project-selection-no-injection"]["failed_checks"] == [
        "regression:upstream-project-regression",
        "hidden:target-project-options",
    ]
    for case_name in (
        "caller-fallback-when-target-missing",
        "environment-only-selection",
        "inject-without-reparse",
        "short-separated-only",
    ):
        assert cases[case_name]["failed_checks"] == ["hidden:target-project-options"]
    assert cases["forbidden-test-edit"]["failed_checks"] == [
        "hidden:target-project-options",
        "policy:scope",
        "policy:test_tampering",
    ]


def test_anyio_process_task_has_pinned_real_repository_provenance() -> None:
    package = load_task_package(ANYIO_PROCESS_TASK)

    assert package.public.task_id == "anyio-extensionless-entrypoint-worker-main"
    assert package.public.split == "same-repo-heldout"
    assert package.public.repository.url == "https://github.com/agronholm/anyio.git"
    assert package.public.repository.base_commit == "01b8d02381ba95ba11241c1ec361e908fe05b8be"
    assert package.public.repository.url in ALLOWED_REMOTE_REPOSITORIES
    assert package.public.constraints.allowed_paths == ["src/anyio/to_process.py"]
    assert package.public.constraints.max_changed_files == 1
    assert package.public.constraints.max_diff_lines == 40
    assert package.environment is not None
    assert package.environment.image_digest == (
        "sha256:d7997027864d2bfb32d649e7e544381f5d1b161df8f1682c719d222d66489dc0"
    )
    assert package.environment.evaluator_image.endswith(f"@{package.environment.image_digest}")
    assert package.public.visible_checks[0].environment["PYTHONPATH"] == "/workspace/src"


def test_anyio_process_public_contract_excludes_evaluator_only_material() -> None:
    package = load_task_package(ANYIO_PROCESS_TASK)
    public_text = (ANYIO_PROCESS_TASK / "public.yaml").read_text(encoding="utf-8")

    assert "test_extensionless_entrypoint_worker_main.py" not in public_text
    assert "runpy.run_path" not in public_text
    assert "ModuleType" not in public_text
    assert "reference.patch" not in public_text
    assert package.private.reference_patch.sha256 not in public_text
    assert ".patchloop-hidden" not in "\n".join(
        argument for check in package.public.visible_checks for argument in check.command
    )


def test_anyio_process_task_is_traceable_to_swe_rebench_row() -> None:
    with Path("data/benchmark-candidate-ledger.csv").open(encoding="utf-8", newline="") as handle:
        rows = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    candidate = rows["agronholm__anyio-1134"]
    assert candidate["benchmark_revision"] == "ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b"
    assert candidate["benchmark_split"] == "2026_03"
    assert candidate["base_commit"] == "01b8d02381ba95ba11241c1ec361e908fe05b8be"
    assert candidate["pr_url"] == "https://github.com/agronholm/anyio/pull/1134"
    assert candidate["changed_files"] == "3"
    assert candidate["f2p"] == "4"
    assert candidate["p2p"] == "36"
    assert candidate["proposed_lane"] == "core-same-repo"
    assert candidate["status"] == "admitted"
    assert candidate["environment_image"].endswith(
        "@sha256:d7997027864d2bfb32d649e7e544381f5d1b161df8f1682c719d222d66489dc0"
    )


def test_anyio_process_oracle_and_bad_patch_inventory_are_explicit() -> None:
    hidden_text = (
        ANYIO_PROCESS_TASK / "hidden/test_extensionless_entrypoint_worker_main.py"
    ).read_text(encoding="utf-8")
    bad_names = sorted(path.name for path in (ANYIO_PROCESS_TASK / "bad").glob("*.patch"))

    assert hidden_text.count("\n    def test_") == 11
    assert bad_names == [
        "double-entrypoint-execution.patch",
        "drop-dunder-metadata.patch",
        "empty-main-module.patch",
        "extensionless-fallback-only.patch",
        "forbidden-test-edit.patch",
        "main-alias-only.patch",
        "module-dict-alias.patch",
        "noop.patch",
        "runpy-without-content.patch",
        "unnamed-run-path.patch",
        "wrong-main-run-name.patch",
    ]


def test_anyio_process_admission_evidence_is_exact_and_distinct() -> None:
    package = load_task_package(ANYIO_PROCESS_TASK)
    entry = require_dataset_role(
        task_id=package.public.task_id,
        task_version=package.public.task_version,
        public_spec_hash=package.public_spec_hash,
        allowed_roles={DatasetRole.CORE_SAME_REPO},
    )
    assert entry.role == DatasetRole.CORE_SAME_REPO
    assert entry.admission_evidence is not None
    assert entry.admission_evidence.reference_pass_runs == 3
    assert entry.admission_evidence.rejected_bad_patches == 10
    development_package = load_task_package(ANYIO_TASK)
    development_entry = require_dataset_role(
        task_id=development_package.public.task_id,
        task_version=development_package.public.task_version,
        public_spec_hash=development_package.public_spec_hash,
        allowed_roles={DatasetRole.MEMORY_DEVELOPMENT},
    )
    assert entry.solution_lineage_id != development_entry.solution_lineage_id

    evidence = json.loads(
        Path(
            "reports/docker-gate/research-anyio-extensionless-entrypoint-worker-main.json"
        ).read_text(encoding="utf-8")
    )
    assert evidence["harness_git_commit"] == "9dfc60dd4b469f17732bb3bf4eeca0e61e10bdac"
    assert evidence["reference_policy"]["kind"] == "exact-upstream-production-only"
    assert evidence["reference_policy"]["rejected_benchmark_production_patch"] is False
    assert evidence["source"]["benchmark_production_patch_sha256"] == (
        package.private.reference_patch.sha256
    )
    assert evidence["reference_pass_count"] == 3
    assert evidence["base_noop_rejection_count"] == 1
    assert evidence["known_bad_patch_rejection_count"] == 10
    assert evidence["semantic_bad_patch_rejection_count"] == 9
    assert evidence["upstream_regression_test_count"] == 36
    assert evidence["benchmark_f2p_declared_count"] == 4
    assert evidence["benchmark_p2p_declared_count"] == 36
    assert evidence["independent_hidden_test_count"] == 11
    for check_id in (
        "submitted_source_binding",
        "extensionless_entrypoint",
        "unknown_suffix_entrypoint",
        "asyncio_and_trio_backends",
        "path_with_spaces",
        "main_module_alias_identity",
        "module_name_and_file_metadata",
        "entrypoint_exactly_once",
        "worker_reuse_without_reload",
        "ordinary_python_script_compatibility",
        "initialization_error_propagation",
        "exact_upstream_production_lineage",
        "same_repository_solution_lineage_is_distinct",
        "public_private_separation",
        "external_image_default_user_disclosed",
    ):
        assert evidence["admission_checks"][check_id] == "pass"

    cases = {case["name"]: case for case in evidence["cases"]}
    assert len(cases) == 14
    assert len({case["run_id"] for case in cases.values()}) == 14
    assert all(case["official"] for case in cases.values())
    assert all(cases[f"reference-{index}"]["observed_success"] for index in range(1, 4))
    assert {cases[f"reference-{index}"]["patch_sha256"] for index in range(1, 4)} == {
        package.private.reference_patch.sha256
    }
    for case_name in (
        "base-noop",
        "main-alias-only",
        "drop-dunder-metadata",
        "double-entrypoint-execution",
        "empty-main-module",
        "module-dict-alias",
        "runpy-without-content",
        "extensionless-fallback-only",
        "unnamed-run-path",
    ):
        assert cases[case_name]["failed_checks"] == ["hidden:extensionless-entrypoint-worker-main"]
    assert cases["wrong-main-run-name"]["failed_checks"] == [
        "regression:upstream-process-regression",
        "hidden:extensionless-entrypoint-worker-main",
    ]
    assert cases["forbidden-test-edit"]["failed_checks"] == [
        "hidden:extensionless-entrypoint-worker-main",
        "policy:scope",
        "policy:test_tampering",
    ]


def test_param_candidate_has_pinned_real_repository_provenance() -> None:
    package = load_task_package(PARAM_TASK)

    assert package.public.task_id == "param-shared-rx-fanout-cache"
    assert package.public.split == "cross-repo-heldout"
    assert package.public.repository.url == "https://github.com/holoviz/param.git"
    assert (
        package.public.repository.base_commit
        == "833c8f05f7a47fa1476620307ef7fd447c45e6fb"
    )
    assert package.public.repository.url in ALLOWED_REMOTE_REPOSITORIES
    assert package.public.constraints.allowed_paths == ["param/reactive.py"]
    assert package.public.constraints.max_changed_files == 1
    assert package.public.constraints.max_diff_lines == 70
    assert package.environment is not None
    assert package.environment.image_digest == (
        "sha256:c10bc0ad51b00c59ed8fa4366ee722c38e83dfaa620a7cc229f78489ccbaf010"
    )
    assert package.environment.evaluator_image.endswith(f"@{package.environment.image_digest}")
    assert package.public.visible_checks[0].environment["PYTHONPATH"] == "/workspace"


def test_param_public_contract_excludes_evaluator_only_material() -> None:
    package = load_task_package(PARAM_TASK)
    public_text = (PARAM_TASK / "public.yaml").read_text(encoding="utf-8")

    assert "test_shared_rx_fanout_cache.py" not in public_text
    assert "self._shared" not in public_text
    assert "_is_async" not in public_text
    assert "reference.patch" not in public_text
    assert package.private.reference_patch.sha256 not in public_text
    assert ".patchloop-hidden" not in "\n".join(
        argument for check in package.public.visible_checks for argument in check.command
    )


def test_param_candidate_is_traceable_to_admitted_swe_rebench_row() -> None:
    with Path("data/benchmark-candidate-ledger.csv").open(encoding="utf-8", newline="") as handle:
        rows = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    candidate = rows["holoviz__param-1117"]
    assert candidate["benchmark_revision"] == "ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b"
    assert candidate["benchmark_split"] == "2026_03"
    assert candidate["base_commit"] == "833c8f05f7a47fa1476620307ef7fd447c45e6fb"
    assert candidate["pr_url"] == "https://github.com/holoviz/param/pull/1117"
    assert candidate["license_spdx"] == "BSD-3-Clause"
    assert candidate["changed_files"] == "2"
    assert candidate["f2p"] == "2"
    assert candidate["p2p"] == "94"
    assert candidate["proposed_lane"] == "core-cross-repo"
    assert candidate["status"] == "admitted"
    assert candidate["environment_image"].endswith(
        "@sha256:c10bc0ad51b00c59ed8fa4366ee722c38e83dfaa620a7cc229f78489ccbaf010"
    )


def test_param_reference_patch_matches_frozen_benchmark_production_patch() -> None:
    package = load_task_package(PARAM_TASK)
    reference_patch = PARAM_TASK / package.private.reference_patch.path

    assert package.private.reference_patch.sha256 == (
        "sha256:531f7143c3eb04494e3eae258685018c70654f4c3c403aefe10f8a5a2f700d23"
    )
    assert sha256_bytes(reference_patch.read_bytes()) == package.private.reference_patch.sha256


def test_param_admission_evidence_binds_shared_fanout_boundaries() -> None:
    package = load_task_package(PARAM_TASK)
    entry = require_dataset_role(
        task_id=package.public.task_id,
        task_version=package.public.task_version,
        public_spec_hash=package.public_spec_hash,
        allowed_roles={DatasetRole.CORE_CROSS_REPO},
    )
    assert entry.role == DatasetRole.CORE_CROSS_REPO
    assert entry.failure_pattern_id == "shared-reactive-source-recomputed-per-branch"
    assert entry.solution_lineage_id == "holoviz-param-pr-1117"
    assert entry.admission_evidence is not None
    assert entry.admission_evidence.reference_pass_runs == 3
    assert entry.admission_evidence.rejected_bad_patches == 9

    evidence = json.loads(
        Path(
            "reports/docker-gate/research-param-shared-rx-fanout-cache.json"
        ).read_text(encoding="utf-8")
    )
    assert evidence["reference_policy"]["kind"] == "exact-upstream-production-only"
    assert evidence["source"]["benchmark_production_patch_sha256"] == (
        package.private.reference_patch.sha256
    )
    assert evidence["reference_pass_count"] == 3
    assert evidence["base_noop_rejection_count"] == 1
    assert evidence["known_bad_patch_rejection_count"] == 9
    assert evidence["semantic_bad_patch_rejection_count"] == 8
    assert evidence["independent_hidden_test_count"] == 10
    assert evidence["benchmark_f2p_declared_count"] == 2
    assert evidence["benchmark_p2p_declared_count"] == 94
    assert evidence["upstream_regression_test_count"] == 94

    cases = {case["name"]: case for case in evidence["cases"]}
    assert len(cases) == 13
    assert len({case["run_id"] for case in cases.values()}) == 13
    assert all(case["official"] for case in cases.values())
    assert all(cases[f"reference-{index}"]["observed_success"] for index in range(1, 4))
    assert {
        cases[f"reference-{index}"]["patch_sha256"] for index in range(1, 4)
    } == {package.private.reference_patch.sha256}
    assert cases["base-noop"]["failed_checks"] == [
        "hidden:shared-rx-fanout-cache"
    ]


def test_hf_task_has_pinned_real_repository_provenance_and_budget() -> None:
    package = load_task_package(HF_TASK)

    assert package.public.task_id == "hf-hub-custom-tqdm-class-contract"
    assert package.public.split == "same-repo-heldout"
    assert package.public.repository.url == (
        "https://github.com/huggingface/huggingface_hub.git"
    )
    assert package.public.repository.base_commit == (
        "6983a4d3d2bdcbd09c6ea08acae64cdf83ccb2e4"
    )
    assert package.public.repository.url in ALLOWED_REMOTE_REPOSITORIES
    assert package.public.constraints.allowed_paths == [
        "src/huggingface_hub/_snapshot_download.py",
        "src/huggingface_hub/utils/tqdm.py",
    ]
    assert package.public.constraints.max_changed_files == 2
    assert package.public.constraints.max_diff_lines == 60
    assert package.public.constraints.dependency_changes_allowed is False
    assert package.public.constraints.public_api_changes_allowed is False
    assert package.environment is not None
    assert package.environment.image_digest == (
        "sha256:cbfae263dff792cc7c763057905869c548bf37733352ff999b3d7d4278c87677"
    )
    assert package.environment.evaluator_image == (
        "swerebench/sweb.eval.x86_64.huggingface_1776_huggingface_hub-4056"
        f"@{package.environment.image_digest}"
    )
    visible_check = package.public.visible_checks[0]
    assert visible_check.id == "upstream-tqdm-regression"
    assert visible_check.timeout_seconds == 60
    assert visible_check.environment["PYTHONPATH"] == "/workspace/src"
    assert package.private.hidden_checks[0].timeout_seconds == 60


def test_hf_task_public_contract_excludes_evaluator_only_material() -> None:
    package = load_task_package(HF_TASK)
    public_text = (HF_TASK / "public.yaml").read_text(encoding="utf-8")

    assert "test_custom_tqdm_class_contract.py" not in public_text
    assert "StrictProgress" not in public_text
    assert "KeywordRecordingProgress" not in public_text
    assert "_create_progress_bar" not in public_text
    assert "reference.patch" not in public_text
    assert package.private.reference_patch.sha256 not in public_text
    assert ".patchloop-hidden" not in "\n".join(
        argument for check in package.public.visible_checks for argument in check.command
    )


def test_hf_task_is_traceable_to_admitted_swe_rebench_row() -> None:
    with Path("data/benchmark-candidate-ledger.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    candidate = rows["huggingface__huggingface_hub-4056"]
    assert candidate["benchmark_family"] == "SWE-rebench-leaderboard"
    assert candidate["benchmark_revision"] == (
        "ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b"
    )
    assert candidate["benchmark_split"] == "2026_03"
    assert candidate["base_commit"] == "6983a4d3d2bdcbd09c6ea08acae64cdf83ccb2e4"
    assert candidate["pr_url"] == (
        "https://github.com/huggingface/huggingface_hub/pull/4056"
    )
    assert candidate["license_spdx"] == "Apache-2.0"
    assert candidate["changed_files"] == "2"
    assert candidate["f2p"] == "2"
    assert candidate["p2p"] == "19"
    assert candidate["proposed_lane"] == "core-same-repo"
    assert candidate["status"] == "admitted"
    assert candidate["environment_image"].endswith(
        "@sha256:cbfae263dff792cc7c763057905869c548bf37733352ff999b3d7d4278c87677"
    )


def test_hf_task_reference_bytes_match_frozen_production_patch() -> None:
    package = load_task_package(HF_TASK)
    reference_patch = HF_TASK / package.private.reference_patch.path
    reference_bytes = reference_patch.read_bytes()

    assert package.private.reference_patch.sha256 == (
        "sha256:4ed0bca7b7370147472f34b56aa7d67aa2938cf9dd03bfa45a1786df495b04bd"
    )
    assert sha256_bytes(reference_bytes) == package.private.reference_patch.sha256
    assert len(reference_bytes) == 3806
    assert reference_bytes.count(b"diff --git ") == 2
    assert b"diff --git a/tests/" not in reference_bytes


def test_hf_task_oracle_and_bad_patch_inventory_are_explicit() -> None:
    hidden_text = (
        HF_TASK / "hidden/test_custom_tqdm_class_contract.py"
    ).read_text(encoding="utf-8")
    bad_names = sorted(path.name for path in (HF_TASK / "bad").glob("*.patch"))

    assert hidden_text.count("\ndef test_") == 13
    assert bad_names == [
        "combined-foreign-only.patch",
        "context-only.patch",
        "exact-hf-class-only.patch",
        "forbidden-test-edit.patch",
        "force-disable-false.patch",
        "hf-policy-dropped.patch",
        "noop.patch",
        "snapshot-only.patch",
        "strip-name-only.patch",
        "unguarded-issubclass.patch",
        "upstream-subclass-treated-as-hf.patch",
    ]


def test_hf_task_prepares_a_distinct_same_repository_solution_lineage() -> None:
    package = load_task_package(HF_TASK)
    development_package = load_task_package(HF_HUB_TASK)
    audit_text = (HF_TASK / "audit.md").read_text(encoding="utf-8")

    assert package.public.repository.url == development_package.public.repository.url
    assert set(package.public.constraints.allowed_paths).isdisjoint(
        development_package.public.constraints.allowed_paths
    )
    assert "hf-hub-xet-endpoint-propagation" in audit_text
    assert (
        "not a module set, trigger, failure mechanism, or solution lineage."
        in audit_text
    )

    with Path("data/benchmark-candidate-ledger.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = {row["candidate_id"]: row for row in csv.DictReader(handle)}
    assert (
        rows["huggingface__huggingface_hub-4056"]["pr_url"]
        != rows["huggingface__huggingface_hub-3180"]["pr_url"]
    )


def test_hf_task_admission_evidence_binds_policy_ownership_boundaries() -> None:
    package = load_task_package(HF_TASK)
    entry = require_dataset_role(
        task_id=package.public.task_id,
        task_version=package.public.task_version,
        public_spec_hash=package.public_spec_hash,
        allowed_roles={DatasetRole.CORE_SAME_REPO},
    )
    assert entry.role == DatasetRole.CORE_SAME_REPO
    assert entry.failure_pattern_id == "custom-progress-class-policy-overridden"
    assert entry.solution_lineage_id == "huggingface-hub-tqdm-class-pr-4056"
    assert entry.admission_evidence is not None
    assert entry.admission_evidence.reference_pass_runs == 3
    assert entry.admission_evidence.rejected_bad_patches == 10

    development_package = load_task_package(HF_HUB_TASK)
    development_entry = require_dataset_role(
        task_id=development_package.public.task_id,
        task_version=development_package.public.task_version,
        public_spec_hash=development_package.public_spec_hash,
        allowed_roles={DatasetRole.MEMORY_DEVELOPMENT},
    )
    assert entry.solution_lineage_id != development_entry.solution_lineage_id

    evidence_path = Path(
        "reports/docker-gate/research-hf-hub-custom-tqdm-class-contract.json"
    )
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert sha256_bytes(evidence_path.read_bytes()) == entry.admission_evidence.sha256
    assert evidence["task_id"] == package.public.task_id
    assert evidence["task_version"] == package.public.task_version
    assert evidence["dataset_role"] == entry.role.value
    assert evidence["split"] == package.public.split
    assert evidence["public_spec_hash"] == package.public_spec_hash
    assert evidence["private_spec_hash"] == package.private_spec_hash
    assert evidence["source"]["base_commit"] == package.public.repository.base_commit
    assert evidence["evaluator_image"] == package.environment.evaluator_image
    assert evidence["evaluator_image_digest"] == package.environment.image_digest
    assert evidence["harness_git_commit"] == (
        "962668e887f78840fec260d705ffb114a788719f"
    )
    assert evidence["reference_policy"]["kind"] == "exact-upstream-production-only"
    assert evidence["reference_policy"]["rejected_benchmark_production_patch"] is False
    assert evidence["source"]["benchmark_production_patch_sha256"] == (
        package.private.reference_patch.sha256
    )
    assert evidence["reference_pass_count"] == 3
    assert evidence["base_noop_rejection_count"] == 1
    assert evidence["known_bad_patch_rejection_count"] == 10
    assert evidence["semantic_bad_patch_rejection_count"] == 9
    assert evidence["independent_hidden_test_count"] == 15
    assert evidence["independent_hidden_test_function_count"] == 13
    assert evidence["benchmark_f2p_declared_count"] == 2
    assert evidence["benchmark_p2p_declared_count"] == 19
    assert evidence["benchmark_patch_added_p2p_count"] == 2
    assert evidence["upstream_regression_test_count"] == 17
    assert evidence["upstream_regression_collected_count"] == 17
    assert evidence["upstream_regression_skipped_count"] == 0
    for check_id in (
        "submitted_source_binding",
        "strict_foreign_constructor_ownership",
        "foreign_upstream_subclass_ownership",
        "context_callable_and_partial_factories",
        "hf_subclass_group_log_and_position_policy",
        "offline_file_download_path",
        "offline_snapshot_foreign_aggregation",
        "offline_snapshot_callable_and_partial_factories",
        "offline_snapshot_hf_group_and_log_policy",
        "combined_escaping_partial_rejected",
        "benchmark_p2p_execution_difference_disclosed",
        "same_repository_solution_lineage_is_distinct",
        "public_private_separation",
    ):
        assert evidence["admission_checks"][check_id] == "pass"

    cases = {case["name"]: case for case in evidence["cases"]}
    assert len(cases) == 14
    assert len({case["run_id"] for case in cases.values()}) == 14
    assert all(case["official"] for case in cases.values())
    for case in cases.values():
        patch_path = HF_TASK / case["patch"]
        assert sha256_bytes(patch_path.read_bytes()) == case["patch_sha256"]
        assert case["observed_success"] is case["expected_success"]
    assert all(cases[f"reference-{index}"]["observed_success"] for index in range(1, 4))
    assert {
        cases[f"reference-{index}"]["patch_sha256"] for index in range(1, 4)
    } == {package.private.reference_patch.sha256}
    for case_name in (
        "base-noop",
        "combined-foreign-only",
        "context-only",
        "exact-hf-class-only",
        "force-disable-false",
        "hf-policy-dropped",
        "snapshot-only",
        "strip-name-only",
        "unguarded-issubclass",
        "upstream-subclass-treated-as-hf",
    ):
        assert cases[case_name]["failed_checks"] == [
            "hidden:custom-tqdm-class-contract"
        ]
    assert cases["forbidden-test-edit"]["failed_checks"] == [
        "hidden:custom-tqdm-class-contract",
        "policy:scope",
        "policy:test_tampering",
    ]


def test_reverted_pypa_build_candidate_remains_excluded() -> None:
    with Path("data/benchmark-candidate-ledger.csv").open(encoding="utf-8", newline="") as handle:
        rows = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    candidate = rows["pypa__build-1027"]
    assert candidate["status"] == "excluded"
    assert "PR #1039" in candidate["notes"]
    assert "revert" in candidate["notes"].lower()


def test_mtplx_candidate_has_pinned_real_repository_provenance() -> None:
    package = load_task_package(MTPLX_TASK)

    assert package.public.task_id == "mtplx-mixed-content-tool-call-stream"
    assert package.public.split == "cross-repo-heldout"
    assert package.public.repository.url == "https://github.com/youssofal/MTPLX.git"
    assert (
        package.public.repository.base_commit
        == "c06cc13286e86d9ff3d2e3b991eba327549c534b"
    )
    assert package.public.repository.url in ALLOWED_REMOTE_REPOSITORIES
    assert package.public.constraints.allowed_paths == ["mtplx/server/openai.py"]
    assert package.public.constraints.max_changed_files == 1
    assert package.public.constraints.max_diff_lines == 110
    assert package.public.constraints.dependency_changes_allowed is False
    assert package.public.constraints.public_api_changes_allowed is False
    assert package.environment is not None
    assert package.environment.image_digest == (
        "sha256:32510a901064f5d405f3d4313a4556d924c94e72b2b0993296a43f04de83370e"
    )
    assert package.environment.evaluator_image.endswith(
        f"@{package.environment.image_digest}"
    )


def test_mtplx_visible_check_pins_base_resident_cpu_regressions() -> None:
    package = load_task_package(MTPLX_TASK)
    check = package.public.visible_checks[0]
    command = check.command

    assert check.id == "upstream-openai-stream-regression"
    assert command[:3] == [
        "/opt/conda/envs/testbed/bin/python",
        "-m",
        "pytest",
    ]
    assert "tests/test_server_openai.py" in command
    assert "tests/test_openai_bridge.py" in command
    assert "-k" not in command
    assert {
        argument for argument in command if argument.startswith("--deselect=")
    } == {
        "--deselect=tests/test_server_openai.py::"
        "test_streaming_session_uses_generation_final_postcommit_without_"
        "retokenized_tail",
        "--deselect=tests/test_server_openai.py::"
        "test_streaming_unsafe_postcommit_releases_without_blocking_second_request",
        "--deselect=tests/test_server_openai.py::"
        "test_streaming_ar_keeps_retokenized_postcommit_path",
    }
    assert check.environment["PYTHONPATH"] == "/workspace"
    assert check.timeout_seconds == 120


def test_mtplx_public_contract_excludes_evaluator_only_material() -> None:
    package = load_task_package(MTPLX_TASK)
    public_text = (MTPLX_TASK / "public.yaml").read_text(encoding="utf-8")

    assert "test_mixed_content_tool_call_stream.py" not in public_text
    assert "_ToolAwareContentStreamTranslator" not in public_text
    assert "_partial_marker_tail_len" not in public_text
    assert "reference.patch" not in public_text
    assert package.private.reference_patch.sha256 not in public_text
    assert ".patchloop-hidden" not in "\n".join(
        argument for check in package.public.visible_checks for argument in check.command
    )


def test_mtplx_admission_is_traceable_to_audited_swe_rebench_row() -> None:
    with Path("data/benchmark-candidate-ledger.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    candidate = rows["youssofal__mtplx-21"]
    assert candidate["benchmark_revision"] == (
        "ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b"
    )
    assert candidate["benchmark_split"] == "2026_03"
    assert candidate["base_commit"] == "c06cc13286e86d9ff3d2e3b991eba327549c534b"
    assert candidate["pr_url"] == "https://github.com/youssofal/MTPLX/pull/21"
    assert candidate["license_spdx"] == "Apache-2.0"
    assert candidate["gold_patch_lines"] == "131"
    assert candidate["test_patch_lines"] == "165"
    assert candidate["changed_files"] == "2"
    assert candidate["f2p"] == "4"
    assert candidate["p2p"] == "5"
    assert candidate["proposed_lane"] == "core-cross-repo"
    assert candidate["status"] == "admitted"
    assert candidate["environment_image"].endswith(
        "@sha256:32510a901064f5d405f3d4313a4556d924c94e72b2b0993296a43f04de83370e"
    )


def test_mtplx_reference_is_source_only_and_hash_bound() -> None:
    package = load_task_package(MTPLX_TASK)
    reference_patch = MTPLX_TASK / package.private.reference_patch.path
    patch_text = reference_patch.read_text(encoding="utf-8")
    patch_lines = patch_text.splitlines()

    assert package.private.reference_patch.sha256 == (
        "sha256:d8f6e6d0fa4ebc181c261816591298f13c079bebc864514fc2097f61944003d5"
    )
    assert sha256_bytes(reference_patch.read_bytes()) == (
        package.private.reference_patch.sha256
    )
    assert sum(
        line.startswith("+") and not line.startswith("+++") for line in patch_lines
    ) == 77
    assert sum(
        line.startswith("-") and not line.startswith("---") for line in patch_lines
    ) == 15
    assert "diff --git a/CHANGELOG.md" not in "\n".join(patch_lines)
    assert '+    _START_MARKER = "<tool_call>"' in patch_text
    assert '_TOOL_CALL_BLOCK_RE.sub("", self._pending)' in patch_text
    assert {
        line.removeprefix("diff --git a/").split(" b/", maxsplit=1)[0]
        for line in patch_lines
        if line.startswith("diff --git a/")
    } == {"mtplx/server/openai.py"}


def test_mtplx_oracle_and_bad_patch_inventory_are_explicit() -> None:
    hidden_path = MTPLX_TASK / "hidden/test_mixed_content_tool_call_stream.py"
    hidden_text = hidden_path.read_text(encoding="utf-8")
    bad_names = sorted(path.name for path in (MTPLX_TASK / "bad").glob("*.patch"))

    assert hidden_text.count("\ndef test_") == 20
    assert "range(len(payload) + 1)" in hidden_text
    assert "inspect.getsourcefile" in hidden_text
    assert "argument_chunk_chars=1" in hidden_text
    assert "_partial_marker_tail_len" not in hidden_text
    assert "<tool_calls>" in hidden_text
    assert "<tool_calligraphy>" in hidden_text
    assert "_parse_generated_tool_calls" in hidden_text
    assert bad_names == [
        "case-sensitive-content-scan.patch",
        "chunk-start-marker-only.patch",
        "content-lock-removed-only.patch",
        "current-chunk-search-only.patch",
        "forbidden-test-edit.patch",
        "initial-buffer-search-drops-preamble.patch",
        "no-partial-tail-hold.patch",
        "noop.patch",
        "one-character-tail-hold.patch",
        "trailing-policy-relaxed.patch",
        "upstream-accepted-missing-delimiter-residue.patch",
    ]
    assert (MTPLX_TASK / "bad/noop.patch").read_bytes() == b"\n"
    upstream_bad = (
        MTPLX_TASK / "bad/upstream-accepted-missing-delimiter-residue.patch"
    )
    assert sha256_bytes(upstream_bad.read_bytes()) == (
        "sha256:5850850bd5993c26aa1d963bf6f38eac694f0a4e799ab3c2db14fb74803094ad"
    )
    audit_text = (MTPLX_TASK / "audit.md").read_text(encoding="utf-8")
    assert "Admitted as the third `core-cross-repo`" in audit_text
    assert "20 test functions collect as 21 cases" in audit_text
    assert "21/21 hidden cases passing" in audit_text
    assert "passed 14 and failed" in audit_text


def test_mtplx_admission_evidence_binds_hardened_streaming_boundaries() -> None:
    package = load_task_package(MTPLX_TASK)
    entry = require_dataset_role(
        task_id=package.public.task_id,
        task_version=package.public.task_version,
        public_spec_hash=package.public_spec_hash,
        allowed_roles={DatasetRole.CORE_CROSS_REPO},
    )
    assert entry.role == DatasetRole.CORE_CROSS_REPO
    assert (
        entry.failure_pattern_id
        == "streamed-tool-call-detection-stops-after-content"
    )
    assert (
        entry.solution_lineage_id
        == "youssofal-mtplx-pr-21-hardened-delimiter-residue"
    )
    assert entry.admission_evidence is not None
    assert entry.admission_evidence.reference_pass_runs == 3
    assert entry.admission_evidence.rejected_bad_patches == 10

    evidence_path = Path(
        "reports/docker-gate/research-mtplx-mixed-content-tool-call-stream.json"
    )
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert sha256_bytes(evidence_path.read_bytes()) == entry.admission_evidence.sha256
    assert evidence["task_id"] == package.public.task_id
    assert evidence["task_version"] == package.public.task_version
    assert evidence["dataset_role"] == entry.role.value
    assert evidence["split"] == package.public.split
    assert evidence["public_spec_hash"] == package.public_spec_hash
    assert evidence["private_spec_hash"] == package.private_spec_hash
    assert evidence["source"]["base_commit"] == package.public.repository.base_commit
    assert evidence["evaluator_image"] == package.environment.evaluator_image
    assert evidence["evaluator_image_digest"] == package.environment.image_digest
    assert evidence["harness_git_commit"] == (
        "82a0c23b6043481010b4aa5e1202fd4189b6ffc0"
    )
    assert evidence["reference_policy"]["kind"] == (
        "hardened-upstream-streaming-production-only"
    )
    assert evidence["reference_policy"]["rejected_benchmark_production_patch"] is True
    assert evidence["reference_policy"]["rejected_upstream_accepted_source_patch"] is True
    assert evidence["source"]["upstream_accepted_source_patch_sha256"] == (
        "sha256:5850850bd5993c26aa1d963bf6f38eac694f0a4e799ab3c2db14fb74803094ad"
    )
    assert evidence["reference_pass_count"] == 3
    assert evidence["base_noop_rejection_count"] == 1
    assert evidence["known_bad_patch_rejection_count"] == 10
    assert evidence["semantic_bad_patch_rejection_count"] == 9
    assert evidence["independent_hidden_test_count"] == 21
    assert evidence["independent_hidden_test_function_count"] == 20
    assert evidence["benchmark_f2p_declared_count"] == 4
    assert evidence["benchmark_p2p_declared_count"] == 5
    assert evidence["upstream_regression_test_count"] == 55
    assert evidence["upstream_regression_collected_count"] == 58
    assert evidence["upstream_regression_deselected_count"] == 3

    cases = {case["name"]: case for case in evidence["cases"]}
    assert len(cases) == 14
    assert len({case["run_id"] for case in cases.values()}) == 14
    assert all(case["official"] for case in cases.values())
    for case in cases.values():
        patch_path = MTPLX_TASK / case["patch"]
        assert sha256_bytes(patch_path.read_bytes()) == case["patch_sha256"]
        assert case["observed_success"] is case["expected_success"]
    assert all(cases[f"reference-{index}"]["observed_success"] for index in range(1, 4))
    assert {
        cases[f"reference-{index}"]["patch_sha256"] for index in range(1, 4)
    } == {package.private.reference_patch.sha256}
    for case_name in (
        "base-noop",
        "content-lock-removed-only",
        "chunk-start-marker-only",
        "current-chunk-search-only",
        "initial-buffer-search-drops-preamble",
        "case-sensitive-content-scan",
        "no-partial-tail-hold",
        "one-character-tail-hold",
        "trailing-policy-relaxed",
        "upstream-accepted-missing-delimiter-residue",
    ):
        assert cases[case_name]["failed_checks"] == [
            "hidden:mixed-content-tool-call-stream"
        ]
    assert cases["forbidden-test-edit"]["failed_checks"] == [
        "hidden:mixed-content-tool-call-stream",
        "policy:scope",
        "policy:test_tampering",
    ]


def test_fusesoc_candidate_has_pinned_real_repository_provenance() -> None:
    package = load_task_package(FUSESOC_TASK)

    assert package.public.task_id == "fusesoc-retained-parse-error-diagnostics"
    assert package.public.split == "cross-repo-heldout"
    assert package.public.repository.url == "https://github.com/olofk/fusesoc.git"
    assert package.public.repository.base_commit == (
        "d2e6e720222f57cb66d6c303a326d336c582aade"
    )
    assert package.public.repository.url in ALLOWED_REMOTE_REPOSITORIES
    assert package.public.constraints.allowed_paths == [
        "fusesoc/coremanager.py",
        "fusesoc/fusesoc.py",
        "fusesoc/main.py",
    ]
    assert package.public.constraints.max_changed_files == 3
    assert package.public.constraints.max_diff_lines == 80
    assert package.public.constraints.dependency_changes_allowed is False
    assert package.public.constraints.public_api_changes_allowed is True
    assert package.environment is not None
    assert package.environment.image_digest == (
        "sha256:1e971791d4ce192eae296747d46dff477cb2ce2c47e08b2ed9d0108ee5a85ad9"
    )
    assert package.environment.evaluator_image.endswith(
        f"@{package.environment.image_digest}"
    )


def test_fusesoc_visible_check_pins_official_boundary_compatible_nodes() -> None:
    package = load_task_package(FUSESOC_TASK)
    check = package.public.visible_checks[0]
    command = check.command

    assert check.id == "upstream-coremanager-regression"
    assert command[:3] == [
        "/opt/conda/envs/testbed/bin/python",
        "-m",
        "pytest",
    ]
    assert "tests/test_coremanager.py" in command
    assert "-k" not in command
    assert {
        argument for argument in command if argument.startswith("--deselect=")
    } == {
        "--deselect=tests/test_coremanager.py::test_export",
        "--deselect=tests/test_coremanager.py::test_lockfile_no_file_create",
    }
    assert check.environment["PYTHONPATH"] == "/workspace"
    assert check.environment["PATH"].startswith("/opt/conda/envs/testbed/bin:")
    assert check.timeout_seconds == 120


def test_fusesoc_public_contract_excludes_evaluator_only_material() -> None:
    package = load_task_package(FUSESOC_TASK)
    public_text = (FUSESOC_TASK / "public.yaml").read_text(encoding="utf-8")

    assert "test_retained_parse_error_diagnostics.py" not in public_text
    assert "_manager_with_mixed_library" not in public_text
    assert "_MissingCoreManager" not in public_text
    assert "reference.patch" not in public_text
    assert package.private.reference_patch.sha256 not in public_text
    assert ".patchloop-hidden" not in "\n".join(
        argument for check in package.public.visible_checks for argument in check.command
    )


def test_fusesoc_candidate_is_traceable_to_frozen_swe_rebench_row() -> None:
    with Path("data/benchmark-candidate-ledger.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    candidate = rows["olofk__fusesoc-776_interface"]
    assert candidate["benchmark_family"] == "SWE-rebench-leaderboard"
    assert candidate["benchmark_revision"] == (
        "ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b"
    )
    assert candidate["benchmark_split"] == "2026_03"
    assert candidate["base_commit"] == (
        "d2e6e720222f57cb66d6c303a326d336c582aade"
    )
    assert candidate["pr_url"] == "https://github.com/olofk/fusesoc/pull/776"
    assert candidate["license_spdx"] == "BSD-2-Clause"
    assert candidate["gold_patch_lines"] == "74"
    assert candidate["test_patch_lines"] == "49"
    assert candidate["changed_files"] == "3"
    assert candidate["f2p"] == "1"
    assert candidate["p2p"] == "14"
    assert candidate["proposed_lane"] == "core-cross-repo"
    assert candidate["status"] == "admitted"
    assert candidate["environment_image"].endswith(
        "@sha256:1e971791d4ce192eae296747d46dff477cb2ce2c47e08b2ed9d0108ee5a85ad9"
    )
    assert "clean-harness official matrix" in candidate["notes"]
    assert "12 of 14 base P2P nodes" in candidate["notes"]
    assert "read-only source mount" in candidate["notes"]


def test_fusesoc_reference_is_exact_production_patch_and_hash_bound() -> None:
    package = load_task_package(FUSESOC_TASK)
    reference_patch = FUSESOC_TASK / package.private.reference_patch.path
    patch_text = reference_patch.read_text(encoding="utf-8")
    patch_lines = patch_text.splitlines()

    assert package.private.reference_patch.sha256 == (
        "sha256:c25ac0f174a7b0b9d9d5d9b5d0a179856103351652a64e4da8483e8f5ed83658"
    )
    assert sha256_bytes(reference_patch.read_bytes()) == (
        package.private.reference_patch.sha256
    )
    assert sum(
        line.startswith("+") and not line.startswith("+++") for line in patch_lines
    ) == 29
    assert sum(
        line.startswith("-") and not line.startswith("---") for line in patch_lines
    ) == 1
    assert {
        line.removeprefix("diff --git a/").split(" b/", maxsplit=1)[0]
        for line in patch_lines
        if line.startswith("diff --git a/")
    } == {
        "fusesoc/coremanager.py",
        "fusesoc/fusesoc.py",
        "fusesoc/main.py",
    }
    assert "diff --git a/tests/" not in patch_text


def test_fusesoc_oracle_and_bad_patch_inventory_are_explicit() -> None:
    hidden_path = (
        FUSESOC_TASK / "hidden/test_retained_parse_error_diagnostics.py"
    )
    hidden_text = hidden_path.read_text(encoding="utf-8")
    bad_names = sorted(path.name for path in (FUSESOC_TASK / "bad").glob("*.patch"))

    assert hidden_text.count("\ndef test_") == 10
    assert "inspect.getsourcefile" in hidden_text
    assert "01-invalid-fileset.core" in hidden_text
    assert "02-invalid-yaml.core" in hidden_text
    assert "::healthy:1" in hidden_text
    assert "test_core_manager_instances_do_not_share_parse_failures" in hidden_text
    assert "second.parse_errors == []" in hidden_text
    assert "failures.append" in hidden_text
    assert "LegacyManager" in hidden_text
    assert "MissingProviderCore" in hidden_text
    assert bad_names == [
        "class-shared-errors.patch",
        "cli-first-error-only.patch",
        "forbidden-test-edit.patch",
        "hard-stop-on-parse-error.patch",
        "import-errors-misclassified.patch",
        "last-error-only.patch",
        "manager-only-retention.patch",
        "missing-cli-propagation.patch",
        "noop.patch",
        "wrapper-only-exposure.patch",
    ]
    assert (FUSESOC_TASK / "bad/noop.patch").read_bytes() == b"\n"

    audit_text = (FUSESOC_TASK / "audit.md").read_text(encoding="utf-8")
    assert "explicitly deselected" in audit_text
    assert "tests/test_coremanager.py::test_export" in audit_text
    assert "tests/test_coremanager.py::test_lockfile_no_file_create" in audit_text
    assert "passes 12 nodes" in audit_text


def test_fusesoc_admission_evidence_binds_parse_diagnostic_boundaries() -> None:
    package = load_task_package(FUSESOC_TASK)
    entry = require_dataset_role(
        task_id=package.public.task_id,
        task_version=package.public.task_version,
        public_spec_hash=package.public_spec_hash,
        allowed_roles={DatasetRole.CORE_CROSS_REPO},
    )
    assert entry.role == DatasetRole.CORE_CROSS_REPO
    assert (
        entry.failure_pattern_id
        == "parse-errors-discarded-before-missing-core-diagnostic"
    )
    assert entry.solution_lineage_id == "olofk-fusesoc-pr-776"
    assert entry.admission_evidence is not None
    assert entry.admission_evidence.reference_pass_runs == 3
    assert entry.admission_evidence.rejected_bad_patches == 9

    evidence_path = Path(
        "reports/docker-gate/research-fusesoc-retained-parse-error-diagnostics.json"
    )
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert sha256_bytes(evidence_path.read_bytes()) == entry.admission_evidence.sha256
    assert evidence["task_id"] == package.public.task_id
    assert evidence["task_version"] == package.public.task_version
    assert evidence["dataset_role"] == entry.role.value
    assert evidence["split"] == package.public.split
    assert evidence["public_spec_hash"] == package.public_spec_hash
    assert evidence["private_spec_hash"] == package.private_spec_hash
    assert evidence["source"]["base_commit"] == package.public.repository.base_commit
    assert evidence["evaluator_image"] == package.environment.evaluator_image
    assert evidence["evaluator_image_digest"] == package.environment.image_digest
    assert evidence["harness_git_commit"] == (
        "da3105d30f0c7eb6fec65650200aedac7eb12b13"
    )
    assert evidence["reference_policy"]["kind"] == (
        "exact-upstream-production-only"
    )
    assert (
        evidence["reference_policy"]["rejected_benchmark_production_patch"]
        is False
    )
    assert evidence["source"]["benchmark_test_patch_sha256"] == (
        "sha256:b046536ed3628c23fec2da7ded058b365205d09e8438182f9756e6f02f6a87fb"
    )
    assert evidence["source"]["accepted_source_blob_sha1"] == {
        "fusesoc/coremanager.py": "1f6d7499f629e7fb6831868c71546b269bc374ac",
        "fusesoc/fusesoc.py": "b964aa4ea512ac8ab033787218367c5a239ad307",
        "fusesoc/main.py": "e1f460dea5de7b683e3e45fb594f6c03db5b3db8",
    }
    assert evidence["reference_pass_count"] == 3
    assert evidence["base_noop_rejection_count"] == 1
    assert evidence["known_bad_patch_rejection_count"] == 9
    assert evidence["semantic_bad_patch_rejection_count"] == 8
    assert evidence["independent_hidden_test_count"] == 10
    assert evidence["independent_hidden_test_function_count"] == 10
    assert evidence["benchmark_f2p_declared_count"] == 1
    assert evidence["benchmark_p2p_declared_count"] == 14
    assert evidence["upstream_regression_test_count"] == 12
    assert evidence["upstream_regression_collected_count"] == 14
    assert evidence["upstream_regression_deselected_count"] == 2
    assert evidence["runtime"]["python_version"] == "3.13.13"
    assert evidence["runtime"]["pytest_version"] == "9.0.3"

    cases = {case["name"]: case for case in evidence["cases"]}
    assert len(cases) == 13
    assert len({case["run_id"] for case in cases.values()}) == 13
    assert all(case["official"] for case in cases.values())
    for case in cases.values():
        patch_path = FUSESOC_TASK / case["patch"]
        assert sha256_bytes(patch_path.read_bytes()) == case["patch_sha256"]
        assert case["observed_success"] is case["expected_success"]
    assert all(cases[f"reference-{index}"]["observed_success"] for index in range(1, 4))
    assert {
        cases[f"reference-{index}"]["patch_sha256"] for index in range(1, 4)
    } == {package.private.reference_patch.sha256}
    for case_name in (
        "base-noop",
        "manager-only-retention",
        "wrapper-only-exposure",
        "missing-cli-propagation",
        "last-error-only",
        "class-shared-errors",
        "hard-stop-on-parse-error",
        "import-errors-misclassified",
        "cli-first-error-only",
    ):
        assert cases[case_name]["failed_checks"] == [
            "hidden:retained-parse-error-diagnostics"
        ]
    assert cases["forbidden-test-edit"]["failed_checks"] == [
        "hidden:retained-parse-error-diagnostics",
        "policy:scope",
        "policy:test_tampering",
    ]
    assert evidence["admission_checks"]["base_visible_checks"] == "pass"
    assert evidence["admission_checks"]["base_hidden_acceptance"] == "fail"
    for check_id in (
        "reference_scrr_three_repetitions",
        "known_bad_boundaries",
        "submitted_source_binding",
        "multiple_parse_failures_retained",
        "valid_core_discovery_continues",
        "accumulation_across_scans",
        "manager_instance_isolation",
        "live_public_property_forwarding",
        "all_parse_failures_rendered",
        "import_error_behavior_unchanged",
        "exact_public_signature_delta",
        "exact_upstream_production_lineage",
        "benchmark_test_patch_excluded",
        "benchmark_p2p_execution_difference_disclosed",
        "public_private_separation",
        "network_disabled_evaluator",
        "read_only_submitted_workspace",
        "immutable_source_commit",
        "immutable_evaluator_image",
    ):
        assert evidence["admission_checks"][check_id] == "pass"


def test_kubeflow_candidate_has_pinned_real_repository_provenance() -> None:
    package = load_task_package(KUBEFLOW_TASK)

    assert package.public.task_id == "kubeflow-exit-handler-after-dependencies"
    assert package.public.split == "cross-repo-heldout"
    assert package.public.repository.url == "https://github.com/kubeflow/pipelines.git"
    assert package.public.repository.base_commit == (
        "98f5b7a300ee52d6c530b429558b718ade9fdb7a"
    )
    assert package.public.repository.url in ALLOWED_REMOTE_REPOSITORIES
    assert package.public.constraints.allowed_paths == [
        "sdk/python/kfp/compiler/compiler_utils.py",
        "sdk/python/kfp/dsl/pipeline_task.py",
    ]
    assert package.public.constraints.max_changed_files == 2
    assert package.public.constraints.max_diff_lines == 110
    assert package.public.constraints.dependency_changes_allowed is False
    assert package.public.constraints.public_api_changes_allowed is True
    assert package.environment is not None
    assert package.environment.image_digest == (
        "sha256:842b24c98e1b2c1145b8826b90a95e0634a3520cd523b3d3ae6940201ec2e79a"
    )
    assert package.environment.evaluator_image.endswith(
        f"@{package.environment.image_digest}"
    )


def test_kubeflow_visible_check_uses_submitted_source_copy_and_related_modules() -> None:
    package = load_task_package(KUBEFLOW_TASK)
    check = package.public.visible_checks[0]
    script = check.command[2]

    assert check.command[:2] == ["/bin/bash", "-lc"]
    assert "cp -a /workspace/sdk/python/kfp" in script
    assert 'export PYTHONPATH="$source_root/sdk/python"' in script
    assert 'export PATH="/opt/conda/envs/testbed/bin:$PATH"' in script
    assert "/workspace/sdk/python/kfp/compiler/compiler_test.py" in script
    assert "/workspace/sdk/python/kfp/dsl/pipeline_task_test.py" in script
    assert "--deselect" not in script
    assert "-k " not in script
    assert check.timeout_seconds == 180
    assert check.environment["PATH"].startswith("/opt/conda/envs/testbed/bin:")


def test_kubeflow_public_contract_excludes_evaluator_only_material() -> None:
    package = load_task_package(KUBEFLOW_TASK)
    public_text = (KUBEFLOW_TASK / "public.yaml").read_text(encoding="utf-8")

    assert "test_exit_handler_after_dependencies.py" not in public_text
    assert "_resolve_dependency_name_to_group_or_task" not in public_text
    assert "reference.patch" not in public_text
    assert package.private.reference_patch.sha256 not in public_text
    assert package.private.hidden_artifacts[0].sha256 not in public_text
    assert ".patchloop-hidden" not in "\n".join(
        argument for check in package.public.visible_checks for argument in check.command
    )


def test_kubeflow_candidate_is_traceable_to_frozen_swe_rebench_row() -> None:
    with Path("data/benchmark-candidate-ledger.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    candidate = rows["kubeflow__pipelines-13112"]
    assert candidate["benchmark_family"] == "SWE-rebench-leaderboard"
    assert candidate["benchmark_revision"] == (
        "ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b"
    )
    assert candidate["benchmark_split"] == "2026_03"
    assert candidate["base_commit"] == (
        "98f5b7a300ee52d6c530b429558b718ade9fdb7a"
    )
    assert candidate["pr_url"] == "https://github.com/kubeflow/pipelines/pull/13112"
    assert candidate["license_spdx"] == "Apache-2.0"
    assert candidate["gold_patch_lines"] == "159"
    assert candidate["test_patch_lines"] == "189"
    assert candidate["changed_files"] == "2"
    assert candidate["f2p"] == "7"
    assert candidate["p2p"] == "278"
    assert candidate["proposed_lane"] == "core-cross-repo"
    assert candidate["status"] == "admitted"
    assert candidate["environment_image"].endswith(
        "@sha256:842b24c98e1b2c1145b8826b90a95e0634a3520cd523b3d3ae6940201ec2e79a"
    )
    assert "passed 3/3 official runs" in candidate["notes"]
    assert "277 base-resident visible tests" in candidate["notes"]
    assert "all 13 cases made zero model/API calls" in candidate["notes"]


def test_kubeflow_reference_is_exact_production_patch_and_hash_bound() -> None:
    package = load_task_package(KUBEFLOW_TASK)
    reference_patch = KUBEFLOW_TASK / package.private.reference_patch.path
    patch_text = reference_patch.read_text(encoding="utf-8")
    patch_lines = patch_text.splitlines()

    assert package.private.reference_patch.sha256 == (
        "sha256:ea57612615fc67d2707284b740ee5be170fa2684ad1d98e72046bf18d5d940a1"
    )
    assert sha256_bytes(reference_patch.read_bytes()) == (
        package.private.reference_patch.sha256
    )
    assert sum(
        line.startswith("+") and not line.startswith("+++") for line in patch_lines
    ) == 83
    assert sum(
        line.startswith("-") and not line.startswith("---") for line in patch_lines
    ) == 15
    assert {
        line.removeprefix("diff --git a/").split(" b/", maxsplit=1)[0]
        for line in patch_lines
        if line.startswith("diff --git a/")
    } == {
        "sdk/python/kfp/compiler/compiler_utils.py",
        "sdk/python/kfp/dsl/pipeline_task.py",
    }
    assert "_test.py" not in patch_text


def test_kubeflow_oracle_and_bad_patch_inventory_are_explicit() -> None:
    package = load_task_package(KUBEFLOW_TASK)
    hidden_path = KUBEFLOW_TASK / "hidden/test_exit_handler_after_dependencies.py"
    hidden_text = hidden_path.read_text(encoding="utf-8")
    bad_names = sorted(path.name for path in (KUBEFLOW_TASK / "bad").glob("*.patch"))

    assert hidden_text.count("\ndef test_") == 11
    for marker in (
        "test_oracle_imports_submitted_kfp_copy",
        "test_after_records_exit_handler_group_name",
        "test_compiler_depends_on_group_not_cleanup_task",
        "test_mixed_task_and_group_dependencies_are_preserved",
        "test_two_completed_groups_keep_requested_order",
        "test_non_exit_group_rejected_before_dependency_mutation",
        "test_arbitrary_dependency_rejected_before_dependency_mutation",
        "test_unknown_recorded_dependency_has_clear_error",
        "test_ambiguous_task_and_group_name_has_clear_error",
        "test_inner_task_dependency_remains_illegal_after_group_exit",
        "test_final_status_is_produced_by_depended_on_exit_group",
    ):
        assert marker in hidden_text
    assert package.private.schema_version == "task-private-v2"
    assert [artifact.path for artifact in package.private.hidden_artifacts] == [
        "hidden/test_exit_handler_after_dependencies.py"
    ]
    assert package.private.hidden_artifacts[0].sha256 == (
        "sha256:77425a3ab8e3d8c8bc1afa6776a7074dac768b9f33f6e2bf815ec0a6e05d778f"
    )
    assert sha256_bytes(hidden_path.read_bytes()) == (
        package.private.hidden_artifacts[0].sha256
    )
    hidden_script = package.private.hidden_checks[0].command[2]
    assert (
        "/workspace/.patchloop-hidden/test_exit_handler_after_dependencies.py"
        in hidden_script
    )
    assert "cp /workspace/.patchloop-hidden" not in hidden_script
    assert bad_names == [
        "compiler-resolution-only.patch",
        "fallback-any-group.patch",
        "first-dependency-only.patch",
        "forbidden-test-edit.patch",
        "group-only-resolution.patch",
        "noop.patch",
        "public-validation-only.patch",
        "resolve-group-as-exit-task.patch",
        "task-precedence-on-collision.patch",
        "unknown-dependency-keyerror.patch",
    ]
    assert (KUBEFLOW_TASK / "bad/noop.patch").read_bytes() == b"\n"

    audit_text = (KUBEFLOW_TASK / "audit.md").read_text(encoding="utf-8")
    assert "277 passing base-resident cases" in audit_text
    assert "task-private-v2" in audit_text
    assert "Admitted as the sixth `core-cross-repo`" in audit_text


def test_kubeflow_private_v2_rejects_hidden_oracle_mutation(tmp_path: Path) -> None:
    copied_task = tmp_path / KUBEFLOW_TASK.name
    shutil.copytree(KUBEFLOW_TASK, copied_task)
    hidden_path = copied_task / "hidden/test_exit_handler_after_dependencies.py"
    hidden_path.write_text(
        hidden_path.read_text(encoding="utf-8") + "\n# unbound mutation\n",
        encoding="utf-8",
    )

    with pytest.raises(ContractError, match="hidden artifact hash mismatch"):
        load_task_package(copied_task)


def test_kubeflow_admission_evidence_binds_exit_handler_boundaries() -> None:
    package = load_task_package(KUBEFLOW_TASK)
    entry = require_dataset_role(
        task_id=package.public.task_id,
        task_version=package.public.task_version,
        public_spec_hash=package.public_spec_hash,
        allowed_roles={DatasetRole.CORE_CROSS_REPO},
    )
    assert entry.role == DatasetRole.CORE_CROSS_REPO
    assert entry.failure_pattern_id == "exit-handler-group-dependency-resolution"
    assert entry.solution_lineage_id == "kubeflow-pipelines-pr-13112"
    assert entry.admission_evidence is not None
    assert entry.admission_evidence.reference_pass_runs == 3
    assert entry.admission_evidence.rejected_bad_patches == 9

    evidence_path = Path(
        "reports/docker-gate/research-kubeflow-exit-handler-after-dependencies.json"
    )
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert sha256_bytes(evidence_path.read_bytes()) == entry.admission_evidence.sha256
    assert evidence["task_id"] == package.public.task_id
    assert evidence["task_version"] == package.public.task_version
    assert evidence["dataset_role"] == entry.role.value
    assert evidence["split"] == package.public.split
    assert evidence["public_spec_hash"] == package.public_spec_hash
    assert evidence["private_spec_hash"] == package.private_spec_hash
    assert evidence["source"]["base_commit"] == package.public.repository.base_commit
    assert evidence["evaluator_image"] == package.environment.evaluator_image
    assert evidence["evaluator_image_digest"] == package.environment.image_digest
    assert evidence["harness_git_commit"] == (
        "5e7b019e60b4d76f67e48bafe6fd1a3b309fe313"
    )
    assert evidence["reference_policy"]["kind"] == "exact-upstream-production-only"
    assert evidence["reference_policy"]["rejected_benchmark_production_patch"] is False
    assert evidence["source"]["benchmark_production_patch_sha256"] == (
        package.private.reference_patch.sha256
    )
    assert evidence["source"]["benchmark_test_patch_sha256"] == (
        "sha256:fb94e7491c0121e4343d3aa246ee10e808aabfc3a88570966aad2cb99c376729"
    )
    assert evidence["source"]["private_hidden_artifact_sha256"] == (
        package.private.hidden_artifacts[0].sha256
    )
    assert evidence["source"]["accepted_source_blob_sha1"] == {
        "sdk/python/kfp/compiler/compiler_utils.py": (
            "e2f16b2bce413efe92b66f630dd917f6ff2df18b"
        ),
        "sdk/python/kfp/dsl/pipeline_task.py": (
            "c77529bad6e3720f328e2c0b3c0c920182db6415"
        ),
    }
    assert evidence["reference_pass_count"] == 3
    assert evidence["base_noop_rejection_count"] == 1
    assert evidence["known_bad_patch_rejection_count"] == 9
    assert evidence["semantic_bad_patch_rejection_count"] == 8
    assert evidence["independent_hidden_test_count"] == 11
    assert evidence["independent_hidden_test_function_count"] == 11
    assert evidence["benchmark_f2p_declared_count"] == 7
    assert evidence["benchmark_p2p_declared_count"] == 278
    assert evidence["benchmark_patch_added_f2p_count"] == 7
    assert evidence["benchmark_patch_added_p2p_count"] == 1
    assert evidence["benchmark_base_resident_p2p_count"] == 277
    assert evidence["upstream_regression_test_count"] == 277
    assert evidence["upstream_regression_collected_count"] == 277
    assert evidence["upstream_regression_subtest_count"] == 15
    assert evidence["upstream_regression_deselected_count"] == 0
    assert evidence["runtime"]["working_directory"] == "/workspace"
    assert evidence["runtime"]["visible_test_location"] == "read-only /workspace"
    assert evidence["runtime"]["hidden_oracle_location"] == "read-only /workspace"
    assert evidence["runtime"]["python_version"] == "3.13.13"
    assert evidence["runtime"]["pytest_version"] == "9.0.3"
    assert evidence["runtime"]["execution_user"] == "image-default-root"
    assert evidence["runtime"]["docker_config_user"] == ""

    cases = {case["name"]: case for case in evidence["cases"]}
    assert len(cases) == 13
    assert len({case["run_id"] for case in cases.values()}) == 13
    assert {case["run_id"] for case in cases.values()} == {
        "run_7876f396980a4c55",
        "run_e2930e730d104a3c",
        "run_f4c2707cc64e4a63",
        "run_28d458248adb4cca",
        "run_9c0ab4f5a208424a",
        "run_fb281c4593234662",
        "run_f4445927f042437d",
        "run_61a35efc95b34a2a",
        "run_030d1c1ffa3c4e0b",
        "run_a3d0b17e1e624efe",
        "run_9b25341374b54dfe",
        "run_d48f210c19244f82",
        "run_2da8391ec73948e4",
    }
    assert all(case["official"] for case in cases.values())
    for case in cases.values():
        patch_path = KUBEFLOW_TASK / case["patch"]
        assert sha256_bytes(patch_path.read_bytes()) == case["patch_sha256"]
        assert case["observed_success"] is case["expected_success"]
    assert all(cases[f"reference-{index}"]["observed_success"] for index in range(1, 4))
    assert {
        cases[f"reference-{index}"]["patch_sha256"] for index in range(1, 4)
    } == {package.private.reference_patch.sha256}
    for case_name in (
        "base-noop",
        "compiler-resolution-only",
        "fallback-any-group",
        "public-validation-only",
        "resolve-group-as-exit-task",
        "task-precedence-on-collision",
        "unknown-dependency-keyerror",
    ):
        assert cases[case_name]["failed_checks"] == [
            "hidden:exit-handler-after-dependencies"
        ]
    for case_name in ("first-dependency-only", "group-only-resolution"):
        assert cases[case_name]["failed_checks"] == [
            "regression:upstream-compiler-and-pipeline-task-regression",
            "hidden:exit-handler-after-dependencies",
        ]
    assert cases["forbidden-test-edit"]["failed_checks"] == [
        "hidden:exit-handler-after-dependencies",
        "policy:scope",
        "policy:test_tampering",
    ]
    assert evidence["admission_checks"]["base_visible_checks"] == "pass"
    assert evidence["admission_checks"]["base_hidden_acceptance"] == "fail"
    for check_id in (
        "reference_scrr_three_repetitions",
        "known_bad_boundaries",
        "submitted_source_binding",
        "after_records_exit_handler_group_name",
        "compiled_dependency_targets_exit_handler_group",
        "mixed_task_and_group_dependencies_preserved",
        "chained_exit_handler_group_order_preserved",
        "non_exit_group_rejected_before_mutation",
        "arbitrary_dependency_rejected_before_mutation",
        "unknown_dependency_clear_error",
        "ambiguous_task_group_name_clear_error",
        "inner_task_cross_group_dependency_rejected",
        "final_status_attributed_to_exit_handler_group",
        "exact_upstream_production_lineage",
        "benchmark_test_patch_excluded",
        "benchmark_p2p_decomposition_verified",
        "private_v2_hidden_artifact_bound",
        "visible_test_read_only",
        "hidden_oracle_read_only",
        "test_tampering_path_recognition",
        "public_private_separation",
        "no_new_dependency",
        "public_api_change_explicitly_allowed",
        "network_disabled_evaluator",
        "read_only_root_filesystem",
        "read_only_submitted_workspace",
        "external_image_default_user_disclosed",
        "immutable_source_commit",
        "immutable_evaluator_image",
        "exact_sha_shallow_checkout",
    ):
        assert evidence["admission_checks"][check_id] == "pass"


def test_tox_dotted_candidate_is_traceable_to_frozen_swe_rebench_row() -> None:
    with Path("data/benchmark-candidate-ledger.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    candidate = rows["tox-dev__tox-3846"]
    assert candidate["benchmark_family"] == "SWE-rebench-leaderboard"
    assert candidate["benchmark_revision"] == (
        "ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b"
    )
    assert candidate["benchmark_split"] == "2026_03"
    assert candidate["base_commit"] == (
        "ae05f2a33ccfe52ff22ac578ec6c8eb9f750ce4a"
    )
    assert candidate["pr_url"] == "https://github.com/tox-dev/tox/pull/3846"
    assert candidate["license_spdx"] == "MIT"
    assert candidate["gold_patch_lines"] == "44"
    assert candidate["test_patch_lines"] == "34"
    assert candidate["changed_files"] == "2"
    assert candidate["f2p"] == "7"
    assert candidate["p2p"] == "110"
    assert candidate["proposed_lane"] == "core-same-repo"
    assert candidate["status"] == "admitted"
    assert candidate["environment_image"].endswith(
        "@sha256:269a32558d3aeac5f9e9b6fc451302667b83a85f260f0b915babe1838b50b3bc"
    )
    assert "hardened #3846+#3851 reference 3/3" in candidate["notes"]
    assert "99 plus two exact prefix-overlap rechecks" in candidate["notes"]


def test_tox_dotted_candidate_has_pinned_real_repository_provenance() -> None:
    package = load_task_package(TOX_DOTTED_TASK)

    assert package.public.task_id == "tox-dotted-version-factor-base-python"
    assert package.public.split == "same-repo-heldout"
    assert package.public.repository.url == "https://github.com/tox-dev/tox.git"
    assert package.public.repository.base_commit == (
        "ae05f2a33ccfe52ff22ac578ec6c8eb9f750ce4a"
    )
    assert package.public.repository.url in ALLOWED_REMOTE_REPOSITORIES
    assert package.public.constraints.allowed_paths == [
        "src/tox/tox_env/python/api.py"
    ]
    assert package.public.constraints.max_changed_files == 1
    assert package.public.constraints.max_diff_lines == 60
    assert package.public.constraints.dependency_changes_allowed is False
    assert package.public.constraints.public_api_changes_allowed is False
    assert package.environment is not None
    assert package.environment.image_digest == (
        "sha256:269a32558d3aeac5f9e9b6fc451302667b83a85f260f0b915babe1838b50b3bc"
    )
    assert package.environment.evaluator_image.endswith(
        f"@{package.environment.image_digest}"
    )


def test_tox_dotted_visible_check_discloses_image_drift_deselections() -> None:
    package = load_task_package(TOX_DOTTED_TASK)
    check = package.public.visible_checks[0]
    script = check.command[2]

    assert check.id == "upstream-python-api-regression"
    assert check.command[:2] == ["/bin/bash", "-lc"]
    assert "tests/tox_env/python/test_python_api.py" in script
    assert "cp /testbed/src/tox/version.py" in script
    assert script.count("--deselect ") == 9
    for node in (
        "test_requirements_txt",
        "test_build_wheel_in_non_base_pkg_env",
        "test_python_set_hash_seed",
        "test_python_generate_hash_seed",
        "test_python_keep_hash_seed",
        "test_python_hash_seed_via_section_substitution",
        "test_python_disable_hash_seed",
        "test_python_hash_seed_from_env_and_override",
        "test_python_hash_seed_from_env_and_disable",
    ):
        assert f"tests/tox_env/python/test_python_api.py::{node}" in script
    assert check.timeout_seconds == 90


def test_tox_dotted_public_contract_excludes_evaluator_only_material() -> None:
    package = load_task_package(TOX_DOTTED_TASK)
    public_text = (TOX_DOTTED_TASK / "public.yaml").read_text(encoding="utf-8")

    assert "test_dotted_version_factor_contract.py" not in public_text
    assert "matrix-py3.12-2.18" not in public_text
    assert "reference.patch" not in public_text
    assert package.private.reference_patch.sha256 not in public_text
    assert ".patchloop-hidden" not in "\n".join(
        argument for check in package.public.visible_checks for argument in check.command
    )


def test_tox_dotted_reference_is_hardened_upstream_union_and_hash_bound() -> None:
    package = load_task_package(TOX_DOTTED_TASK)
    reference_path = TOX_DOTTED_TASK / package.private.reference_patch.path
    patch_text = reference_path.read_text(encoding="utf-8")
    patch_lines = patch_text.splitlines()

    assert package.private.reference_patch.sha256 == (
        "sha256:3245865999cca1398bc922389d93f9f92d8729da19423fcda7e23a0275d4bb37"
    )
    assert sha256_bytes(reference_path.read_bytes()) == (
        package.private.reference_patch.sha256
    )
    assert sum(
        line.startswith("+") and not line.startswith("+++") for line in patch_lines
    ) == 21
    assert sum(
        line.startswith("-") and not line.startswith("---") for line in patch_lines
    ) == 7
    assert {
        line.removeprefix("diff --git a/").split(" b/", maxsplit=1)[0]
        for line in patch_lines
        if line.startswith("diff --git a/")
    } == {"src/tox/tox_env/python/api.py"}
    assert "index f06242261e..b0093787b1" in patch_text
    assert "diff --git a/tests/" not in patch_text


def test_tox_dotted_oracle_and_bad_patch_inventory_are_explicit() -> None:
    hidden_path = (
        TOX_DOTTED_TASK / "hidden/test_dotted_version_factor_contract.py"
    )
    hidden_text = hidden_path.read_text(encoding="utf-8")
    bad_names = sorted(path.name for path in (TOX_DOTTED_TASK / "bad").glob("*.patch"))

    assert hidden_text.count("\ndef test_") == 8
    assert "@pytest.mark.parametrize" in hidden_text
    assert "module_path.is_relative_to(source_root.resolve())" in hidden_text
    assert "lint-3.12-docs" in hidden_text
    assert "eslint-8.3-check" in hidden_text
    assert "matrix-py3.12-2.18" in hidden_text
    assert "test_default_resolution_honors_ignore_policy_in_both_directions" in hidden_text
    assert "test_validation_honors_ignore_policy_in_both_directions" in hidden_text
    assert "test_ignore_keeps_older_single_factor_override_contract" in hidden_text
    assert "test_cli_uses_default_base_python_when_conflict_is_ignored" in hidden_text
    assert bad_names == [
        "exact-3846-partial.patch",
        "exact-3851-partial.patch",
        "explicit-only-regresses-classic.patch",
        "first-match-no-conflict.patch",
        "forbidden-test-edit.patch",
        "ignore-all-validation-conflicts.patch",
        "ignore-default-only.patch",
        "ignore-validation-only.patch",
        "noop.patch",
        "restrict-major-only.patch",
        "strip-compound-threaded.patch",
        "wide-major-compound.patch",
    ]
    assert (TOX_DOTTED_TASK / "bad/noop.patch").read_bytes() == b"\n"

    audit_text = (TOX_DOTTED_TASK / "audit.md").read_text(encoding="utf-8")
    assert "admitted `core-same-repo`" in audit_text
    assert "exact #3846 production patch" in audit_text
    assert "PR #3851" in audit_text
    assert "101" in audit_text
    assert "nine" in audit_text
    assert "All 15 runs used clean harness commit" in audit_text
    assert "216ccfd1f9017ca499c9902ac857a2e6d4ebc0dca1aeb1aff04e9af396485fe6" in (
        audit_text
    )


def test_tox_dotted_admission_evidence_binds_followup_policy_boundaries() -> None:
    package = load_task_package(TOX_DOTTED_TASK)
    entry = require_dataset_role(
        task_id=package.public.task_id,
        task_version=package.public.task_version,
        public_spec_hash=package.public_spec_hash,
        allowed_roles={DatasetRole.CORE_SAME_REPO},
    )
    assert entry.role == DatasetRole.CORE_SAME_REPO
    assert (
        entry.failure_pattern_id
        == "compound-dotted-factor-conflict-before-policy"
    )
    assert entry.solution_lineage_id == "tox-dev-pr-3846-followup-3851"
    assert entry.admission_evidence is not None
    assert entry.admission_evidence.reference_pass_runs == 3
    assert entry.admission_evidence.rejected_bad_patches == 11

    evidence_path = Path(
        "reports/docker-gate/research-tox-dotted-version-factor-base-python.json"
    )
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert sha256_bytes(evidence_path.read_bytes()) == entry.admission_evidence.sha256
    assert evidence["task_id"] == package.public.task_id
    assert evidence["task_version"] == package.public.task_version
    assert evidence["dataset_role"] == entry.role.value
    assert evidence["split"] == package.public.split
    assert evidence["public_spec_hash"] == package.public_spec_hash
    assert evidence["private_spec_hash"] == package.private_spec_hash
    assert evidence["source"]["base_commit"] == package.public.repository.base_commit
    assert evidence["evaluator_image"] == package.environment.evaluator_image
    assert evidence["evaluator_image_digest"] == package.environment.image_digest
    assert evidence["harness_git_commit"] == (
        "678d30a50ae27cb48623c1fbe5bc04bb65d34bad"
    )
    assert evidence["reference_policy"]["kind"] == (
        "hardened-accepted-upstream-union-production-only"
    )
    assert evidence["reference_policy"]["rejected_benchmark_production_patch"] is True
    assert evidence["source"]["follow_up_pull_request_url"].endswith("/pull/3851")
    assert evidence["source"]["resolution_commit"] == (
        "5e1db72ea6e4dbef2dfedaaf6a27de11f3820973"
    )
    assert evidence["source"]["benchmark_gold_patch_sha256"] == (
        "sha256:064fb6156cd9f3b2cda17dfad95f00e7ae8eca598755bc8bcdce282beaf84c85"
    )
    assert evidence["source"]["benchmark_test_patch_sha256"] == (
        "sha256:bacf75f3e975c41a2ff1f150595b1f071a882d63818ec190854aae38ea091bd6"
    )
    assert evidence["source"]["accepted_source_blob_sha1"] == {
        "base": "f06242261e512f6c6970f510920c79e26ac3ec45",
        "after_pr_3846": "24798ea789a53ec4cb354b49f94bea31deac78bf",
        "after_pr_3851": "b0093787b1e0ddde421385c350f82745ec447649",
    }
    assert evidence["reference_pass_count"] == 3
    assert evidence["base_noop_rejection_count"] == 1
    assert evidence["known_bad_patch_rejection_count"] == 11
    assert evidence["semantic_bad_patch_rejection_count"] == 10
    assert evidence["independent_hidden_test_count"] == 17
    assert evidence["independent_hidden_test_function_count"] == 8
    assert evidence["benchmark_f2p_declared_count"] == 7
    assert evidence["benchmark_p2p_declared_count"] == 110
    assert evidence["upstream_regression_test_count"] == 101
    assert evidence["upstream_regression_collected_count"] == 110
    assert evidence["upstream_regression_deselected_count"] == 9
    assert evidence["upstream_regression_prefix_overlap_reincluded_count"] == 2
    assert evidence["runtime"]["working_directory"] == "/workspace"
    assert evidence["runtime"]["image_working_directory"] == "/testbed"
    assert evidence["runtime"]["python_version"] == "3.13.13"
    assert evidence["runtime"]["pytest_version"] == "9.0.3"

    cases = {case["name"]: case for case in evidence["cases"]}
    assert len(cases) == 15
    assert len({case["run_id"] for case in cases.values()}) == 15
    assert all(case["official"] for case in cases.values())
    for case in cases.values():
        patch_path = TOX_DOTTED_TASK / case["patch"]
        assert sha256_bytes(patch_path.read_bytes()) == case["patch_sha256"]
        assert case["observed_success"] is case["expected_success"]
    assert all(cases[f"reference-{index}"]["observed_success"] for index in range(1, 4))
    assert {
        cases[f"reference-{index}"]["patch_sha256"] for index in range(1, 4)
    } == {package.private.reference_patch.sha256}
    for case_name in (
        "base-noop",
        "exact-3846-partial",
        "exact-3851-partial",
        "restrict-major-only",
        "ignore-default-only",
        "ignore-validation-only",
        "strip-compound-threaded",
    ):
        assert cases[case_name]["failed_checks"] == [
            "hidden:dotted-version-factor-contract"
        ]
    for case_name in (
        "explicit-only-regresses-classic",
        "first-match-no-conflict",
        "ignore-all-validation-conflicts",
        "wide-major-compound",
    ):
        assert cases[case_name]["failed_checks"] == [
            "regression:upstream-python-api-regression",
            "hidden:dotted-version-factor-contract",
        ]
    assert cases["forbidden-test-edit"]["failed_checks"] == [
        "hidden:dotted-version-factor-contract",
        "policy:scope",
        "policy:test_tampering",
    ]
    assert evidence["admission_checks"]["base_visible_checks"] == "pass"
    assert evidence["admission_checks"]["base_hidden_acceptance"] == "fail"
    for check_id in (
        "reference_scrr_three_repetitions",
        "known_bad_boundaries",
        "submitted_source_binding",
        "compound_dotted_factor_positions",
        "free_threaded_suffix_preserved",
        "classic_and_whole_name_factors_preserved",
        "non_python_major_versions_rejected",
        "multiple_factor_conflict_preserved",
        "ignore_default_fallback",
        "ignore_validation_preservation",
        "single_factor_override_contract_preserved",
        "exact_pr_3846_partial_rejected",
        "exact_pr_3851_partial_rejected",
        "hardened_followup_lineage",
        "benchmark_test_patch_excluded",
        "benchmark_p2p_execution_difference_disclosed",
        "same_repository_solution_lineage_is_distinct",
        "public_private_separation",
        "network_disabled_evaluator",
        "read_only_submitted_workspace",
        "immutable_source_commit",
        "immutable_evaluator_image",
    ):
        assert evidence["admission_checks"][check_id] == "pass"


def test_dagster_candidate_has_pinned_real_repository_provenance() -> None:
    package = load_task_package(DAGSTER_TASK)

    assert package.public.task_id == "dagster-subset-partition-definition-selection"
    assert package.public.split == "cross-repo-heldout"
    assert package.public.repository.url == "https://github.com/dagster-io/dagster.git"
    assert package.public.repository.base_commit == (
        "f8430dc7bf76bfab4f026165e5c5f821104298df"
    )
    assert package.public.repository.url in ALLOWED_REMOTE_REPOSITORIES
    assert package.public.constraints.allowed_paths == [
        "python_modules/dagster/dagster/_core/definitions/assets/definition/assets_definition.py",
        "python_modules/dagster/dagster/_core/execution/context/system.py",
    ]
    assert package.public.constraints.max_changed_files == 2
    assert package.public.constraints.max_diff_lines == 60
    assert package.public.constraints.dependency_changes_allowed is False
    assert package.public.constraints.public_api_changes_allowed is False
    assert package.environment is not None
    assert package.environment.image_digest == (
        "sha256:98a0b69301022cba2ac7520a8ab1891c2a490cf4ec4ba889d6ce36a29f40831b"
    )
    assert package.environment.evaluator_image.endswith(
        f"@{package.environment.image_digest}"
    )


def test_dagster_visible_check_uses_submitted_source_copy_and_all_p2p() -> None:
    package = load_task_package(DAGSTER_TASK)
    check = package.public.visible_checks[0]
    command = check.command
    script = command[2]

    assert check.id == "upstream-partitioned-assets-regression"
    assert command[:2] == ["/bin/bash", "-lc"]
    assert "cp -a /workspace/python_modules/dagster/dagster" in script
    assert "cp -a /workspace/python_modules/dagster " not in script
    assert 'export PYTHONPATH="$source_root/python_modules/dagster"' in script
    assert (
        "/workspace/python_modules/dagster/dagster_tests/asset_defs_tests/"
        "test_partitioned_assets.py"
    ) in script
    assert "--deselect" not in script
    assert "-k " not in script
    assert check.timeout_seconds == 90
    assert check.environment["PATH"].startswith("/opt/conda/envs/testbed/bin:")


def test_dagster_public_contract_excludes_evaluator_only_material() -> None:
    package = load_task_package(DAGSTER_TASK)
    public_text = (DAGSTER_TASK / "public.yaml").read_text(encoding="utf-8")

    assert "test_selected_entity_partition_definition.py" not in public_text
    assert "_entity_partitions_def" not in public_text
    assert "reference.patch" not in public_text
    assert package.private.reference_patch.sha256 not in public_text
    assert package.private.hidden_artifacts[0].sha256 not in public_text
    assert ".patchloop-hidden" not in "\n".join(
        argument for check in package.public.visible_checks for argument in check.command
    )


def test_dagster_candidate_is_traceable_to_frozen_swe_rebench_row() -> None:
    with Path("data/benchmark-candidate-ledger.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    candidate = rows["dagster-io__dagster-33605"]
    assert candidate["benchmark_family"] == "SWE-rebench-leaderboard"
    assert candidate["benchmark_revision"] == (
        "ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b"
    )
    assert candidate["benchmark_split"] == "2026_03"
    assert candidate["base_commit"] == (
        "f8430dc7bf76bfab4f026165e5c5f821104298df"
    )
    assert candidate["pr_url"] == "https://github.com/dagster-io/dagster/pull/33605"
    assert candidate["license_spdx"] == "Apache-2.0"
    assert candidate["gold_patch_lines"] == "42"
    assert candidate["test_patch_lines"] == "52"
    assert candidate["changed_files"] == "2"
    assert candidate["f2p"] == "1"
    assert candidate["p2p"] == "28"
    assert candidate["proposed_lane"] == "core-cross-repo"
    assert candidate["status"] == "admitted"
    assert candidate["environment_image"].endswith(
        "@sha256:98a0b69301022cba2ac7520a8ab1891c2a490cf4ec4ba889d6ce36a29f40831b"
    )
    assert "all 28 P2P regressions" in candidate["notes"]
    assert "passed 3/3 official runs" in candidate["notes"]
    assert "task-private-v2" in candidate["notes"]


def test_dagster_reference_is_exact_production_patch_and_hash_bound() -> None:
    package = load_task_package(DAGSTER_TASK)
    reference_patch = DAGSTER_TASK / package.private.reference_patch.path
    patch_text = reference_patch.read_text(encoding="utf-8")
    patch_lines = patch_text.splitlines()

    assert package.private.reference_patch.sha256 == (
        "sha256:1f0ec526d126ef8893fb40d032cc5a26b52bb1eb1b2eba56757541088ae0308e"
    )
    assert sha256_bytes(reference_patch.read_bytes()) == (
        package.private.reference_patch.sha256
    )
    assert sum(
        line.startswith("+") and not line.startswith("+++") for line in patch_lines
    ) == 12
    assert sum(
        line.startswith("-") and not line.startswith("---") for line in patch_lines
    ) == 7
    assert {
        line.removeprefix("diff --git a/").split(" b/", maxsplit=1)[0]
        for line in patch_lines
        if line.startswith("diff --git a/")
    } == {
        "python_modules/dagster/dagster/_core/definitions/assets/definition/assets_definition.py",
        "python_modules/dagster/dagster/_core/execution/context/system.py",
    }
    assert "dagster_tests/" not in patch_text


def test_dagster_oracle_and_bad_patch_inventory_are_explicit() -> None:
    package = load_task_package(DAGSTER_TASK)
    hidden_path = (
        DAGSTER_TASK / "hidden/test_selected_entity_partition_definition.py"
    )
    hidden_text = hidden_path.read_text(encoding="utf-8")
    bad_names = sorted(path.name for path in (DAGSTER_TASK / "bad").glob("*.patch"))

    assert hidden_text.count("\ndef test_") == 9
    assert "test_oracle_imports_the_submitted_source_copy" in hidden_text
    assert "test_selected_partitioned_check_defines_partition_context" in hidden_text
    assert "selected_asset_check_keys" in hidden_text
    assert "StepExecutionContext.__dict__" in hidden_text
    assert "execution context duplicated asset selection" in hidden_text
    assert package.private.schema_version == "task-private-v2"
    assert [artifact.path for artifact in package.private.hidden_artifacts] == [
        "hidden/test_selected_entity_partition_definition.py"
    ]
    assert package.private.hidden_artifacts[0].sha256 == (
        "sha256:dbfd76a912a27d498092fda20e37db4d99c69fc359d8a5e1c048751e5be24c86"
    )
    assert sha256_bytes(hidden_path.read_bytes()) == (
        package.private.hidden_artifacts[0].sha256
    )
    hidden_script = package.private.hidden_checks[0].command[2]
    assert (
        "/workspace/.patchloop-hidden/test_selected_entity_partition_definition.py"
        in hidden_script
    )
    assert "cp /workspace/.patchloop-hidden" not in hidden_script
    assert bad_names == [
        "always-unpartitioned.patch",
        "assets-definition-only.patch",
        "check-asset-key-filter.patch",
        "execution-context-only.patch",
        "first-selected-definition.patch",
        "forbidden-test-edit.patch",
        "noop.patch",
        "selected-assets-only.patch",
        "selected-checks-only.patch",
        "unfiltered-check-specs.patch",
    ]
    assert (DAGSTER_TASK / "bad/noop.patch").read_bytes() == b"\n"

    audit_text = (DAGSTER_TASK / "audit.md").read_text(encoding="utf-8")
    assert "all 28 base-resident p2p nodes" in audit_text.lower()
    assert "read-only `/workspace` mount" in audit_text
    assert "Admitted as the fifth `core-cross-repo`" in audit_text


def test_dagster_private_v2_rejects_hidden_oracle_mutation(tmp_path: Path) -> None:
    copied_task = tmp_path / DAGSTER_TASK.name
    shutil.copytree(DAGSTER_TASK, copied_task)
    hidden_path = copied_task / "hidden/test_selected_entity_partition_definition.py"
    hidden_path.write_text(
        hidden_path.read_text(encoding="utf-8") + "\n# unbound mutation\n",
        encoding="utf-8",
    )

    with pytest.raises(ContractError, match="hidden artifact hash mismatch"):
        load_task_package(copied_task)


def test_dagster_admission_evidence_binds_partition_selection_boundaries() -> None:
    package = load_task_package(DAGSTER_TASK)
    entry = require_dataset_role(
        task_id=package.public.task_id,
        task_version=package.public.task_version,
        public_spec_hash=package.public_spec_hash,
        allowed_roles={DatasetRole.CORE_CROSS_REPO},
    )
    assert entry.role == DatasetRole.CORE_CROSS_REPO
    assert entry.failure_pattern_id == "unselected-entity-partition-state-leak"
    assert entry.solution_lineage_id == "dagster-io-dagster-pr-33605"
    assert entry.admission_evidence is not None
    assert entry.admission_evidence.reference_pass_runs == 3
    assert entry.admission_evidence.rejected_bad_patches == 9

    evidence_path = Path(
        "reports/docker-gate/research-dagster-subset-partition-definition-selection.json"
    )
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert sha256_bytes(evidence_path.read_bytes()) == entry.admission_evidence.sha256
    assert evidence["task_id"] == package.public.task_id
    assert evidence["task_version"] == package.public.task_version
    assert evidence["dataset_role"] == entry.role.value
    assert evidence["split"] == package.public.split
    assert evidence["public_spec_hash"] == package.public_spec_hash
    assert evidence["private_spec_hash"] == package.private_spec_hash
    assert evidence["source"]["base_commit"] == package.public.repository.base_commit
    assert evidence["evaluator_image"] == package.environment.evaluator_image
    assert evidence["evaluator_image_digest"] == package.environment.image_digest
    assert evidence["harness_git_commit"] == (
        "26f28cf11d53f3b0e17b2a4663d0ce68afe63b27"
    )
    assert evidence["reference_policy"]["kind"] == "exact-upstream-production-only"
    assert evidence["reference_policy"]["rejected_benchmark_production_patch"] is False
    assert evidence["source"]["benchmark_production_patch_sha256"] == (
        package.private.reference_patch.sha256
    )
    assert evidence["source"]["benchmark_test_patch_sha256"] == (
        "sha256:c8eb674dc7d4082c7e4ef006a65ec229c229f78405b94790cddd1d06a2ebf06a"
    )
    assert evidence["source"]["private_hidden_artifact_sha256"] == (
        package.private.hidden_artifacts[0].sha256
    )
    assert evidence["source"]["accepted_source_blob_sha1"] == {
        "python_modules/dagster/dagster/_core/definitions/assets/definition/assets_definition.py": (
            "641d5c12f673f6f06330e796641e009bc4db43dc"
        ),
        "python_modules/dagster/dagster/_core/execution/context/system.py": (
            "941d5ce1aa6c2306c5934725ea77b909a290cbef"
        ),
    }
    assert evidence["reference_pass_count"] == 3
    assert evidence["base_noop_rejection_count"] == 1
    assert evidence["known_bad_patch_rejection_count"] == 9
    assert evidence["semantic_bad_patch_rejection_count"] == 8
    assert evidence["independent_hidden_test_count"] == 9
    assert evidence["independent_hidden_test_function_count"] == 9
    assert evidence["benchmark_f2p_declared_count"] == 1
    assert evidence["benchmark_p2p_declared_count"] == 28
    assert evidence["benchmark_patch_added_f2p_count"] == 1
    assert evidence["benchmark_patch_added_p2p_count"] == 0
    assert evidence["upstream_regression_test_count"] == 28
    assert evidence["upstream_regression_collected_count"] == 28
    assert evidence["upstream_regression_deselected_count"] == 0
    assert evidence["runtime"]["working_directory"] == "/workspace"
    assert evidence["runtime"]["visible_test_location"] == "read-only /workspace"
    assert evidence["runtime"]["hidden_oracle_location"] == "read-only /workspace"
    assert evidence["runtime"]["python_version"] == "3.13.13"
    assert evidence["runtime"]["pytest_version"] == "9.0.3"

    cases = {case["name"]: case for case in evidence["cases"]}
    assert len(cases) == 13
    assert len({case["run_id"] for case in cases.values()}) == 13
    assert {case["run_id"] for case in cases.values()} == {
        "run_1927909d6cd241e7",
        "run_bd7f5b11e51d4202",
        "run_c66f90c1fc4242cc",
        "run_2a20d874bedf450b",
        "run_d8c2b3eb40814ba8",
        "run_7ea661da98c748f2",
        "run_fb0bd8300f514af9",
        "run_2682f33ade874bd9",
        "run_2204c73911354106",
        "run_91a3c33dfdbc4958",
        "run_55ba57333f1740ec",
        "run_2a7f765456c44ab0",
        "run_2b6c0ba491ee4d86",
    }
    assert all(case["official"] for case in cases.values())
    for case in cases.values():
        patch_path = DAGSTER_TASK / case["patch"]
        assert sha256_bytes(patch_path.read_bytes()) == case["patch_sha256"]
        assert case["observed_success"] is case["expected_success"]
    assert all(cases[f"reference-{index}"]["observed_success"] for index in range(1, 4))
    assert {
        cases[f"reference-{index}"]["patch_sha256"] for index in range(1, 4)
    } == {package.private.reference_patch.sha256}
    for case_name in (
        "base-noop",
        "assets-definition-only",
        "check-asset-key-filter",
        "execution-context-only",
        "first-selected-definition",
        "selected-assets-only",
        "selected-checks-only",
        "unfiltered-check-specs",
    ):
        assert cases[case_name]["failed_checks"] == [
            "hidden:selected-entity-partition-definition"
        ]
    assert cases["always-unpartitioned"]["failed_checks"] == [
        "regression:upstream-partitioned-assets-regression",
        "hidden:selected-entity-partition-definition",
    ]
    assert cases["forbidden-test-edit"]["failed_checks"] == [
        "hidden:selected-entity-partition-definition",
        "policy:scope",
        "policy:test_tampering",
    ]
    assert evidence["admission_checks"]["base_visible_checks"] == "pass"
    assert evidence["admission_checks"]["base_hidden_acceptance"] == "fail"
    for check_id in (
        "reference_scrr_three_repetitions",
        "known_bad_boundaries",
        "submitted_source_binding",
        "selected_nonpartitioned_ignores_unselected_asset",
        "selected_partitioned_asset_preserved",
        "selected_check_partition_context",
        "unselected_check_ignored",
        "compatible_definitions_deduplicated",
        "conflicting_selected_definitions_rejected",
        "execution_context_delegation",
        "exact_upstream_production_lineage",
        "benchmark_test_patch_excluded",
        "private_v2_hidden_artifact_bound",
        "visible_test_read_only",
        "hidden_oracle_read_only",
        "test_tampering_path_recognition",
        "public_private_separation",
        "no_new_dependency",
        "public_api_unchanged",
        "network_disabled_evaluator",
        "read_only_root_filesystem",
        "read_only_submitted_workspace",
        "immutable_source_commit",
        "immutable_evaluator_image",
        "exact_sha_shallow_checkout",
    ):
        assert evidence["admission_checks"][check_id] == "pass"


def test_loguru_timezone_candidate_has_pinned_real_repository_provenance() -> None:
    package = load_task_package(LOGURU_TIMEZONE_TASK)

    assert package.public.task_id == "loguru-post-2038-local-timezone-fallback"
    assert package.public.split == "same-repo-heldout"
    assert package.public.repository.url == "https://github.com/Delgan/loguru.git"
    assert package.public.repository.base_commit == (
        "e310e2029102b5d63a679a2b64501c045aa86336"
    )
    assert package.public.repository.url in ALLOWED_REMOTE_REPOSITORIES
    assert package.public.constraints.allowed_paths == ["loguru/_datetime.py"]
    assert package.public.constraints.max_changed_files == 1
    assert package.public.constraints.max_diff_lines == 80
    assert package.public.constraints.dependency_changes_allowed is False
    assert package.public.constraints.public_api_changes_allowed is False
    assert package.environment is not None
    assert package.environment.image_digest == (
        "sha256:8d899d1147cf88bc088afe57fc5299fdcf2fafe6a1e30ef26825577e8953362f"
    )
    assert package.environment.evaluator_image.endswith(
        f"@{package.environment.image_digest}"
    )


def test_loguru_timezone_visible_check_uses_submitted_source_copy() -> None:
    package = load_task_package(LOGURU_TIMEZONE_TASK)
    check = package.public.visible_checks[0]
    script = check.command[2]

    assert check.command[:2] == ["/bin/bash", "-lc"]
    assert 'cp -a /workspace/loguru "$source_root/loguru"' in script
    assert 'export PYTHONPATH="$source_root"' in script
    assert "/workspace/tests/test_datetime.py" in script
    assert "--deselect" not in script
    assert "-k " not in script
    assert check.timeout_seconds == 60
    assert check.environment["PATH"].startswith("/opt/conda/envs/testbed/bin:")


def test_loguru_timezone_public_contract_excludes_evaluator_material() -> None:
    package = load_task_package(LOGURU_TIMEZONE_TASK)
    public_text = (LOGURU_TIMEZONE_TASK / "public.yaml").read_text(
        encoding="utf-8"
    )

    assert "test_local_timezone_fallback.py" not in public_text
    assert "reference.patch" not in public_text
    assert package.private.reference_patch.sha256 not in public_text
    assert package.private.hidden_artifacts[0].sha256 not in public_text
    assert ".patchloop-hidden" not in "\n".join(
        argument for check in package.public.visible_checks for argument in check.command
    )


def test_loguru_timezone_candidate_is_traceable_to_frozen_rebench_row() -> None:
    with Path("data/benchmark-candidate-ledger.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = {row["candidate_id"]: row for row in csv.DictReader(handle)}

    candidate = rows["Delgan__loguru-1297"]
    assert candidate["benchmark_family"] == "SWE-rebench-leaderboard"
    assert candidate["benchmark_revision"] == (
        "ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b"
    )
    assert candidate["benchmark_split"] == "test"
    assert candidate["upstream_repository"] == "Delgan/loguru"
    assert candidate["base_commit"] == (
        "e310e2029102b5d63a679a2b64501c045aa86336"
    )
    assert candidate["pr_url"] == "https://github.com/Delgan/loguru/pull/1297"
    assert candidate["license_spdx"] == "MIT"
    assert candidate["gold_patch_lines"] == "67"
    assert candidate["test_patch_lines"] == "124"
    assert candidate["changed_files"] == "1"
    assert candidate["f2p"] == "4"
    assert candidate["p2p"] == "34"
    assert candidate["proposed_lane"] == "core-same-repo"
    assert candidate["status"] == "admitted"
    assert candidate["environment_image"].endswith(
        "@sha256:8d899d1147cf88bc088afe57fc5299fdcf2fafe6a1e30ef26825577e8953362f"
    )
    assert "row 209" in candidate["notes"]
    assert "passed 3/3 official runs" in candidate["notes"]
    assert "all 43 visible tests" in candidate["notes"]
    assert "utcfromtimestamp equivalent passed 1/1" in candidate["notes"]
    assert "all 15 cases made zero model/API calls" in candidate["notes"]


def test_loguru_timezone_reference_is_exact_production_patch() -> None:
    package = load_task_package(LOGURU_TIMEZONE_TASK)
    reference_path = LOGURU_TIMEZONE_TASK / package.private.reference_patch.path
    patch_text = reference_path.read_text(encoding="utf-8")
    patch_lines = patch_text.splitlines()

    assert package.private.reference_patch.sha256 == (
        "sha256:850a97a59338efdc693016ccb96b7bfd891426fa6a0b5671e060f7830fad2cf3"
    )
    assert sha256_bytes(reference_path.read_bytes()) == (
        package.private.reference_patch.sha256
    )
    assert sum(
        line.startswith("+") and not line.startswith("+++") for line in patch_lines
    ) == 28
    assert sum(
        line.startswith("-") and not line.startswith("---") for line in patch_lines
    ) == 10
    assert {
        line.removeprefix("diff --git a/").split(" b/", maxsplit=1)[0]
        for line in patch_lines
        if line.startswith("diff --git a/")
    } == {"loguru/_datetime.py"}
    assert "tests/" not in patch_text
    assert "CHANGELOG.rst" not in patch_text


def test_loguru_timezone_oracle_and_bad_patch_inventory_are_explicit() -> None:
    package = load_task_package(LOGURU_TIMEZONE_TASK)
    hidden_path = LOGURU_TIMEZONE_TASK / "hidden/test_local_timezone_fallback.py"
    hidden_text = hidden_path.read_text(encoding="utf-8")
    bad_names = sorted(
        path.name for path in (LOGURU_TIMEZONE_TASK / "bad").glob("*.patch")
    )
    equivalent_paths = sorted(
        (LOGURU_TIMEZONE_TASK / "equivalent").glob("*.patch")
    )

    assert hidden_text.count("\ndef test_") == 5
    for marker in (
        "valid-negative",
        "valid-zero",
        "valid-positive",
        "invalid-positive",
        "invalid-negative",
        "os-error",
        "overflow-error",
        "missing-both",
        "missing-zone",
        "missing-gmtoff",
        "runtime-error",
        "FALLBACK_EAST",
        "FALLBACK_WEST",
        "FALLBACK_ROLLOVER",
        "def utcfromtimestamp",
        "def astimezone",
        "def combine",
    ):
        assert marker in hidden_text
    assert package.private.schema_version == "task-private-v2"
    assert [artifact.path for artifact in package.private.hidden_artifacts] == [
        "hidden/test_local_timezone_fallback.py"
    ]
    assert package.private.hidden_artifacts[0].sha256 == (
        "sha256:9305ebb2a03f8f68c078e537676ffccb68672b81b1b17b732b755d49520df240"
    )
    assert sha256_bytes(hidden_path.read_bytes()) == (
        package.private.hidden_artifacts[0].sha256
    )
    hidden_script = package.private.hidden_checks[0].command[2]
    assert "/workspace/.patchloop-hidden/test_local_timezone_fallback.py" in (
        hidden_script
    )
    assert "cp /workspace/.patchloop-hidden" not in hidden_script
    assert bad_names == [
        "always-fallback.patch",
        "broad-localtime-exception.patch",
        "clamp-invalid-offset.patch",
        "fixed-derived-fallback.patch",
        "forbidden-test-edit.patch",
        "noop.patch",
        "reversed-fallback-offset.patch",
        "unnamed-fallback-zone.patch",
        "utc-on-invalid-offset.patch",
        "wrong-localtime-exceptions.patch",
        "wrong-timezone-exception.patch",
    ]
    assert (LOGURU_TIMEZONE_TASK / "bad/noop.patch").read_bytes() == b"\n"
    assert [path.name for path in equivalent_paths] == [
        "utcfromtimestamp-fallback.patch"
    ]
    assert sha256_bytes(equivalent_paths[0].read_bytes()) == (
        "sha256:860a34c06e00d4e5e4e994a13445da426df68735088f1dadb0b378c9a2e409b4"
    )
    assert "datetime_.utcfromtimestamp(timestamp)" in equivalent_paths[0].read_text(
        encoding="utf-8"
    )

    audit_text = (LOGURU_TIMEZONE_TASK / "audit.md").read_text(encoding="utf-8")
    assert "admitted as the fifth `core-same-repo` task" in audit_text
    assert "11 independent parameter cases" in audit_text
    assert "positive, negative, and date-rollover-derived offsets" in audit_text
    assert "one no-op, nine semantic partials" in audit_text
    assert "positive control for\nimplementation independence" in audit_text
    assert "All 15 official cases made zero model/API calls" in audit_text


def test_loguru_timezone_private_v2_rejects_hidden_oracle_mutation(
    tmp_path: Path,
) -> None:
    copied_task = tmp_path / LOGURU_TIMEZONE_TASK.name
    shutil.copytree(LOGURU_TIMEZONE_TASK, copied_task)
    hidden_path = copied_task / "hidden/test_local_timezone_fallback.py"
    hidden_path.write_text(
        hidden_path.read_text(encoding="utf-8") + "\n# unbound mutation\n",
        encoding="utf-8",
    )

    with pytest.raises(ContractError, match="hidden artifact hash mismatch"):
        load_task_package(copied_task)


def test_loguru_timezone_lineage_is_distinct_from_memory_development_task() -> None:
    development = load_task_package(LOGURU_TASK)
    held_out = load_task_package(LOGURU_TIMEZONE_TASK)
    audit_text = (LOGURU_TIMEZONE_TASK / "audit.md").read_text(encoding="utf-8")

    assert held_out.public.repository.url == development.public.repository.url
    assert held_out.public.repository.base_commit != (
        development.public.repository.base_commit
    )
    assert held_out.public.task_id != development.public.task_id
    assert set(held_out.public.constraints.allowed_paths).isdisjoint(
        development.public.constraints.allowed_paths
    )
    assert "delgan-loguru-pr-1297" in audit_text
    assert "PR #1451" in audit_text
    assert "platform conversion failures" in audit_text
    assert "formatting catch" in audit_text


def test_loguru_timezone_admission_evidence_binds_fallback_boundaries() -> None:
    package = load_task_package(LOGURU_TIMEZONE_TASK)
    entry = require_dataset_role(
        task_id=package.public.task_id,
        task_version=package.public.task_version,
        public_spec_hash=package.public_spec_hash,
        allowed_roles={DatasetRole.CORE_SAME_REPO},
    )
    assert entry.role == DatasetRole.CORE_SAME_REPO
    assert entry.failure_pattern_id == "platform-timezone-fallback-boundary"
    assert entry.solution_lineage_id == "delgan-loguru-pr-1297"
    assert entry.admission_evidence is not None
    assert entry.admission_evidence.reference_pass_runs == 3
    assert entry.admission_evidence.rejected_bad_patches == 10

    evidence_path = Path(
        "reports/docker-gate/research-loguru-post-2038-local-timezone-fallback.json"
    )
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert sha256_bytes(evidence_path.read_bytes()) == (
        entry.admission_evidence.sha256
    )
    assert evidence["task_id"] == package.public.task_id
    assert evidence["task_version"] == package.public.task_version
    assert evidence["dataset_role"] == entry.role.value
    assert evidence["split"] == package.public.split
    assert evidence["public_spec_hash"] == package.public_spec_hash
    assert evidence["private_spec_hash"] == package.private_spec_hash
    assert evidence["source"]["base_commit"] == (
        package.public.repository.base_commit
    )
    assert evidence["evaluator_image"] == package.environment.evaluator_image
    assert evidence["evaluator_image_digest"] == package.environment.image_digest
    assert evidence["harness_git_commit"] == (
        "8c5084eee3a44a44e207345950a9ffb45b23e4b1"
    )
    assert evidence["reference_policy"]["kind"] == (
        "exact-upstream-production-only"
    )
    assert evidence["reference_policy"]["rejected_benchmark_production_patch"] is (
        False
    )
    assert evidence["source"]["benchmark_production_patch_sha256"] == (
        package.private.reference_patch.sha256
    )
    assert evidence["source"]["benchmark_gold_patch_sha256"] == (
        "sha256:62b087dc93f025037988b181ec3afea2b065fb07cbe7a9f2ec3b85f65ff886eb"
    )
    assert evidence["source"]["benchmark_test_patch_sha256"] == (
        "sha256:4d90ad03fbce47a347aa7dbb83d85596d2867052eb53aa31c049ae6aec945432"
    )
    assert evidence["source"]["private_hidden_artifact_sha256"] == (
        package.private.hidden_artifacts[0].sha256
    )
    assert evidence["source"]["base_source_blob_sha1"] == {
        "loguru/_datetime.py": "52fffc3b7ed9022f3f2d3974c3015f2b14d83b29"
    }
    assert evidence["source"]["accepted_source_blob_sha1"] == {
        "loguru/_datetime.py": "d9b132514a3ee358236a722a94fed4e4369bd2ff"
    }
    assert evidence["reference_pass_count"] == 3
    assert evidence["base_noop_rejection_count"] == 1
    assert evidence["known_bad_patch_rejection_count"] == 10
    assert evidence["semantic_bad_patch_rejection_count"] == 9
    assert evidence["independent_hidden_test_count"] == 11
    assert evidence["independent_hidden_test_function_count"] == 5
    assert evidence["benchmark_f2p_declared_count"] == 4
    assert evidence["benchmark_p2p_declared_count"] == 34
    assert evidence["upstream_regression_test_count"] == 43
    assert evidence["upstream_regression_collected_count"] == 43
    assert evidence["upstream_regression_deselected_count"] == 0
    assert evidence["official_run_count"] == 15
    assert evidence["equivalent_solution_pass_count"] == 1
    assert evidence["api_calls"] == 0
    assert evidence["model_cost_usd"] == 0
    assert evidence["runtime"]["working_directory"] == "/workspace"
    assert evidence["runtime"]["network"] == "none"
    assert evidence["runtime"]["root_filesystem"] == "read-only"
    assert evidence["runtime"]["workspace_mount"] == "read-only"

    cases = {case["name"]: case for case in evidence["cases"]}
    assert len(cases) == 15
    assert len({case["run_id"] for case in cases.values()}) == 15
    assert {case["run_id"] for case in cases.values()} == {
        "run_76b8e870024a49ec",
        "run_44fcae6e680445ed",
        "run_f3de06b5c7d24af7",
        "run_9c5e228c646442a3",
        "run_5643e3746f804cb7",
        "run_cc840d2e13634aa3",
        "run_cb02eb1400664bb8",
        "run_1d2ab550b6824215",
        "run_c6e7472411484011",
        "run_197650ce0f014d54",
        "run_40744cf912f047ce",
        "run_2b1157c21b434842",
        "run_18d9696bbefb454f",
        "run_9ca3c4bc27184551",
        "run_c3e433e0ac98456f",
    }
    assert all(case["official"] for case in cases.values())
    for case in cases.values():
        patch_path = LOGURU_TIMEZONE_TASK / case["patch"]
        assert sha256_bytes(patch_path.read_bytes()) == case["patch_sha256"]
        assert case["observed_success"] is case["expected_success"]
    assert all(cases[f"reference-{index}"]["observed_success"] for index in range(1, 4))
    assert {
        cases[f"reference-{index}"]["patch_sha256"] for index in range(1, 4)
    } == {package.private.reference_patch.sha256}
    assert cases["equivalent-utcfromtimestamp"]["observed_success"] is True
    assert cases["base-noop"]["failed_checks"] == [
        "hidden:local-timezone-fallback"
    ]
    assert cases["always-fallback"]["failed_checks"] == [
        "regression:upstream-datetime-regression",
        "hidden:local-timezone-fallback",
    ]
    for case_name in (
        "broad-localtime-exception",
        "clamp-invalid-offset",
        "fixed-derived-fallback",
        "reversed-fallback-offset",
        "unnamed-fallback-zone",
        "utc-on-invalid-offset",
        "wrong-localtime-exceptions",
        "wrong-timezone-exception",
    ):
        assert cases[case_name]["failed_checks"] == [
            "hidden:local-timezone-fallback"
        ]
    assert cases["forbidden-test-edit"]["failed_checks"] == [
        "hidden:local-timezone-fallback",
        "policy:scope",
        "policy:test_tampering",
    ]
    assert evidence["admission_checks"]["base_visible_checks"] == "pass"
    assert evidence["admission_checks"]["base_hidden_acceptance"] == "fail"
    for check_id in (
        "reference_scrr_three_repetitions",
        "known_bad_boundaries",
        "submitted_source_binding",
        "valid_platform_timezone_metadata_preserved",
        "invalid_positive_and_negative_offsets_fallback",
        "localtime_range_errors_fallback",
        "missing_timezone_fields_fallback",
        "derived_positive_negative_and_rollover_offsets",
        "derived_timezone_name_preserved",
        "local_wall_clock_and_microseconds_preserved",
        "unsupported_localtime_exception_propagates",
        "broad_exception_handler_rejected",
        "utcfromtimestamp_equivalent_solution",
        "exact_upstream_production_lineage",
        "benchmark_changelog_hunk_excluded",
        "benchmark_test_patch_excluded",
        "private_v2_hidden_artifact_bound",
        "visible_test_read_only",
        "hidden_oracle_read_only",
        "test_tampering_path_recognition",
        "same_repository_solution_lineage_is_distinct",
        "public_private_separation",
        "no_new_dependency",
        "public_api_unchanged",
        "network_disabled_evaluator",
        "read_only_root_filesystem",
        "read_only_submitted_workspace",
        "immutable_source_commit",
        "immutable_evaluator_image",
        "exact_sha_shallow_checkout",
    ):
        assert evidence["admission_checks"][check_id] == "pass"
