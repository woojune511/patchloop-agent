from __future__ import annotations

import json
from pathlib import Path

from patchloop.evals.anyio_runner_continuity_public_check import (
    CHECK_ID,
    CHECK_SCRIPT,
    QUALIFICATION_PATH,
    build_qualification,
    proposed_check,
    qualification_bytes,
)
from patchloop.util import sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


def test_proposed_runner_continuity_check_is_public_bounded_and_compilable() -> None:
    check = proposed_check()

    assert check["id"] == CHECK_ID
    assert check["expected_base_observation"] == "pass_unverified"
    assert check["expected_reference_observation"] == "pass_unverified"
    assert check["timeout_seconds"] == 30
    assert check["command"][:2] == ["/opt/conda/envs/testbed/bin/python", "-c"]
    assert check["command"][2] == CHECK_SCRIPT
    compile(CHECK_SCRIPT, "<public-runner-continuity-check>", "exec")
    assert "PRIVATE" not in CHECK_SCRIPT.upper()
    assert "HIDDEN" not in CHECK_SCRIPT.upper()
    assert "REFERENCE" not in CHECK_SCRIPT.upper()


def test_proposal_combines_public_outcomes_under_one_runner_lifetime() -> None:
    for marker in (
        '@pytest.fixture(scope="module")',
        "async def shared",
        "async def test_skip",
        "async def test_xfail",
        "async def test_ordinary_failure",
        "async def test_after_outcomes",
        "len(set(loop_ids)) != 1",
        '"shared-cleanup"',
        '"1 failed"',
        '"1 passed"',
        '"1 skipped"',
        '"1 xfailed"',
    ):
        assert marker in CHECK_SCRIPT


def test_source_qualification_is_deterministic_zero_call_and_not_activated() -> None:
    first = build_qualification(REPOSITORY)
    second = build_qualification(REPOSITORY)

    assert qualification_bytes(first) == qualification_bytes(second)
    assert first["content_hash"] == sha256_json(
        {key: value for key, value in first.items() if key != "content_hash"}
    )
    assert first["status"] == "offline-source-qualified-proposal"
    assert first["activation_authorized"] is False
    assert first["task_successor_created"] is False
    assert first["behavior_observed"] is False
    assert first["public_source_contract"]["existing_outcomes_split_across_checks"] is True
    assert first["public_source_contract"]["composite_runner_continuity_present"] is False
    boundary = first["evidence_boundary"]
    assert boundary["public_task_source_only"] is True
    assert boundary["docker_calls"] == 0
    assert boundary["provider_calls"] == 0
    assert boundary["evaluator_calls"] == 0
    assert boundary["visible_check_calls"] == 0
    assert boundary["network_calls"] == 0
    assert boundary["added_cost_usd"] == 0


def test_source_qualification_serialization_round_trips() -> None:
    parsed = json.loads(qualification_bytes(build_qualification(REPOSITORY)))

    assert parsed["proposed_check"]["id"] == CHECK_ID
    assert parsed["qualification_assertions"]["expected_observations_are_unverified"] is True


def test_stored_source_qualification_is_an_exact_byte_audit() -> None:
    raw = (REPOSITORY / QUALIFICATION_PATH).read_bytes()

    assert raw == qualification_bytes(json.loads(raw))
    assert raw == qualification_bytes(build_qualification(REPOSITORY))
