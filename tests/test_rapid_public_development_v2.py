from __future__ import annotations

import json
from pathlib import Path

import pytest

from patchloop.errors import ContractError
from patchloop.evals import rapid_public_development_v2 as rapid
from patchloop.util import sha256_bytes

REPOSITORY = Path(__file__).resolve().parents[1]


def test_consumed_v2_evidence_is_byte_exact() -> None:
    qualification = REPOSITORY / rapid.QUALIFICATION_PATH
    candidate = REPOSITORY / rapid.CANDIDATE_PATH
    result = REPOSITORY / rapid.CONSUMED_RESULT_PATH

    assert qualification.stat().st_size == 8_558
    assert sha256_bytes(qualification.read_bytes()) == (
        "sha256:9e6749f977426fa8f85c1db4ff9f4c738f9646436c2d6846d271c851ea0e8a1f"
    )
    assert candidate.stat().st_size == 8_742
    assert sha256_bytes(candidate.read_bytes()) == (
        "sha256:f944eec474899a71e566e040f600ea69f485b812dad22522030d3ac70e06f760"
    )
    assert result.stat().st_size == 10_819
    assert sha256_bytes(result.read_bytes()) == (
        "sha256:0ef7358c69f1944abef14f6546f012762edcfb5e176d0d5f3d3d3bcec2210ad2"
    )

    payload = json.loads(candidate.read_text(encoding="utf-8"))
    assert payload["content_hash"] == (
        "sha256:6dd7548ef175db4357b7bcd13cb15d19d55d0d8eaeeefefa4e9c22c207722de2"
    )
    assert payload["execution_hash"] == (
        "sha256:f066bd044465a53c5c25e001de316f7e3b522b8ccbc7bcb21e09be8c66cb5ca1"
    )


def test_consumed_v2_live_entry_stops_before_credentials_or_docker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        rapid.DockerSandbox,
        "available",
        lambda: (_ for _ in ()).throw(AssertionError("Docker must not be called")),
    )
    with pytest.raises(ContractError, match="execution is consumed"):
        rapid.run_rapid_public_development_v2(
            approve_live_cost=True,
            approved_execution_hash=(
                "sha256:f066bd044465a53c5c25e001de316f7e3b522b8ccbc7bcb21e09be8c66cb5ca1"
            ),
            repository=REPOSITORY,
        )


def test_consumed_r1_config_and_bundle_bytes_are_unchanged() -> None:
    config = REPOSITORY / "experiments/rapid-public-development-lean-harness-20260818-r1.yaml"
    bundle = (
        REPOSITORY
        / "reports/rapid-development/"
        "rapid-public-dev-lean-harness-20260818-r1-b1b7524bcf9e.jsonl"
    )

    assert config.stat().st_size == 2_280
    assert sha256_bytes(config.read_bytes()) == (
        "sha256:c5efbbd10ebb71ca1ca00a776b7b35842737513a87bc793af2f2470036a59bb6"
    )
    assert bundle.stat().st_size == 10_043
    assert sha256_bytes(bundle.read_bytes()) == (
        "sha256:0d6ce0a3da3adbe76b2321bb412429c05e7dc09538f358875700952ca67804f4"
    )
