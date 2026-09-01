from __future__ import annotations

import json
from pathlib import Path

import yaml

from patchloop.evals.anyio_ordinary_failure_public_check import proposed_check
from patchloop.evals.anyio_ordinary_failure_task_successor import (
    PREDECESSOR_PATH,
    QUALIFICATION_PATH,
    SUCCESSOR_PATH,
    build_qualification,
    materialize_successor,
    qualification_bytes,
    successor_files,
)
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_bytes, sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


def test_successor_bytes_are_deterministic_and_the_delta_is_exact() -> None:
    first = successor_files(REPOSITORY)
    second = successor_files(REPOSITORY)
    assert first == second
    assert set(first) == {
        "audit.md",
        "environment.yaml",
        "hidden/test_interrupt_runner_cleanup.py",
        "private.yaml",
        "public.yaml",
        "reference.patch",
    }

    predecessor_public = (REPOSITORY / PREDECESSOR_PATH / "public.yaml").read_text(encoding="utf-8")
    successor_public = first["public.yaml"].decode()
    assert predecessor_public.count("task_version: 4") == 1
    assert successor_public.count("task_version: 5") == 1
    assert "public-ordinary-failure-preservation" not in predecessor_public
    assert successor_public.count("public-ordinary-failure-preservation") == 1
    assert successor_public.index("public-interrupt-runner-lifecycle") < successor_public.index(
        "public-ordinary-failure-preservation"
    )
    assert successor_public.index("public-ordinary-failure-preservation") < successor_public.index(
        "upstream-pytest-plugin-regression"
    )
    assert "public-behavior-check-v5" in successor_public
    assert "public-behavior-check-v4" not in successor_public

    predecessor_private = (REPOSITORY / PREDECESSOR_PATH / "private.yaml").read_text(
        encoding="utf-8"
    )
    successor_private = first["private.yaml"].decode()
    assert predecessor_private.replace("task_version: 4", "task_version: 5", 1) == (
        successor_private
    )
    for relative in (
        "environment.yaml",
        "reference.patch",
        "hidden/test_interrupt_runner_cleanup.py",
    ):
        assert first[relative] == (REPOSITORY / PREDECESSOR_PATH / relative).read_bytes()


def test_materialized_successor_has_three_ordered_public_checks() -> None:
    assert materialize_successor(REPOSITORY) == REPOSITORY / SUCCESSOR_PATH
    predecessor = load_task_package(REPOSITORY / PREDECESSOR_PATH)
    successor = load_task_package(REPOSITORY / SUCCESSOR_PATH)

    assert successor.public.task_version == successor.private.task_version == 5
    assert successor.public.issue == predecessor.public.issue
    assert successor.public.constraints == predecessor.public.constraints
    assert successor.public.repository == predecessor.public.repository
    assert successor.environment == predecessor.environment
    assert [check.id for check in successor.public.visible_checks] == [
        "public-interrupt-runner-lifecycle",
        "public-ordinary-failure-preservation",
        "upstream-pytest-plugin-regression",
    ]
    assert successor.public.visible_checks[0] == predecessor.public.visible_checks[0]
    assert successor.public.visible_checks[2] == predecessor.public.visible_checks[1]
    qualified = proposed_check()
    expected = {
        key: value
        for key, value in qualified.items()
        if key
        in {
            "id",
            "command",
            "timeout_seconds",
            "working_directory",
            "environment",
            "output_limit_bytes",
        }
    }
    expected["expected_exit_codes"] = [0]
    assert successor.public.visible_checks[1].model_dump(mode="json") == expected
    compile(successor.public.visible_checks[1].command[-1], "<ordinary-failure-v5>", "exec")


def test_successor_is_not_admitted_and_exposes_no_evaluator_material() -> None:
    manifest = yaml.safe_load(
        (REPOSITORY / "data/dataset-manifest.yaml").read_text(encoding="utf-8")
    )
    admitted = {(item["task_id"], item["task_version"], item["path"]) for item in manifest["tasks"]}
    successor = load_task_package(REPOSITORY / SUCCESSOR_PATH)
    assert (
        successor.public.task_id,
        successor.public.task_version,
        SUCCESSOR_PATH.as_posix(),
    ) not in admitted
    public_text = (REPOSITORY / SUCCESSOR_PATH / "public.yaml").read_text(encoding="utf-8")
    commands = "\n".join(
        argument for check in successor.public.visible_checks for argument in check.command
    )
    assert ".patchloop-hidden" not in commands
    assert "reference.patch" not in public_text
    assert successor.private.reference_patch.sha256 not in public_text


def test_qualification_is_deterministic_current_and_zero_call() -> None:
    first = build_qualification(REPOSITORY)
    second = build_qualification(REPOSITORY)
    assert qualification_bytes(first) == qualification_bytes(second)
    assert first["content_hash"] == sha256_json(
        {key: value for key, value in first.items() if key != "content_hash"}
    )
    assert first["status"] == "offline-source-qualified"
    assert first["activation_authorized"] is False
    assert first["rapid_candidate_created"] is False
    assert first["successor_contract"]["visible_check_ids"] == [
        "public-interrupt-runner-lifecycle",
        "public-ordinary-failure-preservation",
        "upstream-pytest-plugin-regression",
    ]
    assert first["successor_contract"]["frozen_dataset_member"] is False
    assert first["delta_contract"]["base_and_reference_both_passed"] is True
    assert first["delta_contract"]["hidden_failure_cause_attributed"] is False
    boundary = first["evidence_boundary"]
    assert boundary["docker_calls"] == 0
    assert boundary["provider_calls"] == 0
    assert boundary["evaluator_calls"] == 0
    assert boundary["registered_check_calls"] == 0
    assert boundary["network_calls"] == 0
    assert boundary["added_cost_usd"] == 0

    stored = (REPOSITORY / QUALIFICATION_PATH).read_bytes()
    assert stored == qualification_bytes(first)
    assert json.loads(stored)["content_hash"] == first["content_hash"]
    assert sha256_bytes(stored).startswith("sha256:")
