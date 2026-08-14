from __future__ import annotations

import json
from pathlib import Path

import pytest

from patchloop.errors import ContractError
from patchloop.evals.heldout_ac_preflight import preflight_heldout_ac
from scripts.run_heldout_ac_preflight import _write_canonical_output

ROOT = Path(__file__).resolve().parents[1]


def _git(_root: Path) -> dict[str, object]:
    return {
        "available": True,
        "commit": "1" * 40,
        "tree": "2" * 40,
        "execution_clean": True,
        "execution_dirty_paths": [],
    }


def _docker(images: tuple[tuple[str, str], ...]) -> dict[str, object]:
    return {
        "available": True,
        "images": [
            {
                "evaluator_image": image,
                "expected_digest": digest,
                "observed_digest": digest,
                "ready": True,
            }
            for image, digest in images
        ],
    }


def _sdk() -> dict[str, object]:
    return {"installed": True, "version": "9.9.9-test"}


def test_preflight_produces_secret_free_candidate_without_runtime_calls(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)
    result = preflight_heldout_ac(
        credential_present=True,
        repository=ROOT,
        runtime=tmp_path,
        _git_observer=_git,
        _docker_observer=_docker,
        _sdk_observer=_sdk,
    )

    assert result["execution_candidate_ready"] is True
    assert result["ready"] is False
    assert result["blockers"] == []
    assert result["candidate"]["execution_hash"] == result["execution_hash"]
    assert len(result["candidate"]["schedule"]) == 48
    assert result["candidate"]["exact_paid_approval_present"] is False
    assert result["candidate"]["provider_execution_authorized"] is False
    assert result["provider_calls_made"] == 0
    assert result["evaluator_calls_made"] == 0
    assert result["agent_runs_made"] == 0
    assert result["model_cost_usd"] == 0.0
    assert result["environment"]["credential"] == {
        "name": "OPENAI_API_KEY",
        "present": True,
        "custom_base_url_present": False,
        "value_observed_or_serialized": False,
    }


@pytest.mark.parametrize(
    ("credential_present", "git_clean", "docker_ready", "sdk_ready", "expected"),
    [
        (False, True, True, True, "OPENAI_CREDENTIAL_MISSING"),
        (True, False, True, True, "GIT_EXECUTION_SOURCE_DIRTY"),
        (True, True, False, True, "DOCKER_IMAGE_UNAVAILABLE"),
        (True, True, True, False, "OPENAI_SDK_UNAVAILABLE"),
    ],
)
def test_preflight_blocks_before_candidate(
    monkeypatch: pytest.MonkeyPatch,
    credential_present: bool,
    git_clean: bool,
    docker_ready: bool,
    sdk_ready: bool,
    expected: str,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)

    def git_observer(root: Path) -> dict[str, object]:
        value = _git(root)
        value["execution_clean"] = git_clean
        value["execution_dirty_paths"] = [] if git_clean else ["patchloop/example.py"]
        return value

    def docker_observer(images: tuple[tuple[str, str], ...]) -> dict[str, object]:
        value = _docker(images)
        if not docker_ready:
            value["images"][0]["ready"] = False
            value["images"][0]["observed_digest"] = None
        return value

    def sdk_observer() -> dict[str, object]:
        return _sdk() if sdk_ready else {"installed": False, "version": None}

    result = preflight_heldout_ac(
        credential_present=credential_present,
        repository=ROOT,
        runtime=tmp_path,
        _git_observer=git_observer,
        _docker_observer=docker_observer,
        _sdk_observer=sdk_observer,
    )

    assert result["execution_candidate_ready"] is False
    assert result["candidate"] is None
    assert result["execution_hash"] is None
    assert expected in {item["code"] for item in result["blockers"]}
    assert result["provider_calls_made"] == 0


def test_preflight_blocks_custom_base_url(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid")
    result = preflight_heldout_ac(
        credential_present=True,
        repository=ROOT,
        runtime=tmp_path,
        _git_observer=_git,
        _docker_observer=_docker,
        _sdk_observer=_sdk,
    )
    assert result["execution_candidate_ready"] is False
    assert {item["code"] for item in result["blockers"]} == {"CUSTOM_OPENAI_BASE_URL"}


def test_preflight_requires_exact_boolean_boundary() -> None:
    with pytest.raises(ContractError, match="must be a boolean"):
        preflight_heldout_ac(
            credential_present=1,  # type: ignore[arg-type]
            repository=ROOT,
            _git_observer=_git,
            _docker_observer=_docker,
            _sdk_observer=_sdk,
        )


def test_preflight_output_is_canonical_utf8_and_new_only(tmp_path: Path) -> None:
    output = tmp_path / "handoff" / "preflight.json"
    payload = {"한글": "보존", "a": 1}

    encoded = _write_canonical_output(output, payload)

    assert output.read_bytes() == encoded
    assert encoded == (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    with pytest.raises(FileExistsError, match="already exists"):
        _write_canonical_output(output, payload)
