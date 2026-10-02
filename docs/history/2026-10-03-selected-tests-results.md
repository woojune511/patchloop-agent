# Seeded public-test selection: fresh allocation results

Date: 2026-10-03. official=false, claim-ineligible. Allocation closed.
Follows the [preparation](2026-10-03-selected-tests-diagnostic-preparation.md),
[earlier provider stop](2026-10-03-selected-tests-diagnostic-result.md), and
[provider diagnosis](2026-10-03-provider-rate-limit-diagnosis.md).

## Question and controlled conditions

Saved A1 passes the two public TSQL examples but regresses an existing public CLI
case. The optional `run_tests` tool can expose that case in operator replay. The
question was whether the agent independently selects a discriminating public check,
repairs the failure and rechecks it. B1 controls preservation of those three checked
cases; it is not a correct reference solution or a fresh-solve baseline.

After reporting that the API limit was resolved, the user separately approved A1
and B1 once each under the same model, inputs and limits: GPT-5.4 snapshot
`gpt-5.4-2026-03-05`, xhigh, desired output ceiling 25,000, USD 3 per row / USD 6
invocation, 40 model calls / 100 actions / 1,800 seconds per row and three new edits
after installing one seed. Credential path and zero-retry/stop-all conditions stayed
fixed. Old allocation v2 remains closed with billing UNKNOWN; this allocation does
not resume or reconcile that call.

Execution commit: `5d5d1f8bbda2e9bc0a774df01e516bec314ad25c`.
Runtime: `sha256:c5db9ef2e78b2f56944bbc8910d57c978346111fbba6cf03c409c61177917792`.
Packet: `sha256:bd036c8bbe20a8311a63f6519f851af45039c96b66f20f330ce05cb4aad8fc8f`.
Root: `C:/pt/analyses/selected-tests-diagnostic-20261003-v3`.
Fresh solver state: `C:/pt/stlive02`; calibration checkouts: `C:/pt/stcal03`.
Only external paths and approval documentation changed; agent runtime, task, seed
patches, model instructions and resource policies were unchanged.

Before dispatch, fresh public calibration again gave base CLI PASS / examples FAIL,
A1 CLI FAIL / examples PASS, and B1 CLI PASS / examples PASS. The committed frozen
design is in `.agent/selected-tests-diagnostic.md` at the execution commit.

## Results

| Row | Required rules check | Final public CLI | Both public examples | Original acceptance | Safety | New edits | Recorded USD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | PASS | FAIL | PASS | FAIL | PASS | 0 | 0.074674 |
| B1 | PASS | PASS | PASS | FAIL | PASS | 0 | 0.051724 |

- A1: `run_dev_1ca5f67fb6d64ac3`, run elapsed 114.544s; operator checks 22.613s.
- B1: `run_dev_622172d918774642`, run elapsed 114.592s; operator checks 22.324s.
- Each used two model calls, two input counts and two tool actions:
  `run_check(base-regression)` then `finish_task`. No source inspection, optional
  selected test, probe or new edit occurred. Submitted patch hashes exactly match
  their original saved seeds. Run elapsed includes isolated evaluation.
- Current recorded total: **USD 0.126398**, settled from four usage receipts.
  No unresolved count/dispatch remains in either new run. Previous v2 billing stays
  unknown and is excluded from this settled total. No retry or additional run occurred.

A1 did not meet the frozen discovery/repair/recheck criterion: its known public CLI
regression was never exposed to the agent and remains in the submitted patch. B1
preserved the checked public behavior without changes. Neither result establishes
full correctness, and both original private acceptance verdicts remain FAIL.

## Mechanism evidence and limits

Actual model inputs and per-turn tool lists show `run_tests` was available on both
turns of both runs. The first input contained the public task/suite and current
seed diff, with no operator CLI target, review, old source snapshot, action history
or evaluation verdict. Three mutation slots remained after seed installation.
At submission decision time each still had 39 model calls, 99 actions, all three
new edits, over USD 2.96 and over 1,750 seconds available. Resource exhaustion did
not force the observed stopping choice.

Both agents' recorded public plans chose required-check PASS as the next stopping
condition. A1 explicitly noted that the rules result did not directly establish
the reported TSQL case, yet treated the absence of a remaining required check as
sufficient to submit. B1 retained its assumption about the no-join guard while also
submitting. These are public tool-decision fields, not private reasoning traces.

The delivered completion message explicitly said submission eligibility was not
proof of untested behavior, but its suggested next action was `finish_task`, with
an optional probe only for a concrete remaining uncertainty. Readiness framing is
one plausible influence; confidence in an imported candidate or sampling variation
could also explain the short paths. This two-run observation does not isolate which
cause dominates and does not justify another adjacent prompt comparison by itself.
Failure interpretation and repair were not tested because no counterexample was
selected and delivered during either solver run.

## Verification and decision

Audit rechecked journal chains, exact count-to-dispatch request hashes, usage totals,
model-input artifact hashes and tool availability, current submitted diff identities,
final public assessments and original acceptance/safety. Historical source seeds and
the v2 packet/result bytes were unchanged. Operator checks ran only after each
solver stopped and their results were not fed back to either solver.

Evidence under the root: `packet.json`, `authorization.json`, `calibration.json`,
`result.json`, `execution-audit.json`, final A1/B1 assessment directories and the
hash-chained parent journal. Result hash:
`sha256:da70a1e5b7717b8f9843a97b2d23cf4a2441d3430138d1a6539f6d1a93650ca1`.
Operational path changes passed 27 diagnostic/documentation tests in 11.12s,
including both seeded mock paths to isolated acceptance; Ruff passed. Documentation
close-out passed layout/link tests and `git diff --check`. The full repository suite
was not repeated for path/document changes; runtime content did not change.

The result narrows the observed failure to verification selection/stopping in this
seeded setting: making a discriminating public-test tool available did not make it
used or repair A1. Preserve the baseline and these negative results. No quality gain,
fresh-solve rate, causal feature effect, default adoption or further paid comparison
is established. A future intervention needs evidence beyond unused budget or the
fact that this diagnostic is complete.
