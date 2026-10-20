# Current-question evidence and countercheck priority

Date: 2026-10-17. Baseline: `a0a2cad6fd84afe74f3c3acd4420693f86e9f9f2`.
Runtime content: `sha256:eac04bee22dc7bc571a925364a0f851c5c9101f721243478690bfd322ecdde76`.

## Problem and decision

The [displacement audit](2026-10-17-handoff-counterevidence.md) found that promoting
an old 61-line builder citation at astroid-1333 boundary 476 removed eight lines
distinguishing module lookup, namespace handling and missing-location failure.
37 newly retained neighboring lines had lower direct relevance to the question.
The unchanged file hash did not make the question current after the patch changed.
This matters because losing branch conditions can preserve an overly broad causal
explanation while hiding the evidence needed to qualify it.

Implement the user's requested focus refinement. Keep existing transition rules,
24,000 retained source characters, two references, 500 question characters,
60,000 counted input tokens, 1,048,576 request bytes, 262,144 bytes per encrypted
item, and existing run/cost limits. No additional model response, review action,
mandatory probe, correctness gate or budget is introduced.

## Implementation and authority

- Each fresh question reference declares `role=primary` or `role=countercheck`,
  at most one of each. The schema and both agent prompts request the smallest
  already-observed unit answering the current question and, where available,
  a competing branch or necessary precondition. A second reference is optional.
- Selection order is mutation anchors/postimages, eligible countercheck, eligible
  primary, then existing ordinary priority/recency. References remain atomic for
  priority admission; an oversized range may still be partially present through
  ordinary selection. Native delivery and overlapping ranges still deduplicate.
- Fresh source evidence requires explicit ranges. A whole read/search/mutation
  result cannot expand all its source into focus. Tool references are bounded
  check/test/probe observations, with their original scope and currency.
- Admission binds `declared_diff_hash` before the tool batch. A changed diff leaves
  the old question and citations visible with `priority_status=needs_refresh` but
  removes their extra source/result priority. An ordinary response can refresh the
  declaration when still relevant. Null updates, source rebinding and generic PASS
  do not refresh it automatically.
- Legacy objects without explicit roles remain `unscoped`; legacy strings retain
  their shape. Neither becomes a fresh declaration by copying old notes. Invalid
  question annotations preserve the previous question, independent valid findings
  still apply, and the main action remains allowed. Explicit clear stays separate
  from null-update preservation. Scope is durable across recovery.
- `eligible` certifies only declaration scope against this diff. Evidence currency,
  actual delivery, model interpretation and behavior coverage remain separate.
  Missing bodies/ranges remain explicit. A refreshed citation to an old failure can
  be prioritized while its execution result remains historical.

Roles, semantic minimality and the relevance of a competing branch remain model
judgments. The implementation does not parse keywords, infer counterevidence from
code, auto-shrink a function or certify an explanation. Same-diff conceptual drift
is not mechanically detected. A broad countercheck can still be a poor declaration;
the unchanged budget and omission reporting expose its cost rather than inventing
a new arbitrary per-reference quota.

## Frozen provider-free comparison

Final evidence root: `C:/pt/analyses/question-evidence-priority-20261017-v3`.
`runs/run_dev_questionpriority.jsonl` records the pre-comparison question, baseline,
fixed declarations, caps, stop conditions, source identity and results. The operator
script is `diagnostics/question_priority_replay.py`; original runs and prior evidence
roots remain unchanged. The runtime is frozen during replay and validation.

The comparison reconstructs all 75 saved `plmini20live02` handoffs using only public
observations preceding each boundary. Original journal chains and artifact hashes
are checked. Source versions, actual composed input inventories, omitted ranges,
mutation protections and absence of cross-segment reasoning are checked locally.
The replay has no task checkout or executor and makes no provider/count/Docker call.
Task outcomes, later actions and evaluator details do not choose references.

There are distinct evidence conditions:

1. **Actual historical questions:** 75/75 retained and delivered source inventories
   match the original inputs exactly. Those historical strings contain no new roles.
2. **Prior implementation's note-derived surrogate as a legacy object:** 75/75 receive
   no extra priority. Against that prior broad-focus replay, 68 lines return and 61
   disappear across two boundaries. This is the cost of declining to invent a new
   focus; it is not a result showing that a model learned to choose better evidence.
3. **Fixed current declarations:** retain the already analyzed builder 122-126
   primary at 303; at 476, declare builder 115-128 primary plus manager 199-211
   countercheck. These pairs were frozen before the new replay, are post-hoc public
   capacity examples, and were never selected by the historical model.
4. **Old question explicitly scoped before the edit:** at 476, builder 110-170 with
   its recorded before-edit diff remains visible but becomes `needs_refresh` despite
   current source bytes. It receives no extra priority and matches original selection.

## Preservation and newly displaced information

| Boundary / declaration | Retained characters | Change vs prior implementation replay | Route-discriminating lines | Mutation-protected lines |
| --- | ---: | --- | ---: | ---: |
| 303, current primary | 23,945 | No source difference | Not the 476 comparison | 0 applicable |
| 476, current primary + countercheck | 23,990 | 53 restored, 48 removed | 8/8 | 14/14 |
| 476, old pre-edit question | 23,997 | 65 restored, 56 removed | 8/8 | 14/14 |

