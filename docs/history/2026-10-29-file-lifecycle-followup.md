# File lifecycle and diagnostic cleanup

Date: 2026-10-29. Parent: `bb042dd6`. Local engineering, public-record inspection
and mock verification; no paid provider or Docker invocation. Historical records
and their approvals are unchanged.

## Why this change

The user requested follow-through after contract normalization, accurate action
budgets and a larger edit allowance. The remaining interface could replace text
but could not create a helper, change coupled files in one action or explicitly
undo an accepted attempt. Those were capability restrictions, not demonstrated
causes of every failed repair. Removing them requires source/evidence, submission
and recovery to agree about the same files.

The smallest coherent extension is one registered `edit_files` action sharing the
existing mutation quota, completion forecast and journal. It does not add another
planner, generic shell, workspace registry or experiment lifecycle. A common
`MUTATION_TOOLS` set replaces assumptions that only `replace_text` mutates source.

## Implemented contract

- `edits` contains 1–16 distinct paths, or `undo_action_id` selects a completed
  mutation in this run. Supply the unused field as null. Both require hypothesis
  and expected_behavior. Each text is bounded at 20,000 characters.
- Existing-file replacements preserve exact delivered anchors and occurrence
  semantics. `old_text=null` creates an absent regular UTF-8 file from `new_text`;
  it never overwrites an existing file. New files use Git intent-to-add, making
  reads, searches, canonical diffs and submitted/evaluated patches agree.
- Full accumulated task scope still applies: allowed paths, changed file count,
  diff size, dependencies, public API and original-test restrictions. For example,
  the existing API policy rejects new Python modules when API additions are
  forbidden; the mock helper fixture explicitly permits them.
- One accepted batch or undo consumes one accepted edit, with no refund. Checks
  must match the resulting diff. Undo restores the recorded exact images and
  removes a file only when that action originally created it. Later unrelated
  changes survive; changed target files reject undo. Legacy receipts lacking file
  images are not undoable with this interface.
- New additive test modules can contain imports, a leading docstring and supported
  tests inside declared test roots. Original imports/tests/fixtures remain intact.
  Isolated original-test grading removes new tests temporarily and restores exact
  bytes/modes afterward, including on exceptions. `repair-verify` retains its
  narrower top-level selector contract; collection errors remain INCONCLUSIVE.
- Arbitrary deletion, renaming and unrestricted shell remain outside the tool.

## Recovery and implementation decisions

Admission writes content-addressed before/after images outside the worktree before
source mutation. A disposable copy of the current index previews the baseline,
incremental patch and complete candidate; earlier explicitly created files remain
part of that preview. Real source/index bytes are unchanged by preview.

Atomicity is logical under the existing execution lock, not an instantaneous
filesystem-wide multi-file rename. Ordinary failures roll the entire action back;
a process crash can leave a mixture of admitted before/after files. Resume accepts
only those states and the recorded baseline/candidate identities. Unknown drift
is rejected. `action_id + input_hash` still prevents duplicate work and conflicts.
Unconfirmed rollback keeps the action pending and stops remaining repetitions.
An expired deadline cannot begin an entirely unwritten mutation; bounded recovery
may reconcile an already partially applied one.

During implementation, raw CRLF diff bytes exposed an older newline-conversion
problem: text-mode subprocess decoding changed Git patch bytes. `diff_summary`
now decodes raw bytes explicitly so preview, delivery and identity use the same
patch. New-file isolated delivery uses `git apply --intent-to-add`.

Integration checks also caught single-file assumptions in failure diagnosis,
before-mutation test comparison and rejected-draft retention. Diagnosis now binds
each actual Python postimage; reversing an undo preserves recreated Git membership;
new diagnosed test modules pass their explicit creation flag. Unexecuted file
transaction drafts share the existing two-draft/32k-byte correction limit and
never become executable source evidence.

## Removed complexity and measured latency

The old `boundary_pair_panel` paid orchestration no longer preserves its B planning
treatment through current compact prompts. Its retired freeze/preflight/run
entry points now reject before I/O; obsolete execution orchestration was removed.
The strict all-turn treatment assertion and utilities used by
`observation_repair_panel` remain. This removes an incompatible driver without
turning an undelivered treatment into a passing experiment.

