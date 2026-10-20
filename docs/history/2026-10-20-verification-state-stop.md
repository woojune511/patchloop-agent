# Verification state OFF/ON: provider stop before a comparison

Status: allocation closed after A1's seventh generation request. No retry,
replacement, continuation, model change or additional paid call. All runs remain
official=false and claim-ineligible.

## Question and frozen execution

The [scope audit](2026-10-20-verification-scope-context-audit.md) found original
requirements and contrary evidence present despite incorrect completion claims.
The [state separation](2026-10-20-verification-state-separation.md) therefore
distinguishes model discussion from computed verification evidence. This
[comparison](../../.agent/plans/verification-state-comparison.md) asks whether that
change reduces unsupported/contradicted completion claims **and** improves actual
repair, independently of submission or silence.

The human approved project `.env`, `gpt-5.4-mini-2026-03-17`, six OFF and six ON
assignments, USD 10.56 new spend. Execution used commit
`f69765b15ab0df037b222a844bddf1f70453cdd9`, manifest
`sha256:760a5c9422cdd378fb1c58846605d7cb6c69a866721a05e8d3cfe9392bcba6fa`
in `C:/pt/verification-state43/`, and fresh state in
`C:/pt/verification-state43-live/`. Authorization and same-day official pricing
review are separate immutable records; the frozen manifest was not rewritten.

The final commit had 5,476 passing tests and 20 skips, focused/grader validation,
both quick selections and isolated mock smoke before admission. The frozen
result-or-size-v1 transitions, two references, 24k source, 60k counted input,
40 model calls, 100 actions, four edits, 1,800 seconds, USD 0.88 per row,
USD 5.28 per arm and all other manifest limits remained unchanged.

## Observed stop and cause boundary

A1 performed four searches and two file reads, with six completed responses and
seven completed input counts. At journal event 91 the seventh generation was
dispatched; event 92 recorded:

`PROVIDER_TIMEOUT_OR_UNKNOWN: provider dispatch failed: InternalServerError`

Its call ID is `call_28a1d4027ebc4899a58bbc4513871ff9`; request hash:
`sha256:08caf683ace0c1a5707f6112f03e2fcf3777844c216d508eaeb76847377cd5c0`.
The run is `run_dev_cac1a1d62c104885`, elapsed active time 42.080 seconds.

The installed OpenAI SDK maps HTTP status >=500 to `InternalServerError`.
The runtime caught the dispatch exception before response parsing/usage settlement.
This is not a counted-input mismatch or a completed response with malformed usage.
The saved record contains the exception class but not the exact HTTP status,
response body or server cause. A transient service failure and a request-dependent
provider failure remain alternatives. Requests 2-6 completed with the exact same
tool schema as request 7; request 1 lacked the not-yet-admitted `replace_text`
tool. B was never dispatched. This does not diagnose the ON mechanism.

The fixed uncertainty stop closed the entire allocation. The unused monetary
allowance does not permit a retry or a replacement row.

## Public judgment and independent repair

The public-only annotation packet was sealed before opening outcome records.
All six decisions were reviewed with action/input/request hashes. Each requests
more inspection; none asserts that the original issue is fixed or verified.
The statement that path resolution is critical is an investigation hypothesis,
not a task-completion assertion.

| Observation | OFF / A | ON / B |
| --- | --- | --- |
| Assigned | 6 | 6 |
| Started / completed | 1 / 0 | 0 / 0 |
| Completion claims | 0; A1 NO_CLAIM | NOT_RUN |
| Unstarted rows | 5 | 6 |
| Submitted patches | 0 | 0 |
| Caller / native evaluations | 0 / 0 | 0 / 0 |
| Judgment effect / repair effect | Unassessable | Unassessable |

The mechanical aggregate records J=0 and R=0 on each fixed six-row denominator,
but `outcomes_complete=false`. These are not evidence of correct judgment or
0% repair accuracy: there were no completion assertions or evaluated submissions.
The favorable comparison criterion was not assessable. No local evaluation was
needed; assessment recorded only its start and closed result, with zero oracles.

## Evidence availability and displacement

The original `pylint src/project` command, missing-initializer setup and versions
were present in all seven dispatched inputs. A1 inspected Astroid builder/modutils
and searched namespace tests. It did not acquire Pylint's caller implementation
or execute the original caller, declare a bound reproduction or observe a current
runtime counterexample.

The acquisition annotation is YES only for partial relevant public evidence
already available; it does not attest a faithful original-caller reproduction.
Separated-state exposure/use is not observed in this OFF row, and all B axes are
NOT_RUN. A's absent treatment field is not a failure.

Previously observed complete source spans in successive inputs numbered
0, 1, 2, 6, 7, 8 and 10. Every complete span remained present; no source or probe
body was newly displaced. Counted inputs rose from 13,755 to 27,955 tokens.
There was one initial segment and no transition. This short prefix says nothing
about later handoffs or ON behavior; no probe evidence existed to preserve.

## Accounting and decision

| Known settled component | Tokens | USD |
| --- | ---: | ---: |
| Uncached input | 55,487 | 0.04161525 |
| Cached input | 71,936 | 0.00539520 |
| Reasoning output | 1,677 | 0.00754650 |
| Other output | 793 | 0.00356850 |
| Total recorded from six responses | | 0.05812545 |

The seventh request's actual charge is **UNKNOWN**. Its conservative reservation
was USD 0.13346625; recorded usage plus that reservation is USD 0.19159170.
Neither the reservation nor their sum is a billed total. No further provider
request was made after the stop.

The live result does not support adoption or rejection of state separation.
Keep the implementation and frozen criteria unchanged; do not infer an LLM
judgment defect or evidence-loss cause from a request without a recorded response.
Any further live diagnostic or new allocation requires its own concrete scope
and authorization. The unresolved execution question is the provider failure;
the original judgment/repair comparison remains untested.

Evidence root `C:/pt/verification-state43/`: `manifest.json`, `authorization.json`,
`pricing-review.json`, `collection.json`, `audit-public/`, `annotations.json`,
`live-public-review.json`, `result.json`, `live-closeout.json`.
The review checks source delivery from actual wire inputs without decoding
encrypted reasoning. Preparation, collection, public-audit and assessment
journals are append-only `dev-run-v1`; the earlier preparation `closeout.json`
and all historical artifacts remain unchanged.
