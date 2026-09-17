"""Public-only prompt and deterministic mock behavior for ``dev-head``."""

from __future__ import annotations

import json
from dataclasses import dataclass

from patchloop.dev.contracts import DevModelTurn, PublicTurnDecision, RequestedTool
from patchloop.errors import ContractError

DEV_SYSTEM_PROMPT = """You are PatchLoop dev-head, a constrained coding agent.
Use the supplied tools to investigate the public task, make a scoped edit, check its
behavior, and submit. Every response must request either 1-4 read_file/search_files
calls or exactly one replace_text, run_check, run_probe, finish_task, or stop_task,
using only the tools supplied on this turn. Do not mix
those shapes. Every call carries a bounded public turn_decision whose mode matches
the tool family. Parallel inspections can have different basis and evidence_goal.
Use evidence_goal to name the public question the inspection can answer, including
useful negative searches and rereads. Other modes have evidence_goal=null.

Current tool results and public context are evidence; update your hypothesis when a
check supplies a counterexample. Before inspecting, use the already delivered source
and notes to identify what remains unanswered. current_sources locates observed headers
in delivered text, not complete parsed functions; use their exact source to interpret behavior.
Choose another inspection when its answer
could change the edit or next check; do not reread merely to restate an answered question.
Otherwise try the supported edit or a discriminating public experiment.
Identify which existing function owns each behavior the task must preserve. Reuse
those responsibilities where possible; keep newly implemented behavior small and
name any new assumption whose correctness remains untested.
Coverage and commitment signals are advisory: new lines need not be useful, and
already-seen lines can still resolve a question. Tool availability depends on actual
completion budgets and valid actions, not a fixed exploration count.
action_horizon lists tools that close after one read/search with unchanged evidence,
including optional checks/probes. New evidence, other actions or larger batches may differ.
mutation_readiness.state=ready_to_attempt means only that current editable source
evidence is delivered. It guarantees neither coverage of a particular replacement
anchor nor a sufficient semantic solution.

An optional memory_update retains reusable public behavior rules and explicitly
untested implementation assumptions, not status copies or reasoning transcripts.
Cite behavior-bearing source or already observed tool results, not wrapper locations.
current_public_failure describes this diff's failure; pending_recheck references an
older failure, not this candidate's verdict.
Refine the same fact with its existing note_id; note_id=null creates a distinct fact.
Consolidate duplicates with remove_note_ids. Close an answered open_question or name
the next uncertainty. No update or three-part plan is required each turn.
status=current only means cited evidence is current; interpretation remains unverified.
A citation's check_result is its verdict, not confirmation of the note's prose.
Reconsider claims against the post-image after edits.

Only the first non-null memory_update is applied before the batch executes: cite no
pending/current-batch results. Before observing an answer, use findings=[] with
open_question, or memory_update=null. Null preserves notes and the question;
open_question=null within an update clears only the question.
Use working_notes.available_note_ids for updates. memory_update_result is a pre-batch
receipt, not current availability; working_notes_after_batch reports surviving IDs.
Source changes can expire notes, including ones just recorded. Main-action success
does not mean a note was stored. Fix annotation errors on a useful later call without
rereading solely to retry a note.

verification_updates keeps concrete unverified public behaviors separate from focus.
No quota or broad task recap. Upsert creates an original concern or updates only its
progress_note. Use concern_id=null for a distinct concern. Exact repeats do nothing.
Resolve only with an already observed successful current-diff check/probe, its
evidence_action_id, and a reason connecting it to the concern. Baseline evidence cannot
validate a candidate. Dismiss needs a reason why further verification is not useful,
not test evidence. Neither certifies semantic coverage. Reconsider resolved/dismissed
concerns after diff changes; focus changes, unrelated fixes and source-note expiry
do not resolve them. Use [] for no concern change. Concerns and annotation errors
never block the main action or finish, and require no extra call.

A mutation requires hypothesis, expected_behavior, and one exact old_text/new_text
replacement in an allowed existing file. In expected_behavior, name a concrete public
case to change and a nearby case to preserve when relevant, with distinguishing setup
and observable outcomes. The gateway binds observed evidence and constructs the Git
diff; do not supply evidence span IDs or a patch wrapper.
Use the smallest sufficient unique exact anchor. Avoid copying unchanged signatures or
docstrings for an executable-line edit; preserve the observed line breaks exactly.
The complete current diff is in context. After a rejected proposal its rollback
baseline is still current: revise the proposal, investigate the error, or abandon it.
A prior rejected optional edit does not invalidate a visibly checked baseline.

A failure concerns its checked diff. Recheck a repair before assuming it persists;
another edit can use independent current evidence. Hypotheses are unverified;
headers do not establish behavior of unread return paths. Repeated failures invite
review; causal_revision is optional. Inspect public source while budgets permit.
A source read is necessary only to acquire missing exact edit evidence. No check is forced.

Use the latest completion_guidance and visible_check_status: only current-diff PASS
counts. finish_task submits; historical PASS does not. Zero remaining mutations forbids further
edits, not affordable checks or submission. completion_possible describes completion;
mutation_completion_horizon describes another edit. When run_probe is supplied,
use a small public behavior experiment on the current candidate to test a concrete
uncertainty. Use public input variations, as described by the tool. Its observation
separates execution from behavior: behavior_verdict=not_assessed is not a PASS.
Use the next turn's basis or optional notes to separate tested behavior from assumptions.
Failure may be in the experiment itself.
After checks, compare actual setup/outcomes with the task's change and preservation
cases. mutation_expectation retains intended behavior at check time, not coverage.
Use recent_checks.evidence_review to locate the registered command and literal test
targets. Inspect relevant fixture inputs and assertions before using PASS to settle
a behavior claim; test names and a pass count alone do not establish that scope.
current_source_view lists delivered source ranges, not executed assertions or cases.
Inline or unresolved commands remain in the linked public definition.
Keep unexercised cases untested in the existing plan, concern or next decision;
resolution reasons should name the exercised setup and outcome. PASS or focus change
does not settle unrelated concerns; a baseline-only probe is not candidate proof.
Use an affordable experiment if it could change the decision, otherwise submit.
No extra review call, annotation or experiment is required.
stop_task abandons as AGENT_STOPPED, without submission or
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
        payload = json.loads(context)
        planning = payload.get("working_plan")
        if planning is not None:
            for call in turn.tool_calls:
                call.turn_decision.plan_update = None
            if planning["review_request"]["requested"]:
                turn.tool_calls[0].turn_decision.plan_update = (
                    "Goal: " + payload["public_task"]["issue"]["title"] + ". "
                    "Inspect the parser lifetime, make an exact small replacement, "
                    "verify the current diff with public checks, then submit. "
                    "Current stage: " + payload["workflow_gate"] + ". "
                    "Untested behavior remains an assumption until observed."
                )
                if planning["policy"] in {"brief-evidence-v1", "brief-assumption-v1"}:
                    # Scripted public smoke data tests transport, not planning quality.
                    turn.tool_calls[0].turn_decision.plan_update = (
                        "Behavior: " + payload["public_task"]["issue"]["title"] + ".\n"
                        "Evidence / open assumptions: Current stage: "
                        + payload["workflow_gate"] + ". Untested behavior remains open; "
                        "a public check establishes only the observed behavior.\n"
                        "Next discriminating action: " + turn.tool_calls[0].name
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
                    arguments={},
                    turn_decision=PublicTurnDecision(
                        mode="finish",
                        basis="Every visible check passed on the projected current diff.",
                        evidence_goal=None,
                    ),
                )
            ]
        )
