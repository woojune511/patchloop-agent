from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from patchloop.task_loader import load_task_package
from patchloop.util import sha256_bytes

SUCCESSORS = (
    (
        Path("tasks/dev-train/pdm-ignore-active-venv-resolution"),
        Path("fixtures/task-packages/pdm-ignore-active-venv-resolution-v2"),
        "public-ignore-active-venv-resolution",
        "upstream-project-regression",
        (
            "PDM_IGNORE_ACTIVE_VENV",
            "VIRTUAL_ENV",
            "CONDA_PREFIX",
            "active/child",
            "active-sibling",
            "created",
        ),
    ),
    (
        Path("tasks/dev-train/anyio-interrupt-runner-cleanup"),
        Path("fixtures/task-packages/anyio-interrupt-runner-cleanup-v2"),
        "public-interrupt-runner-lifecycle",
        "upstream-pytest-plugin-regression",
        (
            "signal.raise_signal(signal.SIGINT)",
            "KeyboardInterrupt",
            "fixture-cleanup",
            "test-resumed",
            "following-test",
        ),
    ),
)

V3_SUCCESSORS = (
    (
        Path("fixtures/task-packages/pdm-ignore-active-venv-resolution-v2"),
        Path("fixtures/task-packages/pdm-ignore-active-venv-resolution-v3"),
        (
            "NoPythonVersion",
            "public behavior mismatch: interpreter resolution stopped",
            'expected="active-sibling"',
            "active/child",
        ),
    ),
    (
        Path("fixtures/task-packages/anyio-interrupt-runner-cleanup-v2"),
        Path("fixtures/task-packages/anyio-interrupt-runner-cleanup-v3"),
        (
            "subprocess.run",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
            "signal.raise_signal(signal.SIGINT)",
            "test-resumed",
            "fixture-cleanup",
            "pytest.skip",
            "pytest.xfail",
            "shared-cleanup",
        ),
    ),
)

V4_SUCCESSORS = (
    (
        Path("fixtures/task-packages/pdm-ignore-active-venv-resolution-v3"),
        Path("fixtures/task-packages/pdm-ignore-active-venv-resolution-v4"),
        (
            "PUBLIC_CASE:pdm:",
            'case_id="exact-active-sibling"',
            'candidates=("active", "active-sibling")',
            'case_id="create-fallback"',
        ),
        ("active/child",),
    ),
    (
        Path("fixtures/task-packages/anyio-interrupt-runner-cleanup-v3"),
        Path("fixtures/task-packages/anyio-interrupt-runner-cleanup-v4"),
        (
            "process.send_signal(signal.SIGINT)",
            "test-waiting",
            "await asyncio.sleep(2)",
            "PUBLIC_CASE:anyio:test-resumed",
            "PUBLIC_CASE:anyio:outcome-events",
        ),
        ("signal.raise_signal",),
    ),
)

V5_SUCCESSORS = (
    (
        Path("fixtures/task-packages/pdm-ignore-active-venv-resolution-v4"),
        Path("fixtures/task-packages/pdm-ignore-active-venv-resolution-v5"),
    ),
)

V6_SUCCESSORS = (
    (
        Path("fixtures/task-packages/pdm-ignore-active-venv-resolution-v5"),
        Path("fixtures/task-packages/pdm-ignore-active-venv-resolution-v6"),
    ),
)


def _opaque_file_hashes(root: Path, pattern: str) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256_bytes(path.read_bytes())
        for path in sorted(root.glob(pattern))
        if path.is_file()
    }


@pytest.mark.parametrize(
    ("predecessor_path", "successor_path", "targeted_check_id", "regression_check_id", "markers"),
    SUCCESSORS,
)
def test_public_behavior_successor_is_versioned_and_publicly_checkable(
    predecessor_path: Path,
    successor_path: Path,
    targeted_check_id: str,
    regression_check_id: str,
    markers: tuple[str, ...],
) -> None:
    predecessor = load_task_package(predecessor_path)
    successor = load_task_package(successor_path)

    assert predecessor.public.task_version == predecessor.private.task_version == 1
    assert successor.public.task_version == successor.private.task_version == 2
    assert successor.public.task_id == predecessor.public.task_id
    assert successor.private.task_id == predecessor.private.task_id
    assert successor.public.repository == predecessor.public.repository
    assert successor.environment == predecessor.environment
    assert successor.private.reference_patch.sha256 == predecessor.private.reference_patch.sha256
    assert [check.id for check in successor.public.visible_checks] == [
        targeted_check_id,
        regression_check_id,
    ]
    assert successor.public.visible_checks[1] == predecessor.public.visible_checks[0]

    source = successor.public.visible_checks[0].command[-1]
    compile(source, f"<{targeted_check_id}>", "exec")
    assert all(marker in source for marker in markers)
    assert ".patchloop-hidden" not in source
    assert "reference.patch" not in source

    assert (successor_path / "environment.yaml").read_bytes() == (
        predecessor_path / "environment.yaml"
    ).read_bytes()
    assert (successor_path / "reference.patch").read_bytes() == (
        predecessor_path / "reference.patch"
    ).read_bytes()
    assert _opaque_file_hashes(successor_path, "hidden/**/*") == _opaque_file_hashes(
        predecessor_path,
        "hidden/**/*",
    )


