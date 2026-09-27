# Time-extended continuation result

Date: 2026-09-28. official=false; separate continuation, not a fresh solve or matched
A/B replacement. Follows [preparation](2026-09-28-time-extension-preparation.md).

The user explicitly approved a new $3 invocation cap for one original-toqito-1538
dev-train continuation, gpt-5.4-2026-03-05 xhigh, existing PatchLoop/.env, with 60
additional active minutes. Model/tool/mutation counters remained inherited. The
source's unresolved request and unknown charge were preserved, not reconciled.

## Result

Preflight READY. One new count and one new model generation produced `finish_task`.
There were no new edits, probes or public checks. The agent used the already-passing
14-test regression on the final source patch. Submission completed: benchmark FAIL,
safety PASS. The solver did not receive private evaluator results or the operator's
post-run public checks. Private evaluator internals were not inspected.

New cost is exactly $0.094595; this invocation's billing is known. Unused $2.905405 is
closed, with no retry/resume. The earlier unknown source charge remains unknown, so
combined historical billing is still not fully known. No global default changed.

All inherited prefix events and the original source journal hash verified. The
first counted/dispatched input matches the frozen live plan, and normalizing only
current time and cost allowance makes it equal the original pending-call input.
Native public-state delivery verified. The submitted patch hash is unchanged:
`sha256:003d549bab52d602d4efb2c0c80b7002c4ab587da5c3fb086ea1a2977351bb50`.
Therefore the earlier two operator public checks still describe this exact patch;
they were not rerun or promoted to full task correctness. Both local checks passed,
but the benchmark now demonstrably does not pass.

The public finish explanation treated the passed regression as sufficient for
submission, and categorized broader optimizer adequacy as a documented numerical
limitation rather than a blocking unresolved issue. With more time available it
chose to submit immediately, rather than investigate further. This establishes the
observed decision under the extended condition; it does not prove what the timed-out
source call would have returned or identify the private evaluator's failing case.

## Evidence

- Implementation: `250f75f`; runtime unchanged from the matched experiment.
- Manifest: `C:/pt/analyses/time-extension-live-plan-20260928-v1/manifest.json`;
  hash `sha256:bc50b9481fcac4b136c1833e773e7fc7ac24b9ce6d8c46867b57dd0ab551a362`.
- Live receipt: `C:/pt/timeextension0928a/result.json`; group journal
  `run_dev_timeextension`, fork `A1/runs/run_dev_33068b6e257f423a.jsonl`.
- Delivery/source/cost/decision audit:
  `C:/pt/analyses/time-extension-results-20260928-v1/audit.json`;
  hash-chained journal `run_dev_extensionresultaudit` binds report and script.
- Prior exact-patch public validation is linked by the matched-result record in
  the preparation chain. Original A/B result and original B NOT_RUN are immutable.

Preparation tests and mock validation are recorded separately. Final documentation
checks passed. This result adds real provider acceptance, exact delivery and isolated
benchmark execution, but no success or generalized quality claim.

## Interpretation and next question

Extra time allowed submission, but did not make this patch benchmark-correct. The
review cue previously produced two local semantic improvements; that is compatible
with remaining task defects. Do not infer the hidden failing test from FAIL alone.
Next inspect the unchanged patch against uncovered public requirements and independent
properties, separating solver numerical adequacy, edge regimes and verification
scope. Use public evidence only and provider-free analysis before another paid run.
No further paid invocation is authorized by the closed $3 cap.
