# Verification state separated from model discussion

Status: implemented; local validation and saved public request projection only.
No live provider or native evaluator invocation, paid rerun or repair-success claim.

## Problem and decision

The [scope audit](2026-10-20-verification-scope-context-audit.md) found that the full
public task and scope warning survived all 358 requests in the closed Astroid A/B.
B2 retained the original failure output, yet the model dismissed its concern while
writing that the failure remained. B5 submitted after helper/suite checks without
an original-caller reproduction. None of the B probes declared a fixed reproduction.
This matters because closing a discussion item must not resemble verified task
coverage. It does not establish that lost context caused the failed repairs.

The accepted intervention reuses the public journal and reproduction bindings.
It does not add a requirements database, an extra model reviewer or a submission
gate. The public requirement-to-experiment mapping still needs semantic judgment;
mechanical comparison cannot certify it. A better mapping mechanism remains a
separate question if the model continues to choose unrelated checks.

## Change

- Every current context carries `reproduction_review.required`, anchored to
  `public_task.issue` and the public task hash, with an explicit unverified state.
- Bound cases compute `UNKNOWN`, `SUPPORTED`, `REFUTED` or `CONFLICT` from actual
  current-diff observations under the fixed program/predicate and observed setup.
  Success after failure on the same snapshot remains a conflict. Changed inputs,
  unrelated PASS or model dismissal cannot erase a counterexample. Old snapshots
  remain history; a new snapshot can supply new comparable evidence.
- The three-case view prioritizes conflict/refutation and counts all omitted case
  states. Two witness IDs retain both sides of a conflict. The latest three other
  executions distinguish unbound probes, registered checks and selected tests.
- Model-facing concerns use `model_position` and `model_open_concern_ids`.
  Plans and concern decisions cannot update computed case evidence or task scope.
  The durable concern schema and action recovery identities remain unchanged.

`SUPPORTED` means the declared experiment matches its fixed expectation. It never
means that the full public task is repaired. The in-process call observer still
does not attest receiver state or all external/environment conditions. The
`unverified_scope` fields make these limits explicit.

The transition policy, two question references, source/input/action/time/spending
caps, probe schemas and submission eligibility remain unchanged. The current
prompt explains the new fields; frozen historical arms are not rewritten.

## Local evidence

Packet: `C:/pt/verification-state39/`; new append-only journal
`runs/run_dev_verificationstate39.jsonl`. Runtime and input hashes are recorded.

Five new tests cover unbound zero-exit/suite success, same-snapshot conflict,
changed setup, model dismissal across a segmented handoff, and bounded-case
counterevidence priority. Existing executing-probe coverage checks mismatch,
fixed replay after edit, stale evidence and isolated mock evaluation.

Validation:

| Execution | Result |
| --- | --- |
| Final quick selection plus focused scope/model-view/mock checks | 147 passed in 60.39s |
| Full regression, four workers | 5,379 passed, 82 failed, 20 skipped in 1,367.55s |
| The 82 failures on clean pre-change `5f2da9aecd9bcd988ad309832784ac144890b464` | 80 failed, 2 passed in 32.62s |
| The same 82 after the final corrections | 80 failed, 2 passed in 33.74s |
| Ruff: runtime, tests and diagnostics | Passed |

The two newly failing tests expected the old concern field name and omitted the
now-always-present review from their explicit context inventory. Their expectations
were updated, preserving frozen-arm assertions and checking the new unknown scope.
Both pass after correction. The same 80 node IDs fail on the baseline and final
retest: this is **not a clean full-suite PASS**. These include stale schema snapshots,
diagnostic probe overrides missing `reproduction_binding`, and an existing full-prompt
8,000-character assertion. That assertion already failed at 8,555 characters before
this change; the final default prompt is 8,553. The memory section remains within
its 2,400-character limit. No bound or timeout was raised to clear a test.
Those inherited failures were not broadly repaired in this scope.

The full run preceded the final prompt shortening and two expectation corrections.
The final 147-test selection and 82-failure retest cover those changes; the full
suite was not run a second time. Isolated mock evaluation reaches `EVALUATOR_PASS`,
with no added completion gate or calls.

An initial model-view inventory failure also preceded the change: the inventory
omitted the already existing `reproduction_review` when probes were enabled.
A second stale schema snapshot expected an old hash. Comparing the baseline and
current schema proved them identical (`sha256:16e1c249375e5c3fbf59d71043e0728c274c4359a651e99cf488d038e23adeba`);
only the current test expectation was refreshed. Historical expectations remain.

## Saved public replay

`final-replay/replay.py` reconstructs all 358 saved Astroid request states and ten requests from
the previously accepted dev20 task 1 trajectory. It uses only completed public
actions before each request. Private evaluation results never enter projected
context. Source artifacts were hashed before and after and remained identical.

- All historical probes remain unbound: no retroactive semantic verdict is
  invented from stdout or a zero process exit. All 202 B requests retain an
  explicit `UNKNOWN` requirement state.
- B2's final concern still says `dismissed_by_model`, with no model-open concern
  IDs, but its original requirement remains independently unverified. The
  original failure output and current source/diff stay intact.
- B5's helper and suite results are displayed as performed checks with
  `requirement_coverage=not_assessed`; its existing submission eligibility stays
  true. Improved disclosure is not evidence that the model would change its choice.
- The accepted dev20 trajectory keeps its successful finish receipt and eligibility
  in the projection. This is historical evidence, not a fresh native evaluation.
  The local mock verifies that the new unknown scope does not introduce a blocker.

The replay leaves every existing task/source/diff/recent-probe/check/budget field
unchanged. Current-state serialized UTF-8 size increases by 429–2,765 bytes
(median 905). These are state bytes, not provider-counted input tokens or cost.
It does not rerun selection, count tokens, predict future handoffs or prove that
later live requests would evict no evidence.

Replay artifact SHA256:
`79f04f47c6e2b9cbeecb00f67b2453a0727ba1992e39cfc90179e09ffbff8514`.

## Remaining question

This change makes evidence state independent of a model's discussion decisions.
It cannot force the model to declare a faithful caller experiment or correctly
interpret an unbound output. Keeping every original requirement `UNKNOWN` is not
a repair-performance improvement; it is an honest limit of the current mapping.
Actual use of the state and improved repair success remain live-untested.
