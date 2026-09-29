from __future__ import annotations

import shutil
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.main import get_command
from typer.testing import CliRunner

from patchloop.cli import app
from patchloop.dev import segments
from patchloop.dev.contracts import (
    DevRunRequest,
    PublicTurnDecision,
    RequestedTool,
    TextReplacementIntent,
)
from patchloop.dev.cost import DEFAULT_OUTPUT_CEILING, DevCostLedger, pricing_for_model
from patchloop.dev.tools import dev_tool_schemas, validate_tool_batch
from patchloop.errors import ContractError
from patchloop.runtime import repository_root, runtime_content_hash, runtime_content_paths
from patchloop.task_loader import load_task_package


def call(name: str, index: int = 0) -> RequestedTool:
    modes = {
        "read_file": "inspect",
        "search_files": "inspect",
        "run_check": "verify",
        "replace_text": "mutate",
        "finish_task": "finish",
        "stop_task": "stop",
    }
    mode = modes.get(name, "inspect")
    return RequestedTool(
        name=name,
        action_id=f"a-{index}",
        arguments={},
        turn_decision=PublicTurnDecision(
            mode=mode,
            basis="shared inspection basis" if mode == "inspect" else f"basis-{name}",
            evidence_goal="one shared source question" if mode == "inspect" else None,
        ),
    )


def test_tool_batch_contract_is_small_and_unmixed() -> None:
    assert validate_tool_batch([call("read_file"), call("search_files", 1)]) == "parallel_read"
    assert validate_tool_batch([call("run_check")]) == "single_action"
    assert validate_tool_batch([call("stop_task")]) == "single_action"
    with pytest.raises(ContractError):
        validate_tool_batch([call("read_file"), call("run_check", 1)])
    with pytest.raises(ContractError):
        validate_tool_batch([call("read_file", item) for item in range(5)])
    with pytest.raises(ContractError):
        validate_tool_batch([call("read_file"), call("search_files")])
    with pytest.raises(ContractError, match="turn_decision"):
        validate_tool_batch(
            [RequestedTool(name="read_file", action_id="missing-decision", arguments={})]
        )
    with pytest.raises(ContractError, match="mode"):
        validate_tool_batch(
            [
                RequestedTool(
                    name="run_check",
                    action_id="wrong-mode",
                    arguments={},
                    turn_decision=PublicTurnDecision(
                        mode="inspect",
                        basis="wrong family",
                        evidence_goal="not a check decision",
                    ),
                )
            ]
        )
    call_specific = call("search_files", 1)
    call_specific.turn_decision = PublicTurnDecision(
        mode="inspect",
        basis="Search for a distinct helper used by the source body.",
        evidence_goal="Locate the helper definition and its callers.",
    )
    assert validate_tool_batch([call("read_file"), call_specific]) == "parallel_read"
    with pytest.raises(ContractError, match="unavailable"):
        validate_tool_batch(
            [call("read_file")],
            allowed_tools=frozenset({"stop_task"}),
            max_parallel_reads=0,
        )
    targeted = call("read_file")
    targeted.arguments = {
        "path": "src/other.py",
        "start_line": 1,
        "end_line": 10,
    }
    with pytest.raises(ContractError, match="targeted repair"):
        validate_tool_batch(
            [targeted],
            allowed_read_paths=("src/changed.py",),
        )


def test_live_parallel_inspection_shape_allows_call_specific_decisions() -> None:
    calls = [
        RequestedTool(
            name="read_file",
            action_id="live-read-shape",
            arguments={
                "path": "pyfakefs/fake_os.py",
                "start_line": 917,
                "end_line": 1040,
            },
            turn_decision=PublicTurnDecision(
                mode="inspect",
                basis=(
                    "Need to inspect the full makedirs implementation and nearby helpers "
                    "to locate where parent traversal loses side effects before mutating."
                ),
                evidence_goal=(
                    "Capture the complete makedirs body and adjacent path-normalization/"
                    "creation helpers that influence parent-directory traversal semantics."
                ),
            ),
        ),
        RequestedTool(
            name="search_files",
            action_id="live-search-shape",
            arguments={
                "path_glob": "pyfakefs/fake_os.py",
                "query": "parent directory component",
            },
            turn_decision=PublicTurnDecision(
                mode="inspect",
                basis=(
                    "Need to search for any existing comments or helpers explicitly dealing "
                    "with parent-directory traversal in fake_os before deciding the patch site."
                ),
                evidence_goal=(
                    "Find references to parent traversal, normalization, or recursive parent "
                    "creation behavior in fake_os."
                ),
            ),
        ),
    ]

    assert validate_tool_batch(calls) == "parallel_read"


