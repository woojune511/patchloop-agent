# Eight-worker dev20 preparation and bounded 429 handling

Date: 2026-11-01. Lane: dev-head, official=false, claim-ineligible.
This record concerns implementation and preparation, not a completed paid panel.

## Question and motivation

After the [review lifecycle fixes](2026-11-01-review-lifecycle-and-delivery-fixes.md),
the user requested a full twenty-task experiment with increased parallelism and
handling for temporary HTTP 429 errors. The latest
[full20](2026-11-01-pre-edit-dev20-results.md) took 4,916.317 seconds with two workers;
7,440.634 of 9,759.695 summed row seconds were provider dispatch time. This makes
overlapping independent tasks a meaningful latency intervention. No observed 429
from that closed run is asserted: it completed without transport uncertainty.

Replaying its row durations without resource contention gives eight workers about
34m26s in index order, or 23m23s with longest-duration-first scheduling. Twenty workers
have the same 23m23s longest-row floor. These calculations motivate eight workers;
they are not a current-code throughput measurement. Recent task18 alone took 24m33s.

## Change and boundaries

The scheduler accepts up to eight independent processes. Opt-in
`rate_limit_policy=bounded-429-v1` permits at most two application retries per logical
input count or generation after an explicit temporary 429 rejection. SDK retries
remain zero. Retry-After is a minimum; otherwise exponential delay and jitter apply.
Total scheduled backoff is at most 120 seconds per logical request and all attempts
remain inside the original deadline. A server delay beyond the bound is not shortened.

Each physical attempt is durably identified and subject to the shared batch admission
stop. The same counted request and conservative generation reservation remain bound.
Rejected HTTP attempts are recorded separately from successful generation usage;
invoice billing and count-endpoint billing are not independently established.
Quota/billing errors, unknown 429 codes, 500/503, lost responses and usage uncertainty
are not retried. There is no task restart, extra evaluation or automatic resume.
Default requests retain their previous no-retry serialization and model identity.

This does not change agent prompts, tools, review semantics, public/private boundaries
or acceptance criteria. Cross-run hints remain disabled. Long-first scheduling uses
only historical elapsed times in operator metadata, never earlier answers or patches.

## Proposed experiment

- All current dev-train tasks 1-20, one fresh solve each.
- gpt-5.4-2026-03-05/xhigh, 25K output, existing primary-repository credential file.
- Eight workers, longest historical row first; existing prepared sources and images.
- Proposed fresh allocation: USD4/task and USD80 total, without transfers.
- Existing 40 logical model calls, 100 actions, 12 edits and 1,800 seconds/task,
  including 330 seconds reserved for independent evaluation. Retries renew none.
- Preparation root: `C:/pt/parallel429-dev20-20261101-v1/`.
- Local validation root: `C:/pt/parallel429-local-20261101-v1/`.

The prior full20 is a descriptive baseline: 12 independent PASS, 8 FAIL, 20 safety
PASS, USD20.972777 and 81m56s. Measure changed acceptance, lost prior passes,
NOT_RUN/ERROR, settled generation cost, task/batch duration, physical retry counts,
waits and uncertainty stops. More probes or a successful submission alone is not
improvement. The integrated agent changes and concurrency change prevent feature-level
causal attribution. Development-exposed tasks are not held-out evidence.

The host exposes 16 logical CPUs and about 32 GiB RAM; existing Docker reports about
15.06 GiB. A registered check can use up to 2 CPU / 2 GiB and a probe 1 CPU / 512 MiB.
Eight simultaneous checks reaching their individual memory ceilings would exceed
Docker memory. This is a capacity caveat, not a measured OOM. No Docker configuration,
image startup/build/pull or unrelated application state is changed by preparation.

## Validation and execution status

Quick regression: **1,573 PASS / one host skip**, 465.607 seconds. The 124-case
transport/provider/parallel/documentation selection initially had 123 PASS and one
documentation-size failure in 26.773 seconds. The new detail was moved to a separate
linked guide and redundant prose shortened; the corrected owner passes in quick.
The eight-process rendezvous, explicit 429 count/generation retry, same-payload
accounting, quota/unknown/500/503 refusal, retry/deadline bounds, peer-stop, interrupted
dispatch recovery and cleanup-failure recovery are covered locally. Quick includes
isolated mock evaluation; no redundant standalone smoke was run.

The additional runner/conversation regression had 64 PASS and two stale allowed-tool
expectations in 155.513 seconds. Both omitted the already supported `edit_files` tool;
the larger case also expected older correction wording. Their existing budget and
exact offered-tool checks remain, and both corrected cases pass. The policy/transition/
correction functions are AST-identical to baseline 78500eb7; these are test expectation
corrections, not a runtime expansion caused by retry handling. Intermediate failed
test corrections are retained in the local validation receipt.
The operator transport collector has four offline passing controls and keeps logical
calls, physical attempt admissions, 429 rejections and scheduled waits separate.
An attempt admission is not proof that the remote server executed it; scheduled wait
is not a measurement of actual elapsed waiting. No raw provider/evaluator body is read.

Final local evidence is in `C:/pt/parallel429-local-20261101-v1/validation.json`.
Exact current commit, source/dependency/image identities and twenty public canaries
must be bound in the separate preparation root before paid authorization. A completed
`preflight.json` is the readiness receipt; neither preparation nor this record grants
approval. No live provider call or new cost authorization has been recorded for this
proposal. All previous allocations remain closed. Local handling tests do not establish
live rate-limit recovery, eight-worker throughput or autonomous repair quality.

Official guidance checked during preparation:
[temporary-rate-limit backoff](https://developers.openai.com/api/docs/guides/rate-limits#retrying-with-exponential-backoff)
and [Standard pricing](https://developers.openai.com/api/docs/pricing).
