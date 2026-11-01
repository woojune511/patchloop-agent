# Fixed-request model snapshot comparison

## Material Passport

Date: 2026-10-27. ARS experiment preparation; official=false, claim-ineligible.
Status: PREPARED_AWAITING_EXACT_EXECUTION_APPROVAL. The user requested preparation and execution of
the next experiment. Exact new model/cap approval is required before provider work;
previous paid allocations are closed. Local scripted tests and public seed checks
are separate from live model repair. No private evaluator input is used.

## Question and reason for this comparison

The [annotation comparison](2026-10-27-request-annotation-results.md) supplied full
exception chains and 148 public source lines in every actual input. Thin-schema B
executed a probe and edited, yet retained the tokenizer exception and failed public
regression. A stopped without an edit. Both retained final decision opportunities;
neither exhausted input, output or money. Requiring action commentary is therefore
not necessary for this failure to occur, but one run per arm does not establish an
annotation effect or complete information sufficiency.

Does the registered full GPT-5.4 snapshot resolve this saved failure under the same
request representation and feasible action horizon where mini has failed? A
successful full-model repair would support a model-dependent capability/action
selection explanation within this case. Failure of both could still reflect
missing evidence, tool/API misunderstandings, the one-edit horizon, or stochastic
behavior. It would not show all models are incapable or justify another mandatory
failure-specific gate. This investigation matters because repeated exploration and
unsuccessful first edits have prevented actual repair despite delivered evidence.

## Fixed conditions and intervention

| Condition | A | B |
| --- | --- | --- |
| Snapshot | gpt-5.4-mini-2026-03-17 | gpt-5.4-2026-03-05 |
| Reasoning | xhigh | xhigh |
| Tool annotations | Existing thin wire schema | Identical |
| Initial messages, evidence and tools | Fixed public source/failure packet | Identical |
| Per-arm monetary ceiling | USD 6.60 | USD 6.60 |

Use `model-setting-pair-v1`, Astroid-1333 at
`tasks/dev-train/current-dev20/13/public.yaml`, saved first candidate
`sha256:9914a973952f5bacc86b5e053c60b2ce1aa9d4b412797dca914fe489d26a507c`,
calibration `C:/pt/exception-frame-calibration-v2/calibration.json`, and the unchanged
packet `C:/pt/source-ready-packet-v1/packet.json`. This retains the previously
delivered helper API description; it adds no repair hint or corrected helper example.

One run per arm, A then B, each in a fresh workspace/conversation. Eight normal
responses plus one protocol correction, twelve model actions, one probe request
attempt, one accepted new edit, 40K ordinary/25K correction output, 60K input,
600-second preparation/model deadline and 390-second post-edit host deadline.
The failed probe attempt accounting is unchanged. A valid edit ends model work;
host feedback cannot lead to another edit in this experiment. SDK retries remain
zero; encrypted continuation and default service tier remain fixed.