def test_mutation_contract_requires_exact_replacement_and_typed_alternative() -> None:
    base = {
        "path": "src/a.py",
        "old_text": "old",
        "new_text": "new",
        "occurrence": 1,
        "hypothesis": "state is reset too early",
        "expected_behavior": "state survives through cleanup",
        "causal_revision": None,
    }
    assert TextReplacementIntent.model_validate(base).causal_revision is None
    with pytest.raises(ValidationError):
        TextReplacementIntent.model_validate({**base, "new_text": "old"})
    with pytest.raises(ValidationError):
        TextReplacementIntent.model_validate(
            {key: value for key, value in base.items() if key != "hypothesis"}
        )
    with pytest.raises(ValidationError):
        TextReplacementIntent.model_validate({**base, "evidence_span_ids": ["span_a"]})
    revision = TextReplacementIntent.model_validate(
        {
            **base,
            "causal_revision": {
                "falsified_prior_hypothesis": "the state reset was not causal",
                "alternative_mechanism": "the caller discards the state",
            },
        }
    )
    assert revision.causal_revision is not None


@pytest.mark.parametrize("field", ["hypothesis", "expected_behavior"])
def test_mutation_explanation_schema_matches_internal_length_contract(field) -> None:
    mutation = next(
        schema for schema in dev_tool_schemas(finish_enabled=False)
        if schema["name"] == "replace_text"
    )
    public = mutation["parameters"]["properties"][field]
    internal = TextReplacementIntent.model_json_schema()["properties"][field]
    for keyword in ("type", "minLength", "maxLength"):
        assert public.get(keyword) == internal[keyword]

    base = {
        "path": "src/a.py", "old_text": "old", "new_text": "new", "occurrence": 1,
        "hypothesis": "a cause", "expected_behavior": "a result", "causal_revision": None,
    }
    for length in (0, 1, 1_500, 1_501):
        value = "가" * length
        advertised_valid = public["minLength"] <= len(value) <= public["maxLength"]
        if advertised_valid:
            assert getattr(TextReplacementIntent.model_validate({**base, field: value}), field)
        else:
            with pytest.raises(ValidationError):
                TextReplacementIntent.model_validate({**base, field: value})


def test_public_turn_decision_is_bounded_strict_and_mode_specific() -> None:
    valid = PublicTurnDecision(
        mode="inspect",
        basis="current public evidence requires one source fact",
        evidence_goal="locate the direct caller",
    )
    assert valid.mode == "inspect"
    with pytest.raises(ValidationError):
        PublicTurnDecision(
            mode="inspect",
            basis="x" * 801,
            evidence_goal="gap",
        )
    with pytest.raises(ValidationError):
        PublicTurnDecision(
            mode="inspect",
            basis="hypothesis",
            evidence_goal="gap",
            raw_reasoning="not an allowed field",
        )
    with pytest.raises(ValidationError, match="require one evidence_goal"):
        PublicTurnDecision(mode="inspect", basis="missing goal")
    with pytest.raises(ValidationError, match="only inspect"):
        PublicTurnDecision(mode="mutate", basis="ready", evidence_goal="extra")


def test_cost_cap_is_checked_before_dispatch_and_can_lower_output_ceiling() -> None:
    pricing = pricing_for_model("gpt-5.4-mini-2026-03-17")
    assert DevCostLedger(Decimal("0.001"), pricing).admit(1_000) is None
    ledger = DevCostLedger(Decimal("0.01"), pricing)
    admission = ledger.admit(1_000)
    assert admission is not None
    assert 128 <= admission.output_ceiling < DEFAULT_OUTPUT_CEILING
    cost = ledger.settle(input_tokens=1_000, cached_input_tokens=0, output_tokens=100)
    assert 0 < cost <= ledger.cap_nanos

    full = DevCostLedger(Decimal("1.20"), pricing).admit(1_000)
    assert full is not None
    assert full.output_ceiling == DEFAULT_OUTPUT_CEILING == 25_000

    restored = DevCostLedger(Decimal("0.01"), pricing)
    restored.restore_settled_usage(
        [{"call_id": "call-resumed", "cost_nanos": cost}],
        base_spent_nanos=123,
    )
    assert restored.spent_nanos == 123 + cost


