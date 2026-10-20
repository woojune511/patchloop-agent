# HTTP evidence for provider usage failures

The closed [recovery comparison](../docs/history/2026-10-20-evidence-recovery-results.md)
received an incomplete B1 response with all-zero SDK usage despite 13,885 counted
input tokens. Its historical records cannot distinguish HTTP reporting from SDK
decoding. This change adds that observation boundary for future parsed failures;
it does not repair the remote cause, reconcile B1 billing, or authorize another run.

`agent/model.py` uses the SDK's raw-response wrapper for the same single request.
After parsing, a usage failure or incomplete response adds
`usage_evidence.response_diagnostics`. `agent/request_transport.py` provides the
same buffered HTTP response when the adapter uses the bounded async facade. It
clears that reference before the next request and on close. Successful responses
do not get an additional diagnostic record or second JSON decode.

The operator-only projection contains:

- HTTP status and a format-checked `x-request-id`.
- Body availability/size; selected response ID, status and incomplete reason.
- Raw JSON usage counters and their missing/null/type states, before SDK decoding.
- The selected SDK metadata and field paths that changed between the two views.

`matched_selected_fields` means those selected fields agree, not that billing is
known or the whole HTTP response is valid. A changed field yields `different`.
Redacted/invalid values cannot certify agreement; absent/unbuffered/malformed or
over-1-MiB diagnostic bodies are explicitly unavailable. The size bound limits
only this local diagnostic decode, not a request, context, output or execution
budget. No stream is read and no additional API request is issued by extraction.

Unknown labels/headers, free-form errors, tool arguments, source text, encrypted
reasoning, reasoning summaries and full HTTP bodies are not retained in this
projection. It follows the existing usage-evidence journal/terminal/recovery path
and is never added to solver inputs or history-search evidence. No SDK parse
exception or missing response is reclassified as a parsed usage result.

Accounting still uses the existing SDK-based validation. Count/billing uncertainty
stops all repetitions; zero SDK retries, request payloads, segment transitions,
two references, admission caps and execution limits are unchanged. Read-only
recovery preserves the diagnostic without dispatching another request.

Focused checks: `tests/test_provider_usage_diagnostics.py`. Real SDK clients use
`httpx.MockTransport`; fixtures distinguish absent/null/zero fields, deliberately
changed decoded values, redaction, unavailable bodies, bounded transport reset,
and crash/terminal recovery. A numeric-string fixture confirmed that the pinned
SDK preserves that invalid type; the changed-value case is explicitly synthetic.
Use `tests/test_episode_requests.py` for the shared transport's timing boundaries
and `tests/quick.txt` for the fast suite and isolated mock evaluation. Paid execution
is not part of this validation; the old raw response cannot be reconstructed.
