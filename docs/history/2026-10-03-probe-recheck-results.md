# Saved-program recheck: fixed ABC comparison

Date: 2026-10-03. All 18 fresh solves completed; allocation CLOSED.
Decision: KEEP_BASELINE. No default or selected-policy change, further run, or
general-performance claim is authorized by this record.

## Question and frozen execution

The [preparation](2026-10-03-probe-recheck-preparation.md) selected a recurring
failure: a visible check can pass while a repair violates public expected behavior.
The intervention reruns a model's saved program after edits, rather than adding
another generic instruction to be cautious. A competing explanation is that the
program targets the wrong input, expectation, or call path; replay cannot fix that
by itself. The question was whether automatic feedback improves subsequent repairs
and final correctness enough to justify its resource cost.

A retained the current brief-v1/probe-policy-none baseline. B used the shared
public-expectation, user-entrypoint and preservation guidance with cases-v1. C was
identical to B plus saved-program-v1. A-to-B therefore compares a bundled authoring
procedure; B-to-C tests the added execution policy. Model-authored probes never
became submission gates. Independent operator programs were not solver inputs.

After implementation and provider-free validation, the user approved the exact
packet with "진행해줘". The fresh approval is retained in authorization.json.
Execution commit: b77f8ad1a8fe4bc9d5f6f60b599d3cc696034818.
Packet hash: sha256:d80ad7c40a312d44593906bf4cb4f2c2df050e01ec957cbeeba6d485945ae1f6.
Runtime hash: sha256:ca68a11874470d7887733422b5c715afb67a11e9b8d22d2a1c1de3e5b3b2b027.

Tasks were the registered dev-train SQLFluff-1733, pydicom-1413 and pydicom-1694
tasks. Each ran A/B/C twice from its public base: repetition 1 ABC/BCA/CAB,
repetition 2 CBA/ACB/BAC. Model gpt-5.4-2026-03-05, xhigh, desired output cap
25,000 tokens; each row retained 40 calls, 100 actions, four edits, 1,800 seconds
and USD 3, within a USD 54 invocation allocation. Credentials came from the
repository .env. No retry, replacement, resume, budget transfer, instruction
revision, image pull/build, or extra paid call occurred. Every run is official=false.

## Results and decision

Counts below use all six planned fresh solves per arm. C's unsent patch is not an
acceptance FAIL: its evaluation is NOT_RUN and it contributes no accepted repair.
Elapsed time is the sum of complete row process durations, including evaluation.

| Arm | Original acceptance PASS / FAIL / NOT_RUN | Independent public PASS / FAIL / NOT_RUN | USD | Seconds |
| --- | --- | --- | ---: | ---: |
| A | 4 / 2 / 0 | 4 / 2 / 0 | 3.4838495 | 1892.450 |
| B | 5 / 1 / 0 | 6 / 0 / 0 | 4.3170660 | 2309.793 |
| C | 4 / 1 / 1 | 4 / 1 / 1 | 6.2464715 | 3283.629 |

Total recorded cost: USD 14.047387; all 18 rows settled within their caps. Unused
allocation is closed. Original accepted counts were A/B/C = 1/2/3 in repetition 1
and 3/3/1 in repetition 2. C cost 79.30% more and took 73.51% longer than A,
exceeding both 25% overhead bounds. In repetition 2, C lost SQLFluff-1733 and
pydicom-1413 successes achieved by both A and B.

| Criterion | Result |
| --- | --- |
| C > A and C >= B in both repetitions | Not met |
| Total C > B | Not met: 4 versus 5 |
| No paired A/B success lost by C | Not met: two task/repetition pairs |
| C cost and time <= 125% of A | Not met |
| Valid automatic failure delivered, then repair, same-program pass and acceptance pass | Met: SQLFluff-1733 C1 |
| Execution/accounting contracts and recorded safety | Passed within observed scope |

Retain the baseline and close this comparison. B's 5/6 is a small, exposed-panel
observation, not a separate adoption decision or evidence of general improvement.
The optional implementation remains available; CLI defaults are unchanged.

## Mechanism and failure evidence

Automatic execution was exercised nine times: SQLFluff C1 three times, SQLFluff C2
four times, and pydicom-1413 C1/C2 once each. The pydicom-1694 rows all succeeded
without probes. Successful C rows cannot all be credited to automatic replay.