The credentials are `C:/Users/geonj/Documents/PatchLoop/.env`. The new invocation
cap is USD 8.60. No prior approval is reused. The [official mini snapshot](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
and [full snapshot](https://developers.openai.com/api/docs/models/gpt-5.4) pages confirm
the IDs, Responses/function-calling support and xhigh setting. The [official price
table](https://developers.openai.com/api/docs/pricing), read on 2026-10-27 KST, matches
the existing registered standard short-context prices: mini input/cached/output
0.75/0.075/4.5 and full 2.5/0.25/15 USD per million tokens. Account access is checked
only by the authorized request, with no fallback model or extra paid availability test.

## Why these caps

Keeping the old USD 1.20 would close full-model exploration through price-based
reservation. Even USD 3 could cut the second request's output under maximum usage.
Maximum uncached cost for eight 60K-input/40K-output responses plus one
60K-input/25K-output correction is USD 1.9575 for mini and USD 6.525 for full.
The same per-arm USD 6.60 ceiling funds both. A total USD 8.60 covers their combined
USD 8.4825 bound and leaves at least USD 6.60 at B's start even after A's maximum,
keeping its prepared first-request remaining display accurate. These are ceilings,
not an expected invoice. Actual token counts, caching, histories and cost may differ.

Changing the monetary cap from the previous annotation run means that run is not
the A baseline: a fresh mini arm is required. The new initial A/B payloads must
be equal after replacing only the model ID. Dynamic histories and remaining costs
can diverge. This measures the model snapshot, not reasoning effort in isolation.

## Procedure, outcomes and stop rules

Preparation reads public evidence and constructs requests without provider calls
or credential loading. Both existing Docker images must match their saved IDs;
never pull/build automatically. Revalidate the restored candidate and registered
source anchors before each arm's credentials. Count immediately before dispatch;
admit and settle each call at that arm's price in both its row and shared USD ledger.
Shared prior USD is never repriced. Stop the entire pair on count/transport/billing
uncertainty or unsafe external execution; no retry, replacement or resume.

Primary conditional repair outcome requires the frozen original/control program
to resolve the failure without unexpected exceptions, retain the control and pass
public regression on the resulting candidate. Report these components separately.
No edit, invalid probe, unknown execution, unchanged exception and regression
failure remain distinct. There is no submission or independent task acceptance.
Also record request errors, probe backend starts, first edit, actions, responses,
token/cost/time limits and whether every offered ordinary/correction output stayed
at its declared ceiling. If a bound unexpectedly truncates opportunity, do not
interpret that outcome as a clean model capability comparison.

The same saved seed's public regression baseline was executed locally in the same
existing image: 1,231 passed, 69 skipped, 15 xfailed (8.70 seconds reported by pytest).
The caller failure remains documented by the fixed calibration; regression PASS
does not contradict it. Baseline artifact:
`C:/pt/model-setting-seed-regression-v1/baseline.json`, hash
`sha256:f49afaa1826b43e188135837277bd5ed0cd27cc3f2d8c616fa593c81154e8901`.
It is operator-only and not added to either model context. This follow-up does not
rewrite the older comparison's missing-baseline record.

## Decision limits and validation

One development-exposed candidate, one stochastic run per model and fixed order
support a diagnostic decision only. No significance test, held-out generalization,
benchmark accuracy or automatic production adoption is warranted. Price/cache and
service timing limit cost/latency claims. A positive result motivates confirmation
on more public development cases; a negative result requires tracing the actual
first invalid request or repair premise before another intervention.

The plan and exact command are in `C:/pt/model-setting-plan-v1/manifest.json` and
`run.ps1`; fresh results will be in `C:/pt/model-setting-live-v1/`. Manifest hash:
`sha256:bf640229355b720ad2c86668e776030662efbbc11dd801f0919dd782655feb28`.
Audit hash: `sha256:196e81ec35b22251010f4a66df2cc39e753dd6e4a5d3c987b0515fd0b1c5ea2a`.
Script hash: `sha256:17df9be10d91e02ceca360a8459ce78021cccd975860573ae72c840d188b1d17`.
Implementation hash:
`sha256:c39b9ba5442fea63c34fdd1798bd96d1e9b4dbe349cbc6719115e76b4f9a31af`.
Core runtime remains
`sha256:5753dbef010721c721db788aa01525fc269ad12093b46e45ffc2ffd158c929f3`.

The ten new focused tests passed in approximately nine seconds. They exercise
maximum usage across both 8+1 response paths, no price-induced output/tool closure,
cached and uncached settlement, conserved prior USD, expensive-model admission,
response identity mismatch, manifest binding and exact approval rejection.
The 56 existing diagnostic-owner tests passed (34.902 seconds JUnit); docs 5 passed;
quick 472 passed (107.025 seconds JUnit), including isolated mock evaluation.
Ruff and diff checks passed. JUnit reports are under `C:/pt/model-setting-local-v1/`.
The earlier saved A/B request hashes also matched reconstructed old-profile payloads
exactly; `legacy-request-audit.json` records that check. Model and cost tests use
scripted providers, with no credential/network execution. Only the separate public
seed regression baseline executed a real container. No model repair is yet observed.
