"""Offline caller preparation and original-call discrimination using synthetic packages."""

from __future__ import annotations

import csv
import io
import json
import os
import shutil
import subprocess
import sys
import textwrap
import zipfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from patchloop import prepared_probe_dependencies as prepared
from patchloop import probe_callers
from patchloop.cli import app
from patchloop.dev import runner
from patchloop.dev.contracts import DevModelTurn, DevRunRequest
from patchloop.dev.model import MockDevAdapter
from patchloop.errors import ContractError
from patchloop.prepared_source import PreparedSource
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes

REAL_RUN = subprocess.run
CALLER = '''import os
import sys
from pathlib import Path
import fixture_project
import fixture_leaf

def run(path):
    sys.path.insert(0, str(Path.cwd() / "src"))
    return fixture_project.load(path, strict=os.environ.get("FIXTURE_MODE") == "strict")
'''
PROJECT = '''from pathlib import Path

def load(path, strict=False):
    if strict:
        return (Path(path) / "entry.txt").read_text()
    return "helper only"
'''


def wheel(root, name, files, requires=()):
    """Test wheel bytes, without a build backend, network or real package special cases."""
    filename = f"{name}-1.0-py3-none-any.whl"
    info = f"{name}-1.0.dist-info"
    files = {**files, f"{info}/WHEEL": "Wheel-Version: 1.0\nTag: py3-none-any\n",
             f"{info}/METADATA": f"Metadata-Version: 2.3\nName: {name}\nVersion: 1.0\n"
             + "".join(f"Requires-Dist: {req}\n" for req in requires)}
    rows = io.StringIO()
    csv.writer(rows).writerows((path, "", "") for path in [*files, f"{info}/RECORD"])
    files[f"{info}/RECORD"] = rows.getvalue()
    path = root / filename
    with zipfile.ZipFile(path, "w") as archive:
        for relative, content in files.items():
            archive.writestr(relative, content)
    return path


@pytest.fixture
def caller_bundle(tmp_path, monkeypatch, smoke_package):
    uv = shutil.which("uv")
    assert uv is not None, "local offline validation requires the existing uv executable"
    repo = tmp_path / "source"
    repo.mkdir()
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "fixture-project"\nversion = "1.0"\n'
        'dependencies = ["fixture-leaf==1.0"]\n', encoding="utf-8",
    )
    (repo / "fixture_project.py").write_text(PROJECT, encoding="utf-8")
    source = PreparedSource(repository_url=smoke_package.public.repository.url,
                            base_commit=smoke_package.public.repository.base_commit,
                            git_commit="a" * 40, git_tree="b" * 40,
                            content_hash=sha256_bytes(b"synthetic public source"))
    source_path = tmp_path / "source.json"
    source_path.write_text(source.model_dump_json(), encoding="utf-8")
    packages = tmp_path / "public-wheels"
    packages.mkdir()
    wheel(packages, "fixture_caller", {"fixture_caller/__init__.py": CALLER},
          requires=["fixture-project>=9", "fixture-leaf==1.0"])
    wheel(packages, "fixture_leaf", {"fixture_leaf.py": "VALUE = 1\n"})
    calls = []

    def execute(command, **kwargs):
        calls.append(command)
        assert "--no-deps" not in command
        if command[1:3] != ["pip", "compile"]:
            assert "--offline" in command and "--no-index" in command
            return REAL_RUN(command, **kwargs)
        # Exercise the real resolver against only synthetic local wheels. Convert
        # its file URLs to fixture public URLs before the production lock admission.
        offline = list(command)
        index = offline.index("--default-index")
        offline[index:index + 2] = ["--no-index", "--find-links", str(packages)]
        result = REAL_RUN(offline, **kwargs)
        if result.returncode == 0:
            lock = Path(command[command.index("--output-file") + 1])
            import tomllib
            data = tomllib.loads(lock.read_text(encoding="utf-8"))
            text = 'lock-version = "1.0"\ncreated-by = "uv"\n'
            for package in data["packages"]:
                # uv may represent explicitly linked fixture wheels as archives.
                name = package["name"].replace("-", "_")
                local = packages / f"{name}-1.0-py3-none-any.whl"
                assert local.is_file()
                text += (f'\n[[packages]]\nname = "{package["name"]}"\nversion = "1.0"\n'
                         '[[packages.wheels]]\n'
                         f'url = "https://files.pythonhosted.org/packages/fixture/{local.name}"\n'
                         f'size = {local.stat().st_size}\n'
                         f'hashes = {{sha256 = "{sha256_bytes(local.read_bytes())[7:]}"}}\n')
            lock.write_text(text, encoding="utf-8")
        return result

    def download(item, destination):
        raw = (packages / item.url.rsplit("/", 1)[-1]).read_bytes()
        assert len(raw) == item.size and sha256_bytes(raw) == item.hash
        destination.write_bytes(raw)

    monkeypatch.setattr(prepared, "load_source", lambda *a, **kw: (source, repo))
    monkeypatch.setattr(prepared, "_download", download)
    monkeypatch.setattr(prepared.subprocess, "run", execute)
    request = dict(public=smoke_package.public, prepared_source=source_path,
                   output=tmp_path / "prepared", resolve=True,
                   caller_requirements=["fixture-caller==1.0"])
    return request, repo, calls


