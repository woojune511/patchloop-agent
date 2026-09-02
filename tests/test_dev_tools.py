from __future__ import annotations

import subprocess

from patchloop.dev.contracts import RequestedTool
from patchloop.dev.model import DEV_SYSTEM_PROMPT, MOCK_MUTATIONS
from patchloop.dev.tools import dev_tool_schemas
from patchloop.sandbox.runner import SandboxResult
from patchloop.util import sha256_json


class CountingFailSandbox:
    official = False

    def __init__(self) -> None:
        self.calls = 0

    def run_check(self, workspace, check):
        del workspace, check
        self.calls += 1
        return SandboxResult(
            command=["fake-check"],
            exit_code=1,
            stdout="same public failure",
            stderr="",
            duration_ms=1,
            timed_out=False,
            truncated=False,
            original_output_bytes=19,
        )


def read_calls() -> list[RequestedTool]:
    return [
        RequestedTool(
            name="search_files",
            action_id="search-source",
            arguments={"query": "def parse_rows", "path_glob": "**/*.py"},
        ),
        RequestedTool(
            name="read_file",
            action_id="read-source",
            arguments={
                "path": "mini_data_utils/csvlite.py",
                "start_line": 1,
                "end_line": 80,
            },
        ),
    ]


def mutation_call(gateway, *, action_id: str = "mutation-1", alternative: bool = False):
    mutation = MOCK_MUTATIONS["csv-quoted-newline"]
    spans = [item["span_id"] for item in gateway.spans.values() if item["path"] == mutation.path]
    return RequestedTool(
        name="apply_git_diff",
        action_id=action_id,
        arguments={
            "git_diff": mutation.patch,
            "hypothesis": mutation.hypothesis,
            "expected_behavior": mutation.expected_behavior,
            "evidence_span_ids": spans[:2],
            "edit_anchor": {
                "path": mutation.path,
                "old_text": mutation.anchor,
                "occurrence": 1,
            },
            "falsified_prior_hypothesis": (
                "physical line handling was the only cause" if alternative else None
            ),
            "alternative_mechanism": (
                "parser lifetime, not line normalization, owns record boundaries"
                if alternative
                else None
            ),
        },
    )


def test_mutation_tool_contract_requires_unwrapped_raw_git_diff() -> None:
    schemas = dev_tool_schemas(finish_enabled=False)
    mutation = next(schema for schema in schemas if schema["name"] == "apply_git_diff")

    assert all(schema["name"] != "apply_patch" for schema in schemas)
    assert mutation["parameters"]["required"][0] == "git_diff"
    assert mutation["parameters"]["properties"]["git_diff"]["pattern"] == "^diff --git a/"
    assert set(mutation["parameters"]["required"]) == set(
        mutation["parameters"]["properties"]
    )
    assert mutation["parameters"]["additionalProperties"] is False
    assert "diff --git a/<path> b/<path>" in mutation["description"]
    assert "*** Begin Patch" in mutation["description"]
    assert "apply_git_diff git_diff" in DEV_SYSTEM_PROMPT
    assert "Never use \"*** Begin Patch\"" in DEV_SYSTEM_PROMPT


def test_patch_wrapper_from_live_transcript_fails_with_exact_git_diff_guidance(
    gateway_factory,
) -> None:
    gateway, _, _ = gateway_factory()
    gateway.execute_batch(read_calls())
    mutation = mutation_call(gateway, action_id="wrapped-live-mutation")
    mutation.arguments["git_diff"] = (
        "*** Begin Patch\n"
        "*** Update File: mini_data_utils/csvlite.py\n"
        "@@\n"
        "-    return rows\n"
        "+    return list(csv.reader(io.StringIO(text)))\n"
        "*** End Patch"
    )

    result = gateway.execute(mutation)

    assert result.status == "failed"
    assert result.error_code == "CONTRACT_ERROR"
    assert "must begin exactly with 'diff --git a/<path> b/<path>'" in result.message
    assert gateway.accepted_mutations == 0


