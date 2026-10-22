# Helper-path information: qualified observation, partial comparison

Closed 2026-10-22. All runs are `official=false`, `claim_eligible=false`.
The four public diagnostics found new execution information without changing the
observed caller behavior. The paid comparison stopped after A1/B1/B2 because a
concurrent documentation commit changed HEAD. All three submitted repairs failed
registered acceptance, independent native acceptance, and the original failing
caller case. The normal caller case passed. A2/A3/B3 are **NOT_RUN**, not failures.
No runtime intervention was adopted; no unused allocation is queued for execution.

## Problem and competing explanations

The [prior caller comparison](2026-10-19-caller-evidence-results.md) supplied the
original caller, arguments, environment and failing/normal controls, but repairs
were 0/6 per arm. Repeating those observations would not answer a new question.
The observer had not collected `file_info_from_modpath` or `_spec_from_modpath`.
The narrow diagnostic distinguished helper bypass from helper execution with
different arguments, branches or exceptions. Mere rediscovery of
`source=True -> file_build` would have stopped this allocation.

The [frozen design](../../.agent/plans/helper-path-comparison.md) asked whether that
new execution information changes public decisions and repairs at one saved
failure checkpoint. Operator-supplied observations do not test autonomous evidence
acquisition. Better retention, prior-interpretation persistence and incorrect
generalization from a helper remain alternative explanations; none is established
as the sole cause by this experiment.

## Four provider-free diagnostics

`diagnostics/helper_path_probe.py` executed missing-off, missing-on, present-off,
present-on exactly once each. OFF retained the old caller profiler; ON additionally
traced bounded lines/returns in the two helpers. Source, dependencies, image and
profile matched the original public caller observation. The entire common caller
observation matched OFF/ON after normalizing only the temporary fixture root.

| Public condition | New helper observation | Common caller outcome, OFF = ON |
|---|---|---|
| Missing `project/__init__.py` | `file_info_from_modpath(['project'])`, `context_file=None`; `_spec_from_modpath` raises `ImportError` at line617, propagated at line398 | exit1, F0010, child file not analyzed |
| Present `project/__init__.py` | `file_info_from_modpath(['src','project'])`; `_spec_from_modpath` reaches `PKG_DIRECTORY` and returns `PY_SOURCE` at line631, location `./src/project/__init__.py` | exit0, child file analyzed |

Both helpers were called once in each ON condition, from Pylint's
`expand_modules.py:91`. This rejects helper bypass for these observed calls and
locates an exception before the classification branch in the missing case. It
does not identify a sufficient repair. The module-name contrast itself was already
known; the measured helper execution and exception/return distinction were new.

String arrays contain at most eight entries, so full search-path completeness is
not claimed. An exception followed by trace `return:null` is not a successful
`None` return. There was no overflow, truncation, timeout or unconfirmed cleanup.
One OFF/ON execution per condition does not establish general noninterference or
repeatability. The information review was shared-context, not blinded.

All four receipts and the result CAS were durable before a derived-export path
error. Journal sequence11 completed collection; sequence12 records that error.
The export helper was fixed to use the output-root ArtifactStore, and sequence13
records recovery from the exact saved CAS. No probe was rerun and no evidence was
overwritten. The information and official-pricing reviews were journaled separately.

## Qualification and funded scope

Task: `tasks/dev-train/current-dev20/13/public.yaml`, Astroid-1333, dev-train.
Base: `d2a5b3c7b1e203fec3c7ca73c30eb1785d3d4d0a`, empty diff.
Parent `run_dev_f1a28479931d443f` was cut before event342, preserving settled events
through341 with prefix hash
`eaf6e01ef57a1df862d728dbd5367dc76736d6b695ba7811f93a4969fe304596`.

The old runtime could not be resumed strictly. Existing explicit current-runtime
fork machinery copied the settled prefix and rebound the envelope, preserving the
parent model, policies, 16 remaining model calls, 76 actions, four edits and
1,530,158ms including a 330s evaluation reserve. Ordinary resume was not bypassed.
Historical cost USD0.37263270 per row was bookkeeping, not billed again.

