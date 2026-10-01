# Isort public comment-ownership diagnosis

## Problem and evidence boundary

Isort was the remaining unexplained fixed-batch failure: original acceptance 0/1
bug cases, 73/73 regressions. Public regression success alone did not establish
the issue's comment-placement requirement. Compare the saved repair and public
action evidence against the issue and controlled public-input variants before
inferring a shared agent problem from the batch.

Run: `run_dev_49397fa9568d4b80`; base
`ae91dadf34951e316d5a81ffe7ac086952f1da65`; patch SHA256
`6edb32a68f8fea1002de9fa6836b1e583de021a53c176b94653dc894567e2940`.
No hidden test contents, private reference patch or evaluator assertions were
inspected. No new model calls or hidden evaluations occurred.

## Trace and competing explanations

The agent read parsing/output/wrapping code, made a broad opening-comment change,
and observed three public regression failures. Two public probes investigated
parsed comment categories and rendering calls. The agent then narrowed the change
to comments containing type: ignore, passed the required regression recheck and
submitted. Both probes preceded that final narrowing; there was no final probe.
This is not absence of diagnostics: useful diagnostic evidence was collected.

The final patch changes only wrap.py. It keeps type: ignore comments on the
opening line when parentheses are configured. Possible explanations were a
general ownership repair, a comment-text workaround, or a profile-specific effect.
The narrow question was whether changing only original placement or comment text
changes correctness while other conditions remain fixed.

## Frozen public diagnostic

Before execution, recorded the program, question, controls and stop condition in
an external hash-chained journal. Executed base and submitted patch once each in
fresh prepared source with the already-installed pinned benchmark image. Each
condition exercised two profiles (default and Black), two comment texts (the
issue's type: ignore[attr-defined] and an ordinary explanation), and two original
placements (opening line and imported member). The module/member names match the
public example. Logged wrap.line input and actual isort.code output; compiled all
outputs and checked idempotence. Imports were verified under /workspace.

| Black profile case | Base comment location | Submitted location |
| --- | --- | --- |
| Opening type: ignore | Member | Opening, repaired |
| Member type: ignore | Member | Opening, ownership regression |
| Opening ordinary comment | Member | Member, unrepaired |
| Member ordinary comment | Member | Member, preserved |

For each comment text, the two distinct original placements produced identical
wrap.line input strings. The final predicate cannot distinguish them at that
boundary. All default-profile cases still place comments on continuation/member
lines; base and submitted outputs are identical there. Default formatting uses
backslash continuation, unlike the issue's parenthesized observed output, so this
profile difference alone does not identify the original hidden failure.

All sixteen outputs compiled and were idempotent, demonstrating that those checks
alone do not detect wrong comment ownership. Both containers exited zero and
confirmed cleanup under read-only workspace/root, network none and 60-second
limits. Zero exit here means diagnostic completion, not all cases correct.

## Decision and next question

The submitted patch is a wording-specific workaround rather than an ownership
repair. It fixes the public example under Black but over-hoists member-level
type comments and leaves ordinary opening comments misplaced. Its source boundary
has already lost the distinction needed for a general repair. A task-level repair
should preserve ownership before that collapse and carry it through rendering;
the exact minimal source change remains unimplemented and uncalibrated.

The agent's probes exposed the loss of distinction, but the final change used
comment text as a proxy for ownership. Passing the regression recheck did not
test the remaining paired ownership cases. This does not establish that a new
mandatory probe rule, memory feature or prompt would fix the agent's decision.
The observed trace is evidence of actions and stated decisions, not private intent.

Together, OpenSandbox's boundary coverage gap, pyinfra's evaluator limitations and
isort's ownership workaround do not justify one shared harness intervention.
Keep the baseline and original three-task results unchanged. A future investigation
can test an ownership-preserving task-level control against these public pairs
and regressions before any agent-quality experiment. No paid run is queued.
The exact hidden assertion responsible for the original FAIL remains unexamined.

## Evidence and validation

Root: `C:\pt\analyses\isort-public-diagnosis-20261001-v1`.
Journal: `runs/run_dev_isortpublicdiagnosis.jsonl` (four validated events).
`summary.json` contains all sixteen input/output observations and wrap inputs;
content-addressed receipts bind execution policy and exact diffs.
Driver: `C:\pt\isort_public_diagnosis_20261001.py`.
Only this record and current status changed for the diagnosis. Documentation
checks and whitespace checks passed; runtime and task packages were not edited.
Original artifacts and prior historical records remain unchanged.
