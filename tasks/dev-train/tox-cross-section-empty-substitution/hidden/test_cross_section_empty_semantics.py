from __future__ import annotations

import configparser
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


class CrossSectionEmptySemanticsTests(unittest.TestCase):
    def config_values(
        self,
        ini: str,
        environments: list[str],
        key: str = "description",
    ) -> dict[str, str]:
        with tempfile.TemporaryDirectory(prefix="patchloop-tox-") as temp:
            root = Path(temp)
            (root / "tox.ini").write_text(textwrap.dedent(ini), encoding="utf-8")
            env = os.environ.copy()
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            repository_src = str(Path.cwd() / "src")
            inherited_pythonpath = env.get("PYTHONPATH")
            env["PYTHONPATH"] = (
                repository_src
                if not inherited_pythonpath
                else os.pathsep.join((repository_src, inherited_pythonpath))
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "tox",
                    "config",
                    "-e",
                    ",".join(environments),
                    "-k",
                    key,
                ],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            self.assertEqual(
                completed.returncode,
                0,
                msg=f"tox config failed\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
            )
            parser = configparser.ConfigParser(interpolation=None)
            parser.read_string(completed.stdout)
            return {
                environment: parser.get(f"testenv:{environment}", key)
                for environment in environments
            }

    def test_unmatched_cross_section_value_disappears_but_matching_value_remains(self) -> None:
        values = self.config_values(
            """
            [tox]
            env_list = plain, plain-sqlite
            no_package = true

            [selectors]
            backend =
                sqlite: sqlite-driver

            [testenv]
            description = before {[selectors]backend} after
            """,
            ["plain", "plain-sqlite"],
        )

        self.assertNotIn("{[selectors]backend}", values["plain"])
        self.assertNotIn("sqlite-driver", values["plain"])
        self.assertIn("sqlite-driver", values["plain-sqlite"])

    def test_existing_filtered_value_does_not_trigger_replacement_default(self) -> None:
        values = self.config_values(
            """
            [tox]
            env_list = plain
            no_package = true

            [selectors]
            backend =
                sqlite: sqlite-driver

            [testenv]
            description = {[selectors]backend:fallback-must-not-apply}
            """,
            ["plain"],
        )

        self.assertEqual(values["plain"], "")

    def test_genuinely_missing_key_still_uses_replacement_default(self) -> None:
        values = self.config_values(
            """
            [tox]
            env_list = plain
            no_package = true

            [selectors]
            present = value

            [testenv]
            description = {[selectors]missing:fallback-driver}
            """,
            ["plain"],
        )

        self.assertEqual(values["plain"], "fallback-driver")

    def test_multiple_cross_section_references_filter_independently(self) -> None:
        values = self.config_values(
            """
            [tox]
            env_list = plain, plain-sqlite, plain-hash
            no_package = true

            [selectors]
            backend =
                sqlite: sqlite-driver
            storage =
                hash: hash-driver

            [testenv]
            description = {[selectors]backend}|{[selectors]storage}
            """,
            ["plain", "plain-sqlite", "plain-hash"],
        )

        self.assertEqual(values["plain"], "|")
        self.assertEqual(values["plain-sqlite"], "sqlite-driver|")
        self.assertEqual(values["plain-hash"], "|hash-driver")

    def test_reference_uses_the_requesting_environment_factors(self) -> None:
        values = self.config_values(
            """
            [tox]
            env_list = alpha, beta
            no_package = true

            [shared]
            marker =
                alpha: selected-alpha
                beta: selected-beta

            [testenv]
            description = {[shared]marker}
            """,
            ["alpha", "beta"],
        )

        self.assertEqual(values["alpha"], "selected-alpha")
        self.assertEqual(values["beta"], "selected-beta")

    def test_same_section_filtered_value_keeps_computed_fallback(self) -> None:
        py_version = f"{sys.version_info[0]}.{sys.version_info[1]}"
        env_a = f"py{py_version}-a"
        env_b = f"py{py_version}-b"
        values = self.config_values(
            f"""
            [tox]
            env_list = {env_a}, {env_b}
            no_package = true

            [testenv]
            base_python =
                a: python{py_version}
            """,
            [env_a, env_b],
            key="base_python",
        )

        self.assertEqual(values[env_a], f"python{py_version}")
        self.assertEqual(values[env_b], f"py{py_version}")


if __name__ == "__main__":
    unittest.main()