@pytest.mark.parametrize("pins", [
    ["caller"], ["caller>=1"], ["caller==1.*"], ["caller===1"],
    ["caller==1; python_version > '3.0'"], ["caller[extra]==1"],
    ["caller @ https://example.com/caller.whl"], ["./caller"], ["--index-url=x"],
    ["caller==1\nother==2"], ["fixture_project==1"], ["Caller==1", "caller==1"],
    [f"caller{i}==1" for i in range(9)], ["caller==" + "1" * 256],
])
def test_invalid_caller_pins_fail_before_any_resolution(caller_bundle, pins):
    request, _, calls = caller_bundle
    with pytest.raises(ContractError):
        prepared.prepare_dependencies(**{**request, "caller_requirements": pins})
    assert not calls and not (request["output"] / prepared.MANIFEST).exists()


def test_caller_preparation_keeps_source_and_transitive_validation(caller_bundle):
    request, repo, calls = caller_bundle
    before = {p.name: p.read_bytes() for p in repo.iterdir()}
    path = prepared.prepare_dependencies(**request)
    descriptor = json.loads(path.read_bytes())
    lock = descriptor["wheel_lock"]
    assert lock["source_metadata"]["requirements"] == ["fixture-leaf==1.0"]
    assert lock["operator_caller_requirements"] == ["fixture-caller==1.0"]
    assert lock["workspace_source"] == {
        "name": "fixture-project", "exclusion_hash": sha256_bytes(b"fixture-project\n"),
        "version_compatibility": "unverified_source_snapshot",
    }
    assert len(calls) == 2 and all("--excludes" in call for call in calls)
    assert (path.parent / "requirements.in").read_text().splitlines() == [
        "fixture-caller==1.0", "fixture-leaf==1.0"]
    assert not list((path.parent / "site-packages").glob("fixture_project.py"))
    assert (path.parent / "site-packages/fixture_leaf.py").is_file()
    assert before == {p.name: p.read_bytes() for p in repo.iterdir()}
    dependencies = prepared.load_dependencies(path, request["public"], prepared.admit(path))
    dependencies.verify()
    assert dependencies.environment["callers"] == ["fixture-caller==1.0"]
    assert dependencies.environment["source_roots"] == ["/workspace"]
    caller = path.parent / "site-packages/fixture_caller/__init__.py"
    caller.write_text(CALLER + "\n# changed", encoding="utf-8")
    with pytest.raises(ContractError, match="contents are missing or changed"):
        dependencies.verify()


def test_offline_install_still_rejects_missing_nonworkspace_dependency(caller_bundle, monkeypatch):
    request, _, calls = caller_bundle
    from patchloop import probe_dependency_resolution as resolution

    original = resolution.select_wheels
    # Inject a missing selected wheel, while leaving all admitted wheel bytes intact.
    monkeypatch.setattr(resolution, "select_wheels", lambda *a, **kw:
                        [w for w in original(*a, **kw) if "fixture_leaf-" not in w.url])
    with pytest.raises(ContractError, match="offline public wheel installation failed"):
        prepared.prepare_dependencies(**request)
    assert len(calls) == 2 and not (request["output"] / prepared.MANIFEST).exists()


