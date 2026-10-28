# Current status

Updated: 2026-10-29. Runtime source owns behavior. Historical reports are evidence,
not an active queue.

## Product and working baseline

Build a single coding agent that repairs public software tasks, verifies changes
and submits within bounded resources. Start improvements from observed failures.
Recovery, sandboxing and isolated evaluation support that product.

- dev-head is the sole mutable runtime; official=false and claim-ineligible.
- General baseline: gpt-5.4-2026-03-05, xhigh, 25,000 output tokens.
- Selected policies: segmented-v1, result-or-size-v1, brief-v1, probes enabled with
  policy none, repair-recheck, protected-v1 inspection, per-call-v1 cost admission.
- Limits: 40 model calls, 100 actions, four accepted edits, 1,800 seconds.
  Paid work also requires the exact task/model/credential/repeat scope and cap.
- Cross-run memory, held-out tuning and claim execution are disabled. Bounded
  run-local notes remain available. Historical Rapid executables are absent.
- These are selected settings, not CLI defaults or evidence of general accuracy.

See [guide](../.agent/guide.md), [operations](operations.md), [product](product.md)
and [evidence boundaries](evidence.md).

## Active decision

Treat benchmark acceptance as the primary repair outcome; report diagnostic
completeness separately. The [three-task result](history/2026-10-29-helper-transfer-three-results.md)
was one isolated PASS, one FAIL and one NOT_RUN. Its additional full verified-chain
criterion was 0/3; that does not mean zero benchmark successes. The allocation is CLOSED.

The [submission-policy change](history/2026-10-29-public-check-submission.md) adds
explicit `public-checks-v1`: current required public checks and scoped diff govern
submission; original reproduction, path diagnosis and observation corrections are
advisory evidence. No new original replay is automatic or reserved. Evidence and
honest delivery labels remain visible; independent evaluator acceptance is unchanged.
The compatible CLI default/control remains `reproduction-gated-v1`. This is an
implemented comparison option, not a globally switched default or proven quality gain.

Keep the [required-public-check contract](history/2026-10-28-required-public-checks.md):
known FAIL and required NOT_RUN block finish, edits invalidate old PASS, and fresh
failure feedback reaches the next response. Source/mutation boundaries, recovery,
uncertain-execution stops, total budgets and private evaluation separation remain.
The [helper API contract](history/2026-10-29-helper-api-contract.md) is unchanged.

The [bounded observation correction](history/2026-10-29-observation-shape-correction.md)
now distinguishes incompatible v11 JSON object fields from a behavioral failure.
Before source edits, one changed observation program can replace that invalid
observation only after the same-condition original failure is reproduced, with
unchanged failure/desired declarations. Failed attempts remain unverified and spend
the shared allowance. Public-check submission keeps this correction optional,
without adding a diagnostic gate or reserve. Local evidence is not model uptake.