def test_provider_options_fail_closed() -> None:
    task = Path("tasks/smoke/csv-quoted-newline/public.yaml")
    with pytest.raises(ValidationError):
        DevRunRequest(
            provider="openai",
            task=task,
            model="gpt-5.4-mini",
            max_cost_usd=Decimal("1"),
        )
    with pytest.raises(ValidationError):
        DevRunRequest(
            provider="openai",
            task=task,
            model="gpt-5.4-mini",
            env_file=Path("credential.env"),
        )
    with pytest.raises(ValidationError):
        DevRunRequest(
            provider="openai",
            task=task,
            model="gpt-5.4-mini",
            env_file=Path("credential.env"),
            max_cost_usd=Decimal("0"),
        )
    with pytest.raises(ValidationError):
        DevRunRequest(
            provider="mock",
            task=task,
            model="mock-dev",
            max_cost_usd=Decimal("1"),
        )
    with pytest.raises(ValidationError):
        DevRunRequest(provider="mock", task=task, model="mock-dev", repeat=7)
    with pytest.raises(ValidationError, match="--repeat 1"):
        DevRunRequest(
            provider="mock",
            task=task,
            model="mock-dev",
            repeat=2,
            resume_run_id="run_dev_existing0001",
        )


def test_full_model_price_reserves_uncached_input_and_settles_reported_cache() -> None:
    ledger = DevCostLedger(Decimal("1.20"), pricing_for_model("gpt-5.4-2026-03-05"))
    admission = ledger.admit(60_000)
    assert admission is not None
    assert admission.output_ceiling == 25_000
    assert admission.reserved_cost_nanos == 525_000_000
    assert ledger.settle(
        input_tokens=60_000, cached_input_tokens=40_000, output_tokens=25_000,
    ) == 435_000_000
    with pytest.raises(ContractError, match="no dev-head price"):
        pricing_for_model("gpt-5.4")


@pytest.mark.parametrize("policy", ["append-v1", "native-window-v1", "segmented-v1"])
def test_full_model_short_context_price_requires_counted_segment_bound(policy, monkeypatch) -> None:
    config = dict(
        provider="openai", task=Path("tasks/dev-train/pyfakefs-makedirs-parent-traversal-v2"),
        model="gpt-5.4-2026-03-05", env_file=Path("credential.env"),
        max_cost_usd=Decimal("1.20"), context_policy=policy,
    )
    if policy == "segmented-v1":
        assert DevRunRequest(**config).context_policy == policy
        monkeypatch.setattr(segments, "MAX_INPUT_TOKENS", 272_000)
    with pytest.raises(ValidationError, match="reviewed GPT-5.4 pricing requires"):
        DevRunRequest(**config)
    # The existing mini context options do not depend on this new model's prices.
    assert DevRunRequest(**{**config, "model": "gpt-5.4-mini-2026-03-17"})


def test_cli_exposes_only_dev_doctor_and_task_commands() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "dev" in result.stdout
    assert "rapid" not in result.stdout
    assert "evaluate" not in result.stdout
    assert "resume" not in result.stdout

    dev_command = get_command(app).commands["dev"]
    resume_option = next(parameter for parameter in dev_command.params
                         if parameter.name == "resume_run_id")
    assert "--resume-run-id" in resume_option.opts


