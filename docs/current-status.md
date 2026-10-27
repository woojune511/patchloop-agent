# Current status

Updated: 2026-10-27. Runtime source owns behavior. Historical reports are evidence,
not an active queue.

## Product and working baseline

Build a single coding agent that repairs public software tasks, verifies changes
and submits within bounded resources. Start improvements from observed failures.
Recovery, sandboxing and isolated evaluation support that product.

- dev-head is the sole mutable runtime; official=false and claim-ineligible.
- General baseline: gpt-5.4-2026-03-05, xhigh, 25,000 output tokens.
- Selected policies: segmented-v1, result-or-size-v1, brief-v1, probes enabled with
  policy none, repair-recheck, protected-v1 inspection, per-call-v1 cost admission.
- Limits: 40 model calls, 100 actions, four accepted edits, 1,800 seconds.
  Paid work also requires the exact task/model/credential/repeat scope and cap.
- Cross-run memory, held-out tuning and claim execution are disabled. Bounded
  run-local notes remain available. Historical Rapid executables are absent.
- These are selected settings, not CLI defaults or evidence of general accuracy.

See [guide](../.agent/guide.md), [operations](operations.md), [product](product.md)
and [evidence boundaries](evidence.md).

## Active decision

The approved [first-edit context A/B](history/2026-10-27-first-edit-checkpoint-results.md)
executed each condition once from the same saved public post-helper checkpoint.
A (duplicate context) normalized caller-supplied paths, resolved F0010, passed all
five public cases/regression and isolated acceptance, scope and safety. This is a
real model-authored accepted repair with supplied saved evidence, not a fresh
benchmark solve or general quality claim. The first original call retained its
identity; the second call's input identity changed while control output stayed equal.

B (lossless references) reduced first input from 56,199 to 36,887 tokens (34.4%)
but changed namespace classification instead. F0010 remained; public cases passed
2/5, regression passed and isolated task acceptance failed. Both made one edit.
One fixed-order pair does not establish that representation caused the different
hypotheses or that compression improves repair quality. Do not adopt it on that claim.

A's next input grew to 65,982 tokens, largely from revalidated source repeated in
the edit result. Generic handoff rebuilt the same request, so the model stopped
at INPUT_LIMIT without receiving its successful verification result. Host checks
still completed. B received the failed result at 46,645 input tokens and stopped,
acknowledging failure; the one-edit design did not permit revision. Task correctness
and successful model completion flow remain separate outcomes.

The next concrete defect is post-edit source retransmission and an ineffective
handoff in the checkpoint request builder. Address that narrow delivery contract
before another broad search; no follow-up implementation or run is authorized by
the completed allocation. The correction time floor was not exercised live.

All five input counts and three generation calls completed with known usage;
zero corrections and no execution uncertainty. Settled cost $0.40829625 under
$2.40; allocation closed. Result: `C:/pt/first-edit-checkpoint-run-v1/result.json`.
The [implementation](history/2026-10-27-first-edit-checkpoint.md) has 112 focused
PASS/71.16s and 472 quick PASS/116.57s including isolated mock; Ruff PASS.
No runtime changes occurred during this experiment.

The [preceding caller-source trial](history/2026-10-27-dependency-source-results.md)
retains one unsettled correction and a closed allocation. Prior evidence and the
separate local operator repair are indexed in [October 27 history](history/2026-10-27/README.md).
The operator solution and private evaluation details were excluded from these
model requests. Context-only comparisons with mini-SWE-agent remain unsupported;
see the [context analysis](history/2026-10-26-target-failure-context-analysis.md).

## Supporting evidence

- [Security maintenance](history/2026-10-23-security.md): refreshed host dependencies
  and public Python 3.12 images after the emSign incident. Old task/legacy images
  remain offline-only. New runs need newly prepared identities; prior manifests
  do not authorize execution against the updated runtime.
- [Helper-path results](history/2026-10-22-helper-path-results.md): useful information,
  no repair in A1/B1/B2; partial comparison stopped on drift. Allocation closed.
- [Invocation linkage](history/2026-10-22-probe-invocation-results.md): submitted
  repairs 0/3; ON mechanism use 0/2. Partial run; no adoption or quality claim.
- [Caller evidence](history/2026-10-19-caller-evidence-results.md): A/B 0/6;
  original-caller verification remained missing.
- [Portfolio remeasurement](history/2026-10-06-portfolio-dev20-results.md): 9/20,
  below the 11/20 threshold; test300 remains unprepared and unauthorized.
- [History](history/README.md) indexes the closed investigations and allocations.
  Their past next steps, settings and approvals do not carry forward.

## Execution and claim boundaries

All prior paid allocations are closed. The [older interrupted call](history/2026-09-28-expectation-review-results.md)
retains unknown billing; later settled allocations do not resolve it. The latest
source-ready diagnostic also retains one unsettled response.

Fresh solves, seeded repairs, funded continuations, saved-patch evaluations,
operator replays and scripted tests are different evidence. Do not pool them as
solve rates or expose private evaluator details to the agent. Public case support,
submission, independent task acceptance and safety are separate. Mock safety is NOT_RUN.

Do not start Docker Desktop or pull/build evaluator images automatically. Preserve
exact recovery identities, zero SDK retries and stop-all on count/transport/billing
uncertainty. Earlier saved candidates failed isolated acceptance; the clean-source operator
resolver candidate passes. The saved-evidence A model trial now passes acceptance;
fresh-solve and held-out improvement remain unverified.
Public-check PASS, safety PASS and successful submission do not establish repair
correctness. Linux CI and general improvement remain unverified.