def test_parallel_read_mutation_check_and_finish(gateway_factory) -> None:
    gateway, _, _ = gateway_factory()
    read_results = gateway.execute_batch(read_calls())
    assert [result.status for result in read_results] == ["succeeded", "succeeded"]
    mutation = gateway.execute(mutation_call(gateway))
    assert mutation.status == "succeeded"
    check = gateway.execute(
        RequestedTool(
            name="run_check",
            action_id="visible-check",
            arguments={"check_id": "existing-unit-tests"},
        )
    )
    assert check.output["passed"] is True
    assert gateway.visible_checks_pass() is True
    finish = gateway.execute(RequestedTool(name="finish_task", action_id="finish", arguments={}))
    assert finish.status == "succeeded"
    assert finish.output["patch_hash"] == gateway.current_diff_hash


def test_allowed_path_and_stale_evidence_fail_closed(gateway_factory) -> None:
    gateway, _, _ = gateway_factory()
    gateway.execute_batch(read_calls())
    stale_call = mutation_call(gateway, action_id="stale-mutation")
    forbidden_read = gateway.execute(
        RequestedTool(
            name="read_file",
            action_id="read-test",
            arguments={"path": "tests/test_csvlite.py", "start_line": 1, "end_line": 20},
        )
    )
    test_span = forbidden_read.output["spans"][0]["span_id"]
    forbidden = gateway.execute(
        RequestedTool(
            name="apply_git_diff",
            action_id="forbidden-mutation",
            arguments={
                "git_diff": (
                    "diff --git a/tests/test_csvlite.py b/tests/test_csvlite.py\n"
                    "--- a/tests/test_csvlite.py\n"
                    "+++ b/tests/test_csvlite.py\n"
                    "@@ -1,3 +1,4 @@\n"
                    " import unittest\n"
                    "+# forbidden\n"
                    " \n"
                    " from mini_data_utils import parse_rows\n"
                ),
                "hypothesis": "tests need a bypass",
                "expected_behavior": "tests change",
                "evidence_span_ids": [test_span],
                "edit_anchor": {
                    "path": "tests/test_csvlite.py",
                    "old_text": "import unittest",
                    "occurrence": 1,
                },
                "falsified_prior_hypothesis": None,
                "alternative_mechanism": None,
            },
        )
    )
    assert forbidden.status == "failed"
    assert forbidden.error_code == "CONTRACT_ERROR"

    assert gateway.execute(mutation_call(gateway, action_id="valid-mutation")).status == "succeeded"
    assert stale_call.arguments["evidence_span_ids"][0] not in gateway.spans
    stale = gateway.execute(stale_call)
    assert stale.status == "failed"
    assert "stale" in stale.message


def test_read_cache_promotes_evidence_and_resets_after_mutation(gateway_factory) -> None:
    gateway, _, _ = gateway_factory()
    first_call = read_calls()[1]
    first = gateway.execute(first_call)
    repeated = gateway.execute(first_call.model_copy(update={"action_id": "read-source-again"}))
    assert first.evidence_cache_hit is False
    assert repeated.evidence_cache_hit is True
    assert repeated.output["new_span_count"] == 0
    assert repeated.output["evidence_repetition"] == 2
    assert repeated.output["stagnation_signal"] is True

    assert gateway.execute(mutation_call(gateway)).status == "succeeded"
    refreshed = gateway.execute(
        first_call.model_copy(update={"action_id": "read-source-after-mutation"})
    )
    assert refreshed.evidence_cache_hit is False
    assert refreshed.output["new_span_count"] == 1