@pytest.mark.parametrize(
    ("relative_path", "public_hash", "private_hash"),
    [
        (
            "smoke/csv-quoted-newline",
            "sha256:e396266522131f4aabfaae3fd140e33c60eaab17dfdd7bca18be03be3a93e04d",
            "sha256:c2174e536111cec56d29ad59bb0d547bd38febfff156bb7ca63cdc42c7ef65be",
        ),
        (
            "dev-train/duration-minute-boundary",
            "sha256:bcd131c3449e9d9b8c193847a3bced62e75934bd53ed49747f3847abec1f5a6b",
            "sha256:27b0045d5b3c8e0a303f24115e75a8b49cf840750091905994a6f08dd4b148bc",
        ),
        (
            "cross-repo-heldout/kubeflow-exit-handler-after-dependencies",
            "sha256:dfaa69083d119046f78f532a99db3cf9eb0ca2a4b34ca73f70f62242a22d5f8c",
            "sha256:bc8c6e70c15d926e24c6b7fcbcdf471b5577704ea9e46fea4f93cf47a4955798",
        ),
    ],
)
def test_task_identity_hashes_survive_reset(
    relative_path: str,
    public_hash: str,
    private_hash: str,
) -> None:
    package = load_task_package(repository_root() / "tasks" / relative_path)
    assert package.public_spec_hash == public_hash
    assert package.private_spec_hash == private_hash


def test_loguru_feedback_v2_preserves_v1_and_adds_public_contract() -> None:
    root = repository_root() / "tasks" / "dev-train"
    original = load_task_package(root / "loguru-invalid-format-feedback")
    revised = load_task_package(root / "loguru-invalid-format-feedback-v2")

    assert original.public.task_id == revised.public.task_id
    assert original.public.task_version == original.private.task_version == 1
    assert revised.public.task_version == revised.private.task_version == 2
    assert original.task_content_hash == (
        "sha256:3032f1b36e3089479a612805c0681e73991c445c131275f75b8ecc35ba929579"
    )
    assert revised.task_content_hash == (
        "sha256:61704553b8ba733bad7350561eec397a7a6c04365a56ef61854a9e12cefe259d"
    )
    assert [check.id for check in original.public.visible_checks] == [
        "upstream-format-regression",
        "basic-format-regression",
        "patcher-field-regression",
    ]
    assert [check.id for check in revised.public.visible_checks] == [
        "invalid-format-feedback-contract",
        "upstream-format-regression",
        "basic-format-regression",
        "patcher-field-regression",
    ]


def test_loguru_feedback_v3_preserves_v2_and_aligns_private_oracle() -> None:
    root = repository_root() / "tasks" / "dev-train"
    predecessor_root = root / "loguru-invalid-format-feedback-v2"
    successor_root = root / "loguru-invalid-format-feedback-v3"
    predecessor = load_task_package(predecessor_root)
    successor = load_task_package(successor_root)

    assert predecessor.public.task_version == predecessor.private.task_version == 2
    assert successor.public.task_version == successor.private.task_version == 3
    assert predecessor.task_content_hash == (
        "sha256:61704553b8ba733bad7350561eec397a7a6c04365a56ef61854a9e12cefe259d"
    )
    assert successor.task_content_hash == (
        "sha256:21f5f668c4f6ef85a2c1a45f4371cbd050de0e73dfcf8605a3c398413374c15b"
    )

    predecessor_public = predecessor.public.model_dump(mode="json")
    successor_public = successor.public.model_dump(mode="json")
    predecessor_public.pop("task_version")
    successor_public.pop("task_version")
    assert successor_public == predecessor_public

    predecessor_private = predecessor.private.model_dump(mode="json")
    successor_private = successor.private.model_dump(mode="json")
    predecessor_private.pop("task_version")
    successor_private.pop("task_version")
    assert successor_private == predecessor_private

    preserved_paths = {
        "environment.yaml",
        "reference.patch",
        "bad/catch-true-only.patch",
        "bad/forbidden-path.patch",
        "bad/generic-message.patch",
        "bad/hardcoded-reproduction.patch",
        "bad/noop.patch",
        "bad/swallow-catch-false.patch",
    }
    for relative_path in preserved_paths:
        assert (successor_root / relative_path).read_bytes() == (
            predecessor_root / relative_path
        ).read_bytes()

    predecessor_hidden = (predecessor_root / "hidden/test_invalid_format_feedback.py").read_text(
        encoding="utf-8"
    )
    successor_hidden = (successor_root / "hidden/test_invalid_format_feedback.py").read_text(
        encoding="utf-8"
    )
    assert 'self.assertIn("logger.bind(key=value)", feedback)' in predecessor_hidden
    assert 'self.assertIn("logger.bind(key=value)", feedback)' not in successor_hidden
    assert "self.assertRegex(feedback, BINDING_GUIDANCE)" in successor_hidden