Across the two fixed current declarations, original historical selection changes by
14 added and 16 removed line occurrences. At 303 alone, this is the same five error
lines gained for three copyright lines lost. The 476 paired case gains nine and
loses 13 relative to the original selector, versus the earlier +56/-65 broad focus.

The **48 newly removed lines against the prior implementation** at 476 are:

| Source | Count | Consequence |
| --- | ---: | --- |
| builder 110-114, 129-141, 152-170 | 37 | Prior-method tail, encoding failure handling, string building and post-build metadata; lower direct relevance to this routing question. |
| builder 142-148 | 7 | Useful counterevidence is lost: module-name derivation occurs after opening the file, so it cannot cause an earlier open failure. |
| builder 149-151 | 3 | Successful post-open construction context is lost. |
| import/spec 111 | 1 | An isolated `try:` line is newly absent; do not claim a universally harmless deletion. |

The 53 restored lines are manager 162-208 and 215-218, astroid_manager 1, and spec 35.
They include the critical manager 167, 199-202 and 206-208, but also less relevant
import paths and non-executable lines: restored count is not a utility score.
Manager 167 survives ordinary selection in this snapshot, not an explicit pin.
Manager 219-221 working-directory restoration is still absent. The paired version
loses manager 219-229 and spec 60/111 relative to original historical selection.

Both new focus references are fully delivered. The old note's 110-170 citation is
correctly `incomplete`; retaining its model interpretation does not certify that
all its supporting source remains in the input. `linebook.md` and `results.json`
record all newly removed/restored lines, source hashes, missing ranges and inputs.

The old question's automatic demotion also has a real cost. Without a refreshed
declaration, its 56 formerly added builder lines are no longer prioritized,
including useful error provenance and causal-order code. They remain eligible for
ordinary source selection, but continued delivery is not guaranteed. This avoids
giving an old interpretation permanent authority; it does not solve model non-use.

The paired input grows from 79,015 to 79,780 serialized input bytes (+765), including
the updated prompt, roles, scope and projection metadata. The 303 input grows from
67,378 to 67,579 bytes with identical source selection. These are input-only byte
counts, not full request/token admission. Existing hard caps are unchanged; exact
remote token counts and live request admission are `NOT_RUN`.

## Validation and remaining limits

An initial candidate exceeded the existing prompt/schema description bounds. The
first full-suite attempt was interrupted after a visible failure; focused contract
checks reproduced the size regression and stale schema fingerprints. The bounds
were not relaxed: redundant memory guidance was compressed to 8,000 total prompt
characters (limit 8,007), 2,344 memory-block characters (limit 2,400), and 3,988
memory-schema bytes (limit 4,000). Intentional role-field fingerprints were updated;
the surrounding action guidance, run schema and resource limits remain pinned.
The v1 evidence root preserves all initial attempts. Replaying the frozen declarations
on the corrected runtime produced identical source inventories and smaller inputs.

The v2 candidate passed 61 admission/lifecycle/selection tests in 40.497s and 38
handoff/fallback/recovery/projection tests in 121.508s while other tests ran
concurrently (1.508s over the two-minute focused-group target). The contract group
passed 92 cases; its remaining old prompt fingerprint was corrected and passed
its focused rerun. The v2 full suite then stopped at 725 passed / 1 failed: an
unscoped/absent question caused a redundant diff observation during context building.
The final runtime skips that unnecessary observation. The existing one-diff-read
assertion remains unchanged, and the legacy-question test also forbids a diff read.
Its ten-case focused reproduction passed. The v2 evidence remains intact.

The final v3 replay uses the same fixed declarations and produces identical source
inventories, displacement and input bytes. Final focused groups passed 62 tests in
53.977s and 38 tests in 106.812s, both under two minutes. Ruff and five documentation
checks passed. The segmented mock (`run_dev_2dab78f6bc6640e0`) reached `EVALUATOR_PASS`
with four mock turns, five tools, one edit, two prepared/committed segments, zero
input-count calls and zero cost. Its external state root is
`C:/pt/analyses/question-evidence-priority-20261017-mock-v3`; safety remains `NOT_RUN`.
The final four-worker full suite passed **5,186 tests**, with **19 skipped**, zero
failures and zero errors in 3,796.73s. Skips were 12 real-execution opt-ins, two
host symlink limitations, four inapplicable brief-plan replacement cases, and one
missing SDK compatibility dependency descriptor. Fake provider tests block real
network dispatch; real-Docker tests remain opt-in. XML/log receipts are preserved
under the final evidence root. The command used was:

```powershell
.venv/Scripts/python.exe -m pytest tests -n 4 --dist loadfile --max-worker-restart 0 --maxfail=1 --durations=20 --basetemp C:/pt/tmp/qprio-all03 --junitxml C:/pt/analyses/question-evidence-priority-20261017-v3/full-suite.xml --tb=short
```

The final integrity pass checked 248 original input files and 153 composed replay
inputs. The transition module is byte-equivalent after newline normalization to
the baseline; source/reference/question/request limits are unchanged. Metadata and
prompt changes can affect future counted input size; fixed replay boundaries do
not establish identical future model trajectories or token-trigger times.

This implements and tests role ordering, diff scope, recovery and honest omission
reporting. The saved cases show that the selected branch evidence can coexist with
mutation protection at 24k. They do not show autonomous minimal-reference selection,
fewer rereads, better repairs or generalization. All historical models were
`NOT_EXPOSED` to this contract. No paid run or follow-up is scheduled.
