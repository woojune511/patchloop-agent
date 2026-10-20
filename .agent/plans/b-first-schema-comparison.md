# B first response: reproduction schema only

Status: provider-free preparation; paid execution is NOT_RUN and not authorized.
The two older allocations stay closed, including both UNKNOWN B1 bills.
This diagnostic neither resumes those allocations nor measures repair success.

## Question and fixed requests

The [B1 diagnosis](../../docs/history/2026-10-20-b1-http-diagnosis.md) located the
latest all-zero usage response before SDK field parsing, but did not identify its
upstream cause. Test the narrow question: with B's complete first input held fixed,
does removing its new probe parameter schema change that first-response failure?
This two-condition check deliberately replaces the earlier proposed four-cell
schema/prompt factorial. A transient server/routing failure remains an alternative.

Use the actual first request from closed allocation 32, B1, with canonical hash
`sha256:798774be66fbda662db93dd8cf95f077528e722e5f38a482644b197906e0f9d8`.
Its public audit export must agree with the hash-chained original dispatch journal.
No repaired source, evaluator content, diagnostic hints or prior output enters it.

| Condition | One change from that saved B request |
| --- | --- |
| schema-off | Delete `tools[4].parameters.properties.reproduction` and its entry in `tools[4].parameters.required` |
| schema-on | None; the saved B request is unchanged |

The removed schema's remaining `run_probe.parameters` must exactly equal the old
A probe parameters. All seven tools, strict mode, descriptions, B system prompt,
initial reproduction-review state, message order and every other request field
stay identical. Do not normalize away segment IDs or elapsed-time values. Request
hash and count-request hash bind the bytes actually dispatched.

Keeping B's prose is intentional: schema-off still contains descriptions of the
reproduction capability whose parameter was removed. Editing that prose would
confound this check. Consequently this is a transport/schema diagnostic; tool
argument quality under that mismatch is not repair-quality evidence. It isolates
the presence of the schema family, including its size, not an individual field,
regex, provider compiler component or token-count effect.

## Exact proposed allocation and budget

- Task identity: `tasks/dev-train/current-dev20/13/public.yaml`, Astroid-1333,
  dev-train, base `d2a5b3c7b1e203fec3c7ca73c30eb1785d3d4d0a`.
- Exact model: `gpt-5.4-mini-2026-03-17`; xhigh, maximum output 25,000 tokens.
  Standard/global Responses, `store=false`, `tool_choice=required`, parallel
  tools enabled, encrypted-output include and disabled truncation remain fixed.
- Credential path for a later authorized execution:
  `C:/Users/geonj/Documents/PatchLoop/.env`; preparation does not read it.
- One independent first response per condition: **at most two generation calls**,
  **at most two input-count calls**, zero tool actions or follow-up generations.
  Serial order: **schema-off, then schema-on**. No adaptive order or added repeat.
  Off comes first because repeating the previously failing on condition first
  could stop collection before the new control. Order/caching effects remain a
  limitation; this is a screening pair, not a failure-rate estimate.
- Count immediately before each generation, using the existing adapter's exact
  count fields. Preserve 60,000 input tokens, 1,048,576 request bytes and 25,000
  output tokens. Do not reduce the output ceiling to fit a smaller cost cap.
- New invocation cap **USD 0.31500000**; each request at most **USD 0.15750000**.
  The [official standard prices](https://developers.openai.com/api/docs/pricing),
  reviewed 2026-10-20, are USD 0.75 input, 0.075 cached input and 4.50 output per
  million tokens. Conservative reservation per request is
  `60,000 * 0.75 / 1,000,000 + 25,000 * 4.50 / 1,000,000 = 0.1575`.
  No cache discount is assumed for admission. Recheck these rates on execution day.
  The original on request counted 13,888 tokens, giving a historical reservation
  of USD 0.122916; the new off count is unknown until authorized counting.
- One 1,800-second invocation deadline; existing bounded waits of 30 seconds for
  counting, 300 for generation, five for local client cleanup. SDK retries zero.
  No retry, resume, replacement, top-up, paid judge, Docker operation or evaluation.

Original agent transition policy `result-or-size-v1`, two references, retained
source limit 24,000 characters and existing execution limits remain unchanged.
This first-response-only collector never reaches a transition, mutation, probe,
continuation or evaluator. It does not use the remainder of the agent's 40-call,
100-action or four-edit allowance. Encrypted output is not decoded or persisted
and never becomes another model input; its bytes cannot cause a handoff here.

## Stop and observation rules

Use the existing bounded SDK transport and usage parser from B runtime
`52915883604f6fdafc2b1738b73c681870c8a333`. Inspect both responses with the same
operator-only HTTP projection. Retain status, request/response IDs, latency,
body size, raw/SDK selected usage fields, mismatch labels, output types/counts,
tool names, conservative reservation and settled cost where known. Do not save
full HTTP bodies, tool arguments or reasoning. Returned tool calls are not executed.

The primary failure signature is `incomplete / max_output_tokens`, explicitly
zero input/output/total usage despite a positive exact count, and no output item.
A healthy first response means completed status, matched valid usage, exact model,
no adapter error and at least one parsed function call. This does not certify its
arguments against task state or imply source acquisition or a correct repair.
Keep HTTP/schema rejection, count error, other incomplete output and usage error
as separate observations; do not collapse them into the original signature.

Stop all remaining requests on count, transport, billing or cleanup uncertainty.
Also stop after any nonhealthy first response, even if its billing is settled.
If schema-off fails, schema-on is NOT_RUN: do not spend an extra call to complete
the table. Unknown billing stays UNKNOWN; zero reported usage is not zero cost.
The cap is an admission limit, not a promise that an anomalous provider bill is
known or reconciled. Previous settled and unknown costs remain separate.

| Observed pair | Supported decision |
| --- | --- |
| Off healthy; on repeats original signature | Schema presence is implicated in this pair; consider a narrower field/schema investigation, without claiming deterministic cause |
| Both healthy | Original failure not reproduced; no schema-removal adoption or full-repair restart follows automatically |
| Off nonhealthy; on NOT_RUN | Schema removal was insufficient in this request; the paired causal question remains unresolved |
| Off healthy; on fails differently | Report the new failure class; it is not reproduction of the old symptom |

No outcome justifies a repair-success, retrieval-benefit or general model-quality
claim. A further paid comparison needs new evidence and its own exact approval.

## Prepared artifacts and validation

Packet: `C:/pt/b-schema34/`; future live state: `C:/pt/b-schema34-live/`.
`schema-off.json` and `schema-on.json` are frozen public requests. `pair-review.json`
records the two changed paths, full input identity and original journal binding.
`execute.py` has separate validate/collect modes; collect requires a new exact
human authorization bound to `manifest.json`, this task/model/credential path,
one repeat per condition, two count/generation limits and the USD 0.315 cap.
No authorization file is created during preparation. A fresh exclusive state
directory prevents restarting or replacing a partially executed allocation.

Focused real-SDK MockTransport controls cover request identity, healthy responses,
zero usage in either position, count rejection, oversized count, transport timeout,
settled incomplete output, full-cap settlement and rejected old/missing approval.
They use a dummy key and prohibit external network and credential access. These
tests do not simulate the provider's schema compiler or reproduce its server error.
Documentation layout and Ruff are checked; the runtime is unchanged, so no new
whole-repository test result is claimed. The manifest binds committed specification,
pinned runtime, SDK versions, payloads, collector and local validation receipts.
