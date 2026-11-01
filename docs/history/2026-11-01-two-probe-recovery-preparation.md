# Two-probe diagnostic recovery preparation

Date: 2026-11-01. Status: preparation; new live execution NOT_RUN.
Baseline repository: `a155ef49b3980587b65cdb3c1d6aba4cc49fb2a2`.
Baseline run: [post-probe stopping diagnostic](2026-11-01-goal-grounded-stopping-results.md).

## Revised decision and question

The last diagnostic selected a relevant additional save_as observation. Its first
probe failed on an unavailable import before the target behavior was exercised.
The model identified the setup failure and proposed a corrected program preserving
the observation and assertions. The one-probe allocation directly prevented that
meaningful recovery from executing. At termination only about 33.5 of 265 seconds
remained, so increasing the probe count alone would not establish sufficient time
for execution, interpretation and reporting.

The earlier recommendation to prioritize helper construction and exhausted-tool
handling over resources was too strong. This follow-up revises that decision
without rewriting the closed result: the small diagnostic must permit at least
one observation, one correction when needed, and a final report before it can
meaningfully assess the whole sequence. The user requested proceeding with that
change. The normal dev runtime does not have this diagnostic's one-probe cap.

Question: at the same saved public post-probe state, does permitting two new probes
and more total time let the model reach a meaningful observation and an adequately
bounded report? A second probe is optional, not a required action. A setup failure
may recur, a different path may be chosen, or cost/model limits may still stop the
run; those outcomes remain distinct from candidate correctness.

## Minimal intervention and controls

Create fresh external preparation `C:/pt/stop-review-20261101-v2/` and intended live
root `C:/pt/stop-review-run-20261101-v2/`. Keep the previous preparation, live result,
closure and unused allocation immutable. No old approval or unused balance carries
into the new invocation.

Change only max_probes from 1 to **2** and total time from 265 to **600 seconds**.
The longer deadline allows room beyond the prior approximately 231-second two-call
attempt for a corrected execution and final model response; completion is still
not guaranteed. Derived per-request waits continue to be clipped by the remaining
overall deadline. Keep four model calls, ten actions including report, 60k input,
full 25k-output reservation or stop, and a proposed new USD1.5431895 cap.

Keep task8/pydicom1413, patch be082f27, gpt-5.4-2026-03-05/xhigh and credential file
`C:/Users/geonj/Documents/PatchLoop/.env`, one fresh attempt. Restore the same source
run run_dev_62da82f8f7e34345 at actual counted request sequence38/ancestor138. Do not
resume the failed v1 run or include its import failure, suggested UID correction,
later decisions or any new source hints in model context. The existing earlier
write_dataset probe remains usable public evidence.

The source checkpoint retains its actual saved remainder (one probe/265 seconds).
Record the new allocation separately and project two probes/600 seconds into the
current state and budget overlay. This is a documented resource intervention,
not an assertion that the source run had those remaining resources. New counters
and cost accounting start from zero. Opaque continuation stays excluded by type;
this is public reconstruction, not exact native resume.

No core runtime, report guidance, offered-tool policy, setup auto-correction,
mutation permission or independent evaluator changes. The normal source/runtime
identities remain unchanged. A failed probe still consumes a probe; no free
retry or extra allowance is added. Only registered read/search/public probe/report
are permitted. Count before dispatch, zero SDK retries, and stop on accounting,
transport or recovery uncertainty. Four maximum calls are not guaranteed by the
cost cap: the existing admission check requires each full output reservation.

## Evaluation and local validation

Accept evidence of useful progress only when the observed program reaches the
relevant target and its assertions, with setup failures classified separately.
When a helper needs correction, inspect whether the model preserves the original
question, input conditions and expected outcome instead of weakening the test.
A final report must distinguish observations, gaps and why stopping is justified.
Do not infer candidate correctness from helper PASS or call counts. If both probes
fail at setup, report that verification remains incomplete. No automatic extra run.

The contrast changes both count and time; it cannot isolate their individual
causal effects. One stochastic rerun also cannot establish general improvement.
It can resolve whether the previously blocked recovery-and-report sequence is
possible under the new bounded allocation at this checkpoint.

Focused local validation covers failed setup -> corrected second probe -> report,
third-probe rejection, immediate report availability, source identity and cutoff,
fresh usage and remaining-deadline clipping. Only external diagnostic allocation
and tests change, so repository validation uses the documented docs-only route;
the already-passing full quick suite is not repeated without a runtime change.

The prepared checkpoint remains
`sha256:0c21b8823ec1edf221c9b0114baa8dea743a00905a08da5d7dd33b3ffe339fd6`.
New request:
`sha256:63ea07a022a5922dde03d33ac1adf7e327fda4892f2f38b3bee401e280530e98`.
`allocation-comparison.json` compares it to v1's prepared request
`sha256:a8a7bba7c100251ffdf539eb160b8792763ecd0308c5a2dc9512029b985199a5`:
exactly four numeric values change, probe1->2 and time265->600 in each of the two
current-budget projections. Public material, report description and tool schemas
otherwise match. This is an offline structural comparison, not a causal live test.

A read-only resource review found that, after the previous actual two-call usage,
the new allocation would retain USD1.076919 and 368.489 seconds. The corrected
probe was already requested by that second response, so an analogous trajectory
would need execution plus one final generation. This gives plausible room but no
guarantee. At uncached60k input and25k output, a full call reserves USD0.525;
three maximal calls cost USD1.575, above this cap. Admission remains authoritative.

The external focused selection passed **10 cases in 25.40 seconds** (22 unselected).
It covers setup ImportError -> corrected helper -> report in three model calls and
two probes; third-probe rejection; reporting without a new probe; exact cost
admission; remaining-deadline clipping and deadline termination; saved cutoff and
opaque exclusion; unchanged saved1/265 with current2/600. Ruff passed for all four
external Python files. The preparation receipt is
`C:/pt/stop-review-20261101-v2/local-validation.json`, bound in CAS and an append-only
development journal. These are local mechanism checks, not live model behavior.
