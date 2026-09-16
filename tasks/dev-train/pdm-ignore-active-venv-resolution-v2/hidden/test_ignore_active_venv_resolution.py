from __future__ import annotations

import inspect
import os
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from packaging.version import Version
from pdm.project.core import Project

WORKSPACE_SOURCE = Path("/workspace/src")


@dataclass(frozen=True)
class FakePython:
    path: Path
    executable: Path
    version: Version = Version("3.11.8")
    valid: bool = True


@dataclass(frozen=True)
class FakeVenv:
    root: Path
    interpreter: Path


class IgnoreActiveVenvResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.temp_root = Path(self.temp_dir.name)
        self.project_index = 0
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def make_python(self, path: Path) -> FakePython:
        return FakePython(path=path, executable=path)

    def make_project(
        self,
        *,
        use_venv: bool = True,
        created_root: Path | None = None,
        system_pythons: tuple[FakePython, ...] = (),
    ) -> Project:
        project = object.__new__(Project)
        self.project_index += 1
        project.root = self.temp_root / f"project-{self.project_index}"
        project.root.mkdir(parents=True)
        project.is_global = False
        project.core = SimpleNamespace(
            ui=SimpleNamespace(
                info=Mock(),
                warn=Mock(),
            )
        )
        project._python = None
        project.__dict__["config"] = {"python.use_venv": use_venv}
        project.__dict__["pyproject"] = SimpleNamespace(metadata={"requires-python": ">=3.10"})
        project._create_virtualenv = Mock(return_value=created_root or (project.root / ".created"))
        project.iter_interpreters = Mock(return_value=iter(system_pythons))
        return project

    def resolve(
        self,
        project: Project,
        *,
        known_pythons: tuple[FakePython, ...],
        managed_venvs: tuple[FakeVenv, ...] = (),
    ) -> FakePython:
        by_path = {python.path: python for python in known_pythons}

        def from_path(path: str | Path) -> FakePython:
            normalized = Path(path)
            if normalized not in by_path:
                raise AssertionError(f"unexpected interpreter lookup: {normalized}")
            return by_path[normalized]

        def get_venv_python(root: str | Path) -> Path:
            return Path(root) / "bin" / "python"

        discovered = tuple((f"managed-{index}", venv) for index, venv in enumerate(managed_venvs))
        with (
            patch(
                "pdm.cli.commands.venv.utils.iter_venvs",
                return_value=iter(discovered),
            ),
            patch(
                "pdm.models.venv.get_venv_python",
                side_effect=get_venv_python,
            ),
            patch(
                "pdm.project.core.PythonInfo.from_path",
                side_effect=from_path,
            ),
            patch("pdm.project.core.is_conda_base", return_value=False),
        ):
            return project.resolve_interpreter()

    def test_submitted_source_is_imported(self) -> None:
        imported = Path(inspect.getsourcefile(Project.resolve_interpreter) or "").resolve()
        self.assertTrue(
            imported.is_relative_to(WORKSPACE_SOURCE),
            msg=f"production code was imported from {imported}, not {WORKSPACE_SOURCE}",
        )

    def test_truthy_flag_skips_active_and_selects_other_managed_venv(self) -> None:
        active_root = self.temp_root / "active"
        other_root = self.temp_root / "managed"
        active = self.make_python(active_root / "bin" / "python")
        other = self.make_python(other_root / "bin" / "python")
        project = self.make_project()
        os.environ.update(
            PDM_IGNORE_ACTIVE_VENV="1",
            VIRTUAL_ENV=str(active_root),
        )

        selected = self.resolve(
            project,
            known_pythons=(active, other),
            managed_venvs=(
                FakeVenv(active_root, active.path),
                FakeVenv(other_root, other.path),
            ),
        )

        self.assertIs(selected, other)
        project._create_virtualenv.assert_not_called()

    def test_truthy_flag_creates_when_only_active_candidate_exists(self) -> None:
        active_root = self.temp_root / "active-only"
        created_root = self.temp_root / "created"
        active = self.make_python(active_root / "bin" / "python")
        created = self.make_python(created_root / "bin" / "python")
        project = self.make_project(created_root=created_root)
        os.environ.update(
            PDM_IGNORE_ACTIVE_VENV="true",
            VIRTUAL_ENV=str(active_root),
        )

        selected = self.resolve(
            project,
            known_pythons=(active, created),
            managed_venvs=(FakeVenv(active_root, active.path),),
        )

        self.assertIs(selected, created)
        project._create_virtualenv.assert_called_once_with()

    def test_false_like_values_keep_active_environment_reuse(self) -> None:
        for value in ("0", "false", "False", "no", "NO"):
            with self.subTest(value=value):
                active_root = self.temp_root / f"active-{value.lower()}"
                active = self.make_python(active_root / "bin" / "python")
                project = self.make_project()
                os.environ.update(
                    PDM_IGNORE_ACTIVE_VENV=value,
                    VIRTUAL_ENV=str(active_root),
                )

                selected = self.resolve(
                    project,
                    known_pythons=(active,),
                )

                self.assertIs(selected, active)
                project._create_virtualenv.assert_not_called()

    def test_conda_prefix_marks_only_that_environment_active(self) -> None:
        active_root = self.temp_root / "conda-active"
        other_root = self.temp_root / "conda-other"
        active = self.make_python(active_root / "bin" / "python")
        other = self.make_python(other_root / "bin" / "python")
        project = self.make_project()
        os.environ.update(
            PDM_IGNORE_ACTIVE_VENV="yes",
            CONDA_PREFIX=str(active_root),
        )

        selected = self.resolve(
            project,
            known_pythons=(active, other),
            managed_venvs=(
                FakeVenv(active_root, active.path),
                FakeVenv(other_root, other.path),
            ),
        )

        self.assertIs(selected, other)

    def test_sibling_path_is_not_treated_as_active_descendant(self) -> None:
        active_root = self.temp_root / "env"
        sibling_root = self.temp_root / "env-tools"
        sibling = self.make_python(sibling_root / "bin" / "python")
        project = self.make_project()
        os.environ.update(
            PDM_IGNORE_ACTIVE_VENV="1",
            VIRTUAL_ENV=str(active_root),
        )

        selected = self.resolve(
            project,
            known_pythons=(sibling,),
            managed_venvs=(FakeVenv(sibling_root, sibling.path),),
        )

        self.assertIs(selected, sibling)
        project._create_virtualenv.assert_not_called()

    def test_ignore_flag_without_active_prefix_keeps_managed_candidate(self) -> None:
        managed_root = self.temp_root / "managed-no-prefix"
        managed = self.make_python(managed_root / "bin" / "python")
        project = self.make_project()
        os.environ["PDM_IGNORE_ACTIVE_VENV"] = "1"

        selected = self.resolve(
            project,
            known_pythons=(managed,),
            managed_venvs=(FakeVenv(managed_root, managed.path),),
        )

        self.assertIs(selected, managed)
        project._create_virtualenv.assert_not_called()

    def test_unset_flag_preserves_direct_active_environment_reuse(self) -> None:
        active_root = self.temp_root / "active-default"
        active = self.make_python(active_root / "bin" / "python")
        project = self.make_project()
        os.environ["VIRTUAL_ENV"] = str(active_root)

        selected = self.resolve(
            project,
            known_pythons=(active,),
        )

        self.assertIs(selected, active)

    def test_saved_interpreter_still_has_precedence(self) -> None:
        saved = self.make_python(self.temp_root / "saved" / "bin" / "python")
        active_root = self.temp_root / "active-after-saved"
        project = self.make_project()
        project.root.joinpath(".pdm-python").write_text(str(saved.path), encoding="utf-8")
        os.environ.update(
            PDM_IGNORE_ACTIVE_VENV="1",
            VIRTUAL_ENV=str(active_root),
        )

        selected = self.resolve(
            project,
            known_pythons=(saved,),
        )

        self.assertIs(selected, saved)

    def test_non_venv_mode_keeps_system_interpreter_fallback(self) -> None:
        system = self.make_python(self.temp_root / "system" / "bin" / "python")
        project = self.make_project(
            use_venv=False,
            system_pythons=(system,),
        )
        os.environ["PDM_IGNORE_ACTIVE_VENV"] = "1"

        selected = self.resolve(
            project,
            known_pythons=(system,),
        )

        self.assertIs(selected, system)


if __name__ == "__main__":
    unittest.main()
