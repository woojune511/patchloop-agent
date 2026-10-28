# Three-task result: one isolated PASS, no complete verified-delivery chain

Status: LIVE_EXECUTED, allocation CLOSED, official=false, claim-ineligible.
All three approved tasks ran once, sequentially, with no intervening runtime or
settings change. No retry, additional paid run or saved-patch evaluation occurred.

## Question, scope and accounting

The [prepared plan](2026-10-29-helper-transfer-three-plan.md) asked whether the
runtime that completed the Astroid task could acquire and verify original failures,
repair, pass public checks, finish normally and pass isolated evaluation on three
other public development tasks. Selection covered numeric return values, exception
suppression and text transformation using public descriptions only. This is an
exposed development panel, not held-out evidence or a randomized comparison.

The user approved the sealed command and USD4.50 per task / USD13.50 total cap.
Manifest: `sha256:cf5de320a946525da9caafd83ef0e6bcd1301b3db5792b8cd2d8336e9f819bb9`.
Preparation commit: `9f8885ff`; runtime remains `14a1aa70` and content hash
`sha256:12637b2377a327f5e2c1ccd176ccc2669c98d6a5efdf76d509d6f39c24cd5a27`.

Actual total **USD4.046135**, all usage and execution receipts settled. Provider
calls and counts were each 47. There were 59 completed action receipts and 61
charged tool actions; two pvlib selected tests each executed base and candidate.
The positive per-task caps were not transferred, and unused allocation is closed.
Runtime, prepared originals, bound inputs and command bytes passed post-run checks.

| Task / row | Terminal | Public checks on final candidate | Original verification and delivery | Isolated acceptance / safety | USD |
| --- | --- | --- | --- | --- | ---: |
| pvlib-1707 / 5 | LIMIT_REACHED | 31 passed | Two cases verified, malformed first case refuted; no submission | NOT_RUN / NOT_RUN | 2.440482 |
| pydicom-1694 / 9 | EVALUATOR_PASS | 26 passed | Original unverified; unverified_delivery | PASS / PASS | 0.7361805 |
| SQLFluff-1733 / 18 | EVALUATOR_FAIL | 506 passed | Original unverified; unverified_delivery | FAIL / PASS | 0.8694725 |

The predefined complete original-to-verified-delivery-and-acceptance criterion was
met on **0/3** tasks. That is distinct from the observed isolated acceptance
outcomes: one PASS, one FAIL and one NOT_RUN. Public-check PASS alone was not
sufficient evidence of task correctness.

| Task | Responses / tool counter / edits | Response containing first edit | First-edit cumulative USD | Active seconds | Peak input / output tokens per response |
| --- | --- | ---: | ---: | ---: | ---: |
| pvlib | 19 / 27 / 3 | 6 | 0.465873 | 1588.483 | 31952 / 20148 |
| pydicom | 14 / 14 / 1 | 10 | 0.5279475 | 303.902 | 34360 / 7917 |
| SQLFluff | 14 / 20 / 1 | 12 | 0.7123145 | 424.252 | 36953 / 5294 |

No provider response was incomplete. None reached the 60K input or 40K general
output ceiling. No protocol-correction response was used. These observations
weaken context/output-cap exhaustion as the explanation for these outcomes; they
do not establish that resource choices never matter.

## pvlib: invalid observation became an unsatisfiable repair obligation

Run `run_dev_5244fd8bb5ca4c3b`, journal sequences 1–339.

The first original request executed the public failing and control calls, observing
NaN and a finite control. Its declared two-field JSON and actual nine-field JSON
had different keys, so both expected and reported-failure comparisons mismatched
(seq33). This was not evidence of a failed implementation repair. The next request
used consistent keys, established the baseline failure and later passed the same
call after the first edit (seq47/95). The result reached the next prepared input
and dispatched request; the feedback was not lost.

The second mutation added a discriminating regression test. Selected-test receipts
later showed original FAIL and candidate PASS (seq188/224), on the pre-third-edit
candidate. The third mutation refined intermediate NaN masking instead of globally
suppressing floating-point warnings. The final candidate again passed 31 public
tests and two current original cases. Neither observation establishes independent
acceptance because this row never submitted a patch for isolated evaluation.

The first malformed case remained independent: both initial requests used
`corrects_action_id=null`, and superseded count stayed zero. At finish, replay of
its fixed nine-field observer still could not equal the frozen two-field schema,
even though `bug_is_nan=false` and its value was zero. The host aggregated it as
REFUTED and rejected finish at seq151 and seq336. Following the first rejection,
the next actual request contained that result but instructed `needs_mutation`.

The apparent correction field was not a usable escape route. Existing
`observation_correction.py` accepts a complete unchanged-base diagnostic judgment
conflict with diagnostic rules, not this `diagnostic_rules=null` JSON shape
mismatch. The actual next requests had correction state none and no target.
Using the first action ID would therefore have been rejected too. This was not
merely a model omission of an available correction ID.

