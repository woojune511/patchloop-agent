from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _run_fresh_interpreter(source: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", source],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_package_imports_do_not_eagerly_load_runner_or_evaluator() -> None:
    completed = _run_fresh_interpreter(
        """
import sys

import patchloop.dev
import patchloop.verifier

unexpected = {
    "patchloop.dev.runner",
    "patchloop.verifier.core",
}.intersection(sys.modules)
assert not unexpected, sorted(unexpected)
"""
    )

    assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize(
    ("first_import", "second_import"),
    [
        (
            "from patchloop.verifier.policy import verify_scope",
            "from patchloop.dev.contracts import dev_tool_surface_hash",
        ),
        (
            "from patchloop.dev.contracts import dev_tool_surface_hash",
            "from patchloop.verifier.policy import verify_scope",
        ),
    ],
)
def test_dev_and_verifier_import_orders_work_in_fresh_interpreter(
    first_import: str,
    second_import: str,
) -> None:
    completed = _run_fresh_interpreter(
        "\n".join(
            (
                first_import,
                second_import,
                "from patchloop.dev import run_dev",
                "from patchloop.verifier import EvaluationEngine",
                "assert callable(run_dev)",
                "assert EvaluationEngine.__name__ == 'EvaluationEngine'",
            )
        )
    )

    assert completed.returncode == 0, completed.stderr
