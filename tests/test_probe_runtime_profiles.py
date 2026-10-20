"""Reviewed runtimes bind interpreter, wheel ABI, image and public evidence."""

import json

import pytest
from test_probe_dependency_resolution import PROJECT, lock_bytes, wheel

from patchloop.contracts import ProbeDependencyIdentity
from patchloop.errors import ContractError
from patchloop.prepared_probe_dependencies import read_descriptor
from patchloop.probe_dependency_resolution import project_requirements, select_wheels
from patchloop.probe_runtime import runtime
from patchloop.sandbox.probes import DockerProbeSandbox, probe_profile


def identity(profile):
    return ProbeDependencyIdentity(
        manifest_hash="sha256:" + "a" * 64,
        content_hash="sha256:" + "b" * 64,
        python=runtime(profile)[0],
        runtime_profile=profile,
    )


@pytest.mark.parametrize("profile", ["python39-v1", "python310-v1", "python312-graphics-v1"])
def test_profile_is_pinned_and_keeps_execution_restrictions(profile):
    current = probe_profile(identity(profile))
    default = probe_profile()
    assert current["image"] == runtime(profile)[1]
    for key in [
        "network",
        "read_only",
        "user",
        "cap_drop",
        "no_new_privileges",
        "pids_limit",
        "thread_policy",
        "memory",
        "cpus",
        "timeout_seconds",
    ]:
        assert current[key] == default[key]
    with pytest.raises(ContractError):
        DockerProbeSandbox("unreviewed:latest")


@pytest.mark.parametrize("python,tag", [("3.9", "cp39"), ("3.10", "cp310")])
def test_legacy_markers_and_wheel_tags_are_not_host_or_python312(tmp_path, python, tag):
    (tmp_path / "pyproject.toml").write_text(
        PROJECT.replace(">=3.10", ">=3.9"), encoding="utf-8",
    )
    requirements = project_requirements(tmp_path, groups=[], extras=[], python=python)
    assert "old-python" in requirements["requirements"]
    candidates = [
        wheel(tag=f"{tag}-{tag}-manylinux_2_17_x86_64"),
        wheel(tag="cp312-cp312-manylinux_2_17_x86_64"),
    ]
    raw = lock_bytes([("fixture", "1.0", candidates, None)]).replace(b">=3.12", b">=3.9")
    selected = select_wheels(raw, project_name="demo", python=python)
    assert f"{tag}-{tag}" in selected[0].url
    with pytest.raises(ContractError):
        probe_profile(identity("python310-v1").model_copy(update={"python": "3.12"}))


def test_descriptor_cannot_mix_profile_interpreter_and_image(tmp_path):
    path = tmp_path / "prepared.json"
    data = {
        "schema_version": "prepared-probe-dependencies-v1",
        "python": "3.10",
        "runtime_profile": "python310-v1",
        "image": runtime("python310-v1")[1],
        "platform": "linux/amd64",
        "source_roots": [],
        "files": {},
        "repository_url": "public",
        "base_commit": "base",
        "content_hash": "sha256:" + "a" * 64,
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    assert read_descriptor(path)[1].python == "3.10"
    for changed in [{"python": "3.12"}, {"image": runtime()[1]}, {"runtime_profile": "unreviewed"}]:
        path.write_text(json.dumps({**data, **changed}), encoding="utf-8")
        with pytest.raises(ContractError):
            read_descriptor(path)