After the first rejected finish, the run used **10 more responses, 13 more action
receipts, USD1.664107 and 1130.227 active seconds**. It performed additional checks,
probes and an implementation cleanup without eliminating the malformed obligation.
It finally stopped with `completion horizon exhausted before provider dispatch`,
not monetary exhaustion. A correct later observation and public tests could not
close an invalid earlier observation, while guidance kept routing to code repair.

## pydicom: acceptance PASS with original behavior still unverified

Run `run_dev_4bc51e8ebb8d49f5`, sequences 1–201.

The first original request called `.parameters` on the string returned by
`target.signature()` and raised AttributeError before any target entry (seq68).
The actual helper description did not state that return type. Its full error was
present in the next actual request (seq71). The model corrected the string handling.

The second original request entered the target twice but inspected the observation
wrapper as the target's return dictionary instead of using `.value`. The wrapper
fields were documented. The Dataset instance was also omitted from captured
arguments, so the call record was incomplete and both comparisons were
`not_compared` (seq82). This result reached the next request (seq86). Two actual
attempts exhausted acquisition; the obligation remained unverified.

A later ordinary helper on unchanged source returned Value[2] for both `b'2.0'`
and `b'2'`, with an invalid-IS warning rather than the reported TypeError (seq113).
That stdout reached seq116. This does not establish the original failure. Public
issue/runtime differences and fixture/configuration fidelity remain unresolved;
do not attribute all of the missing reproduction to the wrapper mistake alone.

The only edit moved `self[key]` into the try block, directly matching the suggested
repair already present in the public report. Public regression passed 26 tests;
the model normally submitted `unverified_delivery`, explicitly acknowledging the
original-verification limitation. Isolated acceptance and safety both passed.
This supports that delivered candidate in the registered evaluation, not independent
cause discovery or complete original-call verification.

## SQLFluff: public regression PASS did not establish the reported repair

Run `run_dev_797a672432444969`, sequences 1–210.

The first original request used a string returned by `reproduction_workspace()`
with the `/` path operator and failed before target entry (seq59). The full error
and failed observation were delivered to the next actual request. The model wrapped
both workspace and output paths with `Path(...)` and retried.

The next request entered the CLI twice and captured processing, L036 fixing and
PASS output with SystemExit(0). Its observation included `bug_present=true` but
false processing flags. Both per-call captures were marked incomplete because
stdout/stderr objects changed during the call. This was not output truncation,
timeout or unknown container cleanup. The host did not accept this as an original
reproduction; acquisition released after two attempts, with no baseline failure
case and the obligation still unverified.

After 15 inspection actions and two probes, the 12th response edited
`Rule_L003._coerce_indent_to()` to delete additional leading whitespace segments.
It then passed 506 public tests and normally submitted `unverified_delivery`.
There was no candidate original-call replay or selected-test comparison after that
edit. Changed-line execution evidence was unknown because the registered launch
used unsupported Python options. The finish request still had seven model slots,
21 tool slots and substantial time/cost available; this was not budget exhaustion.
Isolated acceptance failed while safety passed. Hidden
test contents were not inspected for this analysis, so the exact acceptance failure
is not diagnosed here. Both failed/incomplete probe receipts reached subsequent
actual requests, including the second via fresh segment state. The evidence does
establish that current public regression
and an unverified original call were insufficient to support completion correctness.

## Decision and next question

Keep this run frozen and close the allocation. Do not increase context or output
caps or immediately repeat the panel. The most concrete reusable defect is the
conversion of an invalid observation contract into a code-repair failure and an
unclosable finish obligation. First distinguish observation-request validity from
valid behavioral counterevidence and route the former to bounded request repair.
Any replacement must preserve the original caller/input obligation and establish
the corrected baseline before receiving verification credit; simply dropping
failed cases would hide genuine failures.

Next clarify helper return types and investigate the demonstrated capture/argument
limitations using small local cases. Feedback delivery worked in the audited
transitions, so another prompt-retention mechanism is not supported by these results.
The pydicom and SQLFluff missing original evidence has multiple causes; fixing one
return-type description alone is not evidence that the whole path is solved.

These are proposed next changes, not implementations in this result commit. No
causal quality gain, generalization or comparison with mini-SWE-agent is claimed.

## Evidence

Plan root `C:/pt/helper-transfer-three-plan-v1`; result root
`C:/pt/helper-transfer-three-run-v1`. Each row contains its immutable journal,
`collection.json`, `batch-receipt.json`, public artifacts and separate public
analysis. Aggregate `batch-collection.json`, `summary.json` and `closeout.json`
retain costs, identities, outcomes and the closed allocation. Only public action
records and evaluator summary fields were used for analysis; no private oracle
content or new target execution was used.

Preparation validation remains 3 public-operation + 3 selected-test calls in
71.881 seconds, 3 offline first-request audits, 17 batch-stop cases and Ruff PASS.
The runtime was not changed, so its earlier focused/quick/mock validation was not
repeated. This follow-up adds result documentation and validates its layout/links.
