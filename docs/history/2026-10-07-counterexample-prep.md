# Current-candidate counterexample preparation

Date: 2026-10-07. Implemented and locally tested; one operator public calibration
executed. Provider/count calls: zero. Paid repair collection and new acceptance:
NOT_RUN. All development evidence remains official=false and claim-ineligible.

## Problem, question and decision

The [previous replay pair](2026-10-07-probe-action-results.md) submitted the same
wrong SQLFluff-1733 patch immediately in both arms, without choosing a probe.
Offering replay did not exercise verification or establish a repair benefit.
The current question is whether the model can revise that candidate when it
receives an actual failure of the original public example, given a fresh ordinary
repair allowance. This distinguishes obtaining verification evidence from using it.

The leading possibilities are failure to select verification, failure to interpret
or act on an observed counterexample, and inadequate repair resources. A new patch
passing the original public reproduction, registered regressions and isolated
acceptance would weaken the diagnosis of inability to repair under these conditions.
Changed explanations, probe counts and successful submission alone would not.

The [frozen design](../../.agent/current-counterexample.md) uses the same saved B2
patch and supplies the same original public program to both arms. A's execution
output is withheld; B receives its actual stdout/stderr, exit code and setup result.
A must choose whether to run the supplied program. This is a supplied-program
control, not a comparison of unassisted case discovery. Neither arm inherits old
model history, plans, checks or counters. There are no operator repair hints.

No runtime policy is adopted. The new paid scope is prepared for review; the old
allocation stays closed. A B-only repair would motivate verification-selection work.
A failed B requires tracing ignored evidence, diagnosis/repair error and resource
exhaustion separately. One pair cannot establish an effect size or model inability,
and no larger panel or follow-up runs are automatic.

## Public calibration

External root: `C:/pt/ccecal01`. Its hash-chained journal is
`runs/run_dev_currentcounterexamplecalibration.jsonl`.
`calibration.json` is bound by
`sha256:2c7adb36821e098e28c308cc4f5e4bc49e21a3ac61c73ee910dd56eccdc5908e`.

The fresh provider-free execution used the exact prior public action
`call_YcnJuf5oV8ffOwrmGNBweCbB`, source
`sha256:f7cab304a8f2f5b5b3f7af30d76845dd5e5d5ff79859ce0ebf6552ca7643c9a7`,
on candidate
`sha256:339ced45df8758edfb39c66f63731a9b70537642ab8e7ef219e4efb1ee00cce8`.
Candidate identity was unchanged before/after execution and cleanup was confirmed.
The WITH output had five leading spaces where the program requires eight, so its
assertion failed. The plain SELECT output printed four spaces, but its assertion
was NOT_REACHED after the first failure; do not label that assertion PASS.

Only the original source-agent public program and new receipt enter this design.
Later instrumented operator programs and root-cause findings are excluded. The
receipt grants no required-check credit and becomes historical after a new edit.

## Implementation and frozen execution scope

`b643aa31` adds the coordinator, design and focused tests. It reuses the ordinary
seeded runner and cost guard, previews the real SDK request without provider/count
calls, and checks the normalized first-request identity before live dispatch.
Only timing and the fresh segment identifier are normalized; A/B differ in the
external observation's output. The coordinator preserves per-row settled billing
if a later public audit fails, and does not probe an unsubmitted candidate.

Prepared worktree:
`C:/Users/geonj/.codex/worktrees/counterexample-delivery/PatchLoop`.
Frozen HEAD: `27d10accaf4db0c0f3d3c6ee12391747f528355e`. This includes independent
contract fixes from `345d24b3`; both new arms use that same runtime. The new pair
also has fresh state and a larger remaining repair allowance than the old replay
checkpoint, so it is not a single-variable causal comparison against that old pair.

Manifest: `C:/pt/cceprep02/manifest.json`,
`sha256:0479957a897f2f1d94e90ce4fcdc886790b564830d1cd4a88bceea0b5829e04e`.
Read-only environment preflight: READY. Planned fresh output: `C:/pt/ccelive01`.

| Field | Frozen scope |
| --- | --- |
| Task | dev-train `current-dev20/18`, SQLFluff-1733 |
| Initial candidate | B2, source boundary 526 in `C:/pt/sretcl01/2` |
| Model | `gpt-5.4-mini-2026-03-17`, xhigh, 25,000 desired output tokens |
| Credential file | `C:/Users/geonj/Documents/PatchLoop/.env` |
| Order/repeats | A then B, once each |
| Per-arm limits | 40 model calls, 100 actions, four mutation slots including seed |
| Available new edits | Three per arm |
| Time | 1,800 seconds per arm including 330-second evaluation reserve |
| Context | segmented-v1, result-or-size-v1, brief-v1, 24k retained source |
| Verification | Ordinary probes, repair-recheck, protected-v1 |
| Proposed cap | USD 1.20 per arm; USD 2.40 total, no allowance transfer |

Immediate pre-dispatch counts, zero SDK retries and the existing cost guard apply.
Count, transport, billing, cleanup or infrastructure uncertainty stops the group.
Source/runtime/calibration drift rejects execution. No resume, retry, replacement,
image pull/build or automatic probe policy is added. Each submitted patch receives
one additional frozen-program public audit outside solver context, with no feedback
or continuation. Registered acceptance and sandbox safety stay separate.

## Checkout defect found and fixed

The first clean-worktree preparation failed before provider dispatch because
`current-dev20` lacked the raw-byte Git attribute already used by `portfolio-dev20`.
Normal text conversion had stored LF blobs while the existing task inventories
bound the original CRLF bytes. For one opaque hash-bound asset, the primary file
was 2,216 bytes and the clean checkout 2,191 bytes. This was a reproducible package
integrity defect, independent of the agent's repair behavior.

`27d10acc` adds `tasks/dev-train/current-dev20/** -text -whitespace` and records the
existing primary bytes for 207 task files. The primary working files and declared
hashes were not changed. Ignoring CR-at-EOL yielded no content diff. No validation
was relaxed and no evaluator content or repair hint was projected into the agent.

A new Git-archive regression loads all 20 packages from committed bytes and compares
their public/private/task identities with the primary package identities. Before
the fix the selected task failed; afterward all 20 passed. Evidence is external at
`C:/pt/ccecheckout01`, including `checkout-regression.xml` and the hash-chained
`runs/run_dev_currenttaskcheckout.jsonl`.

## Validation and remaining boundary

- Final fixed worktree: 49 focused tests passed in 36.29 seconds, covering the
  coordinator, all 20 archived task packages and documentation layout;
  `C:/pt/cce-isolated02.xml`.
- Ruff passed for `patchloop`, `diagnostics` and `tests` at the frozen HEAD.
- After this record and current-status update, all five documentation tests passed
  in 0.12 seconds (`C:/pt/cce-docs03.xml`); `git diff --check` also passed.
- Focused coordinator tests include both mock arms through isolated
  EVALUATOR_PASS; mock sandbox safety remains NOT_RUN.
- The final provider-free preparation recorded READY, provider_calls=0,
  cost_nanos=0 and paid_execution_authorized=false. The real public calibration
  above is execution evidence, not model repair or acceptance evidence.
- The full repository test suite, live A/B collection, native evaluation,
  fresh task solves, the 20-task rerun and remote publication are NOT_RUN here.

The next dependent step is approval of the exact new USD 2.40 scope above. Existing
historical journals, source checkpoint and failed replay interpretation are preserved.