def test_pyfakefs_parent_traversal_v2_preserves_v1_and_adds_public_contract() -> None:
    root = repository_root() / "tasks" / "dev-train"
    predecessor_root = root / "pyfakefs-makedirs-parent-traversal"
    successor_root = root / "pyfakefs-makedirs-parent-traversal-v2"
    predecessor = load_task_package(predecessor_root)
    successor = load_task_package(successor_root)

    assert predecessor.public.task_version == predecessor.private.task_version == 1
    assert successor.public.task_version == successor.private.task_version == 2
    assert predecessor.task_content_hash == (
        "sha256:91361d0f68e98968e31d5902797dd7aeadb59777804e6342257ff8121991d141"
    )
    assert successor.task_content_hash == (
        "sha256:276b791c4c0cb1c18fa8659f6518a172f0d05b239526c0f21a7d0d2c378def87"
    )
    assert [check.id for check in predecessor.public.visible_checks] == [
        "upstream-fake-os-regression"
    ]
    assert [check.id for check in successor.public.visible_checks] == [
        "parent-traversal-contract",
        "upstream-fake-os-regression",
    ]

    predecessor_public = predecessor.public.model_dump(mode="json")
    successor_public = successor.public.model_dump(mode="json")
    predecessor_public.pop("task_version")
    successor_public.pop("task_version")
    predecessor_checks = predecessor_public.pop("visible_checks")
    successor_checks = successor_public.pop("visible_checks")
    assert successor_public == predecessor_public
    assert successor_checks[1:] == predecessor_checks

    predecessor_private = predecessor.private.model_dump(mode="json")
    successor_private = successor.private.model_dump(mode="json")
    predecessor_private.pop("task_version")
    successor_private.pop("task_version")
    assert successor_private == predecessor_private

    predecessor_paths = {
        path.relative_to(predecessor_root).as_posix()
        for path in predecessor_root.rglob("*")
        if path.is_file()
    }
    successor_paths = {
        path.relative_to(successor_root).as_posix()
        for path in successor_root.rglob("*")
        if path.is_file()
    }
    assert successor_paths == predecessor_paths
    for relative_path in predecessor_paths - {"public.yaml", "private.yaml"}:
        assert (successor_root / relative_path).read_bytes() == (
            predecessor_root / relative_path
        ).read_bytes()


def test_v1_task_content_hash_binds_hidden_bytes(tmp_path) -> None:
    source = repository_root() / "tasks" / "smoke" / "csv-quoted-newline"
    copied = tmp_path / "task"
    shutil.copytree(source, copied)
    before = load_task_package(copied)
    hidden = copied / "hidden" / "test_multiline.py"
    hidden.write_text(hidden.read_text(encoding="utf-8") + "\n# content drift\n", encoding="utf-8")
    after = load_task_package(copied)
    assert after.public_spec_hash == before.public_spec_hash
    assert after.private_spec_hash == before.private_spec_hash
    assert after.task_content_hash != before.task_content_hash


def test_task_content_hash_binds_raw_yaml_bytes_not_only_normalized_values(tmp_path) -> None:
    source = repository_root() / "tasks" / "smoke" / "csv-quoted-newline"
    copied = tmp_path / "task"
    shutil.copytree(source, copied)
    before = load_task_package(copied)
    public = copied / "public.yaml"
    public.write_text(
        public.read_text(encoding="utf-8") + "\n# byte-only change\n",
        encoding="utf-8",
    )
    after = load_task_package(copied)
    assert after.public_spec_hash == before.public_spec_hash
    assert after.private_spec_hash == before.private_spec_hash
    assert after.task_content_hash != before.task_content_hash


def test_runtime_content_hash_covers_all_python_and_lock_inputs() -> None:
    root = repository_root()
    paths = runtime_content_paths(root)
    expected_python = {
        path.relative_to(root).as_posix()
        for path in (root / "patchloop").rglob("*.py")
        if path.is_file()
    }
    assert expected_python.issubset(paths)
    assert {
        "pyproject.toml", "uv.lock", "docker/probe_runner.py", "docker/Dockerfile.sandbox",
    }.issubset(paths)
    assert runtime_content_hash(root).startswith("sha256:")
