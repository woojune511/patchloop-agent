# Three public repair uses

Requirement: evaluate the unchanged `repair` and `repair-verify` user path on
three new tasks across two repositories, requesting implementation and additive
tests. This tests practical use, not a policy intervention or general accuracy.
Closed C2, pydicom, Click #3362 and dotenv #715 investigations were not reopened.

The user approved the frozen manifest before any paid dispatch. Runtime commit
`295515c9b450689df14f0c4c71aa3348ee7eba54` and content hash
`sha256:713259075f8e8123ad382fc23f218d67ab5d2c2d820c9b35845fba03129270df`
remained unchanged. All three used `gpt-5.4-mini-2026-03-17`, xhigh, 25,000 output
tokens, one fresh run each, USD 3 each/USD 9 total, 40 model calls, 100 actions,
four edits and 1,800 seconds. Prepared Python 3.12/pytest images were reused.
No operator programs or solutions were supplied to the solver.

| Task | Calls / edits | Cost USD | Repair / verify seconds | Base + model tests | Patched checks |
| --- | --- | --- | --- | --- | --- |
| [Click #2786](https://github.com/pallets/click/issues/2786) | 38 / 3 | 0.88878885 | 759.499 / 22.478 | 1 failed, 941 passed | 942 passed |
| [Click #2740](https://github.com/pallets/click/issues/2740) | 21 / 3 | 0.55696080 | 517.962 / 21.405 | 1 failed, 941 passed | 942 passed |
| [dotenv #713](https://github.com/theskumar/python-dotenv/issues/713) | 6 / 2 | 0.16581015 | 114.795 / 10.902 | 2 failed, 218 passed | 220 passed |

All three returned `PATCH_READY`; no non-submission. Each original patch went
through the existing verifier once: `COMPLETE`, `OBSERVED_FAIL_THEN_PASS`, no
collection errors, skips or missing tests. Base checks passed independently.
The failures were behavioral assertions: sentinel instead of callback value,
missing exception note, and missing fsync before replacement. Existing tests,
fixtures and configuration were preserved. No patch/test correction or verifier
bypass occurred. Every acceptance remains `NOT_RUN`; these results do not judge
requirement fit independently of model-authored expectations.

Total settled cost: USD **1.61155980**. Repair wall time: 1,392.256 seconds;
verification: 54.785 seconds. Shared preparation measured 395.234 seconds,
excluding initial instruction/document reading. Operator and assistant-review
active time was not measured. Actual human review is **NOT_PERFORMED**, with
requirement fit **NOT_ASSESSED**. Execution approval is not code review.

Assistant review, separate from those execution observations:

- Click #2786's test covers the public callback case. Skipping an omitted
  same-name parameter bypasses its whole processing method; callback/validation
  scope needs human review. No additional regression was reproduced.
- Click #2740 is a feature request. Its implementation handles absent notes,
  but its test calls Python 3.11's `add_note` unconditionally while the project
  supports Python 3.10. This is a static compatibility finding; 3.10 was not run.
- Dotenv tests both public APIs and fsync-before-replace ordering. The mock does
  not check the descriptor or flush ordering, and no power-loss durability was
  demonstrated. Installed CLI tests were excluded before freeze because the
  prepared environment lacks its executable; the original failed preflight is
  preserved. No environment installation or workaround was added.

Evidence: `C:/pt/repair-usage3-20261005/` contains the three requests, untouched
patches, CLI verification JSON, timings, assistant reviews and `usage-results.json`.
Manifest SHA-256: `a36f022f95932dac3d2027cb1e98f2f812fe980e8fcf852881cf00ba1ae59da7`.
The results snapshot is content-addressed as
`sha256:c759bc0c0cbb05dffa936aae78ccbc1f2c3c88fb3b1b2ac7321425129bcffe7c`.
Repair/verifier journals validate; dispatch/settlement counts and cost reconcile.
An incomplete approval serialization artifact was retained and superseded by the
complete approval record before dispatch. Original source checkouts stayed clean.

Decision: execution scope completed and allocation closed. Existing commands
handled all three uses without runtime changes, new drivers or gates. Keep the
baseline; continued-use selection awaits actual human review of these originals.
No automatic diagnosis, correction, retry, resume, publication or additional paid
run is queued. Full project suites and other environments were not run.
