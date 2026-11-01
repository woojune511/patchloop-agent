# Helper follow-up: first original reproduction with the full model

Status: sealed and locally validated; paid collection NOT_RUN. Official=false.
The earlier model-pair allocation is CLOSED. This plan needs its own exact cap.

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run
- Origin Date: 2026-10-28
- Verification Status: UNVERIFIED for actual model and target execution
- Version Label: helper_first_reproduction_v1

## Question and intervention

The [previous full-model request](2026-10-28-first-reproduction-model-results.md)
was admitted, but `expected_exceptions=(SystemExit,)` caused helper construction
to fail before either target call. The [local fix](2026-10-28-helper-system-exit-fix.md)
accepts that already-captured exception family and makes its API explicit.
Test whether a fresh model request now executes the original call and reproduces
the public F0010 failure. Selecting full follows the concrete failed trajectory;
it is not a model-superiority claim or a new mini/full comparison.

Use the same pre-event-65 public checkpoint from run_dev_3e21775752a54cae.
Keep the previous long description and replace only its exception-contract
paragraph. Use the fixed v8 host; all other request fields match prior B exactly.
Remove opaque reasoning and the stale model-priced completion forecast as in the
previous model pair. Do not supply its generated code, response, chosen observation,
patch or private evaluator information. This is a fresh public reconstruction,
not replay of the previous v7 program or a clean-start solve.

| Condition | Value |
| --- | --- |
| Task | dev-train/current-dev20/13, Astroid-1333 |
| Model / effort | gpt-5.4-2026-03-05 / xhigh |
| Credential file | C:/Users/geonj/Documents/PatchLoop/.env |
| Order / repeats | B only / once |
| Input / normal / correction output | 60K / 40K / 25K tokens |
| Remaining model / tool slots | 16 / 34 |
| Remaining solver / evaluation reservation | 1,903 / 390 seconds |
| Proposed invocation-wide cap | USD 4.41415320 |
| Endpoint | First settled probe, explicit stop, or ordinary terminal failure |

Ordinary bounded protocol correction may precede the first settled probe. A host
request rejection also ends the diagnostic. There is no feedback continuation,
repair, visible regression, submission or isolated evaluation in this scope.
Count immediately before dispatch, retain zero SDK retries and stop on count,
transport, billing, execution or cleanup uncertainty. No automatic retry/resume,
image pull/build or Docker startup. Monitor process and journals at bounded
intervals; the runner enforces the inherited active deadline.

## Outcomes and interpretation

Record completed request, host admission, `target_started`, capture completeness,
actual same-call F0010, baseline declared-failure match, desired-result mismatch,
and processing coverage separately. Verify public issue/call/fixture correspondence;
an outer successful tool receipt or setup PASS is not target execution.
The desired observation must exclude a directory no-op. W0611 from a different
direct-file control alone does not prove original-directory processing. Baseline
failure can lack positive processing, but the desired-result design must require it.

If the helper passes but another stage fails, report the new failure stage without
calling reproduction complete. One fresh stochastic run cannot isolate runtime
versus wording effects or establish reliable repair, clean-start completion,
model superiority or held-out generalization. No default adoption is planned.

## Preparation and authorization

Preparation baseline: c5825ad7cc6b6851e296d5cc0bd6a8035f7ecf41.
Use `diagnostics.first_reproduction_comparison --comparison helper` with inert
providers before collection. Seal the exact request, runtime/implementation hashes,
new cap and fresh external roots. Read-only source/image/dependency preflight must
be ready before dispatch; it checks credential existence/path without reading it.

Plan root: `C:/pt/helper-first-reproduction-plan-v1`.
Reserved result root: `C:/pt/helper-first-reproduction-run-v1`.
Exact command: `& 'C:/pt/helper-first-reproduction-plan-v1/run.ps1'`.

The sealed manifest hash is
`sha256:eb979db8aa9020c72b211ded93eb0a2ede59a538af86b928e13ddb5a3e258ba8`.
Its runtime is
`sha256:8deec9e3573e699515c346aabcfcb5267c78f4cb85752262d8db3e99f7c3e60d`;
diagnostic implementation is
`sha256:74564874e4f84c935486fbda6bda2e8f28f1c54ae7e5cd52a95d3cf7e33311da`.
`run.ps1` executes the single B collection with that manifest and USD 4.41415320;
`validate.ps1` passed with zero provider or target calls.

The owner suite covered 14 cases in 23.203 seconds: 13 passed and one new test
supplied an already-projected input to a checkpoint-only helper. That fixture was
corrected; its targeted rerun passed in 2.917 seconds. This is split validation.
Quick passed all 594 cases in 232.079 seconds, including both existing isolated
mock evaluation cases. No separate mock repetition was necessary. Ruff and five
documentation checks passed. The actual-checkpoint inert rehearsal
admitted full 40K then 25K output at synthetic 60K uncached input on each call.
Its USD 1.275 simulated spending is not an API charge. No credential was read.

Independent artifact review confirmed that the actual previous B first request
and the new request have identical public inputs, parameter schemas and all other
fields; only the exact exception paragraph changes (8,958 to 9,230 characters).
The unchanged public-input hash is
`sha256:0a7bb50b41ed345bdfcfaed414e689bfaf9fbc64f56e86155ba1d2f7fae62ac9`.
The first-settled-probe hook persists the result and stops before another response.
The result root remains absent; these checks establish readiness, not reproduction.

Diagnostic implementation commit: `bf70d22f`. Read-only environment preflight is
READY: task/runtime, prepared source, dependencies and exact local probe image
identity all pass. `preflight.json` and the preparation journal retain that receipt.
No image was pulled/built and Docker Desktop was not started. Collection will
repeat admission checks and will stop rather than use changed prepared inputs.
The preparation journal hashes the four JUnit files and the independent review
receipt. These remain separate from the currently absent paid result directory.
