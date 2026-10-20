# One saved-request retry completed

Status: one separately authorized diagnostic completed and closed. No solver
tool, patch, caller check, native evaluation or A/B continuation was executed.

## Question and scope

The [closed OFF/ON allocation](2026-10-20-verification-state-stop.md) stopped at
A1's seventh generation with `InternalServerError` and unknown billing. The user
requested a retry and approved exactly one new input count and one generation,
project `.env`, `gpt-5.4-mini-2026-03-17`, and USD 0.1575 new spend.

The smallest diagnostic reuses that request without changing input, tools,
model, xhigh effort, 25,000 output tokens, two references or transition settings.
It distinguishes an always-failing saved payload from a request that can complete
on another attempt. Success alone cannot establish the original server cause.

Packet: `C:/pt/verification-state43-request-retry/manifest.json`, hash
`sha256:d01fba857fb46e35bc967c0b6f92cd5ae9bc541d51d19562b672caa7891dfc0b`.
Request hash, identical to the failed dispatch:
`sha256:08caf683ace0c1a5707f6112f03e2fcf3777844c216d508eaeb76847377cd5c0`.
Repository HEAD at execution: `fb046f232c42da7c3a191ce19cda4c0d5223722b`.

The standalone operator helper uses the existing SDK adapter, exact credential
loader, cost ledger and safe exception metadata projection. It executes no
returned function call. HTTP metadata capture is local to this diagnostic;
the production runner's exception-recording gap remains unchanged.
Four local MockTransport cases covered success, generation HTTP 500, count
HTTP 500 and missing usage, with exact request equality and no automatic retry.
Fresh official standard prices matched the frozen rates before dispatch.

## Result

| Measurement | Observation |
| --- | --- |
| Input-count / generation requests | 1 / 1 |
| API response | completed; no adapter error |
| Counted / billed input tokens | 27,948 / 27,948 |
| Cached input tokens | 0 |
| Output / reasoning output tokens | 883 / 765 |
| New settled cost | USD 0.02493450 |
| Returned tool / executions | search_files / 0 |
| Client cleanup | confirmed |
| Solver repair / A/B comparison | NOT_ASSESSED / NOT_RUN |

The original count was 27,955; this attempt counted 27,948 despite the identical
saved request hash. The new response usage matched the new immediate count.
No stale count was reused, and no token discrepancy was ignored.

Known cost across the original prefix and this diagnostic is USD 0.08305995.
The original seventh request's unknown charge remains unresolved and separate;
the successful retry does not reconcile it.

## Decision and remaining question

The exact request can complete, so a deterministic rejection of this unchanged
payload is not supported. A transient provider failure remains plausible, but
the original missing HTTP status/code/request ID prevents identifying its cause.
This is evidence about request execution, not model judgment or repair quality.

The prior A/B allocation and its eleven NOT_RUN assignments remain closed.
No paid follow-up is implied by this result or unused budget. The original
verification-state comparison remains untested.

Evidence: packet root `authorization.json`, `pricing-review.json`,
`local-validation.json`, `attempt/result.json`, `closeout.json`, and the append-only
preparation/execution journals. Source artifacts, the old allocation, and its
public annotation seal were not rewritten. Encrypted continuation remains opaque.
