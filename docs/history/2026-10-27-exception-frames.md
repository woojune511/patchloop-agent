# Bounded exception evidence and the repair bottleneck

Date: 2026-10-27. official=false. Local diagnosis and implementation; model repair
effect NOT_RUN. Parent source: `1e56de89`; runtime identity below owns execution.

## Material Passport

ARS experiment validation using public source, saved execution receipts and new
local replay. No private evaluator material or inferential statistical claim.

## Problem and decision

The [diagnosis-gap analysis](2026-10-26-repair-diagnosis-gap-analysis.md) found that
negative feedback reached the model but exception locations never entered capture.
The latest pilot's two failed edits therefore do not demonstrate that correct
diagnostic information was ignored. Another fresh solve would mix acquisition,
inspection, request construction, repair, verification and resource exhaustion.

The selected question is whether the same saved failed candidate can yield enough
public evidence to distinguish its actual fault from a secondary reporting error.
This precedes testing whether a model can use that evidence for a useful revision.
Keep the failure blocker; do not introduce another mandatory stage or raise context
solely because this trajectory failed. Completion classification and access to
diagnostic evidence must be treated as separate design responsibilities.

## Observed cause

Operator diagnostic `C:/pt/exception-frame-diagnostic-v1/result.json` re-executed the
unchanged authored original against the base and both saved candidates in existing
local images. Only observation instrumentation changed. Its hash is
`sha256:2a50be41099bf5dd8030ed40852ef972e18215b981e8352e0b7c4a4a5c0f8fb6`.

| Candidate | Earlier exception | Escaped exception |
| --- | --- | --- |
| First saved edit, `9914a973...` | `AttributeError: __enter__` at dependency `pylint/utils/utils.py:164`, `tokenize_module` | `FileNotFoundError` at dependency `pylint/lint/utils.py:22`, `prepare_crash_report` |
| Second saved edit, `8feefc03...` | `FileNotFoundError` at public workspace `astroid/nodes/scoped_nodes/scoped_nodes.py:546`, `_get_stream` | The same reporting failure |

The first edit returns a namespace module with neither file nor file bytes; the
consumer attempts `with node.stream()`. The second assigns a nonexistent initializer
path, and the consumer attempts to open it. Both later encounter another error
while Pylint reads that nonexistent file to prepare its crash report. Type/message
alone hid two different earlier faults. The file control remained unchanged.
These are observed failure mechanisms, not a proven correct repair specification.

All three executions completed with confirmed cleanup and untruncated observations.
The diagnostic used no provider or private evaluator. Changed instrumentation gives
diagnostic evidence; it does not retroactively verify the old model's candidate.

## Implementation

Fresh invocation v5 attaches a trusted exception collector; frozen observer v1-v4
bytes are preserved. A separate 32KiB channel avoids competing with core call/output
capture. Bounded details contain up to three exceptions, 16 public frames, at most
12 frames per exception and a 6,144-byte packet. Frames carry origin, relative path,
function, line and file hash, without locals or source text. Cause and unsuppressed
context are retained; truncation, excluded frames and unsupported groups are explicit.

The public packet is bound to the action, execution source, snapshot and selected
call/exception. The model's compact repair view retains it. Malformed or missing
details cannot erase otherwise valid negative evidence or create success credit.
Whole-case UNKNOWN, public checks and submission requirements remain unchanged.
Tool surface v63 and the probe profile bind the new implementation. No new model
tool, mandatory gate, budget, retry or context policy was introduced.

## Local execution and validation

The final registered-gateway calibration is
`C:/pt/exception-frame-calibration-v2/calibration.json`, hash
`sha256:82529d87a5cc86e00d5c1ca670fc54a37ab0a4969a406b90766996109b2027fc`.
Runtime hash:
`sha256:5753dbef010721c721db788aa01525fc269ad12093b46e45ffc2ffd158c929f3`.
Two target executions acquired the current-profile base and exact first saved edit.
The current failure and compact model view both contain two exceptions and nine
public frames, with no bounded-frame omissions. One wrapper frame is outside the
public source scope. Whole-case verification remains UNKNOWN and credit false.

The earlier v1 preparation failed locally after its baseline because an inspection
decision omitted required `evidence_goal`. A separately recorded continuation reused
that settled baseline and completed the candidate observation without duplicate
dispatch. V2 executed afresh after the v63 runtime contract was finalized; it is the
comparison's calibration. Old artifacts were not relabeled or overwritten.

Core focused validation passed 105 tests in 27.35 seconds. The first final quick
attempt found two expected-surface hashes still pinned to v62; those test pins were
updated for v63, preserving frozen historical-arm hashes. Earlier lint failures
and an oversized history index were corrected. Final validation is recorded at
`C:/pt/exception-frames-final-v1/summary.json`: operator/fork/docs checks passed in
22.20 seconds, quick472 passed in 42.79 seconds, Ruff passed. Quick includes isolated
mock evaluation. This is local mechanism/integration evidence, not a repair result.

## Smallest model comparison and interpretation

`diagnostics/exception_frame_repair.py` prepares two requests from the same first
failed candidate and current-profile calibration. A receives type/message, B also
receives bounded frames and exception chain. Initial inputs are checked to differ
only in this field. Later diagnostic tools are identical: A may acquire frames.
This tests initial information availability, not permanent evidence withholding.

The operator allows one new accepted edit, four ordinary responses and one protocol
correction, twelve tool actions and one diagnostic probe per arm. It reuses the
registered adapter, cost ledger and tool gateway. Host original/control replay and
public regression follow the edit. Merely removing F0010 while raising a different
exception is not support. There is no submission or independent acceptance claim.

Prepared scope: dev-train `current-dev20/13`, `gpt-5.4-mini-2026-03-17`, xhigh,
40K ordinary / 25K correction ceilings, A and B once each, new USD 1.20 total and
USD 0.60 per arm, exact repository `.env`. A fresh exact authorization is required
before collection. Preparation has no credentials, counting or provider dispatch.
The user subsequently approved the exact v2 manifest at
`C:/pt/exception-frame-repair-plan-v2/manifest.json`, hash
`sha256:73367ba93e99a6aa09b1312f53bc8ef00cfe857011ae8d2fa3063bdf7d6395a5`.
The approval is separately journaled. Collection results will be a separate record.
Read-only review found missing stop-all handling for tool cleanup/recovery errors
and unsettled tool deadline exceptions in the new operator. It now reuses the
production abort rule in both model and sequential host checks; 22 focused operator
tests passed, including stopping the second arm while retaining known billing.

One pair can show a mechanism or expose another bottleneck, not an improvement rate.
If B still fails despite delivered, usable evidence, inspect its next action and
test tool accessibility or model/reasoning settings separately. Do not keep adding
exception-specific gates or repeatedly restart the whole solve without a question
that those runs can distinguish. Conditional repair success would justify a later
fresh-solve check and other development tasks, not held-out generalization.

The broader architectural recommendation is a small stable loop: observed failure,
relevant public source, testable repair, original replay. Host-side identity, cost,
recovery and completion rules support that loop. The existing specialized path
trigger covers unexecuted changed lines; its `not_needed` does not mean that an
executed but incorrect repair needs no diagnosis. Whether a broader shared diagnostic
operation is needed remains a separate question after testing this information fix.

ARS methodological scan: 11/11 checked. Adaptive selection of one known failing task,
changing historical conditions and missing controlled repair outcomes prevent causal
quality or model-capability claims. Local collector/gateway success is not model uptake.
