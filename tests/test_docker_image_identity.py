from __future__ import annotations

import json
import subprocess

import pytest

from patchloop.sandbox.runner import DockerSandbox

DIGEST = "sha256:" + "a" * 64


@pytest.mark.parametrize(
    ("requested", "recorded", "accepted"),
    [
        ("python:3.12-slim", "python", True),
        ("python", "python", True),
        ("docker.io/python:3.12-slim", "python", True),
        ("registry.example:5000/team/image:reviewed", "registry.example:5000/team/image", True),
        ("registry.example:5000/team/image", "registry.example:5000/team/image", True),
        ("registry.example:5000/team/image:reviewed", "registry.example:6000/team/image", False),
        ("python:3.12-slim", "different-repository", False),
        ("python:3.12-slim", "python", False),
    ],
)
def test_digest_identity_ignores_only_optional_tag(monkeypatch, requested, recorded, accepted):
    different_digest = not accepted and recorded == "python"
    returned_digest = "sha256:" + "b" * 64 if different_digest else DIGEST
    image = f"{requested}@{DIGEST}"
    calls = []

    def inspect(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(
            command, 0,
            json.dumps({"Id": "unused", "RepoDigests": [f"{recorded}@{returned_digest}"]}).encode(),
            b"",
        )

    monkeypatch.setattr(DockerSandbox, "cli_path", staticmethod(lambda: "docker"))
    monkeypatch.setattr("patchloop.sandbox.runner.subprocess.run", inspect)
    assert DockerSandbox(image).image_identity() == (DIGEST if accepted else None)
    repository = requested.rsplit(":", 1)[0] if ":" in requested.rsplit("/", 1)[-1] else requested
    assert calls[0][:4] == ["docker", "image", "inspect", f"{repository}@{DIGEST}"]
