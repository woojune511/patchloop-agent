# Public repair with a model-authored regression test

Requirement: use existing `repair` to return both a bug fix and a valid regression
test, preserving existing tests. This is a use evaluation, not a policy comparison.
[python-dotenv #715](https://github.com/theskumar/python-dotenv/issues/715) reproduced
on current main `0b2880591780a426b0551436f47a17e7a76d954f`. Test edits were explicitly
required and allowed in existing files. No operator test or solution was supplied.

One approved invocation on PatchLoop `86c5410a` used mini `gpt-5.4-mini-2026-03-17`,
xhigh, 25,000 output tokens, USD 3 maximum, 40 calls/100 actions/4 edits/1,800 seconds.
The prepared Linux image contained Python 3.12.13, pytest 8.4.2 and Click 8.3.1.
Its digest and the exact request are frozen in the external preparation record.

`run_dev_cc274e9b0eb144a4` returned `PATCH_READY`: 7 model calls, 12 actions,
2 edits, USD 0.12695715, CLI wall time 98.9673 seconds. The original patch changed
`src/dotenv/variables.py` (+6/-3) and added one parameter case to `tests/test_main.py`.
No existing test, assertion, case, fixture or skip condition was removed or weakened.

The model added its test first. Journal event 76 recorded the bug assertion failure
(`''` instead of `'d'`): 1 failed, 218 passed. After the implementation change,
event 96 recorded 219 passed. External verification applied the same unmodified
model test to base source and the full original patch in separate clean checkouts:
1 failed/218 passed before, 219 passed after. No environment/import error explained
the failure. The public `dotenv_values` API and a concrete expectation are tested.

The model case covers an empty environment variable. The issue's empty value within
the file was separately verified externally: base failed, returned implementation
passed. The model did not author that additional case. Its new case inherits an
existing Windows skip; it executed on Linux. Full suite/other environments and
independent acceptance were not run; acceptance stays `NOT_RUN`.

Evidence: `C:/pt/repair-dotenv-715-20261005/` contains the request, original patch,
test-only patch, public receipts, before/after results, `REVIEW.txt` and hash-bound
`result-summary.json`. The 115-event journal under
`C:/pt/repair-dotenv-715-state-20261005/runs/` passed hash-chain validation.

Decision: this original artifact meets the scoped implementation-plus-test goal
without human correction. Codex reviewed it; final human review remains with the
user. No general quality or new-policy effect is established. Allocation closed;
no runtime changes, retries, resume, publication or follow-up diagnostic.
