# B1 first-response HTTP usage diagnosis

The failure is upstream of the SDK's selected response-field parsing. Saved
requests, local serialization and response controls reveal no reproducible client
defect that explains the zero usage. The leading unresolved question is whether
B's initial request, particularly its changed tool schema, triggers a serving or
schema-processing problem. That is a hypothesis, not an established provider bug
or identification of the responsible field.

This follows the [closed recovery allocation](2026-10-20-recovery-http-results.md).
No paid request, real input-count request, credential read, Docker operation,
solver action or evaluator run was performed. Runtime code, limits, two references,
transitions, both closed allocations and their UNKNOWN billing remain unchanged.

## Observed failure and alternative explanations

The two closed allocations show the following first-response observations. All
four requests used `gpt-5.4-mini-2026-03-17`, xhigh and an output ceiling of 25,000.

| Allocation / row | Counted input | Returned input / output | Status | Dispatch to receipt |
| --- | ---: | ---: | --- | ---: |
| 28 / A1 | 13,400 | 13,400 / 762 | completed | 7.423 s |
| 28 / B1 | 13,885 | 0 / 0 | incomplete / max_output_tokens | 1.710 s |
| 32 / A1 | 13,402 | 13,402 / 909 | completed | 5.679 s |
| 32 / B1 | 13,888 | 0 / 0 | incomplete / max_output_tokens | 1.358 s |

A1 produced 39 and 28 accounted model responses respectively, with no provider
error. Both B1s stopped on their first response with no tool call. These are two
exposed observations in the same order, not randomized evidence of a deterministic
schema fault. An upstream transient or routing difference remains possible.

Only allocation 32 has the new raw HTTP projection: HTTP 200, explicit integer
zero for input/output/cached/reasoning/total usage, and matching selected SDK
values. Its HTTP response ID is distinct from A1's. The original full response
body was not persisted; the 113,739-byte size does not reveal its other contents.
Older B1 lacks HTTP evidence and cannot be retroactively assigned the same layer.

| Explanation | Evidence and disposition |
| --- | --- |
| Client/SDK invented zero for missing usage | Contradicted for new B1: HTTP JSON already contains explicit zero counters; no selected-field change after parsing |
| Counted one payload but sent another | No observed discrepancy: saved generation hashes match bound requests; local SDK serialization reproduces them exactly |
| B used another model, smaller output cap or stale reasoning | Contradicted by saved first requests: same controls, no prior reasoning items or continuation |
| `.env` endpoint/proxy override | Not supported by owning code: exact-key loader, fixed official API URL, `trust_env=False`; credentials were not reread for diagnosis |
| Context/request limit exceeded | Not supported: B has 13,888 counted input tokens and a 74,850-byte request; configured input/request limits are 60,000/1,048,576 |
| Ordinary output exhaustion | Not established: status says max_output_tokens, but returned input and output usage are zero; elapsed time alone is not proof of server work |
| Unsatisfiable or structurally invalid new schema | No violation found in the checked documented subset; nullable and concrete reproduction declarations are satisfiable locally |
| B request interacts with upstream schema/serving behavior | Still plausible; both B starts fail while A works, but no server-side field-isolation test or internal error record exists |

