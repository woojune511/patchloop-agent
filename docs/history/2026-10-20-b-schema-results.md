# B first response: schema OFF/ON result

Schema OFF produced a healthy first response. Schema ON reproduced the original
all-zero usage failure. With B's remaining request held fixed, this implicates the
new reproduction parameter schema in this pair. The specific field, constraint
or upstream processing defect remains unresolved. One fixed-order pair does not
establish a deterministic cause or rule out transient/routing effects.

This follows the [HTTP diagnosis](2026-10-20-b1-http-diagnosis.md) and the
[frozen two-request specification](../../.agent/plans/b-first-schema-comparison.md).
The investigation was selected because both previous B starts failed before any
tool action, preventing the intended repair comparison. The earlier local audit
found no request-serialization or selected SDK parsing defect. The new comparison
distinguishes the schema from the other bundled B prompt/state changes.

## Authorization and execution

The user explicitly approved Astroid-1333, project `.env`,
`gpt-5.4-mini-2026-03-17`, one response per condition, at most two generations and
two input counts, and USD 0.315 new spending with unchanged stop rules.

- Manifest: `sha256:0a1bff91733a4a0c4fde3a2b6febf424a02498ea1166ddbe628e65504812f5ea`.
- Specification commit: `90fc500cd70074420a293f404126e5d941e9080b`.
- Pinned B runtime: `52915883604f6fdafc2b1738b73c681870c8a333`.
- Packet: `C:/pt/b-schema34/`; live state: `C:/pt/b-schema34-live/`.
- Exact execution: schema-off then schema-on; two counts, two generations,
  no retry, continuation, replacement, tool action, Docker operation or evaluation.
- xhigh, 25,000 output tokens, 60,000 input-token bound and all other frozen
  request controls remained unchanged. Transition rules and two references were
  preserved; this response-only experiment never exercised a transition.

The immutable preparation manifest retains `paid_authorized=false`; the subsequent
explicit approval is recorded separately in `authorization.json` and the approval
and collection journals. The official standard/global rates were rechecked before
dispatch: USD 0.75 input, 0.075 cached input and 4.50 output per million tokens
([OpenAI pricing](https://developers.openai.com/api/docs/pricing)).

## Observations

| Condition | Exact input count | Reported input / output | First response | Generation latency | Settled cost |
| --- | ---: | ---: | --- | ---: | ---: |
| Schema OFF | 13,758 | 13,758 / 788 | completed; one parsed `search_files` call | 6.568 s | USD 0.0138645 |
| Schema ON | 13,882 | 0 / 0 | incomplete / max_output_tokens; no output item | 2.046 s | UNKNOWN |

Both HTTP responses had status 200. Their selected raw/SDK fields matched with no
changed fields. ON contained explicit zero for input, output, cached, reasoning
and total usage in the HTTP JSON itself. Its SDK error was
`input_token_count_mismatch`; the original failure signature was reproduced.
The collector stopped and closed with `billing_known=false`.

OFF produced one reasoning item and one function-call item, using 516 reasoning
output tokens and 272 other output tokens. Only output types/counts and the tool
name were retained. Arguments, full HTTP bodies and reasoning content were not
saved; no returned tool call was executed. Healthy here means accounted, completed
output with a parsed tool call, not validation of that call's task-level semantics.

| Condition | Request ID | Response ID |
| --- | --- | --- |
| OFF | `req_56e07950853d4094ae3605bea7b687dd` | `resp_00440d0387d6659a016ad6f66f1d8887d08146f3544c698ec1` |
| ON | `req_8258ad3094cd4ec5bab93f131221838a` | `resp_0dbe629c099b2824016ad6f6764c6087d0a09874dea507bf62` |

## Isolation and accounting audit

The actual journaled request hashes and count-payload hashes match the frozen
payloads. OFF removes only `run_probe.parameters.properties.reproduction` and its
required-key entry. Its remaining probe parameters equal the old A schema.
All four input messages, B descriptions, tool order, strict mode, other schemas,
model and request controls are identical. The size difference is 609 bytes and
the fresh counted-input difference is 124 tokens. The treatment bundles schema
contents and their size; it does not isolate a particular grammar feature.

ON's request hash is exactly the historical B first-request hash. Its fresh count
is 13,882 versus the historical 13,888, despite the identical saved payload. This
six-token count variation was not normalized away or assigned to the treatment.
Each generation used its immediately preceding fresh count. The reason for that
historical counting variation is untested; no extra count request was made.

OFF cost decomposes into USD 0.0103185 uncached input, zero cached input,
USD 0.002322 reasoning output and USD 0.001224 other output. Reservations were
USD 0.1228185 OFF and USD 0.1229115 ON, each below the USD 0.1575 row cap and
together below USD 0.315. Reservations are not charges. New settled usage is
USD 0.0138645 plus an UNKNOWN ON bill; the actual new total is unknown.
Both older allocations and their UNKNOWN bills remain separate and unchanged.

`closeout-audit.json` verifies the complete hash chain, ten-event sequence, two
dispatches, no extra attempts, approval binding, request identity, unchanged
output ceilings, independent cost arithmetic and preserved historical artifacts.
`result.json` in the live root equals the final `allocation_closed` payload.
Client cleanup returned before that receipt. The post-run audit made zero provider
calls and read no credentials. The frozen collector/runtime were not modified.

## Decision and remaining question

The declared outcome is **OFF healthy; ON repeats the original signature**. The
schema family is now a more specific failure candidate than the complete B bundle.
B's prompt and initial reproduction-review state alone were not sufficient to
cause this error in the OFF request. The fault still lies upstream of the selected
SDK field parsing; this experiment does not identify provider compiler internals
or prove that the schema violates documented requirements.

The useful next diagnostic question is which reproduction-schema field or
constraint triggers the failure. A narrower test would need a new frozen scope
and explicit paid authorization. No runtime schema removal or other fix was
adopted, and no additional request or full repair experiment is queued.

Source acquisition, evidence use and actual repair success are all NOT_RUN here.
This is live evidence about first-response reliability, not a repair-quality or
general model-capability result. All records remain `official=false` and
`claim_eligible=false`.