def test_new_files_and_untracked_submission_fail_closed(gateway_factory) -> None:
    gateway, _, workspace = gateway_factory()
    gateway.public_task = gateway.public_task.model_copy(
        update={
            "constraints": gateway.public_task.constraints.model_copy(
                update={"allowed_paths": ["mini_data_utils/**"], "max_changed_files": 2}
            )
        }
    )
    gateway.execute_batch(read_calls())
    mutation = mutation_call(gateway, action_id="mixed-new-file")
    mutation.arguments["git_diff"] += (
        "diff --git a/mini_data_utils/new_helper.py b/mini_data_utils/new_helper.py\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        "+++ b/mini_data_utils/new_helper.py\n"
        "@@ -0,0 +1 @@\n"
        "+VALUE = 1\n"
    )
    rejected = gateway.execute(mutation)
    assert rejected.status == "failed"
    assert "tracked public file" in rejected.message
    assert not (workspace / "mini_data_utils" / "new_helper.py").exists()

    assert gateway.execute(mutation_call(gateway, action_id="tracked-only")).status == "succeeded"
    check = gateway.execute(
        RequestedTool(
            name="run_check",
            action_id="untracked-visible-check",
            arguments={"check_id": "existing-unit-tests"},
        )
    )
    assert check.output["passed"] is True
    (workspace / "unexpected.txt").write_text("not submitted\n", encoding="utf-8")
    finish = gateway.execute(
        RequestedTool(name="finish_task", action_id="untracked-finish", arguments={})
    )
    assert finish.status == "failed"
    assert "untracked files" in finish.message


def test_repeated_signature_across_two_diffs_requires_alternative(gateway_factory) -> None:
    gateway, _, _ = gateway_factory(sandbox=CountingFailSandbox())
    gateway.execute_batch(read_calls())
    gateway._remember_check(  # noqa: SLF001 - direct reconstruction of durable public history
        {
            "check_id": "existing-unit-tests",
            "diff_hash": "sha256:diff-one",
            "passed": False,
            "failure_signature": "sha256:same-failure",
        }
    )
    gateway._remember_check(  # noqa: SLF001
        {
            "check_id": "existing-unit-tests",
            "diff_hash": "sha256:diff-two",
            "passed": False,
            "failure_signature": "sha256:same-failure",
        }
    )
    assert gateway.requires_alternative is True
    rejected = gateway.execute(mutation_call(gateway, action_id="missing-alternative"))
    assert rejected.status == "failed"
    assert "alternative_mechanism" in rejected.message
    accepted = gateway.execute(
        mutation_call(gateway, action_id="material-alternative", alternative=True)
    )
    assert accepted.status == "succeeded"
    assert gateway.requires_alternative is False


def test_action_replay_and_crash_reconciliation_do_not_duplicate_mutation(
    gateway_factory,
) -> None:
    gateway, journal, workspace = gateway_factory()
    read = read_calls()[1]
    first = gateway.execute(read)
    replay = gateway.execute(read)
    assert first.output == replay.output
    assert replay.replayed is True

    call = mutation_call(gateway, action_id="crash-mutation")
    input_hash = sha256_json({"tool": call.name, "arguments": call.arguments})
    journal.append(
        "action_started",
        {
            "action_id": call.action_id,
            "input_hash": input_hash,
            "tool": call.name,
            "arguments": call.arguments,
            "baseline_diff_hash": gateway.current_diff_hash,
            "mutation_admitted": True,
        },
    )
    applied = subprocess.run(
        ["git", "apply", "--whitespace=nowarn", "-"],
        cwd=workspace,
        input=call.arguments["git_diff"].encode("utf-8"),
        capture_output=True,
        check=False,
    )
    assert applied.returncode == 0

    restarted, _, _ = gateway_factory()
    # Rebind to the durable workspace/journal to simulate a process restart.
    restarted.workspace = workspace
    restarted.journal = journal
    restarted.spans.clear()
    restarted._hydrate()  # noqa: SLF001
    recovered = restarted.execute(call)
    assert recovered.status == "succeeded"
    assert recovered.output["recovered_after_crash"] is True
    assert len([e for e in journal.events() if e["event_type"] == "action_finished"]) == 2


def test_completed_check_replays_after_restart_without_execution(gateway_factory) -> None:
    sandbox = CountingFailSandbox()
    gateway, journal, workspace = gateway_factory(sandbox=sandbox)
    call = RequestedTool(
        name="run_check",
        action_id="restart-check",
        arguments={"check_id": "existing-unit-tests"},
    )
    first = gateway.execute(call)
    assert first.status == "succeeded"
    assert sandbox.calls == 1

    restarted, _, _ = gateway_factory(sandbox=sandbox)
    restarted.workspace = workspace
    restarted.journal = journal
    restarted._hydrate()  # noqa: SLF001 - simulate process reconstruction
    replay = restarted.execute(call)
    assert replay.replayed is True
    assert sandbox.calls == 1