Public dev20 timing inspection found 223 provider calls / 4,368.414 seconds and
136 inspection turns containing 292 successful read/search actions. Fifteen
turns added no source coverage and took 210.341 provider seconds (4.8%). Ten of
those were first searches; zero added coverage does not establish redundant work.
No wholly stagnant turn met the existing stagnation signal. Two row-10 literal
OR searches reflect wording already corrected before this change.

The report is stored unchanged as content-addressed artifact
`sha256:f2fc29122c6592c9b4ff7802c34da8b04ccb2fc5d1681c6886756f9409e5dd9c`
under the append-only `dev-run-v1` audit journal:
`C:/pt/public-inspection-latency-audit-20261029/runs/run_dev_publicinspectionaudit20261029.jsonl`.
It contains public timing/coverage evidence, not private evaluator material or
model reasoning. No new blanket warning or exploration block was justified.
Batching independent literal alternatives is a candidate for a controlled next
measurement; no total execution-time improvement is claimed here.

## Validation and limits

Focused file transaction and repository/read tests cover bytes, Git membership,
paths/junctions, partial writes, drift, rollback and replay. Gateway integration
covers create/edit/read/search/undo, scope rejection, current-diff checks, original
tests, action accounting, interrupted replay and unconfirmed rollback. A mock
solver submits a patch whose repair depends on its newly created helper; isolated
acceptance passes and mock safety remains NOT_RUN.

Repair verification passed 40 tests; new-module parser and original-test isolation
passed 15 tests. The public finish-choice audit passed seven tests. These are local
mechanism checks, not evidence of live model uptake or improved repair quality.
Initial integration exposed current tool-set/schema snapshots that still assumed
one mutation tool, plus oversized guidance. Current expectations were updated
while historical branches and strict assertions stayed intact; detailed guidance
moved to `.agent/file-transactions.md`. An exploratory full-suite run also found
an older execution-feedback test looking for a summary removed by completion
projection. Its replacement asserts exact native delivery/current references,
durable replay and no source-admission credit; the full owner module passed 75
tests. The exploratory full suite was interrupted; no completed full-suite result
is claimed. Final quick regression is recorded below.

Final frozen-runtime command:

```powershell
.venv/Scripts/python.exe -m pytest '@tests/quick.txt' -n 4 --dist loadfile `
  --max-worker-restart 0 --tb=short `
  --basetemp=C:/pt/tmp/file-lifecycle-final-20261029 `
  --junitxml=C:/pt/validation/file-lifecycle-final-20261029.xml
```

**1,094 passed in 238.12 seconds.** It includes isolated mock evaluation and the
new file/undo/diagnosis/comparison boundaries. Focused owner checks remained below
two minutes per invocation. `ruff check patchloop tests diagnostics` and diff
checks passed. HTML static validation found 51 unique IDs and 56 valid links;
embedded JavaScript passed `node --check`. Browser visual validation was not
performed. Test selection differs from the prior 1,022-test run, so these wall
times are not a runtime performance comparison. Real provider/Docker behavior,
model uptake, independent real-task improvement and end-to-end speed gains remain
unmeasured.

## Decisions and remaining questions

Adopt the file interface as a requested capability, preserving the shared budget
and recovery contract. Do not add more diagnostic gates based on the few observed
finish choices. The separate [finish audit](2026-10-29-finish-choice-local-audit.md)
shows that missing evidence, edit quota and response shortage are distinct.

1. At A's failure-before-finish boundary, can public source support a concrete
   alternative repair and discriminating check? The model's internal cause is
   unknown; available resources alone do not prove a correct patch was reachable.
2. Does the action forecast preserve the final repair route when one optional
   action would spend it? Vary forecast delivery alone, not the edit quota too.
3. On tasks that actually exhaust edits, does 12 improve over 4 under otherwise
   fixed conditions? The inspected quota-limited row needs only 4 to reopen the
   minimum route, so it does not establish a benefit for 12.
4. Can batched independent literal searches reduce provider time while retaining
   useful exploration and repair correctness?

Any paid comparison needs a fresh exact current task/model/credential/repeat/cap
scope, fixed comparison conditions and stop rules. No prior unused budget or
approval carries forward. Actual repair, regressions, isolated acceptance, cost
and time must be evaluated separately from tool availability or submission.
