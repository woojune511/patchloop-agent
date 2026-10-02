# Selected public tests: implementation and regression control

Date: 2026-10-03. Starting HEAD: `37e6355a`. Provider-free implementation following
the [SQLFluff 1625 scope diagnosis](2026-10-03-sqlfluff-1625-evaluation-scope.md).
Original [A/B scores](2026-10-03-positive-verification-results.md), submitted
patches and closed records retain their original meaning and bytes.

## Problem, question and decision

The saved A1 repair breaks an existing public CLI regression. The registered
required check runs only `test/rules`; the existing public probe snapshot contains
`src`, so the agent could not select the repository's CLI test through that tool.
This concrete omission matters because passing the public examples and required
rules check did not detect the lost warning in an existing caller.

The selected intervention supplies bounded execution of existing public tests.
It does not add another prompt strategy or a new completion gate. The leading
explanation is a missing execution capability; a selectable existing test should
distinguish A1 from preserved public behavior. If the selected test also failed on
the base or B1, or could not execute in the registered environment, this control
would not establish that capability. Autonomous test selection is a separate
unresolved question, not a result of this operator-directed control.

The public target and expected control outcomes were frozen in the replay journal
before dispatch: base PASS, A1 FAIL, B1 PASS. Task selection follows the demonstrated
public CLI regression. No model, credential or provider budget was used. Each
control received a 120-second deadline, the same existing pinned image and public
command prefix; execution uncertainty or a mismatched expected outcome stops the
driver. Workspaces retain their saved patch hashes.

## Change

- Optional `PublicTask.test_suites` registers trusted pytest command prefixes,
  environments, working directories, limits and public roots. Empty registrations
  retain prior serialization. SQLFluff 1625 reuses its existing public wrapper and
  environment, registering the generic `test` root without a suggested node.
- `run_tests` accepts only a registered suite and 1–8 tracked public Python files
  or node IDs. Selection rejects path escapes, hidden paths, untracked files,
  directories, symlinks/reparse points and command injection through flags.
- The existing public-check sandbox executes the derived argv. Optional execution
  retains the protected completion budget and action/input recovery identity.
  Selected results cannot satisfy or erase required-check credit.
- Results retain suite/targets, exit and execution flags, bounded public output
  and diff currency through native/segmented context. Completed results replay
  without execution; pending actions require the same admitted diff. Existing
  runtime/task resume identity remains enforced.

See the [current contract](../../.agent/selected-tests.md). No private specs,
hidden tests, reference patches, evaluator code or historical artifacts changed.

## Executed control

The new gateway and existing Docker backend ran the original public node
`test/cli/commands_test.py::test__cli__command_directed`:

| Saved workspace | Selected test | Exit | Required-check credit |
| --- | --- | --- | --- |
| Base | PASS | 0 | None |
| 1625A1 | FAIL | 1 | None |
| 1625B1 | PASS | 0 | None |

All three executions completed without timeout, deadline/cleanup failure or
output truncation. Replaying each identical request returned the durable result
without another execution or journal write. Patch hashes remained unchanged.
These fresh diagnostic gateways did not run required checks or hidden evaluation.

The tool now exposes the demonstrated public regression when that test is selected.
It does not expose an extra private diagnostic-wording requirement, change original
acceptance grades, or show that an agent discovers the test and fixes its failure.
The baseline guidance remains selected; no paid comparison is queued.

## Validation and evidence

Focused tests cover admission, real pytest file/node execution and missing nodes,
execution error categories, resource reservation, diff currency and durable/pending
recovery. Scripted append-v1 and segmented-v1 mock runs deliver selected results
to the next model input, finish through isolated evaluation with EVALUATOR_PASS,
and resume the closed run without another action; their safety state is NOT_RUN.

- Focused feature suite: 37 passed, one skipped, 30.246 seconds. The skip is real
  symlink creation unavailable on this Windows host.
- Ruff and five documentation layout/link tests passed. Eight refreshed contract
  identity checks passed; existing schemas without a suite remain unchanged.
- Ordinary mock CLI smoke: EVALUATOR_PASS, safety NOT_RUN, four mock model calls,
  five tool actions, one accepted mutation, zero provider cost. Run
  `run_dev_7eff6e91cac64668` under `C:/pt/selected-tests-smoke-20261003`.
- Full suite: 4,008 passed, 43 failed, 17 skipped in 1,289.17 seconds. Of the
  failures, 35 used two lightweight task fixtures missing the new optional field,
  seven had already-loaded old identity expectations, and one hit a 265-character
  Windows CAS temporary path. The two fixtures now declare an empty suite list;
  refreshed hashes preserve the independent legacy schema assertions. Runtime
  source was unchanged during this validation follow-up.
- All 43 failed cases passed on targeted rerun in 42.57 seconds, using the short
  external basetemp `C:/pt/st43a` (the failing path becomes 236 characters).
  Combined coverage is 4,051 passing cases and 17 skips. This is the initial full
  run plus a failure-only rerun, not a second complete green suite invocation.

Focused XML: `C:/pt/validation/selected-tests-focus-20261003-c.xml`;
identity XML: `C:/pt/validation/selected-tests-identities-20261003-b.xml`.
Full XML: `C:/pt/validation/selected-tests-full-20261003-a.xml`; rerun XML:
`C:/pt/validation/selected-tests-full-retry-20261003-a.xml`. Both reports are retained.

- Evidence root: `C:/pt/analyses/selected-tests-replay-20261003-v1`.
- Result SHA-256: `b74edc241797415014c476fdce44cf2aa019833452cb723c4740544fe3c72514`.
- Executed runtime: `sha256:c5db9ef2e78b2f56944bbc8910d57c978346111fbba6cf03c409c61177917792`.
- Replay driver: `diagnostics/selected_tests_replay.py`; exact executed bytes are
  preserved as `executed-driver.py` and in the separate source journal/CAS before
  a formatting-only cleanup of the checked-in driver.
- Preparation/completion journal: `run_dev_selectedtestsreplay`; child action
  journals and CAS receipts are retained below the evidence root.
- Receipt SHA-256: base `c99b7c91c487cea277c8cac64708b68088ad57050083951b108a61bf1d076fc4`,
  A1 `635c24050766374c5a6e1e4a28961780ed4349b066bd58acc4b03c5cb077f5d5`,
  B1 `da4898a1ff035588379b633226dbe8c3dab5906ea917d59a69a4374cf57cf79b`.

Provider calls: 0. Image pulls/builds: 0. New hidden evaluations in the saved-patch
control: 0. Autonomous model selection/repair and causal quality comparison:
NOT_RUN. All execution is official=false and claim-ineligible.

The next question is whether a coding agent uses existing public regression tests
appropriately within its repair budget. This implementation establishes tool
availability and a reproducible detection control, not an answer to that question.
