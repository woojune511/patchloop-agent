"""Prevent a missing mock from turning provider-free unit tests into Docker work."""
from __future__ import annotations

import subprocess

import pytest


@pytest.mark.parametrize("executable", ["docker", "docker.exe", "C:/Docker/docker.exe"])
def test_default_suite_refuses_an_unmocked_docker_launch(executable, monkeypatch):
    from conftest import require_explicit_real_docker_opt_in

    monkeypatch.setenv("PATCHLOOP_TEST_REAL_EXECUTION", "0")
    monkeypatch.setenv("PATCHLOOP_TEST_REAL_PROBES", "0")
    require_explicit_real_docker_opt_in.__wrapped__(monkeypatch)
    with pytest.raises(pytest.fail.Exception, match="real Docker requires"):
        subprocess.Popen(args=[executable, "version"])


def test_explicit_mock_launch_remains_available(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: sentinel)
    assert subprocess.Popen(["docker", "version"]) is sentinel
