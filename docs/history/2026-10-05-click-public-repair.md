# First public repair: Click #3362

Question: can the existing public-only CLI deliver a usable local patch from an
issue and a current source checkout, without benchmark evaluation material?
[Click #3362](https://github.com/pallets/click/issues/3362) reproduced on current
main `06b2a678741131fd577ce170e23e5ca0aeba0309`; no older base was selected.

The separately approved environment used Python 3.12.13 and pytest 8.4.2, image
`patchloop-public-repair-pytest@sha256:4512f41e843d57ad7fb8306ece1e549afa2903db6d97815315fa9bf732c82c1a`.
The issue program and expected text stayed unchanged; the operator added only
an equality assertion. Existing formatting/basic/arguments tests passed 346/346.

One separately approved invocation used the existing `repair --request` CLI on
`1f173bf1` (runtime implementation `a47feb37`), mini `gpt-5.4-mini-2026-03-17`,
xhigh, 25,000 output tokens, USD 3 maximum, 40 calls/100 actions/4 edits/1,800 seconds.
`run_dev_24dbde5f211948d7` delivered `PATCH_READY`: 8 model calls, 12 actions,
1 edit, USD 0.15930945, CLI wall time 178.9566 seconds.

The returned patch changed only `src/click/formatting.py` (+14/-6), disabling
hyphen breaks in both usage layout branches while retaining tab expansion and
whitespace handling. The common text wrapper and public API stayed unchanged.
Applied unchanged to a separate clean checkout, it passed the public reproduction,
all 346 related tests, and `git diff --check`. No manual correction was made.

Evidence: `C:/pt/repair-click-3362-20261005/` contains `request.json`,
`returned.patch`, `public-verification.json`, `review-*.json`, `REVIEW.txt`, and
`result-summary.json` with artifact hashes. The hash-verified 129-event journal
is under `C:/pt/repair-click-3362-state-20261005/runs/`.

Codex inspected the diff; final human review remains with the user. Click's full
suite, other environments, and independent acceptance were not run. Acceptance
is intentionally `NOT_RUN`. This demonstrates one public repair delivery and
local verification, not general repair quality. Allocation closed; no retries,
resume, publication, runtime change, baseline change, or follow-up diagnostic.
