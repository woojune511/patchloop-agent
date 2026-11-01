# One diagnostic definition across baseline, repair and feedback

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: implementation and focused local verification
- Origin Date: 2026-10-27
- Verification Status: IMPLEMENTED / LOCALLY_TESTED; live NOT_RUN
- Baseline: `8015c6aa`; prior paid allocations remain closed

## Problem and design decision

The [clean-start trial](2026-10-27-normal-recovery-fresh-results.md) stopped after its
first repair despite unused model/tool/time capacity. F0010 remained with changed
text. The probe tested the old phrase OR F0010, while the host tested only the old
phrase. Baseline agreement concealed the two different definitions. Their later
disagreement entered a correction path restricted to the unchanged baseline, so
the remaining failure never reached another response. The helper's first attempt
also used the wrong capture-status spelling.

Adding another request to repair two independent extractors would preserve the
source of the inconsistency. Fresh diagnostic observations now have one executable
definition: registered stable code plus call ID, evaluated by the host against the
complete per-call streams. The helper constructs the fixture and invokes the target.
It does not duplicate extraction or record its own Boolean observation.

## Implementation

- Fresh wire v64 / invocation v6 use `{field, call_id, code}` rules. The bounded
  code matcher uses ASCII identifier boundaries, not a task-specific F0010 rule.
  Failure/desired objects retain distinct exact Boolean fields.
- `captured-diagnostic-v2` returns `computed` / `source=host`, canonical JSON and
  channel/offset witnesses. An incidental authored value is retained as information
  only. It cannot override actual captures or create a second extraction conflict.
- No-code observations use null rules and the existing explicit value recording
  path. Diagnostic-code selection and public-task mapping remain unverified.
- Missing/truncated captures, unexpected exceptions, unhealthy execution and failed
  setup remain unverified. The actual complete-capture spelling is documented.
- First-call observation, path diagnosis, repair prediction and concern resolution
  accept the new computed evidence. Independent first-observation recomputation
  still must equal the persisted observation; the status change does not remove
  that integrity check.
- Current-diff code failure uses the existing original replay/feedback/repair loop.
  It remains a mismatch when only the message changes and blocks finish. No new
  retry allowance, budget, model tool or observation-correction stage is added.
- v1-v5 observer programs and v1 literal/agreement/correction semantics remain for
  saved bindings. Fresh code rules cannot silently reinterpret old receipts. Exact
  runtime identity still forbids resuming historical paid runs with changed code.

## Local validation scope

The core fixture sequence is baseline F0010/message A, first candidate F0010/message B,
then a corrected candidate without F0010. Unit checks cover lexical boundaries,
code-only schema/admission, no-record execution, an incorrect authored value,
incomplete/exception captures and unhealthy execution.

The normal-runner integration uses an actual counted/dispatched request capture
with a scripted provider and a tiny public CSV fixture. It verifies changed-text
failure and current-diff/source evidence reach the next response, a second edit
executes, current originals and public checks pass, and normal finish reuses the
same-diff receipts. Both result-boundary and forced 60,001-token handoff paths are
covered without renewing model/tool/edit limits or correction credits.

New core coverage: 23 diagnostic cases and two normal-loop handoff cases PASS. The
two actual-request integration cases took 20.36s. Legacy correction/recovery owner
checks passed 12 cases; final legacy judgment plus documentation checks passed 33.

Quick selected 526 cases in 82.779s, including isolated mock evaluation: 514 passed
initially; 11 failed because current schema hash expectations still described the
previous wire contract, and one failed because guide text exceeded its byte bound.
Structural comparison against HEAD confirmed changes only to the probe contract
and its description; current static hashes were updated, historical arms retained,
and the guide shortened. All 12 failed nodes passed targeted reruns (11 hash nodes
in 1.422s, documentation in its five-test owner file). No full quick repeat was needed
after these test/document-only changes. Ruff and diff checks PASS; no unresolved
test failure remains. Receipt: `C:/pt/canonical-diagnostic-local-v1/summary.json`.

During focused validation, two fixture assertions also needed adjustment: the
second edit must use the current marker-bearing source, and compact repair source
is delivered in current-state mutation spans rather than a native-history index.
These were fixture issues; actual failure delivery and normal finish were checked.

These local fixtures do not demonstrate live-model uptake, Astroid repair or
isolated benchmark acceptance. No provider, credential, Docker or target-benchmark
execution is part of this change.

## Remaining question

The structural duplication is removed for code diagnostics, but selecting the right
code and representative calls remains the model's responsibility. A single code's
absence is not general task correctness. A separately authorized live trial must
show that the real model chooses an adequate observation and uses failed-candidate
feedback to repair the original task. This implementation authorizes no such run.