def test_caller_cannot_be_omitted_or_replaced_by_resolver():
    from test_probe_dependency_resolution import lock_bytes, wheel

    from patchloop import probe_dependency_resolution as resolution
    from patchloop.prepared_probe_dependencies import PublicWheel

    with pytest.raises(ContractError, match="omit or change"):
        probe_callers.verify_selection(["caller==1"], [])
    with pytest.raises(ContractError, match="omit or change"):
        probe_callers.verify_selection(["caller==1"], [PublicWheel(
            url="https://files.pythonhosted.org/packages/a/caller-2-py3-none-any.whl",
            hash=sha256_bytes(b"x"), size=1)])
    with pytest.raises(ContractError, match="includes the workspace"):
        resolution.select_wheels(lock_bytes([
            ("fixture-project", "1.0", [wheel("fixture_project")], None),
        ]), project_name="fixture-project")


@pytest.mark.parametrize("adapter", ["literal", "legacy"])
def test_public_caller_works_with_static_legacy_metadata(caller_bundle, adapter):
    from diagnostics import legacy_probe_metadata, setup_probe_dependencies

    request, repo, _ = caller_bundle
    (repo / "pyproject.toml").write_text('[build-system]\nrequires = ["setuptools"]\n')
    (repo / "setup.py").write_text(
        'from setuptools import setup\nsetup(name="fixture-project", version="1.0", '
        'install_requires=["fixture-leaf==1.0"])\n', encoding="utf-8",
    )
    options = {k: v for k, v in request.items() if k != "resolve"}
    if adapter == "literal":
        path = setup_probe_dependencies.prepare(**options, source_roots=[])
    else:
        path = legacy_probe_metadata.prepare(**options, roots=[])
    dependencies = prepared.load_dependencies(path, request["public"], prepared.admit(path))
    dependencies.verify()
    assert dependencies.environment["callers"] == ["fixture-caller==1.0"]


def test_cli_forwards_explicit_caller_and_rejects_lock_mode(tmp_path, monkeypatch):
    args = ["task", "prepare-probe-dependencies",
            str(repository_root() / "tasks/smoke/csv-quoted-newline"),
            "--prepared-source", "source.json", "--output", str(tmp_path / "out"),
            "--caller-requirement", "caller==1"]
    result = CliRunner().invoke(app, [*args, "--wheel-lock", "lock.json"])
    assert result.exit_code != 0 and not (tmp_path / "out").exists()
    seen = []
    monkeypatch.setattr(prepared, "prepare_dependencies", lambda **kw:
                        seen.append(kw) or tmp_path / prepared.MANIFEST)
    assert CliRunner().invoke(app, [*args, "--resolve", "--runtime-profile",
                                   "python310-v1"]).exit_code == 0
    assert seen[0]["caller_requirements"] == ["caller==1"]
    assert seen[0]["runtime_profile"] == "python310-v1"


PROGRAM = '''
import inspect, importlib.metadata, json, os, tempfile
from pathlib import Path
import fixture_caller, fixture_project
root = Path(tempfile.mkdtemp())
(root / "src/sample").mkdir(parents=True)
os.chdir(root)
os.environ["FIXTURE_MODE"] = "strict"
observed = []
original = fixture_project.load
def capture(path, strict=False):
    check_setup("path", path, "src/sample")
    check_setup("strict", strict, True)
    check_setup("search root", __import__("sys").path[0], str(root / "src"))
    observed.append({"path": path, "strict": strict, "cwd": os.getcwd(),
                     "input_exists": (Path(path) / "entry.txt").exists()})
    return original(path, strict=strict)
helper = original("src/sample")
fixture_project.load = capture
try:
    missing = fixture_caller.run("src/sample")
except FileNotFoundError:
    missing = "original failure"
(root / "src/sample/entry.txt").write_text("normal")
normal = fixture_caller.run("src/sample")
print(json.dumps({"caller_source": inspect.getsource(fixture_caller.run),
                  "caller_version": importlib.metadata.version("fixture-caller"),
                  "implementation": fixture_project.__file__, "helper": helper,
                  "missing": missing, "normal": normal, "observed": observed,
                  "python": __import__("sys").version, "environment": os.environ["FIXTURE_MODE"]}))
'''


