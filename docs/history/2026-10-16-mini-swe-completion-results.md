# mini-SWE-agent: five missing grades and public metadata correction

Date: 2026-10-16. CLOSED; official=false and claim-ineligible.
All five formerly unsubmitted tasks now have completed native grades:
2 PASS / 3 FAIL / 0 ungraded.
Each final candidate was an ordinary agent submission; no operator-collected patch
was used for a live grade. Completion work cost USD 3.0495918;
cumulative cost including both earlier runs was USD 6.2666922
within the approved USD 24 ceiling. The final coverage includes a separate corrected
attempt for row 18; the first follow-up's ERROR remains unchanged.

## Question and resource change

The [original mini panel](2026-10-16-mini-swe-dev20-results.md) ended at 10 PASS,
5 FAIL and five unsubmitted cases, each reaching 40 calls. The user asked to finish
the ungraded tasks. Their current request and prior USD 24/isolated-container bash
approval covered this completion work. Old containers had been destroyed, so these
were fresh attempts rather than resumed trajectories.

The question was whether a larger allowance would obtain completed, correct patches
or only extend unsuccessful work. The [five-task contract](../../.agent/mini-swe-extended.md)
selected rows 8, 13, 16, 17 and 18, one worker. Limits increased to upstream's
250-step/USD 3 defaults, 1,000 bash actions and 3,600 solver seconds; counted input
was bounded at 250,000 tokens. Output ceiling stayed 25,000. Previous cumulative
spend was USD 3.2171004, so the USD 15 new allocation could not exceed USD 18.2171004
cumulatively. There was no budget transfer or SDK retry.

Agent, model and public task inputs stayed fixed: mini-SWE-agent v2.4.6 at
`a83fcae82d2a08f0ee0c688f9d137b3566c097f8`,
`gpt-5.4-mini-2026-03-17`, xhigh, default service tier/global endpoint, exact primary
repository `.env` credential file. No previous patches, trajectories, diagnoses,
grades or hidden material entered a fresh solver. Same public source archives,
local digest-pinned images and native grader; no image pull/build occurred.

## First follow-up and observed environment defect

All five submitted normally in 275 generations and 427 bash actions. The first
four graded PASS/FAIL/FAIL/FAIL. Row 18 submitted after 98 calls and 138 actions at
USD 1.10633235, but native collection failed before any test case was reported.
The frozen wrapper records native NOT_RUN with ContractError; the underlying native
receipt records complete=false, test_exit=4, zero reported cases and confirmed cleanup.
This is an evaluation ERROR, not a native FAIL. Its raw scope field also remains
NOT_RUN because the wrapper raised after grading; a prediction artifact had already
been created after static policy checks passed.

The failure was reproducible using public source alone. Masking the image's original
checkout removed editable package metadata. Plain `import sqlfluff` succeeded, but
default configuration and plugin entrypoints were unavailable. The agent patched
core-plugin registration to compensate, then duplicated the installed entrypoint in
the native environment. A public 2x2 control found:

| Public source | Original solver metadata | After public `setup.py egg_info` |
| --- | --- | --- |
| Base | Default-config loading fails | Default config and one core plugin load |
| Submitted candidate | Default config loads | Duplicate plugin registration; import fails |

This is an operator environment defect with a candidate import failure, not evidence
that tests should be weakened. The import-only readiness canary was insufficient.
`metadata_setup()` now rebuilds public package metadata before import, including
when import alone would succeed. No tracked source is changed, dependencies are not
installed, and no solving hint is added. Older SQLFluff comparisons retain this
environment limitation; they are not a clean harness-quality estimate.

## Corrective continuation and final coverage

The [correction contract](../../.agent/mini-swe-metadata-recovery.md) reran only the
still-ungraded row 18. It retained the remaining original per-row allocation:
152 of 250 calls, 862 of 1,000 actions and USD 1.89366765 of USD 3, after subtracting
the failed evaluation attempt. Solver allowance was 2,400 seconds with the unchanged
330-second native process allowance and 300-second test timeout. Maximum cumulative
spend was USD 7.72059375. The current completion request and existing budget/bash
authorization were bound to the corrective packet before dispatch; no broader
rerun was launched. All count/transport/billing/cleanup stop rules remained.

Corrected row 18 submitted at 52 calls, received native PASS,
and cost USD 0.4397661. Across both row-18 attempts it used
150 calls and USD 1.54609845, below the
original 250-call/USD 3 allocation. The failed first attempt remains an ERROR.

