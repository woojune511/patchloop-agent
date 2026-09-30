# Proposed Darts repair exercise

Prepared 2026-09-30. Provider-free preparation is complete. This proposal does not
authorize a live invocation; the preceding MontePy allocation remains closed.

## Purpose and exact proposed scope

Task: `tasks/dev-train/original-darts-3065/public.yaml`, task ID
`original-darts-3065`, version 1, dev-train; upstream base
`6bfda77e4afc9c123740ab6cc52ca39a7ab92d84`.

The public issue concerns StaticCovariatesTransformer handling OneHotEncoder's
dropped categories, causing an output-column/index mismatch. This exercises data
transformation shape handling, distinct from MontePy's property-reset lifecycle.
The task previously appeared in the original-input pilot, so this is a fresh
development invocation on an exposed task, not an unseen/held-out evaluation.
No previous patch, trace, working notes or evaluator material enters agent input.

- Model: `gpt-5.4-2026-03-05`, xhigh, 25,000 desired output tokens.
- Credential file: `C:\Users\geonj\Documents\PatchLoop\.env`; existence and ignore
  status checked without reading its value.
- One fresh invocation, USD 3.00 invocation-wide cap, 1,800 seconds, 40 model calls,
  100 tools and four accepted edits. No automatic repeat, retry or continuation.
- Policies: segmented-v1, result-or-size-v1, brief-v1, probes enabled with policy
  none, repair-recheck, protected-v1 inspection, per-call-v1 cost admission.
- Edit area `darts/**`, excluding tests and private material; four files / 1,000
  diff lines maximum, no dependency changes. Existing public API permission retained.
- Stop on count, transport, billing or cleanup uncertainty; zero SDK retries.
  No added funding, task replacement or image acquisition follows automatically.

## Prepared inputs

New source descriptor:
`C:\pt\preparations\darts-next-repair-20260930-v1\prepared-source.json`.
Descriptor hash:
`sha256:04c72cde3e859bc3391c75f478ddc06b72e05e6366747cb6a711392fd20fa5ad`.
Source content hash:
`sha256:eca827fcdecea1d6478814728090f82dc656081e45ab73a86d5af6759ae155e5`.

Reused, revalidated public dependency descriptor:
`C:\pt\prepared\original-darts-3065-probe-0927-v5\prepared-probe-dependencies.json`.
Descriptor hash:
`sha256:b1a5ba1cfd17fc430b2cdf3cf87af69d27271782761390659f593218566121b0`.
Content hash:
`sha256:b24b562bd5705077b301a126e1f5104b8c071b7af7a067f2903108321e2ee899`.
Source root `darts`, existing installed-byte cap 768 MiB. No dependency resolution,
download or cap increase occurred. Probe execution retains its existing sandbox
resource limits; the installed-byte cap is not execution memory.

Existing evaluator image:
`sha256:ce882b8e668e4a6d5452c6612cd5dc9227839f21efc3bde67437603e4d14b7d0`.
Existing clean probe image:
`sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de`.
Docker was already running; no start, pull or build occurred.

## Executed preparation and limits

Doctor and task validation passed. The source copy remained unchanged. Normal
isolated probe execution imported Darts and constructed the public issue's data
with deterministic values. With scikit-learn 1.9.1:

| Case | Observed base behavior |
| --- | --- |
| No drop, three categories | Success, static covariate shape [3, 3] |
| drop="first", three categories | IndexError: index 2, axis size 2 |
| drop="if_binary", two categories | Success, static covariate shape [3, 1] |

The first-drop issue is reproducible; the one binary case does not establish all
if_binary behavior. This operator diagnostic neither narrows the public task nor
supplies a repair hint to the later coding agent.

The unchanged registered public regression completed: 8 passed, exit 0, full
output, 6,651 ms. The probe completed in 39,458 ms including preparation; the entire
recorded preparation took 108.867 seconds. Neither receipt reports truncation,
timeout or cleanup failure. Public PASS already occurs on the defective base and
does not prove the requested repair. Private acceptance/safety are NOT_RUN here.

Evidence: `C:\pt\analyses\darts-preparation-20260930-v1`, append-only dev-run-v1
journal `run_dev_dartspreparation`, four events binding the frozen program,
descriptor identities and immutable receipts. Model/provider calls: zero.

## Command for a subsequently authorized invocation

Revalidate clean tracked runtime/task inputs, both descriptors and image identities
at dispatch. Use the fresh external root below; preserve old pilot evidence.

```powershell
$env:PATCHLOOP_STATE_ROOT = 'C:\pt\runs\darts-next-repair-20260930-v1'
uv run --locked patchloop dev `
  --provider openai `
  --task tasks/dev-train/original-darts-3065/public.yaml `
  --model gpt-5.4-2026-03-05 --reasoning-effort xhigh --max-output-tokens 25000 `
  --context-policy segmented-v1 --segment-boundary-policy result-or-size-v1 `
  --planning-policy brief-v1 --enable-probes --probe-policy none `
  --repair-recheck --repair-inspection-policy protected-v1 `
  --completion-cost-policy per-call-v1 `
  --prepared-source C:\pt\preparations\darts-next-repair-20260930-v1\prepared-source.json `
  --prepared-probe-dependencies C:\pt\prepared\original-darts-3065-probe-0927-v5\prepared-probe-dependencies.json `
  --env-file C:\Users\geonj\Documents\PatchLoop\.env `
  --max-cost-usd 3.00 --repeat 1
```

Judge the actual patch, public regression, isolated acceptance, safety, cost and
time separately. A failure should lead to a concrete causal diagnosis; a successful
run does not automatically justify another feature or experiment. All work remains
official=false and claim-ineligible.