SQLFluff C1 provides one reviewed mechanism example. The saved program calls the
actual formatter, asserts the positive eight-space target block, and includes
standalone and already-correct preservation cases. The first automatic execution
printed nine spaces and raised an assertion, with no setup, timeout or truncation
failure. The next model input contains that action, program and output; its public
decision explicitly responds to the remaining nine-space line. A later edit makes
the identical program pass, but the registered regression check fails. A third edit
then passes both checks on the submitted diff and original acceptance succeeds.

The program is pc_dbec7a320e6a438503254352 in run_dev_e063a7e45bc640fe; first
automatic action harness_probe_0d282a3a51010a5509a68e92dcb95005. The full chain,
input hashes, subsequent decisions and submitted-diff binding are preserved in
mechanism-review.json. This is an observed feedback-to-repair path, not proof that
automatic execution was necessary or sufficient for success.

| Unsolved row | Public evidence and bounded classification |
| --- | --- |
| SQLFluff A1 | No probe; registered check passed, but the independent formatter still emitted nine rather than eight spaces. Missing behavioral verification and a remaining defect. |
| pydicom-1413 A1 | Its bytes-like conversion investigation did not activate the backslash-containing bytes case; the submitted conversion-stage patch still failed public save/read. Input construction gap and a remaining defect. |
| pydicom-1413 B1 | No model probe; submitted patch passed all frozen public examples but failed original acceptance. Cause of that separate failure remains unresolved. |
| SQLFluff C2 | Automatic output showed nine, five, five, then eight spaces; the model responded and edited. After edit four, registered regression failed and the completion horizon was exhausted. No submission, acceptance NOT_RUN, independent submitted-patch assessment NOT_RUN. |
| pydicom-1413 C2 | Initial bytes program passed on base. A replacement program supplied array/bytearray directly, while the public report converts its array to bytes first. The patch fixed this alternative path and its auto output; the frozen backslash-containing bytes save/read case still failed. Input scope drift and a remaining defect. |

There is no general finding that the model ignored feedback. SQLFluff C2 acted on
the feedback yet exhausted its edits with a regression; pydicom C2 acted on an
alternative input condition. Repeated execution cannot establish that a selected
test covers the requirement. Conversely, B2 manually reran a saved SQLFluff probe
and eventually succeeded without automatic replay. No further adjacent prompt
experiment or new mandatory gate is selected from these observations.

## Verification, artifacts and limits

The pre-dispatch focused suite passed 30 tests in 100.337 seconds; the full fast
suite passed 4,105 with 17 skipped. Ruff passed and mock smoke reached isolated
EVALUATOR_PASS with mock safety NOT_RUN. Those existing receipts were verified
against the frozen runtime before dispatch; they are not fresh tests in this record.
This closeout changes documentation only: all five layout/link tests and Ruff passed;
the full suite and mock were not repeated. The user's AGENTS.md edit was preserved.

The live audit checked all journal chains, action uniqueness and terminal counts,
per-call cost sums, settled provider/count requests, resource limits, pre-mutation
active selection, exact definition/diff bindings and delivery to the next model
input. All nine automatic actions had unique receipts, with no fabricated native
function-call history. All 17 submitted runs had recorded safety PASS; the unsent
row retains safety NOT_RUN. Interrupted recovery is supported by the earlier
injected local tests, not claimed as exercised in these uninterrupted live runs.

Independent assessments checked the hash-verified submitted workspaces after the
paid panel closed and did not change their diffs. Their coverage remains the frozen
public examples, not every task requirement. The pydicom-1694 public check uses
the explicitly frozen strict-mode malformed-tag construction; it verifies the bad
value activates a conversion error and that valid tags are preserved.

External immutable evidence root: C:/pt/analyses/probe-recheck-20261003-v2.
It contains packet.json, authorization.json, result.json, public-final.json,
contract-audit.json, mechanism-review.json, failure-review.json and decision.json,
with linked append-only dev-run-v1 journals and content-addressed artifacts.
Fresh run journals/workspaces: C:/pt/prlive01/<task-number><arm><repetition>.
result.json binds each row to its run ID, submitted patch and original evaluation.
Earlier preparation and closed experiment records remain unchanged.

The result changes the decision from testing this policy to retaining the baseline.
The unresolved question is how to choose a requirement-relevant input and a repair
that preserves existing behavior within the same limits. This comparison establishes
neither a general rejection of automatic feedback nor authorization for another run.
