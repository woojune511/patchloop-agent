# Changed test selection visibility and host latency

Date: 2026-10-30. Local implementation and read-only public-workspace comparison.
No live model calls, benchmark-task reruns or new paid allocation in this follow-up.

## Problem and decision

The [integrated three-task run](2026-10-30-integrated-dev3-results.md) exposed two
new test files that agents created but did not execute. pvlib's required check
selected a fixed old file; SQLFluff's new filename did not match pytest discovery.
Existing `run_tests` could select either file, and separate operator checks passed
both after the runs. A new tool would not address this observed failure.

The check summary also failed to interpret the actual registered Python pytest
wrappers, leaving their target arguments unresolved. The working hypothesis was
that clearer selection feedback could help the model notice omissions. Selection
feedback cannot prove test collection, execution coverage, or behavior correctness.

For latency, the public trace showed model dispatch-to-return consumed 62-76% of
task time. Exact repeated searches were only two of 39, both after mutations; this
did not justify a blanket duplicate-search rule. Profiling instead found repeated
Git subprocess launches while validating already observed source: SQLFluff checked
47 files separately. Both known improvements were implemented together, without
requiring another paid one-factor comparison.

## Implementation

- `check_review.py` matches the exact Python invocation prefix and working
  directory of a registered pytest suite, then describes literal pytest targets.
  It does not execute or interpret wrapper programs.
- `current_diff.test_execution_review` describes changed Python files under
  registered test roots, current visible selection receipts and valid `run_tests`
  selectors. Explicit file selection, partial node selection, directory discovery
  and no confirming visible receipt remain separate. Missing bounded history does
  not mean a file was never executed. Existing display bounds are reused.
- This is advisory context. No automatic tests, new execution tool, required-check
  credit, finish gate or added model instruction was introduced.
- `tools.py` reads the current Git index once per source inspection, while still
  checking current file bytes and hashes. The inventory lasts only for that call;
  the next call observes new files and tracking changes. Mutation/recovery keeps
  its individual literal-path validation.
- Repository search iterates tracked paths instead of traversing the whole tree.
  Ordering, output bounds, deadline checks and symlink/junction boundaries remain.

The model-facing surface identity changes with the selection-review contract.
Historical envelopes and runs remain bound to their original identities.

## Local measurement

Baseline: `95ae75eb`, before this follow-up. The three completed public workspaces
were unchanged. Source validation ran three alternating before/after repetitions;
table values are medians. Current file contents, observed spans and configuration
were held fixed, and the complete returned validation results were compared.

| Public task | Files / Git processes before | Git processes after | Before | After | Identical valid spans |
| --- | ---: | ---: | ---: | ---: | ---: |
| pvlib1154 | 2 | 1 | 0.0876 s | 0.0422 s | 6 |
| Astroid1333 | 15 | 1 | 1.0167 s | 0.0565 s | 26 |
| SQLFluff1733 | 47 | 1 | 2.9979 s | 0.0757 s | 116 |

The 36 unique historical repository searches also returned identical complete
outputs. Their aggregate measured time was 8.44 s before and 6.03 s after; each
search used one Git process in both versions. This is one warm before/after pair
per search, with some individual searches slower, not a stable search-speed estimate.
Existing solver journal hashes remained unchanged.

Evidence root: `C:/pt/integrated3-source-latency-20261030-v1`.
`comparison.json` points to immutable source, script and result artifacts. Result
CAS: `sha256:b8a91aa74f87fd17bbb34741ea49f658697512205db77cf87a0eba128cb245af`.
The external `dev-run-v1` journal records comparison completion; an initial harness
setup failure was retained separately. Baseline source SHA256 starts `52b0837f`,
measured current source starts `4adba18f`; subsequent source edits only wrap long
lines for Ruff and do not change behavior.

## Validation and remaining question

- Focused source/search/context regression: 75 passed, one symlink permission skip
  in 27.95 s. Selection-review tests also cover actual public task 3/13/18 wrappers,
  stale/unknown receipts, explicit files versus partial nodes, unknown discovery,
  bounds, no source I/O, completion retention and unchanged submission eligibility.
- `uv run --locked pytest @tests/quick.txt --basetemp C:/pt/tmp/test-vis-speed1030
  --junitxml C:/pt/validation/test-vis-speed1030.xml`: 1,172 passed, one skipped,
  two failed in 675.55 s. Both failures were old exact current-surface hash
  expectations in `test_thin_policy_gateway` and `test_dev_memory_guidance_v34`.
  Only those expectations were updated to the deliberately changed contract;
  historical frozen-arm values stayed intact.
- Focused final rerun: 16 passed in 1.65 s, including both corrected checks,
  the memory-guidance module and documentation layout. Receipt:
  `C:/pt/validation/test-vis-final1030.xml`. The entire quick command was not
  repeated after these test-only corrections and formatting-only line wraps.
- Quick included the actual append/segmented mock runs reaching isolated
  evaluation. No unresolved quick-test failure remains; the broader full test
  suite was not run. Mock safety remains NOT_RUN.
- `uv run --locked ruff check patchloop tests` passed. The measured `tools.py`
  snapshot and final formatted source have identical Python ASTs.
- HTML static QA: 51 unique IDs, all 60 local links/fragments resolve, inline
  JavaScript unchanged. Browser visual QA was not performed in this follow-up.

New surface hash:
`sha256:ba96122e880e6d6962fb5fc9bcba696dbe1c8fabf531c59dd032ebab2a555766`.

The local evidence supports batching Git lookups and preserving public search and
source-validation outputs under these conditions. It does not establish improved
model test choices, repair quality, or end-to-end time. The next integrated run can
check whether created tests are explicitly selected and measure full task latency.
The much larger model-response time remains unchanged; no claim is made that this
host optimization removes that bottleneck. Prior paid allocations remain closed.