The [six-run policy result](history/2026-10-29-verification-policy-six-v2-results.md)
is CLOSED at USD3.841041/27: A had two acceptance PASS and one FAIL; B had one PASS,
one FAIL and one NOT_RUN. Five candidates passed public checks and submitted;
only three passed isolated acceptance. All five safety verdicts were PASS.
No shape-correction opportunity occurred, so live correction use remains untested.
B's SQLFluff run stopped on its first response, claiming no edit tool before reading
source. The actual thin request omitted the host's read-to-edit transition message;
the [edit-availability fix](history/2026-10-29-edit-prerequisite-guidance.md) now
preserves the current edit status, blocking reason and available source prerequisite
through thin/compact requests, correction and recovery. Tool admission, host checks
and budgets remain unchanged. Local request/transition tests and isolated mock
smoke validate transport; the live follow-up below checks actual delivery and actions.
Keep the default unchanged: this small exposed panel does not establish a benefit
from optional reproduction or general superiority. Always-visible schemas are not
introduced; inspect the candidate-verification gap below before widening the action set.
The [single SQLFluff follow-up](history/2026-10-29-edit-prerequisite-single-results.md)
is CLOSED at USD0.587558/4.50. All 11 actual request cards and count/dispatch
identities matched; the model searched, received the edit tool, edited once,
passed 506 public tests and submitted. Independent acceptance FAIL, safety PASS.
One baseline helper observed the reported indentation problem, but the candidate
was not replayed on that public example before submission; budgets and further
tools remained available at finish. The subsequent [operator replay](history/2026-10-29-sqlfluff-public-candidate-replay.md)
now confirms that the saved patch leaves the public failure unchanged: the same
helper produces nine spaces before `my_id` on both original and candidate, versus
the expected eight, with identical SQL output and L003 repeated-fix warning.
The [branch trace](history/2026-10-29-sqlfluff-branch-diagnosis.md) confirms that the
changed L036 branch ran once and its fix was accepted, but produced the same
observed intermediate SQL as the original. Later L003 additions create two
four-space pieces; L039 reduces the second to one, then L003 replaces only the
first with eight, leaving nine spaces. A repeated no-op fix is rejected as a seen
state. These diagnostics establish ineffective intermediate behavior in the old
candidate, not L003 normalization as the only viable repair. No repair, runtime
policy or budget change was made by these operator diagnostics.
The [observation follow-up change](history/2026-10-29-probe-followup-guidance.md)
now connects a pre-edit helper's bounded observations to current-patch reexecution
status in ordinary and compact requests. Existing replay references are advertised
only on an offered general probe route. This adds no automatic execution, reserve,
check credit or submission gate. The [single live follow-up](history/2026-10-29-probe-followup-single-results.md)
is CLOSED at USD1.18095550/4.50 with independent acceptance/safety PASS. The first
L036 edit failed two public tests; a second edit narrowed indentation reuse and
passed all 506, followed by normal submission. All five eligible requests carried
the card; four offered replay, but the model performed no post-edit helper and
disclosed that gap at finish. This is one successful repair and live delivery,
not evidence of replay uptake or causal improvement. Original-call verification
remains unverified without downgrading the acceptance PASS. Keep budgets and
submission policy unchanged; repeatability and the effect on choices remain open.
The [saved-patch comparison](history/2026-10-29-sqlfluff-success-mechanism.md) now
confirms the mechanism on public cases: the old edit still produces nine spaces;
both new edits produce the expected eight immediately in L036, and the final
SELECT-column guard also preserves two top-level regression cases. This operator
diagnostic does not retroactively count as solver replay. The discriminating
pre-edit observation and regression-driven revision are evidenced; card causality
remains unestablished because the first repair idea predates the card.
The [pvlib saved-candidate comparison](history/2026-10-29-pvlib-saved-candidate-comparison.md)
confirms both candidates repair the reported 100-degree call and preserve selected
public expectations. The [native evaluation follow-up](history/2026-10-29-private-evaluation-logs-pvlib-native.md)
now reproduces A PASS and B FAIL with all required cases reported; detailed logs
identify the failing assertion and explain it from the saved code. Evaluator
details stay in external operator artifacts, outside solver context. Private
receipts now retain bounded diagnostic streams; native outputs retain full logs
and hashes. This resolves the saved-candidate failure question, not the causal
effect of submission policy. Keep solver rules and budgets unchanged.
The [five-task frozen-agent result](history/2026-10-29-repair-five-results.md) is
CLOSED at USD2.5451965/22.50: 4 acceptance PASS, 1 FAIL, all five public checks and
submissions PASS. Pydicom's settled oracle failure is a logging-contract/coverage
gap; its private details remain operator-only. Astroid used delivered observations
to revise; Pyvista observed the same public list call fail before and succeed
after editing. Formal original obligations remain unverified without erasing
those observations or acceptance outcomes. All 54 model calls and costs reconcile.
Keep rules and budgets unchanged; analyze the failed public contract before a new
intervention. This exposed panel has no control or repeatability evidence.
Helper return types and incomplete capture remain unresolved. Repeatability and
held-out improvement remain unverified; unused funds authorize no further paid run.

## Supporting evidence

- [Astroid clean-start result](history/2026-10-29-helper-contract-fresh-results.md):
  original F0010 repaired, 1231 public tests PASS, isolated acceptance/safety PASS;
  USD2.0153455. Call tracing was incomplete; one exposed development task only.
- [Security maintenance](history/2026-10-23-security.md): refreshed host dependencies
  and public Python 3.12 images after the emSign incident. Old task/legacy images
  remain offline-only. New runs need newly prepared identities; prior manifests
  do not authorize execution against the updated runtime.
- [Helper-path results](history/2026-10-22-helper-path-results.md): useful information,
  no repair in A1/B1/B2; partial comparison stopped on drift. Allocation closed.
- [Invocation linkage](history/2026-10-22-probe-invocation-results.md): submitted
  repairs 0/3; ON mechanism use 0/2. Partial run; no adoption or quality claim.
- [Caller evidence](history/2026-10-19-caller-evidence-results.md): A/B 0/6;
  original-caller verification remained missing.
- [Portfolio remeasurement](history/2026-10-06-portfolio-dev20-results.md): 9/20,
  below the 11/20 threshold; test300 remains unprepared and unauthorized.
- [History](history/README.md) indexes the closed investigations and allocations.
  Their past next steps, settings and approvals do not carry forward.

## Execution and claim boundaries

All prior paid allocations are closed. The [older interrupted call](history/2026-09-28-expectation-review-results.md)
retains unknown billing; later settled allocations do not resolve it. The latest
source-ready diagnostic also retains one unsettled response.

Fresh solves, seeded repairs, funded continuations, saved-patch evaluations,
operator replays and scripted tests are different evidence. Do not pool them as
solve rates or expose private evaluator details to the agent. Public case support,
submission, independent task acceptance and safety are separate. Mock safety is NOT_RUN.

Do not start Docker Desktop or pull/build evaluator images automatically. Preserve
exact recovery identities, zero SDK retries and stop-all on count/transport/billing
uncertainty. Saved-candidate and operator successes remain distinct from clean-start
development outcomes above. Repeated fresh-solve performance and held-out
improvement remain unverified.
Public-check PASS, safety PASS and successful submission do not establish repair
correctness. Linux CI and general improvement remain unverified.
