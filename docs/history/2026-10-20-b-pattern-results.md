# B first response: removing the entrypoint pattern

Removing only `entrypoint.pattern` produced a healthy first response with valid
usage accounting. The reproduction object and all its other constraints remained
present. Together with the earlier schema OFF/ON pair, this narrows the leading
failure candidate to that regex keyword or its interaction with the remaining
schema. It does not identify the provider's internal failure mechanism.

This follows the [field audit](2026-10-20-b-schema-fields.md) and the
[frozen one-call specification](../../.agent/plans/b-pattern-check.md). Repeated B
failures before any tool execution prevented the intended repair comparison. The
diagnostic was selected to isolate one field instead of removing the reproduction
feature or changing the model's reasoning/context budget.

## Fixed scope and result

The user approved manifest `551eb7b98083`, Astroid-1333, project `.env`,
`gpt-5.4-mini-2026-03-17`, one generation, one input count and USD 0.1575 new
spending. The exact approval and same-day price review are recorded separately
from the immutable preparation manifest.

- Full manifest: `sha256:551eb7b98083a2344a72e2792d05be9b29d323429bbf8089fe833a41cb4c7d5b`.
- Specification commit: `ba70fa80f9eb8a080bfcd74943180dfbf402d159`.
- Pinned B runtime: `52915883604f6fdafc2b1738b73c681870c8a333`.
- Packet: `C:/pt/b-pattern36/`; live state: `C:/pt/b-pattern36-live/`.
- Task: `tasks/dev-train/current-dev20/13/public.yaml`, dev-train.
- Exactly one count and one generation; no retry, replacement, continuation,
  tool execution, Docker operation, evaluation or additional condition.
- xhigh, 25,000 output tokens, 60,000 input-token ceiling and all other request
  controls stayed fixed. Transition rules and two references remain unchanged;
  neither a transition nor a repair loop was exercised.

The first two rows below are the saved [allocation-34 pair](2026-10-20-b-schema-results.md),
not additional calls in this allocation.

| Condition | Counted input | Reported input / output | First response | Generation time | Settled cost |
| --- | ---: | ---: | --- | ---: | ---: |
| Entire new schema OFF, historical | 13,758 | 13,758 / 788 | completed; `search_files` | 6.568 s | USD 0.0138645 |
| Original schema ON, historical | 13,882 | 0 / 0 | incomplete / max_output_tokens; no output | 2.046 s | UNKNOWN |
| Only entrypoint pattern removed, new | 13,860 | 13,860 / 955 | completed; `search_files` | 7.789 s | USD 0.0122733 |

The new response was HTTP 200, with selected raw HTTP and SDK fields matching.
Reported input exactly matched the immediately preceding count. Output contained
one reasoning item and one parsed function-call item; arguments and reasoning
content were not saved. The function call was not executed, so its task-level
semantics and usefulness remain untested.

Request ID: `req_7f6e1d0bd1b7464aa95a0de1e0ed6f75`.
Response ID: `resp_014d452233f93b60016ad6fa2117dc87d0a3519e16ed0295e3`.

## Isolation and accounting

The only deleted JSON path was
`/tools/4/parameters/properties/reproduction/anyOf/0/properties/entrypoint/pattern`,
whose value was `^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+$`. All fields, required keys,
length bounds, nullable union, strict mode, B prose and remaining controls were
identical to the saved original B request. Host `Intent` validation was unchanged.

The request hash was
`sha256:e6875fc12fe6c8a859a71413b2921c868a008e30a67528ef26c02e358da774aa`;
the count-payload hash was
`sha256:302a6bd7ae3c082434bebb687af06ad0211e9d90210caee5f2fa1ade6c4b1b3a`.
Removing the keyword reduced the canonical payload by 49 bytes. The fresh count
was 22 tokens below historical ON, but historical identical-request counts had
already varied by six tokens. This is not a same-time token-count measurement.

The conservative reservation was USD 0.122895, below the approved USD 0.1575.
It retained the full 25,000 output-token ceiling. The settled new cost was
USD 0.0122733:

| Component | Tokens | Cost, USD |
| --- | ---: | ---: |
| Uncached input | 10,276 | 0.007707 |
| Cached input | 3,584 | 0.0002688 |
| Reasoning output | 516 | 0.002322 |
| Other output | 439 | 0.0019755 |

Rates were USD 0.75 input, 0.075 cached input and 4.50 output per million tokens
([official pricing](https://developers.openai.com/api/docs/pricing)). Prior
allocations and their UNKNOWN bills remain separate and unresolved; this new
healthy response does not settle those bills. Cache and output-length differences
also prevent interpreting the cost difference as a schema-efficiency improvement.

The provider-free `closeout-audit.json` verifies the complete six-event hash chain,
approval/pricing binding, exact generation/count identities, one-field deletion,
unchanged ceilings, independent cost arithmetic and preserved historical files.
The live `result.json` equals the `allocation_closed` payload, written after
client cleanup returned. No additional provider call or credential read occurred
during the audit. The frozen runtime, collectors, manifests and previous reports
were not modified. Preparation had five passing no-network controls; result-doc
validation and Ruff also passed. No runtime change warranted a full-suite rerun.

## Decision and remaining uncertainty

The expected positive outcome occurred: preserving the feature while omitting
one provider-facing constraint yielded a normal first response. The remaining
reproduction object, nullable union, required fields and length bounds were not
sufficient to reproduce the failure in this call. The evidence now favors a
schema-processing interaction over an agent task-judgment failure for this B
startup error. The saved zero usage was already present in the HTTP response,
so weakening the SDK usage check would conceal the accounting uncertainty.

This remains one new observation against a historical control. Time/routing
effects are not separated; a future failure without the pattern or success with
the exact original schema would weaken a deterministic-pattern explanation.
The test does not distinguish `\w`, the noncapturing group, repeated dotted
segments, or their interaction with length limits. Local Unicode differences
from the field audit do not establish a provider engine or a concrete bad value.
The observed pattern is not proof that the documented `pattern` keyword is
generally unsupported or that the provider grammar compiler is the failing part.

The smallest supported repair candidate is to omit this regex from the
provider-facing reproduction schema while retaining the exact host validator.
That would preserve rejection of invalid declarations locally; it still needs
focused validation of the schema projection and invalid-input behavior. An ASCII
rewrite or broader removal of schema constraints has not been tested. No runtime
workaround was adopted in this diagnostic, and no further paid request is queued.

Source acquisition, evidence use and actual repair success are all NOT_RUN.
The allocation is closed, `official=false` and `claim_eligible=false`; this result
supports a targeted reliability fix candidate, not an agent-quality claim.
