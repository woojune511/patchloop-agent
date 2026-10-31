# Verification continuity after the fixed dev20 run

Date: 2026-10-31 KST. Scope: implementation and local validation; no new live solve.

## Problem and decision

The [frozen dev20 run](2026-10-31-verification-reuse-dev20-results.md) completed with
11 independent PASS, 8 FAIL and one unsubmitted deadline stop. The user asked to
improve the agent's preservation of original inputs, callers and expected behavior.
Correctness takes priority over another generic instruction to reduce repeated checks.

The existing repair and plan instructions already require original-call fidelity,
public grounding of expected behavior and preservation of unresolved verification.
Accepted mutation hypotheses and expectations already survive handoffs. Adding a
second general expectation store or another mandatory probe gate would duplicate
those mechanisms without addressing the observed delivery gaps.

Two public records identify a smaller intervention:

- Task 8's first helper used bytes, while later helpers changed representation to
  bytearray/array. In public model input 204, before the source edit, neither earlier
  program remained available: questions/results survived, but exact inputs/callers/
  assertions did not. The public issue itself was still visible. A separate operator
  diagnostic confirmed a remaining bytes/setter defect, but does not prove program
  omission caused that defect or reveal the private evaluator's failing assertion.
- Task 10's rejected test would have emitted a caller log record and asserted exactly
  one output. It was delivered immediately after rejection at input 113. After a
  successful source-only correction, inputs 128 and 244 lacked that proposal; the
  later accepted test checked logger state instead. Clearing `last_failed_mutation`
  was correct for mutation recovery, but also removed the only retained test text
  when the native segment expired. This is a delivery gap, not proof of forgetting.

The hypothesis is that keeping these existing public facts inspectable will support
comparison of the original and replacement experiment. The model may still choose a
different path, infer the wrong oracle or ignore a visible distinction. Those are
plausible remaining explanations; only a future live run can measure uptake or repair
benefit. Local delivery tests cannot settle them.

## Implementation

`recent_probes` keeps its existing last-three bound. Each record can now include the
exact executed program, at most 8,000 characters, bound to matching action/input,
baseline/result diff, question and source hash. Replay/saved-case requests use the
resolved program recorded at admission. Missing or inconsistent bindings supply no
guessed program. Exact visible native arguments permit a delivery reference; a replay
with null source does not. The raw journal and provider exchanges are unchanged.

Current, repair and completion views carry these programs across a segment reset.
Completion retains only identity/question/program for a historical diff, without its
old output or verdict as current evidence. Programs expose experiment construction;
they grant no original-task mapping, success, required-check or submission credit.
The existing counted input limits still apply; maximum retained program text is 24K
characters. This is a bounded input-size tradeoff, not a measured cost improvement.

`last_rejected_test_proposal` is a pure projection of the latest paired, completed,
rolled-back mutation involving a declared additive test root. It retains up to four
test edits and 8,000 total old/new text characters, explicit omissions, original
action/input/baseline identities, and bounded hypothesis/expected-behavior text.
It survives successful source-only edits, plan changes, checks and stage handoffs.
A newer qualifying rejection replaces it; unrelated failures do not.

The proposal remains historical model-authored text. The original attempt was not
applied; later edits are separate. Even a later test on the same path or a suite PASS
does not establish semantic equivalence to that proposal. No automatic resolution,
new verification obligation, execution, tool, model call or finish gate is added.
Ordinary `last_failed_mutation` still clears after successful mutation admission.
No cross-run memory, hidden test, private oracle or task-specific hint is introduced.

Task 17 also exposed a separate concrete diagnostic bug: a YAML file under a declared
test root was reported as outside the root. The validator now checks root membership
and the Python-only file restriction separately. Python additions and exact-original
file restoration retain their existing behavior; YAML support is not introduced.

## Validation and limits

The [offline public-record audit](C:/pt/verification-continuity-20261031-v1/public-continuity-audit-08-10.json)
binds the old input/event identities and exact recovered programs/assertion text:
`sha256:4bcf87a31824b2e0becde17b76e2fba525d4b24d6fdb8e9edeb856b2512c89fd`.
Both task 8 program hashes match their executed sources; task 10's 3,104-character
test proposal is retained unchanged after source-only recovery. This comparison
reads only public records and makes zero provider, target or evaluator calls.

Local tests cover bound native/inline program delivery, replay identity drift,
current/repair/completion segment transitions, historical/current separation,
rejected proposal persistence after source-only recovery, weaker later test success,
bounded omissions and unchanged available tools/completion gates. Validator tests
cover distinct restrictions, original restoration, atomic rejection and idempotency.
Focused context/program/proposal tests passed 107 cases in 8.55 seconds. Subsequent
malformed-request and repeated-projection controls passed in their owner files
(25 proposal tests and 29 program tests); validator/restoration tests passed 28.
The first fast-suite run found four stale current-contract fingerprint assertions
and two context-construction failures from reading constraints on a lightweight
package view. Current fingerprint fixtures were updated, with legacy fingerprints
and tool argument serialization unchanged; root selection now uses the gateway's
authoritative public task. The six failures plus the existing observation owner
tests passed together: 23 tests in 21.94 seconds. The first failed run is preserved.
Final fast suite: **1,362 PASS / 1 host-symlink SKIP**, 281.54 seconds with four
workers and no worker restart, including isolated mock evaluation. Ruff passed.
[Local validation receipts](C:/pt/verification-continuity-20261031-v1/) retain the
first failed run, focused/correction/final JUnit reports, public-record comparison
and final source/document hashes. No historical experiment or journal was modified.

The implementation addresses information delivery, not semantic judgment. No new
model invocation, target probe, independent evaluation or paid experiment was run.
The earlier 20 outcomes remain unchanged. Task 12's output-oracle ambiguity, task 18's
diagnosis/decision latency and the six overlapping selected-test actions remain open.
Next live evidence should examine whether the retained input/caller/assertion details
actually affect an agent's repair or verification decision, without injecting the
operator's known counterexample or changing private grading.
