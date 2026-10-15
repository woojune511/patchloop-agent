"""Finite fake SDK/check/evaluator responses around real registered public edits.

No target Python is imported/executed. Every target check, probe and evaluation
receipt is synthetic. Workspaces are isolated copies of the frozen public prefix.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from diagnostics import host_plan_checkpoint as checkpoint
from diagnostics import host_plan_execution as execution
from diagnostics import host_plan_review as review
from diagnostics import observation_exposure as exposure
from diagnostics.checkpoint_continuation import ScriptedClient
from diagnostics.decision_sampler import require
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Verdicts, VerdictState
from patchloop.dev import runner
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.runtime import git_commit, repository_root
from patchloop.sandbox.runner import SandboxResult
from patchloop.util import canonical_json, sha256_json

PATH = "server/opensandbox_server/services/validators.py"
ANCHOR = "Shared validation helpers for container-based sandbox services."


def call(name, arguments, mode, identity, *, plan=None):
    return {
        "name": name,
        "action_id": identity,
        "arguments": {
            **arguments,
            "turn_decision": {
                "mode": mode,
                "basis": "Synthetic connector verification; no model/repair evidence.",
                "evidence_goal": "Inspect public source." if mode == "inspect" else None,
                "memory_update": None,
                "plan_update": plan,
            },
        },
    }


def script(*, edits=2, stop=False):
    steps = [
        [
            call(
                "read_file",
                {"path": PATH, "start_line": 14, "end_line": 34},
                "inspect",
                "mock_read",
                plan="Synthetic replacement; verify connector flow.",
            )
        ]
    ]
    if stop:
        return [
            *steps,
            [
                call(
                    "stop_task",
                    {"reason_code": "insufficient_public_evidence", "summary": "Synthetic stop."},
                    "stop",
                    "mock_stop",
                )
            ],
        ]
    text = ANCHOR
    for index in range(edits):
        new = ANCHOR + f" SYNTHETIC CONNECTOR {index + 1}."
        steps.append(
            [
                call(
                    "replace_text",
                    {
                        "path": PATH,
                        "old_text": text,
                        "new_text": new,
                        "occurrence": 1,
                        "causal_revision": None,
                        "hypothesis": "Synthetic docstring edit.",
                        "expected_behavior": "Exercise registered mutation only.",
                    },
                    "mutate",
                    f"mock_edit_{index}",
                )
            ]
        )
        text = new
    steps += [
        [call("run_check", {"check_id": "base-regression"}, "verify", "mock_check")],
        [call("finish_task", {}, "finish", "mock_finish")],
    ]
    return steps


@contextmanager
def offline_environment(
    branch, client, *, check_outcomes=None, public_pass=True, cleanup=True, safety=VerdictState.PASS
):
    require(isinstance(client, ScriptedClient) and branch.provider_free, "offline branch required")
    outcomes = iter(check_outcomes or [True] * 20)
    calls = {"checks": [], "public": [], "evaluations": [], "probes": []}
    original_probe = runner.DockerProbeSandbox

    class Sandbox:
        official, backend, supports_execution_deadline = False, "docker", True
        supports_public_execution = False

        def run_check(self, workspace, check, **kwargs):
            calls["checks"].append(check.id)
            passed = next(outcomes)
            return SandboxResult(
                list(check.command),
                0 if passed else 1,
                "SYNTHETIC CHECK ONLY",
                "",
                0,
                False,
                False,
                20,
            )

    class Probe(exposure.SyntheticProbe):
        def __init__(self, **kwargs):
            super().__init__(branch.envelope, {}, **kwargs)
            self.profile = original_probe(**kwargs).current_profile()
            require(
                sha256_json(self.profile) == branch.envelope.probe_profile_hash,
                "synthetic receipt masks profile mismatch",
            )

        def run_probe(self, *args, **kwargs):
            calls["probes"].append(kwargs)
            raise ContractError("no model probe is scheduled by this finite rehearsal")

    def public(branch, assessment, deadline):
        require(hasattr(branch, "grade"), "public execution before EUR seal")
        calls["public"].append(deadline.remaining_seconds())
        rows = [
            {"case": k, "outcome": v if public_pass else "ACCEPT"}
            for k, v in assessment["primary_expected"].items()
        ]
        rows += [{"case": k, "outcome": "ACCEPT"} for k in assessment["supplementary_only"]]
        return {
            "stdout": canonical_json(rows),
            "exit_code": 0,
            "timed_out": False,
            "truncated": False,
            "cleanup_failed": not cleanup,
            "deadline_exhausted": False,
            "synthetic": True,
        }

    def evaluate(engine, *args, **kwargs):
        require(hasattr(branch, "grade"), "evaluation before EUR seal")
        require(len(calls["public"]) == 1, "evaluation before public terminal result")
        calls["evaluations"].append(kwargs["deadline"].remaining_seconds())
        return SimpleNamespace(
            scope_compliant_success=True,
            verdicts=Verdicts(
                hidden_tests=VerdictState.PASS,
                regression_tests=VerdictState.PASS,
                scope_policy=VerdictState.PASS,
                safety_policy=safety,
            ),
        )

    def forbidden(*args, **kwargs):
        raise ContractError("network or target execution forbidden in provider-free rehearsal")

    with (
        patch("socket.socket.connect", forbidden),
        patch("socket.create_connection", forbidden),
        patch.object(runner, "load_exact_openai_api_key", lambda _: "offline-unused"),
        patch.object(runner, "_live_source_preflight", lambda *a, **k: None),
        patch.object(runner, "_live_sandbox_preflight", lambda *a, **k: Sandbox()),
        patch.object(runner, "DockerProbeSandbox", Probe),
        patch.object(runner.EvaluationEngine, "evaluate", evaluate),
        patch.object(review, "execute_public", public),
    ):
        yield calls


def rehearse(output):
    plan, source = checkpoint.load_design()
    output = output.resolve()
    exposure.disjoint(output, (repository_root(), source.root, checkpoint.DESIGN.parent))
    output.mkdir()
    journal, store = DevJournal(output, "run_dev_hostplanmock"), ArtifactStore(output)
    group = execution.Invocation(journal)
    journal.append(
        "host_plan_mock_started",
        {
            "design_hash": checkpoint.DESIGN_HASH,
            "implementation_hash": exposure.implementation_hash(),
            "runtime_hash": runner._runtime_hash(),
            "harness_git_commit": git_commit(),
        },
    )
    details = {}

    def prepare(arm):
        return checkpoint.restore_branch(
            plan, source, output / ("O1-" + arm), arm, clock=group.clock, deadline=group.deadline
        )

    def execute(branch):
        client = ScriptedClient(script())
        with offline_environment(branch, client) as calls:
            result = execution.run_row(branch, group, reviewer=review.inert_reviewer, client=client)
        details[branch.row["cell"]] = calls
        return result

    rows = execution.run_roster(group, prepare, execute)
    checkpoint.load_design()
    okay = all(
        r.get("result", {})
        and r["result"]["terminal"] == "EVALUATOR_PASS"
        and r["accepted_new_edits"] == 2
        and not r["stop_remaining"]
        and r["first_input_parity"]["status"] == "PASS"
        for r in rows
    )
    result = {
        "status": "PASS" if okay else "FAIL",
        "official": False,
        "provider_free": True,
        "paid_authorized": False,
        "design_hash": checkpoint.DESIGN_HASH,
        "implementation_hash": exposure.implementation_hash(),
        "rows": rows,
        "synthetic_calls": details,
        "provider_calls": 0,
        "credential_reads": 0,
        "metadata_calls": 0,
        "billed_cost_nanos": 0,
        "actual_target_checks": 0,
        "actual_target_diagnostics": 0,
        "actual_isolated_evaluations": 0,
        "actual_acceptance": "NOT_RUN",
        "model_uptake": "NOT_RUN",
    }
    journal.append(
        "host_plan_mock_finished", {"result": store.put_json(result).model_dump(mode="json")}
    )
    with (output / "result.json").open("x", encoding="utf-8") as stream:
        stream.write(canonical_json(result) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    print(canonical_json(rehearse(parser.parse_args().output)))


if __name__ == "__main__":
    main()
