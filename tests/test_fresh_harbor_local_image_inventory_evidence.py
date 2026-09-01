from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from patchloop.evals.fresh_all_cross_successor import CANDIDATE_IDS
from patchloop.evals.fresh_harbor_local_image_inventory import (
    ApprovalReceipt,
    AttemptIntent,
    Candidate,
    SourceQualification,
    Terminal,
    expected_approval_message,
)
from patchloop.evals.fresh_harbor_partial_runner import artifact_bytes
from patchloop.util import sha256_bytes

REPOSITORY = Path(__file__).resolve().parents[1]
EXECUTION_HASH = "sha256:2f72f2a9a1e6bc7ceef2fa656a7878f1e266081615698c61f6d74868bba5ef4c"

ARTIFACTS = (
    (
        "reports/fresh-panel/artifacts/"
        "lean-fresh-harbor-local-image-inventory-source-qualification-r1.json",
        SourceQualification,
        4_198,
        "sha256:423291548e681feda66a8a6ba46e84c844a9e623efa6a791e1ebd97da626cd94",
        "sha256:72fd6a831c2431b12a4cff52c66f64db8bb0bfcf21733ae31ca563ef71e4ad87",
    ),
    (
        "experiments/lean-harness-fresh-harbor-local-image-inventory-20260818-v1.json",
        Candidate,
        7_521,
        "sha256:30b9d92c6ae30a017c5614707e266dc926836de2000e37fa802fc2fed9ee3ec5",
        "sha256:7b5cf816ebd9709f4b3e46dbfcc889f933eca9f591fb10b40489af1c1b138221",
    ),
    (
        "reports/fresh-panel/artifacts/lean-fresh-harbor-local-image-inventory-approval-r1.json",
        ApprovalReceipt,
        1_423,
        "sha256:12b6b4b3d21b87a9a338ab2507d49e858857cda195a7a12be099fd9bdeed5a9c",
        "sha256:b896cb26abee82820a0ba504c0176eb154652666480a9e2ae4e7b2d6abfab54d",
    ),
    (
        "reports/fresh-panel/artifacts/lean-fresh-harbor-local-image-inventory-attempt-r1.json",
        AttemptIntent,
        1_625,
        "sha256:a8773da63c9946a1b109cf09706be17f064f51a17a39e1f5758e1e6bbc4da917",
        "sha256:9e00e72fda6d914bbfbe7fead342db6ec4da9de36b97751b61a8e6fae246afa9",
    ),
    (
        "reports/fresh-panel/artifacts/lean-fresh-harbor-local-image-inventory-terminal-r1.json",
        Terminal,
        6_124,
        "sha256:1766ef3677bf28acb80b97bbc33e192a510c4c47958f12012f7536ad89d08ba9",
        "sha256:f53a4c431083d467652d7c3645aecc3a0a1b1bbd189b06a5ed3c40eca9eb5766",
    ),
)


def _load(relative: str, model: type[BaseModel]) -> BaseModel:
    raw = (REPOSITORY / relative).read_bytes()
    value = model.model_validate_json(raw)
    assert artifact_bytes(value) == raw
    return value


def test_inventory_artifacts_are_exact_canonical_and_append_only() -> None:
    for relative, model, expected_bytes, expected_sha256, expected_content in ARTIFACTS:
        raw = (REPOSITORY / relative).read_bytes()
        value = _load(relative, model)
        assert len(raw) == expected_bytes
        assert sha256_bytes(raw) == expected_sha256
        assert value.model_dump(mode="json")["content_hash"] == expected_content


def test_inventory_authority_chain_and_terminal_projection_are_exact() -> None:
    candidate = _load(ARTIFACTS[1][0], Candidate)
    approval = _load(ARTIFACTS[2][0], ApprovalReceipt)
    attempt = _load(ARTIFACTS[3][0], AttemptIntent)
    terminal = _load(ARTIFACTS[4][0], Terminal)
    assert isinstance(candidate, Candidate)
    assert isinstance(approval, ApprovalReceipt)
    assert isinstance(attempt, AttemptIntent)
    assert isinstance(terminal, Terminal)

    assert candidate.execution_hash == EXECUTION_HASH
    assert approval.execution_hash == attempt.execution_hash == terminal.execution_hash
    assert approval.candidate_binding.content_hash == candidate.content_hash
    assert attempt.approval_binding.content_hash == approval.content_hash
    assert terminal.attempt_binding.content_hash == attempt.content_hash
    assert sha256_bytes(expected_approval_message(candidate).encode()) == (
        approval.user_message_sha256
    )

    assert terminal.status == "LOCAL_IMAGE_INVENTORY_COMPLETE_MISSING_IMAGES"
    assert terminal.command_return_code == 0
    assert (terminal.present_count, terminal.missing_count) == (0, 12)
    assert tuple(item.task_id for item in terminal.target_observations) == CANDIDATE_IDS
    assert not any(item.present for item in terminal.target_observations)
    assert terminal.stdout.byte_count == 16_172
    assert terminal.stdout.sha256 == (
        "sha256:b5e5b7a623ba6a760a723f89fe765af3e41edee2b0daa9c5d9bed0b67cc5911b"
    )
    assert terminal.stderr.byte_count == 0
    assert terminal.docker_cli_calls == terminal.docker_daemon_read_calls == 1
    assert terminal.unrelated_local_image_records_persisted == 0
    assert terminal.raw_stdout_or_stderr_persisted is False
    assert terminal.image_pull_build_tag_remove_prune_calls == 0
    assert terminal.container_mutations == terminal.network_calls == 0
    assert terminal.task_evaluator_agent_provider_calls == terminal.added_cost_usd == 0
    assert terminal.execution_authorized is False
