# isort I3: observation-retention execution bridge

Date: 2026-10-15. Implemented and tested with inert transport, official=false.
Paid execution is not authorized. The
[frozen design](2026-10-15-isort-retention-design.md), I1/I2 records and default
runtime remain unchanged. No credential, model metadata, input-count API or
generation API was accessed. No isort probe, registered check or evaluator ran.

## Implementation and preserved conditions

The separate `diagnostics/isort_retention_checkpoint.py`,
`isort_retention_execution.py`, `isort_retention_review.py` and
`isort_retention_collection.py` implement I3. Existing I1/I2 source files remain
byte-identical. The ordinary budget, action admission, automatic repair recheck,
terminal public oracle, isolated evaluation and offline guards are reused.
No new default runtime policy, prompt, tool or completion gate is introduced.

The first request matches I2 after normalizing only the displayed active seconds.
Every later request carries the exact bound operator packet. On the seed, the
ordinary current diff must match its full recorded patch. After an edit, the
packet and frozen seed patch appear under `historical_operator_public_observation`,
while the new current diff stays unchanged. Exact return to the seed restores
the current-observation form. The packet is not converted into a registered
check or model-authored working note.

For each assembly the bridge stores the ordinary and retained input artifacts.
Removing the one added field must recover the entire ordinary input, including
plans, completion advice and native items. Count and dispatch verify this binding
and current workspace diff. Every dispatch records request, packet, candidate,
segment and placement identities. There is no extra turn or forced handoff.
The 60,000-input-token stop applies to later requests as well as the first; no
retention-specific trimming, replacement handoff or output shrink is allowed.

U keeps the original semantic rubric and public explanation/accepted-edit
requirements. C matches actual provider dispatches to retained input records and
requires a later segment on the seed before the first new edit. An early edit
without that exposure is NOT_EXERCISED. R requires public classification of every
executed pre-edit probe: known-case ownership recheck, exact replay, case citations,
configuration coverage and rationale. Configuration changes do not exempt a
same-case recheck. Missing classifications block the review; insufficient evidence
is recorded explicitly. Zero rechecks without an edit is NOT_OBSERVABLE.

The existing public-review callback/file exchange now seals U and the computed
C/R grades before the terminal public oracle and isolated evaluation. Invalid U
or R evidence prevents all seals and both assessments. Review time is inside the
same 720 s. Unknown transport/billing or input integrity stops leave grades
NOT_RUN; no late review is fabricated. Terminal results never re-enter the solver.

## Free validation

The final focused suite has **84 passing tests in 75.23 s**, including:

- Whole first-input parity; current observation after an actual segment boundary
  and within a segment; historical placement after edits; exact-return data form.
- Unchanged plans/advice/native items, and rejection of later input corruption or
  stale current-observation placement before another count/dispatch.
- A local fixture completing two edits, required verification, submission and
  isolated evaluation, with U then C/R sealed before both terminal assessments.
- The failing-check/repair/automatic-recheck path; conditional U qualification;
  invalid U or probe-review citations; no-edit and no-handoff outcomes.
- Same-case checks under changed configuration versus strict identical replays;
  ambiguous classifications; no retrospective waiver based on probe outcome.
- USD 3.50/full-output reservation, fresh exact single-use counts, six generations
  and counts, accepted-edit ceiling, individual parallel-action counting,
  completion reserve and all solver/phase/invocation deadlines.
- Sixth-count/sixth-generation handling, late usage settlement without late tools,
  later input overflow without pruning, and count/transport/usage/cleanup/setup
  uncertainty without retries, correction calls or evaluator continuation.
- Funded-entry identity/scope/price/readiness rejection with inert key and SDK
  doubles, one metadata attempt, no resume and no private verdict in the summary.

The first 65-test file-batched run passed in 161.02 s; distributing independent
tests across workers brought the final expanded focused run under two minutes.
The intermediate 82-test run also passed. These were provider-free engineering
checks, not additional experimental samples or changes to the frozen design.

The final real-checkpoint rehearsal is `C:/pt/isortretainbridge02/result.json`.
Its collection journal is `runs/run_dev_isorttablebridge.jsonl` inside that new
root; the reused journal identifier does not refer to the closed I2 root. Events
are labelled `isort_retention_*` and the row is I3.
It restored the original pre-339 isort prefix and used two scripted responses,
two simulated counts and two actions (read, stop). The first input's displayed
time was 278 s versus the static preview's 270 s; its normalized request hash is
`sha256:fd14c6ea17b4491b55597d6b66b380f9c46239cf8fb4bfe33e598de907331099`.
The real inherited deadline was enforced, not reset to the preview clock.

The second dispatched input retained the complete diagnostic after the ordinary
handoff. Synthetic C is PASS; synthetic U/R are NOT_OBSERVABLE because this
rehearsal intentionally stops without an edit. D, model uptake, retention effect
and actual isort acceptance remain NOT_RUN. USD 0.001100 in provisional mock
accounting is not a provider charge: actual calls and billed cost are zero.
`isortretainbridge01` is a preserved earlier successful rehearsal; the final
manifest uses bridge02, whose implementation hash matches the final source.

Separately, the standard mock smoke at `C:/pt/isortretainsmoke01` reached local
isolated `EVALUATOR_PASS`, run `run_dev_ae027881da5b4313`, with four mock turns,
five actions, one edit and zero cost. That CSV fixture result is not an isort
repair result. Ruff passed across `patchloop`, `diagnostics` and `tests`.
The complete fast-suite selection passed with **4,915 passed and 19 skipped in
1,490.97 s**; the full suite is broader than the under-two-minute focused check.
Five documentation layout/link tests also passed. `focused.xml`, `full.xml` and
the sealed `validation.json` bind these results to the final implementation and
rehearsal; the separate validation journal is append-only and hash-chained.

## Frozen execution preparation

The design remains
`sha256:d43f3e998691a1b73c288217ee3480262dfa3a7f36eb409f91a774f6f11e5ee4`.
The runtime remains
`sha256:b3c8e80c0656fb4954eebcb5d30de411d4b0fa687a150ef3308883487bb08208`.
The diagnostic implementation is
`sha256:bfba89f3a9de92e0ba8305d994e437c5759b20a59fb6c46bc330c88fbc32e4ce`.
Validation evidence lives under `C:/pt/isortretainchecks02`, with append-only
`dev-run-v1` records and hashes for the source, tests and rehearsal.

Preparation writes `C:/pt/isortretainready01/manifest.json` only after the connector
is committed and validation is bound. It fixes I3 once, `original-isort-2491`,
`gpt-5.4-2026-03-05`/xhigh/default, the existing repository `.env` path, USD 3.50,
six generations/counts, eighteen tools, two edits, 281 s solver/720 s total,
30 s public oracle/330 s isolated evaluation, and every other original cap.
It also binds the exact packet, observed diff, retention policy, U/C/R criteria,
first-wire preview/parity, final rehearsal and validation. The new live output
is `C:/pt/isortretainlive01`; it must remain absent until an approved invocation.

The collection module's CLI only prepares the manifest. Its separate `collect`
entry point requires the exact manifest hash and positive USD 3.50 approval,
fresh official price review, read-only environment readiness and at most one
exact-model metadata read. No automatic Docker start, image pull/build, retry,
resume, replacement row or result-based tuning is permitted. Human approval of
this preparation is not paid-execution approval.

No I3 model result, target diagnostic result, final repair, hidden acceptance or
performance gain is established. The baseline decision remains unchanged.