def test_public_behavior_successors_are_not_admitted_to_the_frozen_dataset() -> None:
    manifest = yaml.safe_load(Path("data/dataset-manifest.yaml").read_text(encoding="utf-8"))
    admitted = {(item["task_id"], item["task_version"], item["path"]) for item in manifest["tasks"]}

    for _, successor_path, _, _, _ in SUCCESSORS:
        successor = load_task_package(successor_path)
        assert (
            successor.public.task_id,
            successor.public.task_version,
            successor_path.as_posix(),
        ) not in admitted
        assert not list(Path("tasks").glob(f"**/{successor_path.name}/public.yaml"))


@pytest.mark.parametrize(("predecessor_path", "successor_path", "markers"), V3_SUCCESSORS)
def test_v3_public_behavior_successor_preserves_opaque_evaluator_bytes(
    predecessor_path: Path,
    successor_path: Path,
    markers: tuple[str, ...],
) -> None:
    predecessor = load_task_package(predecessor_path)
    successor = load_task_package(successor_path)

    assert predecessor.public.task_version == predecessor.private.task_version == 2
    assert successor.public.task_version == successor.private.task_version == 3
    assert successor.public.task_id == predecessor.public.task_id
    assert successor.private.task_id == predecessor.private.task_id
    assert successor.public.repository == predecessor.public.repository
    assert successor.environment == predecessor.environment
    assert successor.private.reference_patch.sha256 == predecessor.private.reference_patch.sha256
    assert successor.public.visible_checks[1] == predecessor.public.visible_checks[1]

    source = successor.public.visible_checks[0].command[-1]
    compile(source, f"<{successor.public.visible_checks[0].id}-v3>", "exec")
    assert all(marker in source for marker in markers)
    assert ".patchloop-hidden" not in source
    assert "reference.patch" not in source
    assert "hidden:" not in source

    assert (successor_path / "environment.yaml").read_bytes() == (
        predecessor_path / "environment.yaml"
    ).read_bytes()
    assert (successor_path / "reference.patch").read_bytes() == (
        predecessor_path / "reference.patch"
    ).read_bytes()
    assert _opaque_file_hashes(successor_path, "hidden/**/*") == _opaque_file_hashes(
        predecessor_path,
        "hidden/**/*",
    )


def test_v3_public_behavior_successors_are_not_admitted() -> None:
    manifest = yaml.safe_load(Path("data/dataset-manifest.yaml").read_text(encoding="utf-8"))
    admitted = {(item["task_id"], item["task_version"], item["path"]) for item in manifest["tasks"]}

    for _, successor_path, _ in V3_SUCCESSORS:
        successor = load_task_package(successor_path)
        assert (
            successor.public.task_id,
            successor.public.task_version,
            successor_path.as_posix(),
        ) not in admitted


@pytest.mark.parametrize(
    ("predecessor_path", "successor_path", "markers", "forbidden_markers"), V4_SUCCESSORS
)
def test_v4_public_behavior_successor_is_public_only_and_opaque_bytes_are_stable(
    predecessor_path: Path,
    successor_path: Path,
    markers: tuple[str, ...],
    forbidden_markers: tuple[str, ...],
) -> None:
    predecessor = load_task_package(predecessor_path)
    successor = load_task_package(successor_path)

    assert predecessor.public.task_version == predecessor.private.task_version == 3
    assert successor.public.task_version == successor.private.task_version == 4
    assert successor.public.task_id == predecessor.public.task_id
    assert successor.private.task_id == predecessor.private.task_id
    assert successor.public.repository == predecessor.public.repository
    assert successor.environment == predecessor.environment
    assert successor.private.reference_patch.sha256 == predecessor.private.reference_patch.sha256
    assert successor.public.visible_checks[1] == predecessor.public.visible_checks[1]

    source = successor.public.visible_checks[0].command[-1]
    compile(source, f"<{successor.public.visible_checks[0].id}-v4>", "exec")
    assert all(marker in source for marker in markers)
    assert all(marker not in source for marker in forbidden_markers)
    assert ".patchloop-hidden" not in source
    assert "reference.patch" not in source
    assert "hidden:" not in source

    assert (successor_path / "environment.yaml").read_bytes() == (
        predecessor_path / "environment.yaml"
    ).read_bytes()
    assert (successor_path / "reference.patch").read_bytes() == (
        predecessor_path / "reference.patch"
    ).read_bytes()
    assert _opaque_file_hashes(successor_path, "hidden/**/*") == _opaque_file_hashes(
        predecessor_path,
        "hidden/**/*",
    )


