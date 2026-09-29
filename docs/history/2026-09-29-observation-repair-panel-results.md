# Fixed observation to repair: closed results

Date: 2026-09-29. `official=false`; diagnostic seeded episodes, no adoption or
held-out/generalization claim. Preparation and causal limits remain in the
[design](2026-09-29-observation-repair-panel-design.md) and
[contract](../../.agent/observation-repair-panel.md).

## Problem and hypothesis

An unchanged model-authored public probe had exposed an explicit-versus-ambient
endpoint error in the fixed H candidate. Would supplying its actual observation,
beyond the same program and expected values already shown to both arms, cause
independent inspection and repair? This tests a narrow observation-to-action link,
not fresh solving or an information-versus-no-information comparison.

## Execution

The user authorized the exact proposed new USD 8 invocation by replying to its
approval request. Four episodes ran in frozen A1/B1/B2/A2 order using
hf-hub-xet-endpoint-propagation v5 (dev-train), gpt-5.4-2026-03-05, xhigh,
25K maximum output tokens, and C:/Users/geonj/Documents/PatchLoop/.env.
Limits were USD 2 and 900 seconds per episode, 4200 seconds overall, 40 calls,
100 actions and four mutation slots including the seed. No retries, extensions,
replacement episodes or continuation were used. Both arms received the same seed,
public task, frozen probe, expectations and tool settings; only feedback stdout
withheld (A) or supplied (B) the registered replay observations.

Each settled episode received one external frozen public probe on its final diff.
Those results were not returned to the agent. Isolated benchmark acceptance and
safety are separate measurements; no private evaluator details informed a repair.

| Run | New edits | Final public checks | External frozen probe | Acceptance | Safety | USD | Active seconds |
| --- | ---: | --- | --- | --- | --- | ---: | ---: |
| A1 | 0 | PASS | FAIL | FAIL | PASS | 0.1576325 | 60.135 |
| B1 | 3 | PASS | PASS | FAIL | PASS | 1.7342175 | 887.081 |
| B2 | 0 | PASS | FAIL | FAIL | PASS | 0.1032765 | 78.594 |
| A2 | 0 | PASS | FAIL | FAIL | PASS | 0.0820195 | 60.235 |

All four submitted and ended EVALUATOR_FAIL; no NOT_RUN or infrastructure outcome.
The seed consumes one mutation slot separately from the new-edit column. B1 used
14 model calls; each other episode used three. No episode invoked run_probe,
including A: there was no self-acquisition crossover. Total settled provider cost
is USD 2.077146; unused USD 5.922854 is closed, not future authorization.

## Evidence to action

B1 initially ran the contract check. After PASS, its next public decision explicitly
cited the supplied ambient-client counterexample and searched HfApi endpoint state.
It read constructor and wrapper source, then made three accepted edits: preserve
constructor endpoint in `_explicit_endpoint`, and forward that explicit value in
metadata, download and snapshot wrappers. Both required public checks passed on
the resulting diff. The external probe confirmed direct/ambient routes remained
unchanged while the explicitly configured route rebased. The final benchmark
still failed; neither this probe nor the visible checks explain that residual failure.

B2 received the identical B feedback on all three turns but only ran the two
required checks and submitted the unchanged seed. Its finish decision said there
was no concrete remaining public uncertainty to justify an extra probe. Thus a
known delivered counterexample did not enter its public action sequence. A1 and
A2 also submitted the unchanged seed after those checks. These traces support an
inconsistent use of supplied contrary evidence; they do not reveal private reasoning
or establish whether salience, check-coverage interpretation, completion incentives
or resource-horizon wording caused it. B2's reference to a final completion call
warrants inspecting those signals before prescribing another prompt or gate.

B1 also submitted without rerunning the discriminating probe itself. Its targeted
repair was confirmed by the separate operator audit, not agent verification credit.
One success in two treated episodes is insufficient for a reliable causal advantage;
full-task acceptance did not improve. Keep the working baseline unchanged.

## Integrity and limits

All 23 dispatched model inputs were reconstructed and checked against frozen arm
feedback. B1 retained current-candidate feedback for five inputs and correctly
marked it historical for nine after edits. The other nine inputs remained current.
Final workspace diffs matched submitted hashes and each external probe identity.
Provider starts/finishes and input counts reconciled 23/23; all responses completed
with valid usage, and token-based prices reproduced ledger costs. Probe cleanup
was confirmed with no timeout/deadline uncertainty or workspace drift. No runtime,
contract or historical artifact was changed during execution.

Four seeded runs on one already exposed task cannot establish general performance.
The program already disclosed the hypothesis to both arms. The supplied observation
is an operator intervention sourced from an earlier model-authored public probe.
Frozen-probe PASS proves only the exercised boundary, not all download behavior,
benchmark correctness or regression freedom. No additional live run is authorized.

## Evidence and validation

Execution source: commit `33eee18`. External append-only journals and immutable
artifacts: `C:/pt/analyses/observation-repair-panel-20260929-v1`.
Packet hash: `sha256:d3fa07e2afc24240dd84bdf2a49e8f8c254cc316d1cb4fb6f37a603035d8cd33`.
Approval: `approval.json`; closure: `runs/run_dev_observationrepair.jsonl`;
per-episode state: `state/{A1,B1,B2,A2}`; frozen probes: `audit-*.json`;
verified input/action summary: `analysis/summary.json`; billing and probe-binding
verification: `analysis/settlement.json`, both linked in the analysis hash journal.

Preparation had 28 focused/mock/documentation tests and Ruff passing, including
normal repair/check/submission/isolated evaluation through the mock path. Closing
this result changes documentation only; documentation-layout tests and diff checks
are rerun. No new production behavior, fresh solve or quality claim is introduced.

Next question: why can public-check PASS close the episode while a current public
counterexample remains unresolved? First inspect existing B1/B2 inputs, coverage
statements and completion horizon without another provider call. Keep delivery,
interpretation, repair and final acceptance separate.
