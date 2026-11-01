# Fresh observation-contract pilot: acquired failure, no repair

Date: 2026-10-25 KST. Run: `run_dev_3f0132d090d04653`.
official=false; claim_eligible=false. One approved fresh solve, now closed.

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent.
- Origin Mode: run, followed by public receipt interpretation.
- Verification Status: ANALYZED; live execution and integrity checked, no independent rerun.
- Version Label: observation25-live-v1.

## Question and prospective scope

The [preceding pilot](2026-10-24-invoke-live.md) captured the actual stdout error
but checked stderr, mixed metadata into a different observation shape and omitted
a control. It never acquired its declared failure or made a repair. The
[v53 change](2026-10-25-observation.md) clarified small observation values,
channel/outcome/exit-code interpretation and bounded field differences. Local
controls passed; the selected question was whether a fresh model could use that
interface to acquire the original failure/control and continue through repair.

Prepared request: `C:/pt/observation25-live-ready-v1/request.json`, hash
`sha256:339092fd966e23fc15313c958755e232de45d117b96557f9c42f456ec8a9bbba`.
The user approved it with `실행해줘`; the request-bound receipt is
`C:/pt/observation25-live-ready-v1/authorization.json`. Earlier allocations stayed closed.

- Task: `tasks/dev-train/current-dev20/13/public.yaml`, Astroid-1333.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh, 25,000 requested output ceiling.
- Credential file: repository `.env`; repeat one, invocation cap USD 0.88.
- Runtime commit: `be8742250b48dbd1b1f5d230bed2bc9e5e8d1a72`.
- Runtime hash: `sha256:6dd1cad5aeb16063857c28bb5df099cf52c75debb471d1ba1c57ba42ce5aaef1`.
- Same task/model/environment, segmented-v1, result-or-size-v1, brief-v1,
  probes/none, bounded-v1 acquisition, repair-recheck/protected-v1 and
  completion-recovery-v1; 40 model calls, 100 actions, four edits, 1,800 active seconds.
- Outer supervision: 1,920 seconds; at most two frozen post-submission public
  checks sharing 120 seconds. No seeded program, previous solver context or repair hint.

The exact supervisor and assessment commands are in the frozen preparation plan.
Read-only source/dependency/local-image preflight and a runner-stubbed CLI roundtrip
passed before execution. Two synthetic terminal branches verified that no submission
or solver stop records NOT_RUN without launching checks. No images were acquired.
The previous local suite was not rerun against unchanged runtime code.

One stochastic solve on a repeatedly exposed development task is a diagnostic,
not a randomized comparison or evidence of generalization. Guidance and feedback
changed together. Plausible failures included an incorrect predicate, no useful
response to feedback, no repair after acquisition, and resource/response limitations.

## Executed result

The process ran from 17:04:47.036 to 17:13:24.663 UTC on October 24 (October 25 KST).
Wall time was 517.658 seconds. Controlled CLI exit was zero; the solver terminal
was **INCOMPLETE_RESPONSE**, not repair success and not COST_CAP_REACHED.
Settled cost was **USD 0.788844900**; USD 0.091155100 remained. Billing and input
counting were known. There was no retry, resume or transfer of the unused allocation.

| Stage | Observed result |
|---|---|
| Requests and calls | 23 model calls, 25 input counts, 20 tool actions |
| Original probe | One accepted, completed probe; two observed target calls |
| Failure/control | `bad_has_f0010=true`, `control_has_f0010=false` |
| Frozen declarations | Declared failure matched; desired result mismatched |
| Host acquisition | `acquired`; unchanged base remains `refuted` against desired behavior |
| Subsequent actions | Eight searches and eleven reads; zero mutation attempts |
| Candidate replay/checks/submission | NOT_RUN |
| Independent acceptance and safety | NOT_RUN; no submitted patch |
| Frozen public caller/control checks | NOT_RUN, reason `no_submission`; zero check dispatches |

The model built both fixtures, called `pylint.lint.Run` with list arguments and
`exit=False`, and applied one extractor to each call's captured stdout/stderr.
It tested for F0010 plus the file-load diagnostic. The failing call emitted the
reported diagnostic on stdout; the normal input emitted other pylint diagnostics
but no F0010. Both calls returned normally with complete capture and null exit code.
Execution metadata and diagnostic tails were not mixed into the two-boolean value.

The third dispatched model request contained the exact probe feedback: no differences
from the declared failure and one desired-value difference at `/bad_has_f0010`.
The prepared request hash was checked against the actual dispatch. Thus receipt
generation and delivery occurred. There was no malformed field structure to correct
and no subsequent probe, so autonomous field-correction effectiveness is NOT_OBSERVED.

Mutation was offered from model call 4. The 19 subsequent inspection actions
never became a mutation or a further behavior experiment. Token metadata shows:

| Model call | Admitted output ceiling | Returned output/reasoning tokens | Outcome |
|---|---:|---:|---|
| 1 | 25,000 | 25,000 / 25,000 | Incomplete; no tool call |
| 2 | 25,000 | 17,789 / 16,834 | Funded correction produced the valid original probe |
| 22 | 18,107 | 18,107 / 18,107 | Incomplete while inspection/mutation were available |
| 23 | 10,657 | 10,657 / 10,657 | Incomplete with only mutation/stop offered |

The single funded correction credit was consumed at call 2. The later correction
used ordinary remaining admission; it did not replenish that credit. Inspection
closed for the final call because of the completion horizon. Reserving future
check/finish costs did not yield a valid final action. Reasoning content was not
inspected, so the token counts do not explain the model's internal reasoning.

## Interpretation and remaining boundary

This sample reached a stage the preceding pilot did not: a faithful observed
failure/control value qualified for original acquisition. It did not establish
repair improvement or show that field feedback fixed a malformed request. The
selected observation interface can now be retained while the first unresolved
executed transition, evidence-to-edit, is investigated. No new intervention is
selected merely because funds remained.

The probe used a random temporary directory, HOME pointing there and empty
`input_paths`. Its fixtures were not content-fingerprinted. Cross-execution
condition stability was not tested; no candidate replay occurred. The source and
current normalization rules make the random cwd/HOME a replay risk, but this run
does not demonstrate an actual replay rejection. Preserve that distinction before
claiming end-to-end original-call verification.

## Evidence and integrity

Result root: `C:/pt/observation25-live-v1/`.

- `collection.json`: `sha256:7d4416bd235e0847caf1dd90cdb2a1bb5167413bb6a941a767f5a77efd39b5a5`.
- `public-analysis.json`: `sha256:de8c95c1c4ec69b1786d9f6c8323b683e8dff237666c0867b94aa042ee75585a`.
- `process-result.json`, `cli-result.json`, `public-assessment.json`, source-bound
  preparation/solver/operator journals and CAS retain the underlying receipts.

Collection checked 111 frozen source inputs, 121 CAS objects, journal hash chains,
all 20 action/input-hash pairs, settled provider dispatch/return accounting and
cleanup flags. Public analysis additionally checked the actual feedback delivery
and the unchanged empty tracked diff. Derived obligation/completion projections
are labeled separately from the CLI summary. This analysis did not inspect private
tests/reference patches or provider reasoning contents; opaque artifacts were
integrity-hashed only, and evaluator material was not exposed to the coding agent.
Historical artifacts are unchanged and this allocation is closed.