A received the exact old caller packet; B received that packet plus the new helper
measurements and collector code, without a repair recommendation. Supplements were
injected into the first current state only. Two provider-free rehearsals qualified
the final implementation; the second followed a fix to stop on between-row HEAD
or implementation drift. B minus its helper field equaled A's complete prepared
request. Task, tools, twelve current source records, inherited state and limits
were common. An earlier list/dict adapter error was fixed before these rehearsals.

Execution commit: `0ff74c2db3204d8d307ff37dfeb9cf544a6540b7`.
Runtime hash: `sha256:3ab80d0f583d4cf939c9ac7281ea84fa4f4b61e1b1554d8778d49e5ea8ac27c2`.
Final manifest: `sha256:f504ae625b5c60f3a2860b6e752a91a30c57e4c11faa74a7ec44208a356a85e1`.
Model: `gpt-5.4-mini-2026-03-17`, xhigh, desired output25000, zero SDK retries.
Authorized order: A1 B1 B2 A2 A3 B3; new cap USD0.50736730/row,
USD3.04420380 total, no transfer, replacement or resume. The exact credential
path remained bound; its contents were neither displayed nor sent to evaluators.
[Official prices](https://developers.openai.com/api/docs/pricing) were checked
before dispatch: input/cached/output USD0.75/0.075/4.50 per million tokens.

First actual inputs matched the prepared hashes; successful counts immediately
preceded their admitted dispatches. A1 began at 33,229 input tokens; B1 and B2 at
36,767. The extra 3,538 tokens, attention and cost are part of the intervention;
an isolated semantic-information effect cannot be claimed.

## Partial execution and assessed outcomes

| Row | New calls / counts | New USD | Accepted edits | Registered / native | Original missing / present |
|---|---:|---:|---:|---|---|
| A1 | 9 / 9 | 0.39623460 | 2 | FAIL / FAIL | FAIL / PASS |
| B1 | 6 / 7 | 0.26950275 | 1 | FAIL / FAIL | FAIL / PASS |
| B2 | 9 / 10 | 0.40282695 | 2 | FAIL / FAIL | FAIL / PASS |
| A2, A3, B3 | 0 / 0 | 0 | 0 | NOT_RUN | NOT_RUN |

Total new cost **USD1.06856430**, 24 dispatches, 26 input counts; billing known.
Execution lasted 07:12:23-07:26:42 UTC, including local checks/evaluation and row
admission. The row usage sum equals the invocation ledger. All three submitted;
registered safety and cleanup passed. This is 0/1 successful executed A repairs
and 0/2 executed B repairs. There were three assigned rows per arm, but reporting
0/3 as three evaluated failures per arm would be incorrect.

The unrelated commit `45d9d828b46fb87d5ef002821edfc0b0b476d056` changed only current
status, the history index, and a separate caller-linkage report after B2 started.
All three executing-runtime identities remained `0ff74c2d`; runtime/diagnostic
bytes were unchanged. The fixed-HEAD preflight nevertheless stopped A2 with
`execution controls changed`; A3/B3 were never admitted. The collector's broad
stop label is `NOT_RUN`; the row records retain the precise cause. The gate was
not relaxed after observing outcomes. This operational interruption leaves the
planned balanced comparison incomplete; it is not evidence of a semantic runtime
change or a model failure. A future independently justified protocol should make
documentation-only concurrency explicit before execution, or isolate the checkout.

Public action annotations were sealed before any fresh acceptance grade was
opened. Assessment reused the frozen original public programs and pinned native
harness without provider calls or image acquisition. Each submission received
two public caller checks and one independent native evaluation, with a shared
600s per-submission allowance. Registered/native grades agreed in all three rows.
Original missing cases retained exit1/F0010 and did not analyze the child; present
cases analyzed the child and passed. Caller checks used the source projection;
native evaluation used the exact full submitted diff. B2's additive test file was
excluded only from the caller projection; source bytes and both hashes are bound
in its receipts. No hidden test details or reference patch entered solver context.

## Public decisions, retention and interpretation

- A1 immediately changed the manager fallback (seq353), corrected its explicit
  modname cache regression after a failed check, and finished after the current
  regression passed (seq446). It made no new probe. Its claim that the suite
  confirmed the repair without a remaining gap (seq473) lacked original-caller
  verification.
- B1 first searched for manager test style (seq353). Its third decision called
  `modpath_from_file` and `ast_from_file(..., 'project', source=True)` directly in
  a new fixture (seq381), returning `ImportError` and `AstroidBuildingError` before
  editing (seq386). Probe process PASS did not mean those calls succeeded. It
  added an `isfile` guard, passed regression, and explicitly acknowledged no
  post-edit extra reproduction while declaring the gap non-blocking (seq431).
- B2 first treated an inherited direct-helper success as evidence that core
  namespace handling was safe (seq353). Its third decision tested
  `ast_from_module_name('project')` under different contexts; only directory
  context succeeded. Later it described that result as a `src.project` call
  (seq415). It changed directory/source classification and added a directory-input
  test, then called that the exact failure shape (seq475). This test did not
  reproduce the original Pylint caller tuple.

Neither B public trajectory explicitly linked the new helper execution,
exception or return observations to a changed action: **0/2 positive uses; both
NO_OBSERVED**, not proof of no internal influence. All three completion claims were
unsupported in original-task scope when judged from public evidence. They were
not labelled contradicted by a solver-visible current-candidate counterexample.
The later independent failures do not retroactively change those sealed labels.

Deep equality over all public input routes found the complete original packet in
A1 inputs1-2, and both complete packets in B1/B2 inputs1-3. B1/B2 selected their
different helper probes while both packets were still present. Whole packets and
the complete missing-helper call record disappeared from later public inputs at
handoff. This does not prove loss of every fact, summary or interpretation, nor
does it isolate retention as the cause of the earlier scope choice. Raw/encrypted
reasoning was not inspected. The audit used Codex plus a shared-context read-only
reviewer; it was neither a blinded human study nor a separate paid model judge.

## Decision, validation and evidence

The advancement criterion was B>=2/3 repairs, B>A, at least two helper-linked
successful behavior changes and no normal-control regression. It was not met.
New information was demonstrated, but repair benefit was not. The incomplete,
single-checkpoint sample cannot estimate a reliable A/B effect or general quality.
No trace expansion, new prompt, memory mechanism, runtime adoption or paid rerun
follows from this result. The unresolved question is how to preserve and test the
original caller tuple when a narrower helper result seems sufficient to the agent.

Validation: final focused helper tests 12 passed in0.95s; relevant comparison and
ledger tests 33 passed earlier in66.64s. The quick suite plus documentation checks
passed 244 tests in358.95s before the final drift-only fix. Ruff and diff checks
passed. Closing validation combined the focused tests, documentation checks and
explicit isolated mock smoke: **18 passed in7.26s**. Final Ruff and `git diff --check`
also passed. These are local engineering checks, not repair accuracy.

Generated evidence is outside the repository in immutable CAS and hash-chained
`dev-run-v1` journals; private evaluator logs are not part of the public audit:

- `C:/pt/helperpath22-g0/`: four receipts, result, gate/pricing reviews;
  `runs/run_dev_helperpathgate.jsonl` preserves completion and export reconciliation.
- `C:/pt/helperpath22-prep/` and `C:/pt/helperpath22-prep-v2/`: provider-free input
  rehearsals; only v2 authorized the paid invocation.
- `C:/pt/helperpath22-live/result.json` and
  `runs/run_dev_helperpathcomparison.jsonl`: raw collection, usage and stop reason.
  Its `repair_effect=NOT_ASSESSED` is the immutable collection-stage value.
- `C:/pt/helperpath22-analysis/`: frozen analysis contract/driver,
  `audit-public/index.json`, `input-inventory.json`, sealed `annotations.json`,
  `result.json`, and per-submission caller/native receipts. The audit journal orders
  the annotation seal before assessment; this result supplies the later repair verdict.

Existing historical records and the user's AGENTS.md modification were preserved.
The experiment introduced diagnostics and tests; production `patchloop/` behavior
was unchanged.
