# Selectable observed-source retention

Date: 2026-10-06. Provider-free implementation and comparison preparation.
Base commit: e55393eda23c7a2f0ed6ef24fffb37231b0c28e7.

## Problem and change

The [preceding audit](2026-10-06-resource-budget-context-review.md) reproduced
source loss before a wrong SQLFluff-1733 edit. A 48k-character retained pool kept
the relevant arithmetic where 24k/32k did not. The user requested the next proposed
step: implement a selectable 48k pool, regression tests, and comparison conditions.

`patchloop dev --retained-source-chars 48000` now selects the larger pool;
omission or explicit 24000 preserves the default. The same typed setting is
available in development and public repair requests. Other values are rejected
before execution. The value binds model identity, run envelope and run-start
metadata; a resumed run cannot change it. Default serialization omits the new
field so older envelope records remain readable. Ordinary resume still requires
the exact runtime and all other envelope identities; this is not an old-run migration.

The gateway uses the selected cap for both retained-source projection entry points,
and model-visible metadata reports the actual value. Selection priorities, native
latest outputs, complete-line/gap/stale-source rules and mutation evidence stay
unchanged. The per-read 24k output and 400-line limits, 60k counted-token admission,
request/encrypted-item byte limits, prompts and tool reservations are unchanged.

## Comparison preparation and interpretation

The [comparison design](../../.agent/source-retention-comparison.md) defines fresh
24k/48k arms on the same current implementation. SQLFluff-1733 is the observed
failure; pvlib-1072 is an existing-success regression control. Two repetitions
per task/arm yield eight proposed rows, four waves of two different tasks, mini
xhigh, USD 1.20/row and USD 9.60 total. These are proposed limits, not spending
authority. The general full-model baseline is unchanged.

External `comparison-proposal-v2.json` binds validated requests and the current task,
source and dependency descriptors. It contains no secret values or execution
authorization. A real execution packet still needs the final code/driver identity,
environment checks, calibrated public examples and exact human paid-scope approval.
No provider/token-count, real Docker, image acquisition, native grading or live
repair comparison ran in this preparation.

The proposal's canonical hash is
`sha256:6dc5dcb5af814c485916a2631165333e1cc122516c1428b6259a8a7fc548fe6a`;
its file hash is
`sha256:722e6623a33ba395da3532f9b68a9ff45d7078e76ad8c2b541891c3dd101eae4`.
Readback verified that paired requests differ only in retention and isolated state
paths. Both task source checkouts and dependency descriptors match their selected
identities. The first preparation operator used a nonexistent deadline factory and
stopped before those checks; it and its failure receipt remain preserved. Version 2
uses the existing `ExecutionDeadline.from_remaining` API and completed preparation.
The final proposal was rebound after the default contract-identity correction below;
the preceding proposal, operator versions and receipts remain immutable.

The question advances from source availability to actual patch acceptance. More
source may help a correct hypothesis, be ignored, leave verification omitted, or
consume resources sooner. A positive pilot requires better accepted repairs without
a per-task regression and evidence of the mechanism; ties or unexercised changes
preserve default 24k. The earlier arithmetic reappeared before submission, so this
change does not claim to fix untested submission by itself.

## Validation

Evidence root: `C:/pt/analyses/source-retention-option-20261006-v1`.
Validation commands, logs and receipts use append-only hash-chained dev-run-v1
journals outside the repository. Focused new-option/source tests passed 38 cases
in 20.18s. They cover supported/default/invalid requests, source retention across
fresh segments, observed gaps, stale source, unchanged read bounds, immutable
resume settings, crash recovery and fresh-state token/byte admission failure.

Ruff and the five documentation checks passed. The explicit 48k CLI mock smoke
reached isolated EVALUATOR_PASS in 17.660s, with zero billed cost and safety NOT_RUN.
Readback confirmed the 48k setting in its envelope and all four actual model input
contexts. Its two segments used the unchanged result-driven handoff. These are
local contract checks, not evidence of model quality or real Docker safety.

The full four-worker suite completed in 3,389.68s: 4,334 passed, six failed and
19 skipped. All six failures asserted unchanged default tool/planning identities.
The initial implementation had unnecessarily replaced a global projection-contract
label, changing those default identities. Restoring the original default label
fixed the failures; the opt-in cap remains bound separately in model identity and
the run envelope. No prompt or schema snapshot assertion was weakened.

The six failures plus the 38 source/option cases then passed together: 44 passed
in 20.77s. Combined coverage is 4,340 passed and 19 skipped, with no unresolved
test failures. This combines the original full run with targeted final reruns; the
original full-run failure record is preserved. Only the default identity label
changed in runtime source after that full run. Final Ruff and documentation checks
passed. The final 48k CLI mock also reached EVALUATOR_PASS in 9.463s after the identity
correction; envelope and all four contexts retained 48k, safety stayed NOT_RUN.
Linux CI,
real Docker safety, model/token-count calls and a repair-quality comparison remain
NOT_RUN. The 24k default and all historical experiment bytes are preserved.

`closeout.json` verifies all six repaired test nodes, the exact one-label runtime
delta after the full run, 14 journal chains, the current proposal/runtime binding
and the preserved user AGENTS.md bytes. Its file hash is
`sha256:9c7a50979fa744ed7ca90a4bbca6421905c79dcddb6e99f929e0245feb6fb343`.
