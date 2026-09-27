# Matched expectation-review live result

Date: 2026-09-28. `official=false`; one development pair, not fresh solves.
Follows [rehearsal](2026-09-28-expectation-review-rehearsal.md), which links the
frozen checkpoint and earlier expectation-provenance investigation.

## Question and intervention

Does a generic first-turn request to distinguish independent specifications from
self-authored expectations change the next action and repair? Both arms restore
exactly the same completed prefix before the earlier guard-removal decision and
retain completion-advice removal. B alone adds `expectation_review`; no formula,
witness, numeric answer, private test or evaluator detail enters solver context.

The user authorized original-toqito-1538 dev-train, gpt-5.4-2026-03-05, xhigh,
25,000 output tokens, existing PatchLoop/.env, A1 then B1 once each, total fresh cap
$6 and per-arm $3. Historical spend $1.7544445 per fork is provenance only. No unused
historical funds were reopened; no cross-arm transfer, SDK retry or automatic resume.
The inherited active horizon was approximately 918 seconds per arm.

Collector implementation: `1708f77`; [contract](../../.agent/expectation-review-collector.md).
Runtime unchanged: `sha256:850942479181d7ce55199c21f08aa0221edd9bbaaa71098ca13ce6521b51b1de`.
Preparation verified pinned source/dependencies and existing Docker images READY.
No Docker startup, image pull/build, hidden-test inspection, or runtime adoption.

## Executed results

| Evidence | A1 control | B1 review cue |
| --- | --- | --- |
| New counts / dispatches | 4 / 4 | 18 / 16 (15 recorded responses) |
| New probes / accepted edits | 1 / 1 | 4 / 2 |
| Final public regression | 14 passed | 14 passed |
| Submitted / benchmark | Yes / FAIL | No / NOT_RUN |
| Safety evaluation | PASS | NOT_RUN |
| Recorded fresh cost | $0.578648 | $2.3480835 plus one unknown call |
| Operator feasible-bound check | FAIL | PASS |
| Operator same-input ordering | FAIL | PASS |

A kept the disputed CQ expectation, removed the downarrow guard, and submitted.
Its additional probe stopped on `check_setup` cq_trace mismatch after product,
Bell and alpha=1 observations; it did not complete the CQ assertion. The final
patch is byte-identical to the earlier advice-removal patch, and still fails both
public counterexamples. Passing the regression did not resolve that semantic defect.

B's first action was independent optimization rather than the guard-removal edit.
The first probe exposed a complex-to-float trace error in candidate density decoding;
the second stopped on strict setup mismatch. The third produced independent Powell
and grid values exceeding both the CQ helper and current API on the same input:
helper 0.408154634, API 0.424961780, Powell 0.490645387, grid 0.453812508.
It explicitly revised its assumption. Source inspection briefly narrowed the repair
to the decoder crash, but a fourth post-check probe rediscovered the semantic gap.
After more searches, B removed the CQ shortcut and reran the public regression.
These decisions are public action explanations, not private reasoning transcripts.

The final B model call began at active elapsed 1,795,501 ms of 1,800,000 ms: only
4,499 ms remained. It ended with APITimeoutError, response_not_recorded and billing
UNKNOWN. Finish was available but no finish decision was received; this is not proof
that the model selected submission. The near-deadline dispatch is observed; a specific
provider-side cause is not established. No new paid work followed uncertainty.
Total recorded fresh usage is $2.9267315; final total and exact unused amount are
unknown. The invocation is closed, including unused authorization.

## Delivery and separate public validation

All 20 dispatched public-state bindings verified; each inherited prefix is exact.
Both first requests match the funded manifest. Removing B's one review field makes
its first request exactly equal A's. The field is absent from later current states;
history/notes can retain it naturally. Both arms keep recommendation removal.

Frozen final patches were copied into separate pinned-source workspaces and tested
without feeding results back to either agent. On the existing feasible witness, A
returns 0.584962501 below the feasible 0.771552706; B returns 0.771553303. On the
existing same-input ordering example A's up-minus-down is -0.007208809; B's is
+0.173913207. These two public checks establish local improvement, not full task
correctness or a benchmark pass. Private evaluator internals were not read.

The first operator-check batch mistakenly reused container execution identities
across arms, causing conflicts/kills. Its v1 records are retained as infrastructure
failures, not mathematical outcomes. v2 used distinct run identities and completed
sequentially. No experimental model was rerun to recover this operator error.

## Evidence and validation

- Frozen input: `C:/pt/analyses/expectation-review-checkpoint-20260928-v1/packet.json`.
- Funded manifest: `C:/pt/analyses/review-live-plan-20260928-v1/manifest.json`;
  hash `sha256:ea4c592ec725a4b1e9d44e57fcf30af180896fbbb86a10aa4f7c2ab1c8d70fb6`.
- Live receipt: `C:/pt/reviewlive0928a/result.json`; group journal
  `run_dev_reviewcomparison`; A1/B1 fork journals `run_dev_33068b6e257f423a`.
- Delivery, public decisions, patch hashes: `C:/pt/analyses/review-results-20260928-v1/audit.json`.
- Closure, timing, bound public checks: same directory `closure.json`, journal
  `run_dev_reviewresultaudit`.
- Public checks: `C:/pt/analyses/review-public-checks-20260928-v2-A1/results.json`
  and sibling `review-public-checks-20260928-v2-B1/results.json`.
- A patch: `sha256:878cb57a001bc0aacd1847a0ad55aaf09fe0c5baf56d1e39bf73ea9f35d68250`.
- B patch: `sha256:003d549bab52d602d4efb2c0c80b7002c4ab587da5c3fb086ea1a2977351bb50`.

Synthetic collector cases passed for paired delivery, historical/new cost separation,
cap mismatch, single-use and count/transport/usage uncertainty stopping B. A test
initially expected FileExistsError, but the existing disjoint-root ContractError
correctly rejected reuse; its expectation was corrected. Review continuation and
shared post-edit regressions passed (16 tests), collector cases passed (4 tests),
and documentation checks passed (5 tests). Ruff passed. Ordinary mock
`run_dev_b18c20d913284f29` reached isolated EVALUATOR_PASS, safety NOT_RUN, zero cost
at `C:/pt/runs/review-live-mock-20260928-v1`. Full repository suite was not run.

## Interpretation and next question

The cue was followed by independent expectation testing and a locally better patch,
but the pair does not establish improved benchmark success: B never submitted.
Do not tune from hidden failures or adopt the cue by default from one pair.
The next provider-free diagnostic is the path from first decisive counterexample to
final repair: redundant source searches, failed probe setup, temporary loss of the
unresolved contradiction, and remaining-time dispatch admission. Separate semantic
repair progress from completing submission with known billing. No further paid
retry, resume or budget extension is authorized by this closed invocation.
