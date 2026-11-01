# Bounded temporary-rate-limit handling

`RunRequest.rate_limit_policy` defaults to `none`. The explicit `bounded-429-v1`
policy is recorded in the run envelope and model identity. It changes request
transport, not solver prompts, tools, task correctness criteria or task resources.

The normal runner injects its journal into `BoundedResponsesClient`. For input
counting and generation, a logical request has at most three physical attempts.
Only HTTP 429 with `rate_limit_exceeded` or `slow_down` authorizes another attempt.
Quota/billing errors, unknown 429 codes, 500/503, timeout, connection loss, parsing
failure and usage uncertainty retain the existing stop behavior. Native compaction
does not use this retry policy. SDK retries remain zero.

Use a valid Retry-After seconds or HTTP-date value as a minimum, with small jitter.
Without it, use exponential backoff with jitter. Total scheduled backoff is at most
120 seconds per logical request; a longer server delay is not shortened. The
original caller deadline includes every attempt and wait. No task deadline, output
ceiling, model-call allowance or cost allocation is renewed by a rejection.

The payload hash is stable across physical attempts. The prior exact input count
and conservative generation reservation apply to the same payload. Rejected HTTP
attempts are separate transport evidence, not successful generation usage receipts
and not an invoice reconciliation. A successful logical response settles once.
An unmatched logical dispatch after interruption remains non-resumable; this policy
does not replay an uncertain request after a process restart.

The external parallel scheduler supports up to eight independent task processes.
Its shared admission lock also covers every physical attempt, so a peer's stop
prevents subsequent retry admission while already admitted work may settle.
Each row's entire cost allocation is reserved before execution, without transfers.
Scheduling order is operator metadata, never a solver hint or retained answer.

Existing Docker resources still constrain throughput. Registered checks have 2 CPU /
2 GiB limits and public probes 1 CPU / 512 MiB limits. Eight solver processes do not
prove that eight peak-memory checks fit the host. Preparation must inspect existing
resources; it must not start Docker Desktop or pull/build images automatically.

Focused owners: `tests/test_rate_limit_retry.py` and `tests/test_parallel_dev_batch.py`.
The current [preparation record](../docs/history/2026-11-01-parallel429-preparation.md)
separates local tests from paid execution. Official reference:
[OpenAI retry guidance](https://developers.openai.com/api/docs/guides/rate-limits#retrying-with-exponential-backoff).
