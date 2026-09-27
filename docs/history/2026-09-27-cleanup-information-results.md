# Cleanup information continuation results

## Question and authorized execution

Would later raw cancellation-order/state observations help the agent repair the
first failed lifecycle check on B1's existing candidate? A retained the saved
request; B added only the exact candidate's traced/untraced operator program and
stdout/stderr once. No rescue patch, other candidate or causal verdict was supplied.
Both arms retained the source's previous exposure to the earlier caller-state probe.

The user approved the prepared four-row A1/B1/B2/A2 allocation on 2026-09-27.
Collector commit: `0cf07b81035a4d1a412c7362eee1a9bad00643e3`.
Task: `dev-train/anyio-interrupt-runner-cleanup-v3`; model
`gpt-5.4-2026-03-05`, xhigh, 25,000 output tokens; repository `.env` path.
New invocation cap: $2.786950; each row retained $0.6967375 remaining allowance.
Manifest: `C:\pt\analyses\cleanup-information-comparison-20260927-v1\manifest.json`;
hash `sha256:2c0969f5b86ba0346cc3f10b8310841e402dab82554d24e582bf57d3d5e1c64f`.

## Executed results

| Row | First action | New repairs | New model calls | Both public checks | Acceptance / safety | New cost USD |
| --- | --- | ---: | ---: | --- | --- | ---: |
| A1 | replace_text | 1 | 3 | PASS | PASS / PASS | 0.411305 |
| B1 | replace_text | 1 | 3 | PASS | PASS / PASS | 0.4441585 |
| B2 | read_file | 1 | 4 | PASS | PASS / PASS | 0.513527 |
| A2 | search_files | 1 | 4 | PASS | PASS / PASS | 0.545683 |

All four submitted after one new repair. Recorded runtime counters include the
inherited first repair; the table excludes it. Each new lifecycle check and upstream
regression check passed on that row's exact repaired diff. No new probe ran.
All outcomes are official=false, claim_eligible=false.

A1 restricted caller-side cancellation to an unfinished future and added runner
uncancel handling. B1 explicitly named caller re-cancellation as stranding teardown,
removed that handler and stopped pre-cancelling the future in the outer path.
B2 read source first, removed the caller handler, added runner uncancel handling
and separated ordinary exception/cancellation handling from outer interruption.
A2 searched an existing uncancel idiom, removed the caller handler, cleared runner
cancellation and drained the outstanding future after cancelling the runner.
These are public hypotheses and actual edits, not access to private reasoning.

Both arms therefore achieved 2/2 acceptance with one new repair each, and seven
new model calls per arm. A cost $0.956988; B cost $0.9576855. These two repetitions
per arm do not establish equivalence, general improvement or a default policy.
B1's hypothesis is consistent with the supplied measurements, but A also reached
successful repairs without the new supplement. Do not infer an information benefit
from B success alone or treat the earlier closed B1 trajectory as a matched control.

## Delivery, cost and cleanup audit

All 14 actual input counts and 14 dispatches were verified against saved public
projections and native continuation records. All four first requests matched their
frozen hashes. B's extra field appeared in the first current-state message only.
First-input tokens: A 23,610; B 27,187 (+3,577). Every row preserved exactly 90
source events and the source envelope; inherited charges were bookkeeping only.
The original source packet and probe evidence revalidated without changes.

Known new cost: **$1.9146735**. Unused **$0.8722765** is closed, not authorization for
another run. No unresolved counts or usage failures remain. All eight owned check
containers are absent. Count-before-dispatch and zero SDK retries were retained.
No runtime/task/default prompt changes were made during or after collection.

Live root: `C:\pt\cleanupinfo0927a`.
Audit and closure: `C:\pt\analyses\cleanup-information-results-20260927-v1`:
`audit.py`, `public-audit.json`, `closure.json`, CAS and hash-chained audit/closure journals.
Audit hash: `sha256:a6dc828ccba1f33f73bda2ad3fb2197ba6c09ddc8b4f9cac7e21705f9bd8f544`.

## Remaining question

Observed success, first-repair count and model-call count did not distinguish the
conditions. Do not add this observation as a default prompt policy. The concrete
remaining coverage question is whether these repairs preserve an actual waiting
caller.cancel() request: this comparison did not execute that operator control on
the new candidates. Existing check/acceptance success must not be enlarged into
that unmeasured claim. Any such provider-free follow-up needs a separately bounded
scope; no additional paid execution or automatic retry is active.
