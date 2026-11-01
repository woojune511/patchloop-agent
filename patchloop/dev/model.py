"""Public-only prompt and deterministic mock behavior for ``dev-head``."""

from __future__ import annotations

import json
from dataclasses import dataclass

from patchloop.dev.contracts import DevModelTurn, PublicTurnDecision, RequestedTool
from patchloop.dev.repair_guidance import INSTRUCTIONS as REPAIR_GUIDANCE
from patchloop.errors import ContractError

DEV_SYSTEM_PROMPT = """You are PatchLoop dev-head, a constrained coding agent.
Investigate the public task, edit, check behavior, and submit.
Request 1-4 read_file/search_files calls or one other supplied tool; never mix.
replace_text, edit_files, stop_task and observe_original omit decision/plan/memory annotations.
Other tools carry public turn_decision matching their family.
At needs_path_diagnosis, omit annotations; choose offered source exploration or run_probe.
Parallel inspections may differ in basis/evidence_goal. evidence_goal names the
inspection question, including negative searches/rereads; other modes use null.

Before rereading, name what could change the repair/check.
If only an evidenced repair's outcome is unknown, edit and check it. Revise failed
hypotheses; limit claims to observed inputs and label assumptions.
current_sources has headers, not bodies; get needed source. Keep changes scoped.
Coverage and commitment are advisory. Tools depend on budgets and valid actions.
completion_guidance.stage names the prerequisite; next_action names an offered step.
In needs_source_evidence, inspect allowed source. Temporary tool absence alone is not
a public_task_conflict. action_horizon forecasts closures after one read/search with
unchanged evidence; new evidence/actions can differ. mutation_readiness.state=
ready_to_attempt means source evidence is delivered, not anchor coverage or correctness.

memory_update retains model interpretations and untested assumptions, not reasoning
transcripts or status copies. Cite behavior-bearing observed source/results.
current_public_failure is current; pending_recheck concerns an older diff.
Refine using note_id; note_id=null creates a distinct interpretation.
Use remove_note_ids. open_question is null or {text, evidence}:
at most one primary and one countercheck. Cite minimal observed units and a competing
branch/precondition if available. After edits refresh with an ordinary action if relevant:
mutation anchors precede current countercheck, then primary. Do not invent counterchecks.
Missing bodies stay explicit. evidence_currency=current and closed_by_model never certify
behavior. A citation's check_result is its verdict, not confirmation of the note's prose.
Reconsider claims after edits. Updates are optional.

Apply the first non-null memory_update before the batch executes; cite no
pending/current-batch results. Use findings=[] with open_question or memory_update=null
before an answer. Null preserves notes and the question;
open_question=null within an update clears only the question.
Tool outputs report action outcomes only. Optional note/plan receipts are in
working_notes.last_update_result / working_plan.last_update_result; rejection
is nonblocking. Use working_notes.available_note_ids and last_source_lifecycle for
current IDs. Source changes can expire notes. Receipts precede the batch.
Fix annotation errors on a useful later call.

verification_updates keeps concrete unverified public behaviors separate from focus.
No quota or broad task recap. Upsert creates an original concern or updates only its
progress_note. Use concern_id=null for a distinct concern. Exact repeats do nothing.
Resolve only with an already observed successful current-diff check/probe, its
evidence_action_id, and a reason connecting it to the concern. Baseline evidence cannot
validate a candidate. Dismiss needs a reason why further verification is not useful,
not test evidence. Neither certifies semantic coverage. Reconsider resolved/dismissed
concerns after diff changes; focus changes, unrelated fixes and source-note expiry
do not resolve them. Use [] for no concern change. Concerns and annotation errors
do not mechanically gate actions or finish; no extra call is required.

A mutation sends only its offered fields. hypothesis and expected_behavior are unverified intent.
edit_files supports atomic batches, creation and receipt undo.
Use the smallest sufficient unique exact anchor; preserve line breaks. Omit unchanged
signatures/docstrings. The gateway binds observed evidence and builds the diff;
do not supply evidence span IDs or a patch wrapper. The diff is supplied; rejection
restores its baseline and checks. Revise, investigate or abandon a rejected proposal.

""" + REPAIR_GUIDANCE + """

A failure concerns its checked diff. Recheck a repair before assuming it persists;
another edit can use independent current evidence. Hypotheses are unverified;
headers do not establish behavior of unread return paths. Repeated failures invite
review; connect the next mutation hypothesis to any required completed call-path diagnosis.
For run_probe in that stage select focus and any offered call_id; host binds watches/lines.
Separate function entry and branch execution; unknown is not no-hit.
The completed diagnosis grants no repair credit.
A source read is required for edit admission only when exact evidence is missing;
behavioral questions can still justify inspection. No check is forced.

Use the latest completion_guidance and visible_check_status: only current-diff PASS
counts. finish_task submits; historical PASS does not. Zero remaining mutations forbids further
edits, not affordable checks or submission. completion_possible describes completion;
mutation_completion_horizon describes another edit starting now; its false eligibility
flags do not predict availability after acquiring missing source evidence.
Investigate the original public call and failure; helpers are separate diagnoses.
Bind purpose/input/setup/expected JSON in run_probe; replay_action_id preserves them.
reproduction_review.completion retains cases independently of plans/notes. finish_task
automatically replays stale invocation-bound cases on the current diff. Current comparable
mismatch/conflict blocks finish; repair or stop. Missing cases, unavailable execution or
changed conditions remain unverified, never a PASS. Different programs/expectations create
different cases and cannot close the original. Observe ordinary-input controls too.
original_obligation retains unmet task verification. Follow its bounded pre-edit stage;
only unchanged-base failure acquires a case. Release/normal/helper PASS gives no credit.
For CLI observed_target, set sys.argv and preserve cwd/fixtures.
SUPPORTED is case evidence, not task coverage. Explain caller mapping;
helpers/suite PASS cannot replace the reported behavior. model_position and
model_open_concern_ids describe discussion. behavior_verdict=not_assessed is not PASS.
evidence_review does not certify requirements. Reading/adding tests is not execution;
mutation_expectation is intent, not observation.
run_tests.comparison runs identical tests on original_base/before_mutation and candidate.
Select an implementation mutation, not test addition. PASSED_BOTH is nondiscriminating;
assertion fail-to-pass supports only that test. Setup/errors give no repair credit.
Finish assessment cites current evidence/inference and gaps. Skipped checks remain unperformed.
Resolve material gaps when feasible. Missing original evidence returns unverified_delivery;
independent evaluation is separate. Edits require fresh checks.
stop_task sends only reason_code and summary and abandons as AGENT_STOPPED, without submission or
evaluation; it is not completion. Use it when no available action supports progress,
not merely when no edit is needed. Keep decisions and findings concise; never emit
raw chain-of-thought. Private tests, reference patches, and evaluator details are
unavailable and must not be inferred.
"""


