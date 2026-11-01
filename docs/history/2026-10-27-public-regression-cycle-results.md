# Single-A result: regression failure delivered, revised candidate passes

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: approved execution and public-artifact audit
- Origin Date: 2026-10-27
- Verification Status: LIVE_EXECUTED / CLOSED; bounded revision exercised successfully
- Implementation: `ca96a4cb`; sealed execution source: `393d40a4`

The [sealed trial](2026-10-27-public-regression-cycle-plan.md) ran A exactly once
after exact approval, with the same saved public evidence and the $1.20 cap.
The question was whether returning registered regression before model completion,
with one funded revision, lets the model repair a regression while preserving
original-call success. The previous trial stopped before its regression failure
was available. This trial exercises the complete feedback sequence, not merely
first-edit success or local scripted behavior.

## Observed outcomes

| Stage | Observation |
|---|---|
| First accepted edit | Normalizes the search root through `_cache_normalize_path` |
| First original recheck | supported; F0010 resolved, first-call conditions preserved |
| First public regression | FAIL: 1 failed, 1,230 passed, 69 skipped, 15 xfailed |
| Actual failure delivery | Fresh original and regression results in the next dispatched request |
| Second accepted edit | Preserves absolute/symlink matching and adds normalized-real-root matching |
| Second original recheck | supported; F0010 still resolved, control output unchanged |
| Second public regression | PASS: 1,231 passed, 69 skipped, 15 xfailed |
| Next response | Receives current success, calls `stop_task`, accurately acknowledges both results |
| Supplementary public cases | 5/5 PASS; child selected and parsed, no F0010 |
| Isolated evaluation | acceptance PASS, scope PASS, safety PASS; one evaluator dispatch |
| Usage | $0.38928225 / $1.20, all usage settled; allocation closed |

The first failure was
`test_load_from_module_symlink_on_symlinked_paths_in_syspath`, raising `ImportError`.
Its public log completed in 9.16s without clipping. The model's second public
hypothesis explicitly connected realpath-only root normalization to this failure.
The edit tries the absolute root as well as the normalized real root, matching
absolute/real filename forms against each candidate. It also simplifies the
namespace-prefix expression to `".".join(modpath)`. No read/search or operator
repair intervened: the model revised directly from the delivered source and failure.
Because this revision changes more than one expression, the trial does not isolate
the independent contribution of each changed expression.

The first candidate diff was
`8347b51de99f81f43cab8b9eef4eff0f771dbac66be474ed06b68568e62e2a49`.
The successful final diff was
`28c3ea5b8f0a181ae77d843dfc84eb4b6efc7fb40ba5ba7d3c7ac9177d274116`.
Original and regression feedback bind these exact identities. Final public checks
reuse the completed second-diff regression receipt instead of rerunning it.

## Delivery, resources and completion

| Response | Input tokens | Output tokens | Generation seconds | Cost |
|---|---:|---:|---:|---:|
| First edit | 56,269 | 31,589 | 251.28 | $0.18435225 |
| Revision | 55,068 | 26,531 | 225.34 | $0.16069050 |
| Stop | 55,488 | 583 | 5.13 | $0.04423950 |

All three generations had zero cached input tokens. Three ordinary responses,
zero corrections, three model tools and two accepted edits were used. Host work
used three original actions (one shared baseline, two candidates), two regression
passes and the separately authorized final checks. No extra helper, optional
original selection, automatic retry or additional trial ran.

The first post-edit request counted 62,946 tokens, over the unchanged 60K limit.
The actual context handoff reduced it to 55,068 and preserved fresh original and
regression feedback plus counters. The counted and dispatched request had the
same bytes/hash. The final 55,488-token request carried the second-diff PASS
results. Public journal sequences 39 -> 46 -> 48 -> 51 -> 54 -> 56 tie the first
regression failure, delivered request, accepted revision, second regression,
final delivered request and stop together. This exercises real handoff delivery,
as well as regression-driven revision.

Collection start through model-row completion took 558.49s; through final controls,
isolated evaluation and closure, 661.35s. These times include host work and setup,
not only generation. The approved 1,200s model/intermediate limit, 390s final
public/isolated limits, token ceilings and dollar cap were unchanged during execution.

The stop summary correctly states that original and public regression now pass.
Its raw diagnostic reason code was `public_task_conflict`; that label is not a
task-success verdict. Success here comes from bound check receipts and the separate
isolated result. This diagnostic uses `stop_task` and a synthetic operator submission,
so it does not demonstrate the product's complete `finish_task` submission flow.

The first original call retained input conditions; the second call still reports
different input identity because cache output inside the input root can affect
later calls. Control output stayed unchanged. Do not claim both original calls
ran under identical inputs.

## Decision and limits

Retain regression-before-completion, bounded revision and exact receipt reuse:
their intended live path worked for this saved-evidence trial. Increasing the
context ceiling was unnecessary here because the handoff fit and delivered the
failure accurately. This does not establish that every future request will fit.

The leading question is resolved within this condition: the real mini model used
a public regression failure, revised once, preserved original-call success and
passed the registered regression and isolated acceptance. The result is not a
fresh solve, randomized causal comparison, benchmark success rate or generalization
claim. Prompt/resource policy differs from historical trials and the first edit
is stochastic. General production behavior remains unchanged.

The next evidence gap is transfer to an unseeded run through the normal agent
completion path, including preservation of the observed feedback and resource
contracts. That needs a separately specified trial; unused budget authorizes no
repeat. All paid allocations are closed.

## Evidence

- Manifest: `C:/pt/public-regression-cycle-plan-v1/manifest.json`, SHA-256
  `3f470e864a1b2b2f578dcf6f727918a781b916a88795857d75ac93b22f375b19`.
- Direct approval: same folder, `approval.json`.
- Executed command: `& 'C:/pt/public-regression-cycle-plan-v1/run.ps1'`; exit 0.
- Result: `C:/pt/public-regression-cycle-run-v1/result.json`, SHA-256
  `f393b2a9b5c36aac91e0b899ed6cb1a1d38d2fa110416206d6eb3bf6738a50cd`.
- Public analysis: `C:/pt/public-regression-cycle-analysis-v1/public-analysis.json`,
  SHA-256 `476a4ef7d4b1dc7b9aa2fb915d853ea8bcce9685216304655ae4bfde287e7954`.
- Independent delivery audit: same folder, `delivery-audit.json`, SHA-256
  `2fe35f9387363040ccf505124beb6d68ac344a22b1a4936b2dccebd1e85d7f20`.
- Candidate patch: same folder, `candidate.patch`; hash equals the final diff above.
- Final registered regression receipt SHA-256:
  `01396c7984b4a7d632ad16e5350367003a1afb7693b8fe48bb753d1db69d38cf`.

Audit used public requests/actions/checks and isolated scalar verdicts. Opaque
reasoning, hidden tests, reference fixes and private evaluator payloads were not
inspected or delivered to the model. Public journals validate their hash chains;
runtime code did not change during the approved execution. The earlier plan,
implementation record and historical candidates remain immutable.
