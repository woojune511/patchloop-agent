# Restore comparison continuity across review and completion

Date: 2026-11-01. Follow-up to
[requirement comparison continuity](2026-11-01-requirement-comparison-continuity.md).
Parent: `3004b3fbf0464f14f17459196f3d242212309796`. Implementation and local controls
only; official=false, claim-ineligible. No paid model call or development-task solve.

## Why this work was selected

Before another experiment, the user requested an audit of missing or incorrectly
implemented behavior, especially lost context. The audit found four concrete
integration defects. Their smallest reproductions are preserved outside the repo at
`C:/pt/preexperiment-review-20261101-v1/`, with `review.json` bound to its journal.
These matter because the next experiment asks whether the agent can use an original/
helper discrepancy; losing the instruction or misreporting the review state would
confound that question. No new inference about model capability was required.

1. A helper comparison was recorded, then an unrelated public-check scope review
   replaced it. The same issue/helper/diff returned from `review_recorded` to
   `review_needed`, including after restart.
2. A base helper ran, then an edit happened before review. The pending comparison
   still requested review, but citing its historical execution was rejected as
   `scope_review_execution_not_current`. A source-inferred annotation could not
   record that executed comparison. This conflicted with proceeding on source evidence
   without another execution.
3. The actual segmented completion request retained the comparison and base/current
   programs/results but omitted the specific shared comparison instructions. Generic
   review guidance and tool descriptions remained; this was not total evidence loss.
   Append history could retain initial planning guidance, so the observed omission
   was phase/context dependent.
4. Three operator diagnostic projections omitted `public_issue`, dropping the new
   comparison while overwriting `working_plan`. Normal fresh runner calls passed
   the issue correctly. This was a diagnostic-path defect, not a normal-run omission.

The audit also checked selected tests across a handoff. Although `recent_tests` was
absent from compact repair, the selected target and PASS remained in the actual input
through an action card. That was not classified as proven loss or changed here.

## Changes and boundaries

**Recorded comparison:** search existing journal annotations for the newest matching
issue hash and execution action/input/diff/tool. Later unrelated scope reviews do not
erase that fact. If the matching case is absent from the latest scope review, retain
one bounded `recorded_review` with its conditions, expectation, interpretation and
authoring turn/diff. This avoids preserving only a completion flag while losing the
actual conclusion. Execution currency follows the current candidate; model-authored
interpretation and `not_certified` authority remain explicit. No new durable ledger.

**Historical comparison:** allow an executed scope case to cite the latest bound
helper or its direct replay parent after the diff changes, only when it also contains
a valid literal public-issue quote. Preserve the execution's actual diff and historical
currency. Other stale results, mismatched identities, unbound programs and original
reproduction records do not gain this exception. Current verification and submission
eligibility are unchanged. The schema description and ordinary guidance identify the
exception; the brief prompt stays within its existing character bound.

**Completion guidance:** factor the existing short comparison paragraph into one
shared constant. Planning-enabled completion uses it from entry, before a helper even
exists. Activation therefore cannot lag when a helper appears inside the same segment.
Planning OFF retains its prior completion prompt. The full initial-plan instructions
are not copied into compact completion. Both runner prompt selectors use the contextual
function; the completion-guidance diagnostic checks the corresponding seed prefix
while preserving its intended variant and common suffix.

**Diagnostics:** pass the actual public issue through size-only replay, history-search
replay and verification-role context projection. Verification-role phase filtering
still removes the prior phase's plan interpretations while retaining public observations.
A real history-search replay test additionally exposed an existing `gateway=None`
crash in action-card construction. That adapter now supplies a read-only view of its
existing public event prefix; it grants no real gateway, execution or action credit.

No additional model stage, required probe, finish gate, resource increase, private
task hint or task-specific repair was introduced. Existing latest-helper/direct-parent
retention is still bounded; this is not an exhaustive semantic obligation ledger.

## Local validation

Evidence root: `C:/pt/review-fixes-20261101-v1/`. Final counts, durations, source/runtime
hashes and individual artifacts are in `validation.json`; `commit.json` records the
resulting commit. Initial fixture/compatibility failures remain beside corrected results.

Final evidence: 129 focused cases PASS after native-reference fixture correction;
initial 127 PASS/2 fixture failures in 76.723s, all four completion variants PASS in
29.208s. Full quick initially: 1,547 PASS/2 failures/
1 host skip in 418.370s. The failures were stale wording assertions
for the non-mandatory-check rule removed during the previous prompt compression;
the actual runs already reached EVALUATOR_PASS without extra checks. Updated assertions
match the retained current guidance. The whole owner module passed
14 tests in 20.708s; combined quick
coverage is 1,549 PASS/1 skip. Product source stayed frozen, and the
full quick suite was not repeated after these assertion corrections. Ruff PASS.
Isolated mock EVALUATOR_PASS is exercised
by the actual completion/recovery controls and the quick suite, with safety NOT_RUN;
no separate redundant smoke invocation was launched.

The integrated fixture correction follows native argument/output references in the
actual input and checks source hash plus action/tool/diff identities. It does not
drop the program/output equality assertions. Initial failure logs are preserved.

Controls include:

- helper review -> unrelated review -> restart, preserving both recorded status and
  the original interpretation; the newest matching revision wins;
- base helper -> mutation -> literal-quote review, retaining historical execution;
  unrelated/stale/unbound records remain rejected and new helpers/issues need review;
- actual append/segmented completion inputs with base/current evidence, no-action
  correction and idempotent completed-run resume;
- completion entry without a comparison -> first helper -> next decision, with a
  stable comparison instruction already present;
- actual diagnostic wrapper/composer outputs, including verification phase separation
  and nonempty history-search results;
- contract identities, unchanged action/schema limits, prompt bound, Ruff, quick
  regressions and the suite's isolated mock evaluation controls.

Initial completion fixtures incorrectly required append mode to omit its retained
initial prompt; that assertion was narrowed to segmented mode. A resume check during
concurrent implementation correctly rejected changed runtime identity, so integrated
validation uses frozen source. Initial history-search fixture visibility was corrected;
the subsequent real adapter crash was a product defect and was fixed separately.
These failures were not hidden or counted as successful runs.

## Decision and remaining question

Keep the fixes: the final local controls passed. They address confirmed continuity
and compatibility defects, not a hypothesized increase in autonomous repair quality.
The model can still select an insufficient quote, misinterpret an observed result or
decide to submit with uncertainty. No host semantic correctness judgment was added.

The next empirical question remains whether preserved comparisons lead the model to
inspect a different cause, execute a discriminating public case and repair the original
behavior. No new paid experiment is scheduled or authorized by this record. Historical
task results and closed allocations remain unchanged.
