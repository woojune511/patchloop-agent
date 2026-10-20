# Provider rate-limit diagnosis

Date: 2026-10-03. Read-only investigation and offline SDK fixtures; no provider calls.
Follow-up to the [stopped seeded diagnostic](2026-10-03-selected-tests-diagnostic-result.md).

## Question and observed evidence

The user requested the cause of A1's first-generation `RateLimitError`. Distinguishing
a temporary request/token limit from credit or spending limits matters because their
remedies differ. The closed two-run allocation, uncertain billing and unattempted B1
remain unchanged. No retry or model substitution was attempted.

At investigation HEAD `ec67d44d0dcf52fa602b059d610b5d93dde3e2ca`, the A1 journal
`C:/pt/stlive01/A1/runs/run_dev_4daeb0d826594696.jsonl` contains one completed input
count, one generation dispatch and the terminal exception class. It contains no
generation HTTP status, provider error code/type, request ID or usage receipt.
The original message is `provider dispatch failed: RateLimitError`.

Installed OpenAI SDK 2.47.0 maps HTTP 429 to `RateLimitError`. The runtime uses the
official API base, `httpx.Client(trust_env=False)` and `max_retries=0`. Thus HTTP 429
classification is supported by the SDK mapping; an exact quota subtype is not.
A successful input count does not establish available generation quota or credits.

## Why the record cannot distinguish the cause

`patchloop/dev/runner.py` catches generation exceptions after dispatch and retains
only `type(exc).__name__` in the terminal message. `OpenAIResponsesAdapter.execute_request`
lets the original SDK exception propagate from `responses.create`; the information
is discarded at the runner catch, rather than missing from the SDK exception design.

By contrast, `patchloop/agent/count_diagnostics.py::input_count_error_metadata`
already extracts bounded, allowlisted HTTP status, code, type and request ID for
count failures, without storing free-form errors or credentials. Generation dispatch
does not use that path. This is a concrete observability gap, not evidence that it
caused the provider to reject the request.

Two offline `httpx.MockTransport` fixtures returned HTTP 429 with respective codes
`rate_limit_exceeded` and `insufficient_quota`. Both produced the same exception-class
message used by the runner. The existing safe extractor distinguished both codes
and retained HTTP 429. No network connection, real credential or provider request
was used. These fixtures demonstrate information loss; they do not identify the
actual failed call's code.

## Official meaning and remaining access

[Official OpenAI error documentation](https://developers.openai.com/api/docs/guides/error-codes#api-errors),
checked on 2026-10-03, distinguishes temporary request limits, traffic ramp limits,
exhausted prepaid credits, organization/project spend limits and organization usage
limits within HTTP 429. It directs billing diagnosis to `error.code`; `error.type`
may broadly say `insufficient_quota`. Retrying a billing/credit limit does not restore
access. The exact failed-call subtype cannot be recovered from the local journal.

The read-only [organization limits page](https://platform.openai.com/settings/organization/limits)
redirected to login and displayed a human-verification challenge in the available
browser. Account limits and credit balance were not read. The user was asked to
complete human verification/login; no challenge was solved or account setting changed.

## Decision

Actual provider cause remains unresolved pending authenticated account evidence.
Do not relabel the original bill as zero or infer a model-quality failure. If future
generation error logging is changed, preserve bounded safe metadata while retaining
the current no-retry, stop-all and unknown-billing behavior. Such a change cannot
recover this historical response; no runtime change was made in this investigation.
Documentation layout/link checks and `git diff --check` passed.
