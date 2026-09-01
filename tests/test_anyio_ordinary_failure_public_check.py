from __future__ import annotations

import json
from pathlib import Path

from patchloop.evals.anyio_ordinary_failure_public_check import (
    CHECK_ID,
    CHECK_SCRIPT,
    build_qualification,
    proposed_check,
    qualification_bytes,
)
from patchloop.util import sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


def test_proposed_check_is_public_bounded_and_compilable() -> None:
    check = proposed_check()

    assert check["id"] == CHECK_ID
    assert check["expected_base_observation"] == "pass"
    assert check["expected_reference_observation"] == "pass"
    assert check["timeout_seconds"] == 30
    assert check["working_directory"] == "."
    assert check["command"][:2] == ["/opt/conda/envs/testbed/bin/python", "-c"]
    assert check["command"][2] == CHECK_SCRIPT
    compile(CHECK_SCRIPT, "<public-check>", "exec")
    assert "PRIVATE" not in CHECK_SCRIPT.upper()
    assert "HIDDEN" not in CHECK_SCRIPT.upper()
    assert "REFERENCE" not in CHECK_SCRIPT.upper()


def test_proposed_check_covers_the_missing_public_intersection() -> None:
    required = (
        '@pytest.fixture(scope="module")',
        "async def shared",
        "async def test_ordinary_failure",
        "assert False",
        "async def test_after_failure",
        '"shared-cleanup"',
        "completed.returncode != 1",
        '"1 failed"',
        '"1 passed"',
        "PUBLIC_CASE:anyio:ordinary-failure-status",
        "PUBLIC_CASE:anyio:ordinary-failure-events",
        "PUBLIC_CASE:anyio:ordinary-failure-summary",
    )
    assert all(item in CHECK_SCRIPT for item in required)
    expected_block = CHECK_SCRIPT.split("expected_events = [", 1)[1].split("]", 1)[0]
    assert expected_block.index('"ordinary-failure"') < expected_block.index('"after-failure"')
    assert expected_block.index('"after-failure"') < expected_block.index('"shared-cleanup"')


def test_qualification_is_deterministic_public_only_and_not_activated() -> None:
    first = build_qualification(REPOSITORY)
    second = build_qualification(REPOSITORY)

    assert qualification_bytes(first) == qualification_bytes(second)
    assert first["content_hash"] == sha256_json(
        {key: value for key, value in first.items() if key != "content_hash"}
    )
    assert first["status"] == "offline-source-qualified"
    assert first["activation_authorized"] is False
    assert first["task_version_created"] is False
    assert first["paid_execution_authorized"] is False
    assert first["public_source_gap"]["targeted_ordinary_failure_present"] is False
    assert first["r14_public_result"]["submitted_visible_checks_passed"] == [2, 2]
    assert first["r14_public_result"]["hidden_failure_cause_attributed"] is False
    assert first["proposed_check_hash"] == sha256_json(first["proposed_check"])
    boundary = first["evidence_boundary"]
    assert boundary["public_only"] is True
    assert boundary["private_task_spec_read"] is False
    assert boundary["hidden_evaluator_content_read"] is False
    assert boundary["reference_patch_read"] is False
    assert boundary["reasoning_text_read"] is False
    assert boundary["docker_calls"] == 0
    assert boundary["provider_calls"] == 0
    assert boundary["evaluator_calls"] == 0
    assert boundary["registered_check_calls"] == 0
    assert boundary["network_calls"] == 0
    assert boundary["added_cost_usd"] == 0


def test_qualification_serialization_round_trips() -> None:
    raw = qualification_bytes(build_qualification(REPOSITORY))
    parsed = json.loads(raw)

    assert parsed["schema_version"].endswith("source-qualification-v1")
    assert parsed["proposed_check"]["id"] == CHECK_ID
