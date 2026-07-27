from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from pdm.core import Core

WORKSPACE_SOURCE = Path("/workspace/src")


class TargetProjectOptionsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.caller = self.write_project(
            "caller",
            {
                "install": ["--no-editable"],
                "sync": ["--no-editable"],
            },
        )
        self.original_cwd = Path.cwd()
        os.chdir(self.caller)
        self.addCleanup(os.chdir, self.original_cwd)

    def write_project(self, name: str, options: dict[str, list[str]]) -> Path:
        root = self.root / name
        root.mkdir()
        option_lines = [
            f"{command} = {json.dumps(arguments)}"
            for command, arguments in sorted(options.items())
        ]
        root.joinpath("pyproject.toml").write_text(
            "\n".join(
                [
                    "[project]",
                    f'name = "{name}"',
                    'version = "0.1.0"',
                    "",
                    "[tool.pdm.options]",
                    *option_lines,
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return root

    def invoke(
        self,
        args: list[str],
        *,
        obj_root: Path | None = None,
        environment: dict[str, str] | None = None,
    ):
        home = self.root / "home"
        home.mkdir(exist_ok=True)
        run_environment = {
            "HOME": str(home),
            "PDM_HOME": str(self.root / "pdm-home"),
            "PDM_CHECK_UPDATE": "0",
            "XDG_CACHE_HOME": str(self.root / "xdg-cache"),
            "XDG_CONFIG_HOME": str(self.root / "xdg-config"),
            "XDG_DATA_HOME": str(self.root / "xdg-data"),
            "PATH": os.environ.get("PATH", ""),
        }
        run_environment.update(environment or {})
        with (
            patch.dict(os.environ, run_environment, clear=True),
            patch("pdm.core.is_in_zipapp", return_value=True),
        ):
            core = Core()
            selected_obj = core.create_project(obj_root) if obj_root is not None else None
            handle = Mock(name="handle")
            core.handle = handle
            core.main(list(args), obj=selected_obj)

        self.assertEqual(handle.call_count, 1)
        project, options = handle.call_args.args
        return project, options

    def assert_selected(
        self,
        args: list[str],
        expected_root: Path,
        *,
        expected_true: tuple[str, ...],
        expected_false: tuple[str, ...],
        obj_root: Path | None = None,
        environment: dict[str, str] | None = None,
    ) -> None:
        project, options = self.invoke(
            args,
            obj_root=obj_root,
            environment=environment,
        )
        self.assertEqual(project.root.resolve(), expected_root.resolve())
        for name in expected_true:
            self.assertTrue(getattr(options, name), msg=f"{name} was not enabled for {args}")
        for name in expected_false:
            self.assertFalse(getattr(options, name), msg=f"{name} leaked into {args}")

    def test_submitted_source_is_imported(self) -> None:
        imported = Path(inspect.getsourcefile(Core.main) or "").resolve()
        self.assertTrue(
            imported.is_relative_to(WORKSPACE_SOURCE),
            msg=f"production code was imported from {imported}, not {WORKSPACE_SOURCE}",
        )

    def test_short_separated_project_uses_target_options(self) -> None:
        target = self.write_project("short-target", {"install": ["--no-self"]})
        self.assert_selected(
            ["install", "-p", str(target)],
            target,
            expected_true=("no_self",),
            expected_false=("no_editable",),
        )

    def test_long_project_forms_use_target_options(self) -> None:
        target = self.write_project("long-target", {"install": ["--no-self"]})
        for project_args in (
            ["--project", str(target)],
            [f"--project={target}"],
        ):
            with self.subTest(project_args=project_args):
                self.assert_selected(
                    ["install", *project_args],
                    target,
                    expected_true=("no_self",),
                    expected_false=("no_editable",),
                )

    def test_attached_short_project_forms_use_target_options(self) -> None:
        target = self.write_project("attached-target", {"install": ["--no-self"]})
        for project_arg in (f"-p{target}", f"-p={target}"):
            with self.subTest(project_arg=project_arg):
                self.assert_selected(
                    ["install", project_arg],
                    target,
                    expected_true=("no_self",),
                    expected_false=("no_editable",),
                )

    def test_repeated_project_options_use_the_last_target(self) -> None:
        first = self.write_project("first-target", {"install": ["--no-editable"]})
        second = self.write_project("second-target", {"install": ["--no-self"]})
        self.assert_selected(
            ["install", "-p", str(first), f"--project={second}"],
            second,
            expected_true=("no_self",),
            expected_false=("no_editable",),
        )

    def test_environment_selected_project_supplies_options(self) -> None:
        target = self.write_project("environment-target", {"install": ["--no-self"]})
        environment = os.environ.copy()
        environment.update(
            HOME=str(self.root / "home"),
            PDM_HOME=str(self.root / "pdm-home"),
            PDM_CHECK_UPDATE="0",
            PDM_PROJECT=str(target),
            PYTHONPATH="/workspace/src",
        )
        script = """
import json
from unittest.mock import Mock, patch
from pdm.core import Core

core = Core()
handle = Mock(name="handle")
core.handle = handle
with patch("pdm.core.is_in_zipapp", return_value=True):
    core.main(["install"])
project, options = handle.call_args.args
print("__PATCHLOOP__" + json.dumps({
    "root": str(project.root.resolve()),
    "no_self": options.no_self,
    "no_editable": options.no_editable,
}))
"""
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=self.caller,
            env=environment,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        payload_line = next(
            line for line in completed.stdout.splitlines() if line.startswith("__PATCHLOOP__")
        )
        payload = json.loads(payload_line.removeprefix("__PATCHLOOP__"))
        self.assertEqual(Path(payload["root"]), target.resolve())
        self.assertTrue(payload["no_self"])
        self.assertFalse(payload["no_editable"])

    def test_explicit_project_object_has_precedence(self) -> None:
        supplied = self.write_project("supplied-object", {"install": ["--no-self"]})
        other = self.write_project("ignored-cli-target", {"install": ["--no-editable"]})
        self.assert_selected(
            ["install", "--project", str(other)],
            supplied,
            expected_true=("no_self",),
            expected_false=("no_editable",),
            obj_root=supplied,
        )

    def test_global_project_does_not_inherit_caller_options(self) -> None:
        project, options = self.invoke(["install", "--global"])
        self.assertTrue(project.is_global)
        self.assertFalse(options.no_editable)
        self.assertFalse(options.no_self)

    def test_non_install_command_uses_the_same_target_policy(self) -> None:
        target = self.write_project("sync-target", {"sync": ["--no-self"]})
        self.assert_selected(
            ["sync", "-p", str(target)],
            target,
            expected_true=("no_self",),
            expected_false=("no_editable",),
        )

    def test_target_without_command_options_does_not_fall_back_to_caller(self) -> None:
        target = self.write_project("empty-target", {"sync": ["--no-self"]})
        self.assert_selected(
            ["install", "--project", str(target)],
            target,
            expected_true=(),
            expected_false=("no_self", "no_editable"),
        )

    def test_invocation_without_project_preserves_caller_options(self) -> None:
        self.assert_selected(
            ["install"],
            self.caller,
            expected_true=("no_editable",),
            expected_false=("no_self",),
        )


if __name__ == "__main__":
    unittest.main()
