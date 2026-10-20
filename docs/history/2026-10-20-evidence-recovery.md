# Recover source at search hits and separate reproduction scope

2026-10-20. Implementation/local validation follow-up to the closed
[search non-use diagnosis](2026-10-20-history-search-nonuse.md).
Base commit: `bbdb2f4b7a20183aa2a974ed6a91e5687a87bdf5`.
All work is provider-free; historical artifacts and verdicts are unchanged.

## Problem and chosen intervention

B5 selected another definition search after losing an already delivered body.
B6 drew an original-task conclusion from a narrower probe. All six ON runs lacked
an observed original Pylint route; search cannot recover evidence never acquired.
These failures matter because making a tool available did not make it get used,
and a successful helper process did not establish repair of the reported behavior.

The user authorized three changes: recover prior source through ordinary tools,
separate helper and original-caller evidence, and freeze the purpose/program/
expectation of a before/after reproduction. This changes information delivery and
comparison bookkeeping, not the segment policy or an automatic correctness oracle.
The [runtime contract](../../.agent/evidence-recovery.md) describes the boundaries.

1. With `public-v1`, a current literal source search can restore a same-version,
   overlapping read previously dispatched to this run. It keeps the full read and
   original hit edges within the existing 24k search cap. Already visible source
   is not repeated; old hashes and overflow produce explicit recovery pointers.
2. Ordinary probes remain helper/unbound diagnostics. Declared reproductions bind
   a public issue quote, Python entrypoint, input/setup description and expected
   JSON before execution. Bounded actual-call feedback distinguishes an unobserved
   target/setup failure from an observed output comparison.
3. Existing action-ID replay preserves that declaration and exact authored program.
   Current-state and submission receipts keep helper counts, original baselines and
   same-reproduction results separate. Changed expectations/programs cannot close
   the original case. A later edit invalidates current-diff comparison.

Alternative explanations remain: the agent might deliberately choose a different
implementation strategy, fail to acquire the caller environment, or misjudge fully
visible evidence. Therefore restoring source is not sufficient evidence of better
repair. The purpose-to-caller mapping also remains model-authored; a JSON mismatch
is not proof that the reported failure was reproduced. No hard submission gate,
automatic probe, new question reference or budget expansion was introduced.

## Saved-log replay

Evidence root: `C:/pt/evidence-recovery27/`; `replay.py`, the final
`final-replay/replay-results.json` and hash-chained `run_dev_evidence_recovery27`
journals. Socket connections are blocked.
Each actual search result was evaluated independently against only the preceding
dispatched inputs from the six immutable `C:/pt/historyperf25/audit-public/B-rN-t13.json`
exports. This is not a simulated new agent trajectory.

| Saved row | Search results | Expanded results | Added source lines, summed per result |
| --- | ---: | ---: | ---: |
| B1 | 14 | 0 | 0 |
| B2 | 17 | 0 | 0 |
| B3 | 8 | 0 | 0 |
| B4 | 20 | 2 | 465 |
| B5 | 23 | 8 | 1,147 |
| B6 | 8 | 0 | 0 |

All 90 replayed results preserve every original source line and hit; no source
line is displaced within these tool results. Every expanded response stays within
24,000 source characters. Counts are repeated-result totals, not unique evidence.

At B5 request 468 / result 474, `def file_build` grows from 113-117 to 113-160:
43 additional lines / 1,791 source characters. It recovers the exact earlier
115-160 read, including `open_source_file(path)`, and retains 113-114. No special
Astroid identifier appears in the runtime selection rule.

Old probe results carry no frozen reproduction binding, so the derived view does
not retroactively certify them as original-caller repair evidence. Original logs
are read-only and byte hashes are rechecked. No new solve, probe, evaluation or
provider call was made by this replay. Next-request admission, later context
displacement, model use and actual repair benefit remain unmeasured.

## Local validation and decision

Validation receipts are recorded under the same external root. The final focused
12 tests passed in 118.22 seconds (`final-focused.xml`). They cover source
loss/visibility/restart/old hashes/overflow, fixed JSON and call
identity across edit/replay, missing targets/setup failures, changed predicates,
current-diff invalidation, handoff projection and separation of authored intent.
The frozen quick selection plus changed-owner tests passed **220/220** in 319.44
seconds (`frozen-tests.xml`, four workers, no worker restart). This includes the
12 new tests and a segmented reproduction/replay/submit run through isolated mock
evaluation: task acceptance PASS, Docker safety NOT_RUN, claim-ineligible. Ruff
passed; `final-source.json` binds the unchanged runtime and test sources. The full
repository suite and real Docker were not run.

Development failures remain in separate receipts. An OFF-policy instruction
disclosed the disabled tool name; its contract was corrected and rechecked. A mock
evaluation ERROR during overlapping edits/tests was diagnosed by the read-only
manifest validator as `runtime_content_hash` mismatch (`validation-drift.json`).
The final 220-test run held runtime/test bytes fixed throughout; no timeout,
identity check or assertion was weakened. Current schema/prompt fingerprints were
updated intentionally, while frozen historical arm expectations were retained.
`final-validation.json` binds the completed checks and immutable replay to the
resulting implementation commit.

Keep history opt-in and preserve transition rules, two references and all limits.
The mechanism is implemented; whether it improves caller selection, evidence use
or acceptance needs a separately approved controlled run. Existing paid approvals
remain closed, and the previous full-suite timing failures are not reclassified.
