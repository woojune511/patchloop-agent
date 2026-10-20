"""Public E/U/R seal followed by the frozen public program and isolated evaluation."""

from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from time import sleep
from unittest.mock import patch

from diagnostics import host_plan_checkpoint as checkpoint
from diagnostics.decision_sampler import require
from diagnostics.host_plan_execution import BoundStop, phase_deadline
from patchloop.contracts import RegisteredCheck
from patchloop.dev import runner
from patchloop.repository import WorkspaceManager
from patchloop.sandbox.runner import DockerSandbox
from patchloop.util import ensure_within, sha256_bytes

PUBLIC_EVENTS = {
    "action_started",
    "action_finished",
    "turn_decision_recorded",
    "working_notes_updated",
    "working_plan_updated",
}
ASSESSMENTS = {
    "host_plan_terminal_public_started",
    "host_plan_terminal_public",
    "host_plan_isolated_evaluation_started",
    "evaluator_started",
    "evaluator_finished",
}


def file_reviewer(directory):
    """One public semantic grade within this row's 120-second review phase."""

    def receive(ref, packet, deadline):
        ready, grade = directory / "public-review-ready.json", directory / "public-grade.json"
        require(not ready.exists() and not grade.exists(), "public review already used")
        deadline.check()
        with ready.open("x", encoding="utf-8") as stream:
            stream.write(
                json.dumps(
                    {
                        "artifact": ref.model_dump(mode="json"),
                        "deadline_monotonic": deadline.expires_at,
                    }
                )
                + "\n"
            )
        while not grade.exists():
            deadline.check()
            sleep(min(0.2, deadline.remaining_seconds()))
        deadline.check()
        return json.loads(grade.read_bytes())

    return receive


def validate_grade(grade, packet, review_hash):
    require(grade["review_hash"] == review_hash, "public grade binding changed")
    decisions = packet["plan_replacements"]
    reviews = grade["plan_reviews"]
    require(
        len(reviews) == len(decisions)
        and {r["sequence"] for r in reviews} == {d["sequence"] for d in decisions},
        "exactly one semantic review per plan replacement required",
    )
    events = {e["sequence"]: e for e in packet["public_events"]}
    for item in reviews:
        decision = next(d for d in decisions if d["sequence"] == item["sequence"])
        require(
            item["status"] in {"PASS", "FAIL", "NOT_OBSERVABLE"} and item["reason"],
            "semantic plan judgment required",
        )
        require(item["input_hash"] == decision["input_hash"], "plan/input linkage changed")
        citations = item["public_event_sequences"]
        require(
            set(citations) <= events.keys() and all(s <= item["sequence"] for s in citations),
            "plan judgment cites future or nonpublic evidence",
        )
        if item["status"] in {"PASS", "FAIL"}:
            require(item["sequence"] in citations, "plan judgment needs its decision citation")
    u = (
        "NOT_EXERCISED"
        if not reviews
        else "FAIL"
        if any(r["status"] == "FAIL" for r in reviews)
        else "NOT_OBSERVABLE"
        if any(r["status"] == "NOT_OBSERVABLE" for r in reviews)
        else "PASS"
    )
    require(grade["U"] == u, "U aggregation must retain an earlier narrowing failure")
    require(
        grade["R"] in {"PASS", "FAIL", "NOT_ASSESSABLE"} and grade["R_reason"],
        "semantic final-source review required",
    )
    sources = packet["final_public_sources"]
    citations = grade["source_citations"]
    for citation in citations:
        source = sources[citation["path"]]
        require(
            citation["content_hash"] == source["content_hash"]
            and 1 <= citation["start_line"] <= citation["end_line"] <= source["line_count"],
            "source citation does not bind final public code",
        )
    if grade["R"] in {"PASS", "FAIL"}:
        require(citations, "R judgment requires final public-source citations")
    return {**grade, "E": packet["exposure"]["E"]}


