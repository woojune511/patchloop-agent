import os
import subprocess
import sys

from diagnostics.swebench_lite_packages import PUBLIC_RUNNER


def test_public_launcher_uses_current_source_and_preserves_failure(tmp_path):
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
    before = {str(p.relative_to(tmp_path)): p.read_bytes()
              for p in tmp_path.rglob('*') if p.is_file()}

    def run():
        return subprocess.run(
            [sys.executable, "-B", "-c", PUBLIC_RUNNER, "tests", "checks"],
            cwd=tmp_path, capture_output=True, text=True, timeout=30,
            env={**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
        )

    healthy = run()
    assert healthy.returncode == 0, healthy.stdout + healthy.stderr
    assert "2 passed" in healthy.stdout
    after = {str(p.relative_to(tmp_path)): p.read_bytes()
             for p in tmp_path.rglob('*') if p.is_file()}
    assert before == after
    source.write_text("VALUE = False\n")
    broken = run()
    assert broken.returncode == 1
    assert "1 failed, 1 passed" in broken.stdout