@pytest.mark.parametrize("real_docker", [False, True])
def test_original_caller_observes_input_environment_and_current_edits(
    caller_bundle, monkeypatch, tmp_path, real_docker,
):
    if real_docker and os.environ.get("PATCHLOOP_TEST_REAL_PROBES") != "1":
        pytest.skip("real Docker caller validation is explicitly opt-in")
    request, repo, _ = caller_bundle
    path = prepared.prepare_dependencies(**request)
    dependencies = prepared.load_dependencies(path, request["public"], prepared.admit(path))
    monkeypatch.setattr(prepared.subprocess, "run", REAL_RUN)
    if real_docker:
        from patchloop.sandbox.probes import DockerProbeSandbox

        REAL_RUN(["git", "init", str(repo)], check=True, capture_output=True)
        REAL_RUN(["git", "-C", str(repo), "add", "."], check=True, capture_output=True)
        backend = DockerProbeSandbox(dependencies=dependencies)
        backend.preflight()  # Inspection only; no image acquisition or daemon startup.
    else:
        copied = tmp_path / "dependencies"
        dependencies.verify(target=copied)
    # A helper-only change still fails through the caller; a route change is observed
    # in the current tracked project, without installing a replacement distribution.
    for index, source in enumerate((PROJECT, PROJECT.replace("helper only", "helper fixed"),
            PROJECT.replace('if strict:', 'if strict and (Path(path) / "entry.txt").exists():'))):
        (repo / "fixture_project.py").write_text(source, encoding="utf-8")
        if real_docker:
            receipt = backend.run_probe(repo, "Observe the original caller and a normal control",
                                        textwrap.dedent(PROGRAM), deadline=None,
                                        execution_identity={"run_id": tmp_path.name,
                                                            "action_id": f"caller-{index}"})
            (tmp_path / f"receipt-{index}.json").write_text(
                canonical_json(receipt), encoding="utf-8")
            assert receipt["status"] == "passed", receipt
            assert receipt["setup_checks"]["status"] == "passed"
            output = receipt["stdout"]
        else:
            from patchloop.sandbox import probe_setup

            program = (Path(probe_setup.__file__).read_text(encoding="utf-8")
                       + f"\nimport sys; sys.path[:0] = {[str(repo), str(copied)]!r}\n"
                       + '\ncheck_setup = SetupChecks({"request_hash": "fixture"}).check\n'
                       + PROGRAM)
            result = REAL_RUN([sys.executable, "-I", "-S", "-B", "-c", program],
                              capture_output=True, text=True, encoding="utf-8", check=True,
                              timeout=10)
            output = result.stdout
        observed = json.loads(output)
        assert observed["missing"] == ("original failure" if index < 2 else "helper only")
        assert observed["normal"] == "normal" and observed["caller_version"] == "1.0"
        assert observed["helper"] == ("helper fixed" if index == 1 else "helper only")
        assert "strict=os.environ.get" in observed["caller_source"]
        assert "fixture_project.py" in observed["implementation"]
        assert "site-packages" not in observed["implementation"]
        if real_docker:
            assert observed["python"].startswith(dependencies.identity.python + ".")
        assert observed["environment"] == "strict"
        assert [row["input_exists"] for row in observed["observed"]] == [False, True]
        assert all(row["strict"] and row["path"] == "src/sample" for row in observed["observed"])
        dependencies.verify()


@pytest.mark.parametrize("policy", ["append-v1", "segmented-v1"])
def test_caller_discovery_is_delivered_and_mock_reaches_isolated_evaluation(
    caller_bundle, monkeypatch, tmp_path, policy,
):
    from test_dev_probes import probe_call
    from test_prepared_probe_dependencies import DependencyProbe

    request, _, _ = caller_bundle
    path = prepared.prepare_dependencies(**request)
    monkeypatch.setattr(prepared.subprocess, "run", REAL_RUN)
    monkeypatch.setattr(runner, "DockerProbeSandbox", DependencyProbe)
    seen = []

    class CallerThenMock(MockDevAdapter):
        def next_turn(self, context, tools):
            description = next(t["description"] for t in tools if t["name"] == "run_probe")
            assert "fixture-caller==1.0" in description
            assert "inspect.getsource" in description
            assert "actual arguments, cwd, sys.path" in description
            assert "version compatibility remains unverified" in description
            assert str(path) not in description
            if not seen:
                seen.append(description)
                return DevModelTurn(tool_calls=[probe_call()])
            return super().next_turn(context, tools)

    monkeypatch.setattr(runner, "MockDevAdapter", CallerThenMock)
    result = runner.run_dev(DevRunRequest(
        task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml",
        provider="mock", model="mock-dev", enable_probes=True, context_policy=policy,
        prepared_probe_dependencies=path, state_root=tmp_path / "state",
    ))["runs"][0]
    assert seen and result["terminal"] == "EVALUATOR_PASS"
