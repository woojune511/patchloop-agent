# Main integration: full regression contract audit

Date: 2026-11-02. Provider-free integration work; official=false.

## Problem and evidence

Integrating the accumulated development branch into main required full regression,
including closed diagnostic controls absent from the quick selection. Integration
commit `9b7bc445` combined development head `f58b505c` with main `f08bbed4`.
Its Ubuntu CI collected 8,139 tests: 7,678 passed, 248 failed, 186 errored and 27
skipped. This was a mixed set of runtime defects and stale fixtures, not evidence
that every failure was introduced by the merge. The initial local full run was
interrupted after the complete Ubuntu result became available; it was not a pass.

The work was selected because context loss, rejected valid edits and broken
recovery affect agent reliability, while stale control fixtures obscure those
defects. The alternative explanation that failures were only snapshot drift was
insufficient: focused executions reproduced missing public evidence, uninitialized
journal readers and a valid edit rejected as an externally changed workspace.

## Causes and changes

- Three immutable diagnostic readers bypassed `DevJournal.__init__`, leaving its
  validated-prefix cache uninitialized. Use the normal constructor with
  `create_dirs=False`; preserve read-only source inspection and byte validation.
- Compact stages dropped registered public diagnostic overlays and current
  mutation/check, test or probe evidence. Preserve those bounded fields, causal
  mutation claims, rejected-edit feedback and harness recheck receipts. Completion
  still omits replacement/postimage bodies and historical bulk output.
- A prepared completion segment added `context_handoff` to the plan on restore,
  changing a frozen first request despite unchanged task evidence. Completion
  already requests no handoff review; its projection now consistently removes
  that bookkeeping-only reason and retains substantive review reasons.
- Copying a Git index without its timestamp broke Git's racy-clean handling of
  same-size edits. Preserve index metadata with `copy2`. A regression restores a
  file's timestamp after a same-size edit and checks exact preview/admission hashes.
- Dependency preparation now validates incompatible options before reading task
  caller requirements. The local reproduction driver uses the offered current
  observation helper and purpose shape.

Fresh tests now reflect annotation-free mutations, `edit_files`, twelve-edit
defaults, actual output-role reservations and mandatory stage boundaries. Tests
whose question requires four edits explicitly request four. Closed experiment
fixtures explicitly isolate their pre-stage prompt when necessary; current stage
and recovery behavior remains exercised separately. Optional archive tests retain
their fallback/uncertainty controls and add a real compact-completion control.
Large history delivery needed no runtime change: observed source preservation now
avoids an old fixture's extra source read. Updated evaluator-byte tests pin the
already accepted assertion-logging revision `b247345d`, preserving exact bytes.

## Local validation and integration decision

Evidence is retained outside the repository at
`C:/pt/main-integration-20261102-v1/`:

- `evidence-transaction.xml`: 164 passed, one host skip for current evidence,
  mutation preview, selected tests, public endpoint and comparison owners.
- `failed-rerun-v3.xml`: 381/434 passed after the first fixes; 53 remaining failures
  were diagnosed rather than accepted. `remaining-v1.xml` then had 112 passed and
  18 failed. The final affected controls and sampler checks in `remaining-v2.xml`
  all passed: 38 tests, including uncertainty, crash and immutable-source checks.
- `quick-final-v1.xml`: 1,619 passed and one host skip; includes isolated mock smoke.
  These are local mechanism tests, not a paid coding-agent comparison.
- `final-focused.xml`: all 110 focused controls passed in 22.7 seconds, covering
  completion projection, immutable journals, file transactions, docs and sharding.
- Ruff, documentation bounds/links and CI partition controls passed separately.

The prior Windows CI reached 90% after about 61 minutes and was cancelled after
its Ubuntu peer had already failed. Its partial log is retained as
`windows-9b7bc445-job.log`; neither platform's old result is final merge acceptance.
Windows CI now divides the actual pytest collection into four jobs by file;
Ubuntu retains a single full job. Module fixtures stay together. The local
partition audit covered all 8,157 collected tests exactly once, with shard counts
2,002 / 2,076 / 2,029 / 2,050. Collection errors or empty shards stop execution.

Full Ubuntu and all four Windows checks on the submitted head remain the merge
gate, tracked in [PR #23](https://github.com/woojune511/patchloop-agent/pull/23).
Use a merge commit to preserve source commits referenced by frozen diagnostics.
No acceptance predicates, historical result bytes or solver private-data boundary
were changed. No new paid run or repair-quality/generalization claim was made.

The decision is to keep these reliability fixes and explicit control contracts.
The unresolved product question remains whether agents use retained evidence to
resolve original-task gaps; passing integration controls cannot establish that.
