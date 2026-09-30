import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from patchloop.task_loader import load_task_package

ROOT = Path(__file__).resolve().parents[1] / "tasks/dev-train"


def test_revision_preserves_task_and_private_material():
    old = load_task_package(ROOT / "original-montepy-933")
    new = load_task_package(ROOT / "original-montepy-933-v2")
    assert new.public.task_version == new.private.task_version == 2
    assert old.public.model_dump(exclude={"task_version", "visible_checks"}) == (
        new.public.model_dump(exclude={"task_version", "visible_checks"})
    )
    assert old.private.model_dump(exclude={"task_version"}) == (
        new.private.model_dump(exclude={"task_version"})
    )
    old_check, new_check = old.public.visible_checks[0], new.public.visible_checks[0]
    assert old_check.command[:3] == new_check.command[:3]
    assert ["-ra" if arg == "-rA" else arg for arg in old_check.command[4:]] == (
        new_check.command[4:]
    )
    assert old_check.model_dump(exclude={"command", "infrastructure_exit_codes"}) == (
        new_check.model_dump(exclude={"command", "infrastructure_exit_codes"})
    )
    for relative in ["reference.patch", "environment.yaml", *(
        p.relative_to(Path(old.root)) for p in (Path(old.root) / "hidden").rglob("*")
        if p.is_file()
    )]:
        assert (Path(old.root) / relative).read_bytes() == (Path(new.root) / relative).read_bytes()


def test_git_preserves_hash_bound_v2_bytes():
    package = load_task_package(ROOT / "original-montepy-933-v2")
    repo = ROOT.parents[1]
    for artifact in package.private.hidden_artifacts:
        path = Path(package.root) / artifact.path
        relative = path.relative_to(repo).as_posix()
        filtered = subprocess.run(
            ["git", "hash-object", f"--path={relative}", str(path)],
            cwd=repo, capture_output=True, text=True, check=True,
        ).stdout.strip()
        raw = subprocess.run(
            ["git", "hash-object", "--no-filters", str(path)],
            cwd=repo, capture_output=True, text=True, check=True,
        ).stdout.strip()
        assert filtered == raw, f"Git filters change hash-bound bytes: {relative}"


@pytest.mark.parametrize("drift", [None, "missing", "duplicate"])
def test_public_override_is_disposable_and_source_drift_fails_before_pytest(
    tmp_path, monkeypatch, drift,
):
    public = yaml.safe_load((ROOT / "original-montepy-933-v2/public.yaml").read_text())
    check = public["visible_checks"][0]
    source = (
        "from hypothesis import given, strategies as st\n"
        "class TestFill:\n"
        "    def test_fill_index_setter(self, indices, width):\n"
        "        end = np.array(indices) + np.array(width)\n"
        "        assert (fill.max_index == end).all()\n"
    )
    if drift == "missing":
        source = source.replace("np.array(width)", "other(width)")
    elif drift == "duplicate":
        source += "        end = np.array(indices) + np.array(width)\n"
    test_path = tmp_path / "tests/test_universe.py"
    test_path.parent.mkdir()
    test_path.write_text(source)
    implementation = tmp_path / "montepy/cell.py"
    implementation.parent.mkdir()
    implementation.write_text("# unchanged implementation\n")
    calls = []

    def execute(command, *, cwd, env):
        calls.append(command)
        revised = (cwd / "tests/test_universe.py").read_text()
        assert "dtype=object" in revised
        assert revised.count("@example(") == 5
        assert "assert (fill.max_index == end).all()" in revised
        assert (cwd / "montepy/cell.py").read_bytes() == implementation.read_bytes()
        assert env["PYTHONPATH"] == str(cwd)
        assert command[2:] == check["command"][4:]
        return SimpleNamespace(returncode=0)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("subprocess.run", execute)
    monkeypatch.setattr("sys.argv", ["-c", *check["command"][4:]])
    with pytest.raises(SystemExit) as exc:
        exec(compile(check["command"][3], "public-wrapper", "exec"), {})
    assert exc.value.code == (2 if drift else 0)
    assert len(calls) == (0 if drift else 1)
    assert test_path.read_text() == source
    assert check["infrastructure_exit_codes"] == [2]
