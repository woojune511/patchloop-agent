from __future__ import annotations

import json
import shutil
import subprocess

from typer.testing import CliRunner

from patchloop.cli import app
from patchloop.sandbox import DockerSandbox


def test_doctor_decodes_wsl_utf16_and_reports_authenticated_gh(monkeypatch) -> None:
    paths = {
        "uv": "C:\\tools\\uv.exe",
        "git": "C:\\tools\\git.exe",
        "gh": "C:\\tools\\gh.exe",
        "wsl": "C:\\Windows\\System32\\wsl.exe",
        "wsl.exe": "C:\\Windows\\System32\\wsl.exe",
    }
    monkeypatch.setattr(shutil, "which", lambda name: paths.get(name))
    monkeypatch.setattr(
        DockerSandbox, "cli_path", staticmethod(lambda: "C:\\tools\\docker.exe")
    )
    monkeypatch.setattr(DockerSandbox, "available", staticmethod(lambda: True))
    monkeypatch.setattr(
        DockerSandbox, "image_identity", lambda _self: "sha256:evaluator"
    )

    def run_probe(command, **_kwargs):
        if command[1:] == ["--list", "--quiet"]:
            output = "\ufeffUbuntu-24.04\nDebian\n".encode("utf-16-le")
            return subprocess.CompletedProcess(command, 0, output, b"")
        if command[1:] == ["auth", "status"]:
            return subprocess.CompletedProcess(command, 0, b"\xff", b"")
        raise AssertionError(f"unexpected probe: {command}")

    monkeypatch.setattr(subprocess, "run", run_probe)

    result = CliRunner().invoke(app, ["doctor"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["github_cli"]["authenticated"] is True
    assert payload["wsl"]["distributions"] == ["Ubuntu-24.04", "Debian"]
    assert payload["official_evaluation_ready"]["ok"] is True


def test_doctor_turns_probe_errors_into_failed_checks(monkeypatch) -> None:
    paths = {
        "uv": "C:\\tools\\uv.exe",
        "git": "C:\\tools\\git.exe",
        "gh": "C:\\tools\\gh.exe",
        "wsl": "C:\\Windows\\System32\\wsl.exe",
        "wsl.exe": "C:\\Windows\\System32\\wsl.exe",
    }
    monkeypatch.setattr(shutil, "which", lambda name: paths.get(name))
    monkeypatch.setattr(DockerSandbox, "cli_path", staticmethod(lambda: None))
    monkeypatch.setattr(DockerSandbox, "available", staticmethod(lambda: False))

    def failed_probe(command, **_kwargs):
        if command[1:] == ["--list", "--quiet"]:
            raise subprocess.TimeoutExpired(command, 10)
        if command[1:] == ["auth", "status"]:
            raise PermissionError("configuration is inaccessible")
        raise AssertionError(f"unexpected probe: {command}")

    monkeypatch.setattr(subprocess, "run", failed_probe)

    result = CliRunner().invoke(app, ["doctor"])

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["github_cli"]["authenticated"] is False
    assert payload["wsl"]["distributions"] == []
    assert payload["official_evaluation_ready"]["ok"] is False


def test_run_help_exposes_explicit_self_validation_opt_in() -> None:
    result = CliRunner().invoke(app, ["run", "--help"])

    assert result.exit_code == 0
    assert "--self-validation" in result.stdout
