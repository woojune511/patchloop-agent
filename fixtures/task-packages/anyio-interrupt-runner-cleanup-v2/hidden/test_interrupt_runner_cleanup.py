from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


class InterruptRunnerCleanupTests(unittest.TestCase):
    def run_pytest_case(self, source: str) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        with tempfile.TemporaryDirectory(prefix="patchloop-anyio-") as temp:
            root = Path(temp)
            test_file = root / "test_case.py"
            marker = root / "lifecycle.log"
            test_file.write_text(textwrap.dedent(source), encoding="utf-8")
            env = os.environ.copy()
            env["PATCHLOOP_LIFECYCLE_MARKER"] = str(marker)
            env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "--no-header",
                    "-q",
                    "-s",
                    "-p",
                    "no:cacheprovider",
                    "-p",
                    "anyio.pytest_plugin",
                    str(test_file),
                ],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            markers = marker.read_text(encoding="utf-8").splitlines() if marker.exists() else []
            return completed, markers

    def test_interrupt_never_resumes_and_fixture_cleans_once(self) -> None:
        completed, markers = self.run_pytest_case(
            """
            import asyncio
            import os
            import signal
            from pathlib import Path

            import anyio
            import pytest

            MARKER = Path(os.environ["PATCHLOOP_LIFECYCLE_MARKER"])

            def mark(value: str) -> None:
                with MARKER.open("a", encoding="utf-8") as handle:
                    handle.write(value + "\\n")

            @pytest.fixture
            def anyio_backend():
                return "asyncio"

            @pytest.fixture
            async def lifecycle():
                mark("ENTER")
                try:
                    yield
                finally:
                    await anyio.sleep(0)
                    mark("CLEANUP")

            @pytest.mark.anyio
            async def test_interrupted(lifecycle):
                loop = asyncio.get_running_loop()
                loop.call_later(0.02, os.kill, os.getpid(), signal.SIGINT)
                await anyio.sleep(0.20)
                mark("RESUMED")
            """
        )

        diagnostic = f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        self.assertEqual(completed.returncode, 2, diagnostic)
        self.assertEqual(markers.count("ENTER"), 1, diagnostic)
        self.assertEqual(markers.count("CLEANUP"), 1, diagnostic)
        self.assertNotIn("RESUMED", markers, diagnostic)
        self.assertNotIn("Task was destroyed but it is pending", completed.stderr, diagnostic)

    def test_expected_outcome_preserves_shared_fixture_lifecycle(self) -> None:
        completed, markers = self.run_pytest_case(
            """
            import os
            from pathlib import Path

            import anyio
            import pytest

            MARKER = Path(os.environ["PATCHLOOP_LIFECYCLE_MARKER"])

            def mark(value: str) -> None:
                with MARKER.open("a", encoding="utf-8") as handle:
                    handle.write(value + "\\n")

            @pytest.fixture(scope="module")
            def anyio_backend():
                return "asyncio"

            @pytest.fixture(scope="module")
            async def shared_scope():
                with anyio.CancelScope():
                    mark("SCOPE_ENTER")
                    yield
                    await anyio.sleep(0)
                    mark("SCOPE_EXIT")

            @pytest.mark.anyio
            async def test_expected_skip(shared_scope):
                pytest.skip("expected outcome")

            @pytest.mark.anyio
            async def test_followup_uses_same_scope(shared_scope):
                mark("AFTER_SKIP")
            """
        )

        diagnostic = f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        self.assertEqual(completed.returncode, 0, diagnostic)
        self.assertEqual(markers, ["SCOPE_ENTER", "AFTER_SKIP", "SCOPE_EXIT"], diagnostic)
        self.assertIn("1 passed, 1 skipped", completed.stdout, diagnostic)
