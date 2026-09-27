# Current mutation-advice checkpoint comparison, 2026-09-27

## Problem, hypothesis and scope

N1's original first post-probe repair assumed caller cancellation without measuring
it. The diagnostic asks whether the current completion message's explicit mutation
recommendation contributed to that premature repair. A preserves the exact saved
request; B removes only its `next_action` and imperative mutation sentence. The
remaining repair-stage wording, tools, observations, budget, native encrypted history
and earlier exposure are preserved. Both arms can read, search or probe. Subsequent
turns use the ordinary runtime. These are checkpoint continuations, not fresh solves.

The user started Docker, read-only admission passed, and then explicitly approved
the exact task/model/credential/repeat/cap proposal. Collector checkpoint: `8da9e09`.
No production runtime or task files changed during execution. Every result is
`official=false`; no general claim or default adoption is authorized by this sample.

## Fixed execution

- Task: `tasks/dev-train/anyio-interrupt-runner-cleanup-v3/public.yaml`.
- Model: `gpt-5.4-2026-03-05`, xhigh, desired output ceiling 25,000; existing baseline
  context, plan, probe, inspection and completion-cost policies unchanged.
- Credential path: repository `.env`; no credential contents in evidence or agent context.
- Order: A1, B1, B2, A2. Each retains 37 model calls, 92 tools, four mutations and
  the inherited active-time allowance; setup is outside that active deadline.
- Each row has $0.967463 new allowance, after $0.232537 inherited bookkeeping.
  New invocation cap: $3.869852. No transfer, retry, resume or extra sample.
- Manifest: `C:\pt\analyses\checkpoint-live-comparison-20260927-v1\manifest.json`,
  `sha256:0ecec11aef5ab719a9d0cc83bde0dda66f8ac5e6b110759f4c541a3b22b9b408`.
- Environment follow-up: `C:\pt\analyses\checkpoint-live-readiness-20260927-v1`.
  This supersedes the earlier failed environment observation, without rewriting it.

## Observed results

| Row | First lifecycle check | Accepted mutations | New model calls / counts | Submission and isolated result | New cost USD |
| --- | --- | --- | --- | --- | --- |
| A1 | PASS | 1 | 4 / 4 | Submitted; acceptance PASS, safety PASS | 0.584870 |
| B1 | FAIL | 2 | 6 / 6 | Submitted; acceptance PASS, safety PASS | 0.644412 |
| B2 | FAIL | 2 | 7 / 8 | COST_CAP_REACHED; acceptance/safety NOT_RUN | 0.9285125 |
| A2 | FAIL | 3 | 8 / 9 | COST_CAP_REACHED; acceptance/safety NOT_RUN | 0.8817265 |

All four selected `replace_text` first, before any new inspection or probe. Initial
input counts were 36,637 for both A rows and 36,625 for both B rows. Their first
request hashes exactly match the frozen pair. New total usage is **$3.039521**,
with **$0.830331 unused and closed**. Historical usage is excluded from this total.
Both arms have one accepted submission and one resource-limited non-submission;
the latter must not be presented as a rejected patch or an evaluated wrong answer.

A1's first repair explicitly handled interruption and retained the shared task.
It passed lifecycle 7/7 and upstream 32 tests (three deselected), then submitted.
B1, B2 and A2 instead depended on the waiting caller being cancelled. Their first
lifecycle runs all reported the interrupted test resuming in function/module/taskgroup
cases: 4 passed, 3 failed. The inherited probe observed shared-runner liveness and
test resumption, but did not measure caller cancellation. This is a public
observation-to-hypothesis mismatch, not evidence of missing input delivery.

B1 read the implementation after failure and replaced the conditional caller hook
with interruption handling. Its second repair passed both public checks and isolated
evaluation. B2 and A2 also revised their repairs and passed lifecycle, but upstream
`test_keyboardinterrupt_during_test[asyncio]` timed out its subprocess after three
seconds (31 other tests passed, three deselected). A2's third repair still hit that
timeout. Its lifecycle PASS belongs to the second diff; no final-diff lifecycle PASS
or isolated acceptance is claimed.

B2's final public probe observed `run_test` raise KeyboardInterrupt and then a worker
still alive inside exit, with the send stream open and runner task pending. This
supports investigation of the close path; it does not by itself prove a unique cause
of the upstream timeout or cover every cancellation scenario. The probe process
itself exited successfully with confirmed cleanup; the daemon worker observation is
not a leftover Docker container. A2 used no new probe; B2 used one, after both repairs.

## Information delivery and resource boundary

The public-trace audit verified all **25 generation requests and 27 counts** against
saved public projections and native continuation. It verified every branch's exact
58-event inherited prefix and envelope, first A/B request identity, count-before-
dispatch binding and new usage against the group ledger. The frozen original source
packet still validates. No private evaluator material was projected into model inputs.

B2's final probe result was present in the next counted 42,333-token input, but no
generation followed: the minimum request could not fit the row's remaining cap.
A2's final failed upstream check likewise reached a counted input without a following
generation. Do not call these observations ignored by a model that subsequently
decided; there was no subsequent model decision. Last dispatched output ceilings
were 25,000 / 21,156 / 10,525 / 14,620 for A1/B1/B2/A2 respectively. The terminal
codes and messages establish cost admission stops, not a newly observed transport
failure or a claim that useful reasoning necessarily would have fit another budget.

All billing evidence is known. No input-count, transport or cleanup uncertainty
stopped the group. Exact new check/probe container names were derived from execution
identities; **all 13 are absent** in the final Docker inventory. B2/A2 task safety is
still NOT_RUN because isolated evaluation was not executed. No auto retry/resume ran.

## Artifacts, changes and limits

- Live immutable results and branch journals: `C:\pt\mutationlive0927a`.
- Operator audit packet: `C:\pt\analyses\checkpoint-live-results-20260927-v1`.
  `audit.py` binds its own hash in the append-only audit journal; `public-audit.json`
  contains request bindings, public actions/checks/probe, costs and container checks.
- Runtime identity remains
  `sha256:e3b533ac585ea2b48d159a6f8449d3996cd991b3da73fa268dbda71f8d5230c3`.
- This closure changes current documentation only. Earlier packets, closed histories,
  reports, experiments, task files and runtime code are preserved. The previous
  preparation's automated tests are not represented as freshly rerun here.

Removing the current recommendation showed no observed benefit in this bounded
sample: first-action choice was unchanged and neither arm completed both rows.
This does not prove equivalence, general harm/benefit, or that all mutation guidance
is irrelevant. Earlier cues and encrypted history remain; two repetitions per arm
at one task boundary do not establish general capability. Keep the baseline unchanged.

The next proposed diagnostic is a provider-free public observation of the waiting
caller's actual cancellation state at the callback-interrupt boundary. That can test
the repeated unsupported condition directly before adding another prompt policy or
funding more comparisons. Shutdown diagnosis and the existing explicit-cancel
same-task public coverage gap remain separate questions; no new execution is implied.
