# Frozen remeasurement and repository release

Closed after approved execution: 9/20, below the 11/20 threshold. See
[results](../docs/history/2026-10-06-portfolio-dev20-results.md).
No remaining paid authorization, test300 preparation or remote publication.

## Stage 1: existing dev20

Use `python -m diagnostics.portfolio_dev20 freeze|preflight|run` with `--root`,
`--live-root` (freeze only), and the exact `--packet-hash` (preflight/run).
The external root first needs `validation.json` in the existing panel validation
format: runtime hash and hashed focused/full JUnit, Ruff and mock receipts.
Freeze binds current commit, implementation, historical manifest/summary, all
twenty serialized requests, prices, source descriptors and installed native harness.
Preflight checks existing images and full prepared sources; it never pulls/builds.

Use the original 2026-10-02 dev20 roster/order, one fresh run each, mini snapshot
gpt-5.4-mini-2026-03-17, xhigh, 25,000 desired output tokens, USD 1.20 each / 24 total,
40 calls / 100 actions / 4 edits / 1,800 seconds. Existing baseline policies are
explicit; saved-program recheck stays off and prepared probe dependencies are absent,
as in the old requests. All original package bytes must match before dispatch.

SQLFluff-1625's current public package later acquired a different public launcher
and selected-test suite. Keep that package unchanged. The separate registered
`tasks/dev-train/portfolio-dev20/sqlfluff-1625` snapshot copies all thirteen package
files byte-for-byte from 3077f81afe3d85e301e3af99b09bf4c117425f52; it is the same
development instance, not a new task or a renamed test-split instance. No hidden
content is projected into solver requests. Other nineteen packages retain their paths.

Relative to the old runtime at 3077f81a, the current solver contains these changes:

| Change | Behavior in this rerun |
| --- | --- |
| Optional saved-program recheck and its context/recovery fields | Disabled (`probe_recheck=none`) |
| Registered `run_tests`, pytest observations and segment support | Old packages register no suites; tool remains unavailable, although the current system prompt lists its name |
| Public `repair` delivery and request/envelope types | Existing `dev` task path and independent evaluation retained |
| Separate `repair-verify` command | Not called by this benchmark; not an acceptance oracle |

Thus the runtime is current, not an exact replay of old model inputs. Settings and
task bytes are matched; no particular changed feature's effect is isolated.

Run requires a new `authorization.json` containing approved=true, packet_hash and
the exact human_message. The shared one-shot driver refuses restart/resume and new
roots are mandatory. Old allocations and files are never changed or reused as state.
Its optional after-row callback evaluates the exact submitted patch with the existing
native runner before dispatching the next task. Native verdict disagreement,
incomplete evaluation, cleanup uncertainty, provider uncertainty or cap breach stops
remaining rows. Native subprocess allowance is 600 seconds including the existing
300-second task evaluation; this is separate from the solver's 1,800-second limit.
Timeout never authorizes cleanup assumptions, another native invocation or a solver retry.

`summary.json` retains twenty rows, historical/current outcomes, transitions,
non-submissions, NOT_RUN/ERROR, artifact identities, costs and separate solve/native
time. Full agreement, known cost, safety PASS and twenty complete evaluations are
required to consider the threshold. At least 11 resolved authorizes preparing the
next proposal only; otherwise close with documentation. This is an exposed panel and
historical comparison, not a causal gain or a held-out score. Retain the original
eight environment corrections and two public-check projections as limitations.

## Conditional stage 2

Do not prepare test300 before the threshold. If met, freeze all Lite test instances,
use public repair requests and the existing loop, export original prediction JSONL,
and use separate official evaluation. Never relabel test tasks as dev-train.
Only input/export/aggregation adapters may be added; no solver tool or policy change.
Do not select paths/checks from reference patches or answer-test metadata. Keep all
solver submissions fixed before inspecting hidden outcomes. Public repair acceptance
remains NOT_RUN, separate from external benchmark resolved status.

Proposed scope: PatchLoop alone, same mini, 300 fresh runs, USD 3 each / 900 total;
model cap across both stages is USD 924. Compute/environment costs are separate.
Inventory resources and obtain explicit environment acquisition approval before any
image pull/build, and exact paid approval after offline preparation. No external
agent comparison, result-based tuning, retries, replacements or automatic diagnostics.
Incomplete batches retain the 300-instance denominator. Self-evaluation is not an
official leaderboard submission; official=false and claim_eligible=false remain.

## Public material

Lead README with public repair/verification and saved evidence. Explain engineering
tradeoffs in product.md and keep historical measurements separate in evidence.md.
Use the original dotenv-715 patch for a clearly labelled saved-result demo, not a
new solve. Public copies omit credentials, personal paths, raw provider state and
private evaluation material. Record transformations and hashes; retain originals.
Human approval remains unreported unless the user explicitly records a decision.
Remote publication is a separate action. Preserve the user's AGENTS.md changes.
