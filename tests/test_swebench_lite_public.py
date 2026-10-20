import os
import subprocess
import sys
from pathlib import Path

import pytest

from diagnostics.swebench_lite_packages import PUBLIC_RUNNER
from patchloop.runtime import repository_root
from patchloop.task_loader import load_public_task


def sqlfluff_runner():
    public = load_public_task(
        repository_root() / "tasks/dev-train/swebench-lite-dev-sqlfluff-sqlfluff-1625/public.yaml"
    )
    return public.visible_checks[0].command[3]


@pytest.mark.parametrize("sqlfluff", [False, True])
def test_public_launcher_uses_current_source_and_preserves_failure(tmp_path, sqlfluff):
    (tmp_path / "tests").mkdir()
    (tmp_path / "checks").mkdir()
    (tmp_path / ".patchloop-hidden").mkdir()
    (tmp_path / ".patchloop-hidden" / "secret.py").write_text("raise AssertionError")
    source = tmp_path / "sample.py"
    source.write_text("VALUE = True\n")
    (tmp_path / "tests" / "test_sample.py").write_text(
        "from sample import VALUE\ndef test_value():\n    assert VALUE\n"
    )
    (tmp_path / "checks" / "test_boundary.py").write_text(
        "import os\nfrom pathlib import Path\ndef test_boundary():\n"
        "    assert not Path('.patchloop-hidden').exists()\n"
        "    (Path(os.environ['HOME']) / 'cache').write_text('temporary')\n"
    )
    if sqlfluff:
        # A local installer double keeps this test independent of host pip/build
        # dependencies. The real offline plugin install is covered by Docker controls.
        (tmp_path / "pip.py").write_text(
            "import sys\nfrom pathlib import Path\n"
            "target = Path(sys.argv[sys.argv.index('--target') + 1])\n"
            "target.mkdir()\n"
            "(target / 'sample.py').write_text('VALUE = False\\n')\n"
            "(target / 'example_probe.py').write_text('AVAILABLE = True\\n')\n"
        )
        (tmp_path / "checks" / "test_plugin.py").write_text(
            "from pathlib import Path\nimport example_probe\n"
            "def test_temporary_plugin():\n"
            "    assert example_probe.AVAILABLE\n"
            "    assert Path(example_probe.__file__).parent.parent == Path.cwd().parent\n"
        )
    before = {str(p.relative_to(tmp_path)): p.read_bytes()
              for p in tmp_path.rglob('*') if p.is_file()}

    def run():
        return subprocess.run(
            [sys.executable, "-B", "-c", sqlfluff_runner() if sqlfluff else PUBLIC_RUNNER,
             "tests", "checks"],
            cwd=tmp_path, capture_output=True, text=True, timeout=30,
            env={**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
        )

    healthy = run()
    assert healthy.returncode == 0, healthy.stdout + healthy.stderr
    assert f"{3 if sqlfluff else 2} passed" in healthy.stdout
    after = {str(p.relative_to(tmp_path)): p.read_bytes()
             for p in tmp_path.rglob('*') if p.is_file()}
    assert before == after
    source.write_text("VALUE = False\n")
    broken = run()
    assert broken.returncode == 1
    assert f"1 failed, {2 if sqlfluff else 1} passed" in broken.stdout


def test_sqlfluff_failed_setup_stops_before_pytest_and_cleans_temporary_files(tmp_path):
    (tmp_path / "pip.py").write_text(
        "import sys\nfrom pathlib import Path\n"
        "print(Path.cwd(), flush=True)\nraise SystemExit(7)\n"
    )
    (tmp_path / "pytest.py").write_text("print('PYTEST_MUST_NOT_RUN')\n")
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    result = subprocess.run(
        [sys.executable, "-B", "-c", sqlfluff_runner(), "test"],
        cwd=tmp_path, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 2
    assert "PYTEST_MUST_NOT_RUN" not in result.stdout
    assert not Path(result.stdout.strip()).exists()
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}