def test_v4_public_behavior_successors_are_not_admitted() -> None:
    manifest = yaml.safe_load(Path("data/dataset-manifest.yaml").read_text(encoding="utf-8"))
    admitted = {(item["task_id"], item["task_version"], item["path"]) for item in manifest["tasks"]}

    for _, successor_path, _, _ in V4_SUCCESSORS:
        successor = load_task_package(successor_path)
        assert (
            successor.public.task_id,
            successor.public.task_version,
            successor_path.as_posix(),
        ) not in admitted


@pytest.mark.parametrize(("predecessor_path", "successor_path"), V5_SUCCESSORS)
def test_v5_pdm_successor_removes_only_publicly_unsupported_off_case(
    predecessor_path: Path,
    successor_path: Path,
) -> None:
    predecessor = load_task_package(predecessor_path)
    successor = load_task_package(successor_path)

    assert predecessor.public.task_version == predecessor.private.task_version == 4
    assert successor.public.task_version == successor.private.task_version == 5
    assert successor.public.task_id == predecessor.public.task_id
    assert successor.public.repository == predecessor.public.repository
    assert successor.environment == predecessor.environment
    assert successor.private.reference_patch.sha256 == predecessor.private.reference_patch.sha256
    assert successor.public.visible_checks[1] == predecessor.public.visible_checks[1]

    before = predecessor.public.visible_checks[0].command[-1]
    after = successor.public.visible_checks[0].command[-1]
    compile(after, "<public-ignore-active-venv-resolution-v5>", "exec")
    assert before.replace('    ("false-off", "off"),\n', "") == after
    assert '"false-off"' not in after
    assert '"off"' not in after
    assert '"false-zero"' in after
    assert '"false-false"' in after
    assert '"false-no"' in after

    assert (successor_path / "environment.yaml").read_bytes() == (
        predecessor_path / "environment.yaml"
    ).read_bytes()
    assert (successor_path / "reference.patch").read_bytes() == (
        predecessor_path / "reference.patch"
    ).read_bytes()
    assert _opaque_file_hashes(successor_path, "hidden/**/*") == _opaque_file_hashes(
        predecessor_path,
        "hidden/**/*",
    )


def test_v5_pdm_successor_is_not_admitted() -> None:
    manifest = yaml.safe_load(Path("data/dataset-manifest.yaml").read_text(encoding="utf-8"))
    admitted = {(item["task_id"], item["task_version"], item["path"]) for item in manifest["tasks"]}
    successor_path = V5_SUCCESSORS[0][1]
    successor = load_task_package(successor_path)

    assert (
        successor.public.task_id,
        successor.public.task_version,
        successor_path.as_posix(),
    ) not in admitted


@pytest.mark.parametrize(("predecessor_path", "successor_path"), V6_SUCCESSORS)
def test_v6_pdm_successor_represents_conda_with_virtual_env_absent(
    predecessor_path: Path,
    successor_path: Path,
) -> None:
    predecessor = load_task_package(predecessor_path)
    successor = load_task_package(successor_path)

    assert predecessor.public.task_version == predecessor.private.task_version == 5
    assert successor.public.task_version == successor.private.task_version == 6
    assert successor.public.task_id == predecessor.public.task_id
    assert successor.public.issue == predecessor.public.issue
    assert successor.public.constraints == predecessor.public.constraints
    assert successor.public.repository == predecessor.public.repository
    assert successor.environment == predecessor.environment
    assert successor.private.reference_patch.sha256 == predecessor.private.reference_patch.sha256
    assert successor.public.visible_checks[1] == predecessor.public.visible_checks[1]

    before = predecessor.public.visible_checks[0].command[-1]
    after = successor.public.visible_checks[0].command[-1]
    compile(after, "<public-ignore-active-venv-resolution-v6>", "exec")
    old_case = '''    case_id="conda-false-zero",
    ignore="0",
    virtual_env="",
    conda_prefix="conda",'''
    new_case = '''    case_id="conda-false-zero",
    ignore="0",
    virtual_env=None,
    conda_prefix="conda",'''
    assert old_case in before
    assert before.replace(old_case, new_case) == after
    assert new_case in after

    assert (successor_path / "environment.yaml").read_bytes() == (
        predecessor_path / "environment.yaml"
    ).read_bytes()
    assert (successor_path / "reference.patch").read_bytes() == (
        predecessor_path / "reference.patch"
    ).read_bytes()
    assert _opaque_file_hashes(successor_path, "hidden/**/*") == _opaque_file_hashes(
        predecessor_path,
        "hidden/**/*",
    )


def test_v6_pdm_successor_is_not_admitted() -> None:
    manifest = yaml.safe_load(Path("data/dataset-manifest.yaml").read_text(encoding="utf-8"))
    admitted = {(item["task_id"], item["task_version"], item["path"]) for item in manifest["tasks"]}
    successor_path = V6_SUCCESSORS[0][1]
    successor = load_task_package(successor_path)

    assert (
        successor.public.task_id,
        successor.public.task_version,
        successor_path.as_posix(),
    ) not in admitted