The [model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
documents this snapshot, xhigh, a 400,000-token context window and 128,000 maximum
output. Input plus the 25,000-token allowance is far below that context window.
The [reasoning guide](https://developers.openai.com/api/docs/guides/reasoning#allocating-space-for-reasoning)
explains that output exhaustion can precede visible text and still incur reasoning
cost. It does not establish that an all-zero usage response is a valid settled
bill. Raising the context/output budget is therefore not justified by this record.

## Actual request and schema inspection

The first dispatched public wire hashes match their recorded generation hashes.
The initial inputs contain four text messages and no encrypted reasoning item.
Actual A/B inputs differ at exactly the six frozen locations: system prompt,
empty reproduction review, two tool descriptions, the probe's reproduction schema
and its required-key list. Other controls are equal, including `tool_choice=required`,
parallel tools, `store=false`, encrypted-output request, standard tier and disabled
automatic truncation. B adds 486 counted tokens and 2,683 request bytes.

Actual requests differ from the provider-free initial captures only in two shared
remaining-time fields: 1,470 to 1,467 solver seconds and 1,800 to 1,797 total seconds.
This is elapsed preparation time, identical in A and B; it changes no limit or
assigned contrast. No additional difference was normalized away.

Both requests offer seven strict tools. The changed `run_probe` schema has 44
object properties versus A's 38; total properties across all seven schemas are
266 versus 260. Maximum object depth is four in both. Object required-key sets
match their properties, `additionalProperties=false` is present, root objects
are objects, and the inspected schemas stay below the documented property,
nesting, enum and string-size bounds. No unsupported composition keyword was found.
The nullable reproduction branch is explicit, and a concrete `x.y` entrypoint
declaration validates against the owning Pydantic model. A's successful first
`search_files` action has the identical parameter schema in B, so B is not forced
to produce a reproduction declaration as its first action.

These checks follow [strict-mode requirements](https://developers.openai.com/api/docs/guides/function-calling#strict-mode)
and the [supported schema subset](https://developers.openai.com/api/docs/guides/structured-outputs#supported-schemas).
They are not a replacement for provider grammar compilation. In particular,
Python regex compilation does not certify the provider's regex implementation.
No basis was found to disable strict mode or remove accounting validation.

## Local SDK controls and evidence boundaries

The installed OpenAI SDK is 2.47.0 and HTTPX is 0.28.1. The actual A/B first request
bodies were passed through the real bounded async SDK facade with MockTransport,
a dummy key and external socket/DNS access blocked. Windows asyncio's internal
loopback socketpair was allowed. Four controls ran: A/B crossed with reconstructed
zero usage or a synthetic healthy response containing the saved A search call.
Eight mock HTTP visits covered count and generation; no real provider was contacted.

For both arms:

- The count body exactly matched the adapter's selected count fields; the generation
  body exactly matched the saved request, including model/tools/output ceiling.
- The healthy response produced one parsed tool call with no error. No tool executed.
- Explicit zero usage produced `input_token_count_mismatch`, no accepted tool call,
  and matching HTTP/SDK diagnostics. The existing stop was preserved.

The model adapter, request transport, usage diagnostics and exact-key loader have
identical bytes in the pinned A/B worktrees and the inspected root runtime. The
fixed SDK endpoint is `https://api.openai.com/v1`; process environment proxy settings
are ignored by the HTTP client. This does not prove what occurred inside OpenAI's
infrastructure or reproduce the remote failure locally.

Evidence root: `C:/pt/b1-http-diagnosis33/`, including `result.json`,
`analyze_v3.py` and hash-chained `run_dev_b1httpdiagnosis33`. Protected original
logs, manifest, result and unrelated `AGENTS.md` bytes were checked unchanged.
Two local audit-fixture failures are retained: an overstrict capture-equality
assumption omitted shared elapsed-time fields, and an all-socket guard blocked
Windows event-loop IPC before any mock HTTP visit. Their corrected local audit
does not relax the solver, accounting or experiment gates.

Eight focused usage/transport regression checks and five documentation checks
passed, as did Ruff and `git diff --check`. These supplement the four local SDK
controls; they are not a live reproduction or a new full-suite result.

## Decision

No runtime fix or budget increase is supported yet. Preserve the hard stop and
both UNKNOWN billing entries. The next discriminating check, if separately
authorized, should be a small first-response request comparison rather than
another twelve full repairs: cross the original/new probe parameter schema with
the remaining A/B input bundle (prompt, descriptions and initial reproduction
review), while fixing every other field. This would test the schema family
against the other input changes; it would still not
identify an individual regex/field without a later supported narrowing step.
Those requests have not been dispatched or funded, and the old allocation cannot
resume. The recorded HTTP request ID can support a provider-side investigation;
no message or diagnostic payload has been sent to another party.
