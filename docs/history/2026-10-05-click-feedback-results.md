# Click feedback correction results

The user approved the two requests in
[preparation](2026-10-05-click-feedback-preparation.md), manifest SHA-256
`c98ef2be05052d64c6db1947f89c034f86cacd4fbf56eb1dfbd22a7c82548e9b`.
Runtime `c83974e2` remained unchanged. Each existing `repair` invocation started
fresh from its fixed original-patch source, with public review feedback and
operator reproductions explicitly supplied. These are feedback-informed
corrections, not new unexposed solves or resumed original runs.

| Task | Run | Calls / edits | New cost USD | Repair / verification seconds |
| --- | --- | --- | --- | --- |
| Click #2786 | `run_dev_0db5c1b4f0f148d8` | 14 / 4 | 0.38734935 | 315.445 / 52.875 |
| Click #2740 | `run_dev_69e6d5e9779f442c` | 8 / 1 | 0.14811570 | 124.651 / 56.740 |

Both returned `PATCH_READY`. Total new cost **USD 0.53546505**, repair 440.096
seconds and verification 109.615 seconds. No count/transport/billing uncertainty,
retry, resume, operator patch/test correction or runtime change occurred. Original
requests, patches, review and results were hash-checked and remain unchanged.

For #2786, correction removes the broad processing skip and places its condition
after type/callback processing, at the shared-destination winner decision. An
additional model test checks callback invocation, returned value and rejection.
The correction's new test fails on the original submitted implementation and
passes on the corrected one. Upstream-base composition fails the original issue
test before and passes afterward; the preservation test passes in both versions.
The same final candidate passes **943 tests** and the frozen operator callback
check. Both verifier reports are `COMPLETE` / `OBSERVED_FAIL_THEN_PASS`.

For #2740, only the model-authored test body changes. It checks actual `add_note`
availability, retaining notes assertions when supported and checking ordinary
output otherwise. All three original exception paths remain covered. The
correction-only verifier returns **`UNSUPPORTED`: existing test body/decorators
changed**; that original report is preserved without reinterpretation.
Against upstream, the composed patch is an additive test change:

- Python 3.12: `COMPLETE` / `OBSERVED_FAIL_THEN_PASS`; **942 pass**, notes and
  legacy public output check pass; the notes test actually executes.
- Python 3.10: `COMPLETE` / `PASSED_BOTH`; **942 pass**, legacy output check passes.
  This is compatible test execution, not notes support or a failing-before result
  on 3.10. The original-patch 3.10 failure is preserved in preparation evidence.

There are no skips, collection errors or missing tests in these final checks.
Correction and upstream-composed patches are separate artifacts. Applying either
route in clean checkouts yields identical tracked trees. Verifier final diffs
match the composed patch bytes, including across both Python environments.
Five verifier invocations produced four complete reports and one unsupported
report. No supplemental execution was needed: completed composed reports already
ran all frozen checks on the exact final candidates.

Evidence: `C:/pt/repair-click-feedback-20261005/` contains `results.json`,
`RESULTS.txt`, correction/composed patches, five original verification JSON files,
composition identities, timing records and separate assistant reviews. Results
snapshot: `sha256:9d398ceaa69a13c5f63d90f026b0e90a6f35a4d462146ba3cea80305efac8f66`.
Repair/verifier journals validate; dispatch/count/settlement records reconcile.

Decision: Codex review recommends both corrected candidates within the verified
scope. Original modification-required findings remain valid for the originals;
no general success-rate or new-policy effect is established. Human approval and
active review time remain unreported. Full suites and other environments were
not run; independent acceptance stays `NOT_RUN`. Allocation closed, baseline
unchanged; no further model batch, correction, diagnosis or publication queued.