| Row | Instance | Final native | Calls in final attempt | Bash actions | Final-attempt USD |
| --- | --- | --- | ---: | ---: | ---: |
| 8 | pydicom__pydicom-1413 | PASS | 44 | 63 | 0.37108905 |
| 13 | pylint-dev__astroid-1333 | FAIL | 40 | 51 | 0.3342162 |
| 16 | sqlfluff__sqlfluff-1517 | FAIL | 41 | 88 | 0.466887 |
| 17 | sqlfluff__sqlfluff-1625 | FAIL | 52 | 87 | 0.3313011 |
| 18 | sqlfluff__sqlfluff-1733 | PASS | 52 | 57 | 0.4397661 |

All final patches passed scope checks. Every dispatched generation was settled,
and solver/native cleanup was confirmed. Solver containers were destroyed before
private grading. Registered PatchLoop evaluation and registered safety remain
NOT_RUN; container isolation is separate evidence. Original follow-up wall time was
2110.767s; corrective solve/grading wall time was
416.612s, excluding diagnosis and preparation.

## Historical comparison and decision

| Row | Final mini coverage | Original PatchLoop | Portfolio PatchLoop | Corrected PatchLoop | Separate supplement |
| --- | --- | --- | --- | --- | --- |
| 8 | PASS | FAIL | FAIL | PASS | NOT_INCLUDED |
| 13 | FAIL | FAIL | FAIL | FAIL | NOT_INCLUDED |
| 16 | FAIL | FAIL | FAIL | FAIL | NOT_INCLUDED |
| 17 | FAIL | FAIL | FAIL | FAIL | NOT_INCLUDED |
| 18 | PASS | FAIL | FAIL | NOT_RUN | FAIL |

Historical verdicts remain unchanged, including corrected row 18's original
NOT_RUN and its later separate supplement. No new PatchLoop solve or regrading
was performed. The combined 20-task coverage is
12 PASS /
8 FAIL / 0 ungraded. It mixes budgets,
attempts and the corrected row-18 environment; it is not uniformly measured 20-task
accuracy. Original mini remains 10 PASS / 5 FAIL / 5 NOT_RUN.

The missing grades are resolved and the environment defect is corrected. Preserve
the original evidence, qualify SQLFluff comparisons, and adopt no PatchLoop policy
change from this result. Fresh stochastic attempts and multiple changed conditions
do not identify a causal resource or harness effect. No paid follow-up is queued.

## Validation and immutable evidence

- Extended adapter: 33 focused tests and Ruff PASS; 64 cost/usage regressions PASS.
- Metadata correction: 32 focused tests and Ruff PASS in primary and frozen checkouts.
- Real upstream/SDK mocks exercised isolated bash, settled-limit patch capture,
  cleanup and native grading of deliberately wrong patches. The corrected SQLFluff
  control produced complete expected native FAIL. Actual provider calls/cost: zero.
- Full repository suite NOT_RUN; unrelated concurrent runtime edits were excluded
  by frozen checkouts. An initial Windows temp-directory permission issue was
  resolved with a fresh external pytest base directory.
- Original five-task checkout: `b95aeba5b9bb3f716a284331e0dff90df6107806`;
  packet `sha256:3988013ceaedf7526d7baf224505208dc1e737b6807061405fe3afb82e418eeb`; roots `C:/pt/mini5extprep01`,
  `C:/pt/mini5extlive01`, `C:/pt/mini5extaudit01`.
- Corrected checkout: `26d0353bf8c14c834be41524b24c8f79bd65c32c` at
  `C:/Users/geonj/.codex/worktrees/mini-swe-metadata/PatchLoop`;
  packet `sha256:26e6e19992c75db875fef4b7d14f8ce1a3ed1ee7552d8853ac851902dc9f16bd`; roots `C:/pt/mini5metadataprep01`,
  `C:/pt/mini5metadatalive01`, `C:/pt/mini5metadataaudit01`.
- Core runtime remained `sha256:8d1abdcba22c1f91beb037bd22dc9ed4d209ef173843a74e9b643d9ebd1c12ba`.
- Audits rechecked prior evidence hashes, source/dependency bindings, CAS bytes,
  hash-chained journals, action identities, count/dispatch equivalence, reservations,
  usage charges, patch bytes and native controls. Costs are provider-usage ledger
  amounts, not invoice reconciliation. Public metadata controls never used hidden tests.
