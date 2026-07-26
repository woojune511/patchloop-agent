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
HF_HUB_TASK = Path("tasks/dev-train/hf-hub-xet-endpoint-propagation")
PDM_TASK = Path("tasks/dev-train/pdm-ignore-active-venv-resolution")
PYFAKEFS_TASK = Path("tasks/dev-train/pyfakefs-makedirs-parent-traversal")
MOTO_TASK = Path("tasks/dev-validation/moto-query-scanned-count")
BABEL_TASK = Path("tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes")
SQLGLOT_TASK = Path(
    "tasks/cross-repo-heldout/sqlglot-duckdb-ignore-nulls-modifier-order"
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
    assert candidate["changed_files"] == "3"
    assert candidate["f2p"] == "1"
    assert candidate["p2p"] == "38"
    assert candidate["proposed_lane"] == "core-cross-repo"
    assert candidate["status"] == "screening"


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
