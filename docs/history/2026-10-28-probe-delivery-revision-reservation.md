# Latest helper delivery and a shared revision reserve

Date: 2026-10-28. Lane: mutable dev-head, official=false, claim-ineligible.
Scope: implementation and local validation only; no provider or target execution.

## Problem and evidence

The [public-counterexample continuation](2026-10-28-public-counterexample-repair-results.md)
made no new edit and resubmitted the same candidate. Its final public comparison
still failed all three candidate regressions. Two mechanisms were selected because
they lost already-paid-for evidence or removed the action requested by the user:

- The second helper's receipt captured 684 stdout characters, but a fresh completion
  segment omitted them from the next request. Earlier source reads were delivered.
- Optional exploration protected the already-verified candidate's finish path,
  while editing required a longer edit/check/finish path. At three remaining
  responses, one was reserved for correction; editing was no longer offered.
  Money, input context and output tokens had not been exhausted.

The model nevertheless received and acknowledged the public counterexamples. Lost
helper output alone therefore does not explain its choice to finish. These local
changes test delivery and action availability, not whether the model will select
or produce a correct repair. Raising the total budget was not needed to distinguish
these mechanisms.

## Change and decision

`completion_context.py` retains the latest current-diff probe's bounded public
streams, host observation, setup/exception/path diagnostics, reproduction data and
completeness flags. Failed, partial, timed-out and truncated results retain their
status; they receive no success or verification credit. Probe programs and older
source bulk stay omitted. Existing native-result deduplication prevents double
delivery when the native exchange remains in the request.

`runner._tool_policy` accepts an optional host-owned
`requested_revision_diff_hash`. The public-counterexample diagnostic binds it to
its sealed packet only when candidate regressions exist. On that unchanged diff,
with `ready_to_submit`, edit capacity, a cost ledger and `completion-recovery-v1`,
optional reads/searches/history/helper/tests must retain a successful revision
path. It includes a missing edit anchor when necessary, edit, all original replays,
fresh public checks and finish.

Shared steps supply response/action counts, role-specific output costs and nominal
time. Existing adapter floors are retained by maxima rather than duplicate work;
all cost alternatives remain funded. The unused correction reserve and total
limits are unchanged. A helper can close before the final affordable edit window.
The reserved final public matrix action/time is already outside ordinary runner
limits and is not charged twice here.

This is an optional diagnostic budget binding, not a new mandatory mutation or
finish gate. Ordinary runs with no binding preserve their policy. Changed diffs
make the measured failures historical and remove this particular reserve; no-op
or rejected edits keep it. Returning to the same measured hash reactivates the
same binding, so it is not described as a run-wide consumable credit. Model notes
cannot activate it. Original failure obligations and action idempotency remain.

## Local evidence

The new controls cover affordable exploration, the last edit window, exact
response/action/cost/time boundaries, missing anchors, multiple public checks and
original replays, selected-test child executions, legacy adapter floors, stale
binding, no-request behavior, preview/reconstruction and diagnostic packet binding.
Projection controls cover native/fresh segments, failures, truncation, stale data,
later batches and idempotence.

Saved-data projection used receipt 286 and prepared request 290 from
`C:/pt/public-counterexample-repair-run-v1/repair/runs/run_dev_3e21775752a54cae.jsonl`.
The canonical context, receipt and request artifact hashes were checked. Reassembly
through the actual completion/segment/projection/model-input functions changes
stdout delivery from zero to exactly one. All 684 characters, the host observation,
receipt identity and completeness flags match. Gates, original review, current diff,
public counterexample packet, checks and budgets remain exact. No provider count,
dispatch, target, private evaluator artifact or opaque model history was used.

External evidence: `C:/pt/latest-probe-reservation-local-v1/` contains the reproduction
script, immutable artifacts and a hash-chained `dev-run-v1` journal. The
`probe-projection-audit.json` hash is
`sha256:23226fc51f57223bf38a20f257a06445364e2133f629dbdd5af4d75fc9623836`.

Saved policy replay used prepared requests 260/274 and their public turn snapshots
263/277. It restored the ordinary counters from each journal prefix and reconstructed
the gateway from saved public task, diff, anchors, checks and completion state;
no workspace or sandbox execution was needed. The original offered tool sets match
the unbound policy exactly at both points.

| Saved state | Existing admission | Bound revision admission |
| --- | --- | --- |
| 5 responses, 8 actions remaining | Read/helper/edit/finish available | Same tools; successful revision reserved |
| 4 responses, 7 actions remaining | Helper/test/edit/finish available | Helper/test close; edit/finish/stop remain |

The four-response rejection is `model_calls`. One correction response and its
USD0.525 reservation remain intact. The exact saved remaining cost/time values are
USD3.146866700 / 1265.5180967999622 solver seconds and USD3.019920700 /
1185.5180228999816 seconds. Limits remain 20 responses, 39 ordinary actions,
three edits, 2365 seconds including 390 evaluation seconds, and 40K/25K output.
The original USD4.50 cumulative ledger includes USD1.119211300 inherited spending
and the closed USD3.380788700 allocation; replay does not reopen either allocation.
No-packet, empty-failure-packet and stale-packet controls exactly match default.

`requested-revision-budget-audit.json` has hash
`sha256:2c94531a07e2a4bef8a8f2f50d2f96d809b36617a777139ab26df90506a72c4c`.
`evidence-index.json` has hash
`sha256:06d0c1f785769ce8f3c16a44545862d4bd31565534833804085f77c595261ce1`.
The projection proof precedes the final policy-only runner changes; its projection
source is unchanged. The budget proof uses the final policy. These are separate
proofs with recorded implementation hashes, not a combined live execution.

Validation:

- Focused projection: 36 PASS in 0.909s. Focused revision/resources/routes/diagnostic:
  52 PASS in 1.239s. Both are below the two-minute focused-test limit.
- Quick plus changed owners: 760 PASS, two contract-hash expectation failures,
  219.942s. Both isolated mock evaluations passed. The changed context contract
  correctly changed the overall surface identity; affected current and derived
  pins were updated, leaving frozen historical-arm expectations intact.
- Narrow contract rechecks: eight PASS in 1.184s. Five documentation checks passed.
  An additional probe contract check exposed an already-stale system-prompt pin;
  the unchanged prompt source was inspected, its expectation refreshed, and that
  check passed in 0.889s. No tool schema or system prompt was changed for those pins.
- Ruff and `git diff --check` passed. The full quick suite was not repeated after
  expectation-only fixes. No paid model, real target or real evaluator ran.

JUnit records are `C:/pt/tmp/completion-latest-probe28.xml`,
`requestedrevision28.xml`, `proberevisionfinal28.xml`, `proberevisionpins28.xml`,
`proberevisiondocs28.xml` and `proberevisionprobepin28.xml` in that directory.
The first report serialization attempt found a set in counter metadata; sorting
it into a list fixed reporting only. The pure policy assertions had already passed.

## Limits and next question

Local delivery does not establish that a live model uses the observation. Reserving
one successful revision path does not guarantee a valid edit, another failed-repair
cycle, sufficient reasoning time or correct behavior. The final public matrix still
runs after submission and is not returned to the model; informational counterexamples
still do not independently block finish. The next empirical question is whether
the same bounded continuation uses the retained evidence and preserved edit window
to repair the public regressions. It is unrun and unfunded. All prior allocations
remain closed; changed runtime hashes invalidate old execution manifests.