def seal_review(branch, group, reviewer):
    require(not hasattr(branch, "review_started"), "public review cannot repeat")
    branch.review_started = True
    deadline = phase_deadline(branch, group, 120)
    deadline.check()
    events = branch.journal.events()
    require(
        not any(e["event_type"] in ASSESSMENTS for e in events[branch.inherited_events :]),
        "terminal assessment preceded public review",
    )
    diff = WorkspaceManager.diff_summary(branch.workspace, deadline=deadline)
    public = [
        {
            "sequence": e["sequence"],
            "event_type": e["event_type"],
            "payload": {k: v for k, v in e["payload"].items() if k != "continuation_ref"},
        }
        for e in events
        if e["event_type"] in PUBLIC_EVENTS
    ]
    replacements = []
    for event in public:
        if (
            event["sequence"] <= branch.inherited_events
            or event["event_type"] != "working_plan_updated"
            or event["payload"]["receipt"]["status"] not in {"created", "updated"}
        ):
            continue
        dispatch = next(
            (
                e
                for e in reversed(events)
                if e["sequence"] < event["sequence"] and e["event_type"] == "host_plan_dispatched"
            ),
            None,
        )
        require(dispatch is not None, "replacement has no delivered input")
        replacements.append(
            {
                "sequence": event["sequence"],
                "payload": event["payload"],
                "input_hash": dispatch["payload"]["request_hash"],
                "input": dispatch["payload"]["request"],
            }
        )
    sources = {}
    for path in sorted(
        set(diff.changed_files)
        | {
            "server/opensandbox_server/services/docker.py",
            "server/opensandbox_server/services/validators.py",
        }
    ):
        deadline.check()
        file = ensure_within(branch.workspace, path)
        if file.is_file():
            data = file.read_bytes()
            sources[path] = {
                "artifact": branch.store.put_bytes(data, "text/plain; charset=utf-8").model_dump(
                    mode="json"
                ),
                "content_hash": sha256_bytes(data),
                "line_count": len(data.decode().splitlines()),
            }
    packet = {
        "public_task": branch.package.public.model_dump(mode="json"),
        "public_events": public,
        "plan_replacements": replacements,
        "delivered_requests": [r["request"] for r in branch.dispatched],
        "new_events_after": branch.inherited_events,
        "final_patch": diff.patch,
        "patch_hash": diff.patch_hash,
        "final_public_sources": sources,
        "submitted": any(e["event_type"] == "submission_recorded" for e in events),
        "terminal_assessments_present": False,
        "synthetic": branch.provider_free,
        "exposure": {
            "E": "PASS" if branch.dispatched else "UNEXPOSED",
            "first_parity": getattr(branch, "first_parity", None),
            "dispatched_request_hashes": [r["request_hash"] for r in branch.dispatched],
        },
        "rubric": json.loads(checkpoint.read_bound(branch.plan["grading"])),
    }
    ref = branch.store.put_json(packet)
    branch.journal.append("host_plan_public_review", {"artifact": ref.model_dump(mode="json")})
    grade = reviewer(ref, packet, deadline)
    deadline.check()
    grade = validate_grade(grade, packet, ref.content_hash)
    branch.public_review, branch.grade = ref, grade
    branch.journal.append("host_plan_EUR_sealed", grade)
    return grade


def inert_reviewer(ref, packet, deadline):
    """Inert transport provides no semantic evidence about a model or repair."""
    return {
        "review_hash": ref.content_hash,
        "U": "NOT_OBSERVABLE" if packet["plan_replacements"] else "NOT_EXERCISED",
        "plan_reviews": [
            {
                "sequence": d["sequence"],
                "input_hash": d["input_hash"],
                "status": "NOT_OBSERVABLE",
                "public_event_sequences": [],
                "reason": "Synthetic plan; model uptake NOT_RUN.",
            }
            for d in packet["plan_replacements"]
        ],
        "R": "NOT_ASSESSABLE",
        "R_reason": "Synthetic connector rehearsal only.",
        "source_citations": [],
    }


def public_grade(receipt, assessment):
    if receipt.get("exit_code") != 0 or any(
        receipt.get(k) for k in ("timed_out", "truncated", "cleanup_failed", "deadline_exhausted")
    ):
        return {"status": "ERROR"}

    try:
        rows = json.loads(receipt["stdout"])
        expected = assessment["primary_expected"]
        ids = set(expected) | set(assessment["supplementary_only"])
        require(
            isinstance(rows, list) and len(rows) == len(ids) and {r["case"] for r in rows} == ids,
            "missing/duplicate public observations",
        )
        require(all(r["outcome"] in {"ACCEPT", "REJECT"} for r in rows), "unknown outcome")
        by_case = {r["case"]: r for r in rows}
        return {
            "status": "PASS"
            if all(by_case[k]["outcome"] == v for k, v in expected.items())
            else "FAIL",
            "primary": [r for r in rows if r["case"] in expected],
            "supplementary": [r for r in rows if r["case"] not in expected],
        }
    except (KeyError, TypeError, ValueError, runner.ContractError):
        return {"status": "ERROR"}


def repair_success(row):
    """U is a mechanism axis, never an extra requirement for actual correct repair."""
    if row.get("synthetic"):
        return "NOT_RUN"
    result = row.get("result") or {}
    evaluator = result.get("evaluator") or {}
    if (
        row.get("stop_remaining")
        or result.get("terminal") not in {"EVALUATOR_PASS", "EVALUATOR_FAIL"}
        or row.get("E") != "PASS"
        or row.get("R") == "NOT_ASSESSABLE"
    ):
        return "NOT_ASSESSABLE"
    if (
        any(row.get(k) == "FAIL" for k in ("R", "P"))
        or result["terminal"] == "EVALUATOR_FAIL"
        or evaluator.get("safety_state") == "FAIL"
    ):
        return "FAIL"
    if (
        row.get("R") == row.get("P") == evaluator.get("safety_state") == "PASS"
        and evaluator.get("task_acceptance") == "PASS"
    ):
        return "PASS"
    return "NOT_ASSESSABLE"


