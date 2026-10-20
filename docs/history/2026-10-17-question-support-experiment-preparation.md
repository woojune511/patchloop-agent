# Final-source validation and a bounded call-support comparison

Date: 2026-10-17. Preparation only, provider calls zero, paid execution not authorized.
The exact runtime is implemented; repair-quality evidence remains NOT_RUN.
This follow-up preserves the preceding [saved-input record](2026-10-17-question-call-support.md).

## Problem and selected comparison

The saved-input comparison recovered direct caller conditions and local exclusion
evidence, but also displaced useful indirect evidence. Its active references were
operator-authored. The unresolved question is whether the model autonomously selects
and uses those references, and whether repair gains outweigh the information lost.
Another saved-case selection adjustment would not answer that question.

The [protocol](../../.agent/plans/question-support-comparison.md) freezes a narrow
comparison of A `04fb9e005523e8690910c72303b6aad168e11b46` and B
`18dfe0e68dbbc2d3617c4d4cdcdec7d1ae5b6dad`. The three runtime differences are
`dev/context.py`, the selector identity in `dev/contracts.py`, and
`dev/question_support.py`. The broader notes/handoff redesign is common to both.

| Setting | Proposed scope |
| --- | --- |
| Tasks | Current dev-train indices 13, 1, 9: Astroid-1333, Marshmallow-1343, Pydicom-1694 |
| Model | `gpt-5.4-mini-2026-03-17`, xhigh, desired output 25,000 tokens |
| Replication | Two fresh solves per task per arm; 12 rows; A1, B1, B2, A2 waves |
| Parallelism | Two independent workers; order 13, 1, 9 within each wave |
| Spending | USD 0.88 per row, USD 2.64 per wave, **USD 10.56 total**; no transfer |
| Agent resources | 40 model calls, 100 actions, four accepted edits, 1,800 seconds, including 330 seconds reserved for registered evaluation |
| Context | Same transition algorithm and thresholds, at most two question references, 24,000 retained-source characters |
| Credential location | `C:/Users/geonj/Documents/PatchLoop/.env`; contents unread during preparation |
| Live root | `C:/pt/qcscompare17live01`; reserved name only, not created |

The model and per-row spending ceiling match the observed failure panel. These are
new proposed allocations, not reuse of its closed allowance or of the older revision
proposal. All three tasks are development-exposed; the two additional tasks were not
the active-reference examples used to adjust this selector. Their public traces
exercise nested validation and exception propagation. No hidden outcome or reference
patch was used to select them or to supply a solver hint.

## Exact final-source tests and the failure

The entire suite was requested at exact B in a detached, clean checkout, using the
existing lock-matched Python 3.14.5 environment and four pytest workers. All 33 installed
distribution versions matched `uv.lock`. Both the runtime hash and every tracked byte
were checked before and after the first invocation; no runtime or test source changed.

The first invocation stopped on its first failure after **2,553 passed, six skipped,
one failed**, with 2,560 cases reported in 2,025.10 seconds. The failed case was
`tests/test_sandbox_capture.py::test_real_local_timeout_retains_partial_output_and_leaves_no_readers`.
The process timed out, but no `partial` line was captured. This test requires a fresh
Python process to start and print within **0.3 seconds**. Its standalone recheck passed.

Eight independent child-start observations during the remaining parallel execution
measured two starts beyond that bound: **0.4448773 and 0.4648702 seconds**. This supports
a startup-timing explanation and demonstrates that this host does not always satisfy
the test's timing assumption. The original failure retained no child-start timestamp,
so it does not establish the exact cause of that particular failure or rule out every
capture issue. No timing threshold, runtime budget, or assertion was weakened.

The original failure is immutable. Collection found 5,221 distinct cases and matched
all 2,560 original results by pytest node identity. The completion invocation covered
the 2,661 not yet reported cases plus the one failed case, with no fail-fast stop:
**2,649 passed, 13 skipped** in 2,086.40 seconds. The original failing case passed again.
The union exactly covers all 5,221 collected identities: 5,202 have a passing result,
19 were skipped, and one of the passing cases also has the preserved initial failure.
This is complete result coverage across invocations, not a clean full-suite pass.
Both invocations preserved all tracked bytes and the exact B runtime hash.

The 19 skips comprise two host symlink restrictions, four append-only brief-planning
exclusions, twelve explicit real-Docker/probe/execution opt-ins, and one unavailable
public dependency descriptor for SDK compatibility. They are not successful tests.

## Provider-free preparation evidence

Evidence is external at `C:/pt/analyses/question-support-experiment-20261017-v1` in
hash-chained `dev-run-v1` journals and immutable, referenced artifacts.

- Both arms' runtime bytes match their exact Git objects. Their prompt, note schema,
  transition code, resource defaults, common execution drivers and task package bytes
  agree. The prompt remains 8,000 characters and the question-reference limit is two.
- All three prepared public source checkouts and dependency file inventories passed
  current local verification. Existing evaluator/probe image identities were checked;
  no image was pulled/built and Docker Desktop was not started.
- Fresh public import, ordinary-operation and selected-test canaries passed for all
  three tasks under B. A's environment identities match those fresh receipts and its
  environment driver/profile bytes are identical. These are environment checks, not
  task-acceptance or repair-quality results. The pinned native harness identity matches.
- A mock `run_dev_a8bc4fafd9754843` and B mock `run_dev_c1d080095b714464` both reached
  isolated EVALUATOR_PASS: four mock turns, five tools, one edit and two segments each;
  input counts/cost are zero and mock safety remains NOT_RUN.
- Nineteen specification controls passed, including rejection of an extra reference,
  a larger source budget, changed transitions/model/caps, shared state, resume and
  operator question injection. Ruff passed on the frozen runtime/tests.
- All five documentation layout/link tests passed after this record and the current
  status were finalized. The final documentation commit changes no runtime/test bytes.
- Two initial mock commands used an unsupported CLI state-root option and stopped
  before execution. Corrected invocations used the documented environment variable.
  An offline uv setup in the new worktree lacked a cached wheel; Ruff instead used
  the existing verified environment. These setup attempts are not hidden or counted
  as successful checks.

Standard/global prices were rechecked against [OpenAI pricing](https://developers.openai.com/api/docs/pricing):
USD 0.75 input, USD 0.075 cached input and USD 4.50 output per million tokens, matching
the existing runtime table. The official [model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
confirms the selected snapshot and xhigh support. Account access, remote counting and
live request admission remain NOT_RUN; no credential contents were read.

## Decision and unresolved work

The experiment specification is concrete, but the original full-suite failure must
remain visible in readiness. Do not waive that gate or spend the allocation merely
because the isolated rerun passed. No provider call, paid run, retry/resume of an old
allocation, held-out tuning or quality claim occurred.

The sealed `manifest.json` and `ready.json` in the evidence root bind the proposal,
both test invocations, the coverage inventory, mock receipts and local environment
checks. Their status is `SPEC_PREPARED_VALIDATION_NOT_CLEAN_NO_PROVIDER_AUTHORITY`;
`experiment_execution_ready=false`. The reserved live root remains uncreated.

The protocol separates autonomous feature exposure, exact gained/lost evidence,
observable hypothesis/verification changes, and independent repair acceptance. It
requires all intended rows to remain in the report, including NOT_RUN/ERROR and
resource-censored cases. Equal acceptance or absent exposure is not a repair gain.
Three exposed tasks and two repetitions per arm cannot establish general accuracy.

The next local question is how to make the partial-output timeout test establish
that its child emitted output before expecting that output to survive cancellation,
without changing the runtime's startup-inclusive deadline. The call-support selector
itself was not retuned in this preparation.