@dataclass(frozen=True)
class MockMutation:
    path: str
    old_text: str
    new_text: str
    hypothesis: str
    expected_behavior: str


_CSV_MUTATION = MockMutation(
    path="mini_data_utils/csvlite.py",
    old_text=(
        "import csv\n"
        "\n"
        "\n"
        "def parse_rows(text: str) -> list[list[str]]:\n"
        '    """Parse CSV text into rows while preserving quoted values."""\n'
        "\n"
        "    rows: list[list[str]] = []\n"
        "    for physical_line in text.splitlines():\n"
        "        rows.extend(csv.reader([physical_line]))\n"
        "    return rows"
    ),
    new_text=(
        "import csv\n"
        "import io\n"
        "\n"
        "\n"
        "def parse_rows(text: str) -> list[list[str]]:\n"
        '    """Parse CSV text into rows while preserving quoted values."""\n'
        "\n"
        '    return list(csv.reader(io.StringIO(text, newline="")))'
    ),
    hypothesis="Physical-line splitting resets the CSV parser inside a quoted record.",
    expected_behavior="One csv.reader over a text stream preserves quoted embedded newlines.",
)

MOCK_MUTATIONS = {"csv-quoted-newline": _CSV_MUTATION}


class MockDevAdapter:
    """One public smoke transcript used only for deterministic offline tests."""

    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        try:
            self.mutation = MOCK_MUTATIONS[task_id]
        except KeyError as exc:
            raise ContractError(f"no dev-head mock script for task: {task_id}") from exc

    def next_turn(self, context: str, tools: list[dict]) -> DevModelTurn:
        turn = self._next_action(context, tools)
        fields_by_tool = {tool["name"]: tool["parameters"]["properties"] for tool in tools}
        for index, call in enumerate(turn.tool_calls):
            fields = fields_by_tool.get(call.name)
            if fields is None:
                continue
            arguments = dict(call.arguments)
            if call.name == "replace_text" and "causal_revision" not in fields:
                arguments.pop("causal_revision", None)
            if "turn_decision" in fields:
                call.arguments = arguments
            else:
                turn.tool_calls[index] = RequestedTool(
                    name=call.name, action_id=call.action_id, arguments=arguments,
                    preserve_annotation_presence=True,
                    **({"memory_update": call.actual_memory_update}
                       if "memory_update" in fields else {}),
                )
        payload = json.loads(context)
        planning = payload.get("working_plan")
        annotated = [call for call in turn.tool_calls if call.turn_decision is not None]
        if planning is not None and annotated:
            for call in annotated:
                call.turn_decision.plan_update = None
                call.turn_decision.plan_update_reason = None
                call.turn_decision.scope_review = None
            if planning["review_request"]["requested"]:
                if planning["plan"] is not None:
                    annotated[0].turn_decision.plan_update_reason = (
                        "The scripted stage changed; unfinished public verification remains "
                        "in the plan. Only already executed checks count as observations."
                    )
                annotated[0].turn_decision.plan_update = (
                    "Goal: " + payload["public_task"]["issue"]["title"] + ". "
                    "Inspect the parser lifetime, make an exact small replacement, "
                    "verify the current diff with public checks, then submit. "
                    "Current stage: " + payload["workflow_gate"] + ". "
                    "Untested behavior remains an assumption until observed."
                )
                if planning["policy"] in {"brief-evidence-v1", "brief-assumption-v1"}:
                    # Scripted public smoke data tests transport, not planning quality.
                    annotated[0].turn_decision.plan_update = (
                        "Behavior: " + payload["public_task"]["issue"]["title"] + ".\n"
                        "Evidence / open assumptions: Current stage: "
                        + payload["workflow_gate"] + ". Untested behavior remains open; "
                        "a public check establishes only the observed behavior.\n"
                        "Next discriminating action: " + annotated[0].name
                        + " for the next scripted public obligation; use results bound "
                        "to the current diff to decide whether to repair or submit."
                    )
        return turn

    def _next_action(self, context: str, tools: list[dict]) -> DevModelTurn:
        del tools
        try:
            payload = json.loads(context)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ContractError("dev-head mock received invalid public context") from exc
        latest_spans = [
            span
            for result in payload.get("latest_tool_results", [])
            for span in result.get("output", {}).get("spans", [])
        ]
        spans = [*latest_spans, *payload.get("source_spans", [])]
        current_diff = payload.get("current_diff", {})
        remaining_check_ids = payload.get("remaining_visible_check_ids", [])
        if not spans and not current_diff.get("patch"):
            decision = PublicTurnDecision(
                mode="inspect",
                basis="Locate and inspect the public parser implementation once.",
                evidence_goal="Identify the parser lifetime and exact mutation anchor.",
            )
            return DevModelTurn(
                tool_calls=[
                    RequestedTool(
                        name="search_files",
                        action_id="mock-search-source",
                        arguments={"query": "def parse_rows", "path_glob": "**/*.py"},
                        turn_decision=decision,
                    ),
                    RequestedTool(
                        name="read_file",
                        action_id="mock-read-source",
                        arguments={
                            "path": self.mutation.path,
                            "start_line": 1,
                            "end_line": 80,
                        },
                        turn_decision=decision,
                    ),
                ]
            )
        if not current_diff.get("patch"):
            matching_spans = [item for item in spans if item.get("path") == self.mutation.path]
            if not matching_spans:
                raise ContractError("mock mutation requires a current source span")
            return DevModelTurn(
                tool_calls=[
                    RequestedTool(
                        name="replace_text",
                        action_id="mock-apply-mutation",
                        arguments={
                            "path": self.mutation.path,
                            "old_text": self.mutation.old_text,
                            "new_text": self.mutation.new_text,
                            "occurrence": 1,
                            "hypothesis": self.mutation.hypothesis,
                            "expected_behavior": self.mutation.expected_behavior,
                            "causal_revision": None,
                        },
                        turn_decision=PublicTurnDecision(
                            mode="mutate",
                            basis=(
                                "The public source confirms that physical-line iteration resets "
                                "the CSV parser."
                            ),
                            evidence_goal=None,
                        ),
                    )
                ]
            )
        if remaining_check_ids:
            check_id = remaining_check_ids[0]
            return DevModelTurn(
                tool_calls=[
                    RequestedTool(
                        name="run_check",
                        action_id=f"mock-visible-check-{check_id}",
                        arguments={"check_id": check_id},
                        turn_decision=PublicTurnDecision(
                            mode="verify",
                            basis="Run the next unexecuted visible check on the current diff.",
                            evidence_goal=None,
                        ),
                    )
                ]
            )
        return DevModelTurn(
            tool_calls=[
                RequestedTool(
                    name="finish_task",
                    action_id="mock-finish",
                    arguments={
                        "assessment": (
                            "The scoped replacement implements the public task's requested "
                            "behavior and all required checks pass on this diff. This is a "
                            "deterministic mock assessment; untested behavior remains unverified."
                        ),
                    },
                    turn_decision=PublicTurnDecision(
                        mode="finish",
                        basis="Reviewed the repair and current public checks for submission.",
                        evidence_goal=None,
                    ),
                )
            ]
        )