def pair_result(rows):
    outcomes = [repair_success(row) for row in rows]
    if len(outcomes) != 2 or any(s not in {"PASS", "FAIL"} for s in outcomes):
        interpretation = "INCONCLUSIVE"
    else:
        interpretation = {
            ("FAIL", "PASS"): "LOCAL_FAVORABLE_ONLY",
            ("PASS", "FAIL"): "LOCAL_UNFAVORABLE",
            ("PASS", "PASS"): "NO_DEMONSTRATED_REPAIR_ADVANTAGE",
            ("FAIL", "FAIL"): "NO_COMPLETE_REPAIR_IMPROVEMENT",
        }[tuple(outcomes)]
    return {
        "repair_success": outcomes,
        "interpretation": interpretation,
        "adoption": False,
        "additional_runs_authorized": False,
    }


def execute_public(branch, assessment, deadline):
    """Existing read-only Docker runner; no evaluator files are mounted here."""
    program = checkpoint.read_bound(assessment["program"]).decode()
    env = assessment["environment"]
    sandbox = DockerSandbox(env["image"])
    require(
        sandbox.image_identity(deadline=deadline) == env["image"].split("@", 1)[1],
        "frozen terminal public image unavailable",
    )
    check = RegisteredCheck(
        id="host-plan-terminal-public",
        command=[env["python"], "-B", "-c", program],
        environment=env["environment"],
        timeout_seconds=60,
        output_limit_bytes=200000,
    )
    return asdict(
        sandbox.run_check(
            branch.workspace,
            check,
            deadline=deadline,
            execution_identity={
                "run_id": branch.journal.run_id,
                "root": str(branch.root),
                "action_id": "host_plan_terminal_public",
            },
        )
    )


@contextmanager
def submitted_assessment(branch, group, reviewer):
    evaluate = runner.EvaluationEngine.evaluate
    used = []

    def assess(engine, task_dir, patch_path, manifest, **kwargs):
        require(not used, "one submitted assessment only")
        used.append(True)
        group.check()
        submitted = kwargs["submitted_patch_artifact"]
        summary = WorkspaceManager.diff_summary(branch.workspace, deadline=branch.row_deadline)
        require(
            sha256_bytes(Path(patch_path).read_bytes())
            == submitted.content_hash
            == summary.patch_hash,
            "submitted artifact differs from final public code",
        )
        seal_review(branch, group, reviewer)
        # Freeze success inputs before either terminal result; never feed results back to a solver.
        checks = {}
        for event in branch.journal.events()[branch.inherited_events :]:
            if event["event_type"] == "action_finished":
                action = event["payload"]["result"]
                if action["tool"] == "run_check" and action["status"] == "succeeded":
                    checks[action["output"].get("check_id")] = action["output"]
        regression = all(
            checks.get(c.id, {}).get("passed") is True
            and checks[c.id].get("diff_hash") == submitted.content_hash
            for c in branch.package.public.visible_checks
        )
        assessment = json.loads(checkpoint.read_bound(branch.plan["terminal_public_assessment"]))
        deadline = phase_deadline(branch, group, 60)
        deadline.check(reserve_seconds=5)
        branch.public_attempts = 1
        branch.journal.append(
            "host_plan_terminal_public_started",
            {"patch_hash": submitted.content_hash, "synthetic": branch.provider_free},
        )
        receipt = execute_public(branch, assessment, deadline)
        verdict = public_grade(receipt, assessment)
        require(
            WorkspaceManager.diff_summary(branch.workspace, deadline=branch.row_deadline).patch_hash
            == submitted.content_hash,
            "public diagnostic changed candidate",
        )
        branch.public_repair = (
            "ERROR"
            if verdict["status"] == "ERROR"
            else "PASS"
            if verdict["status"] == "PASS" and regression and summary.patch
            else "FAIL"
        )
        branch.journal.append(
            "host_plan_terminal_public",
            {
                "patch_hash": submitted.content_hash,
                "receipt": receipt,
                "behavior": verdict,
                "fresh_final_diff_regression": regression,
                "P": branch.public_repair,
                "solver_feedback": False,
                "synthetic": branch.provider_free,
            },
        )
        if verdict["status"] == "ERROR":
            raise BoundStop("public diagnostic execution/cleanup uncertainty", all_rows=True)
        kwargs["deadline"] = phase_deadline(branch, group, 330)
        kwargs["deadline"].check()
        branch.isolated_attempts = 1
        branch.journal.append(
            "host_plan_isolated_evaluation_started",
            {"patch_hash": submitted.content_hash, "synthetic": branch.provider_free},
        )
        result = evaluate(engine, task_dir, patch_path, manifest, **kwargs)
        branch.isolated_assessment = {
            "verdicts": result.verdicts.model_dump(mode="json"),
            "task_acceptance": "PASS" if result.scope_compliant_success else "FAIL",
            "synthetic": branch.provider_free,
        }
        branch.journal.append("host_plan_isolated_result", branch.isolated_assessment)
        if "error" in branch.isolated_assessment["verdicts"].values():
            raise BoundStop("isolated assessment integrity/infra uncertainty", all_rows=True)
        return result

    with patch.object(runner.EvaluationEngine, "evaluate", assess):
        yield


__all__ = ["file_reviewer", "inert_reviewer", "seal_review", "submitted_assessment"]
