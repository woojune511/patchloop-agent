# Closed repair exercise scope: tox configuration substitution

Prepared and completed 2026-09-30. The user approved exactly one invocation in the
conversation; it completed and the allocation is closed. This retained scope and
command authorize no rerun. See [result](../docs/history/2026-09-30-tox-fresh-repair.md).

## Purpose and evidence

Use the working agent unchanged for one complete fresh repair/check/submission path.
The checked-in public task describes an existing cross-section value that becomes
empty after factor filtering but remains an unresolved reference. Preserve matching
factor values, explicit defaults, caller context and same-section computed defaults.
The important distinction is filtered-empty versus missing; neither an empty result
nor an unresolved reference alone establishes correct handling of all cases.

The closed development review records a seeded tox repair that reacted correctly
to a public missing-default counterexample. That is evidence that this distinction
is useful, not a fresh-solve gain. A fresh run here exercises the product without
introducing another prompt ablation or operator-supplied repair hint. Prior traces,
reference patches and private evaluators must not enter model input. The task has
already been exposed and cannot support held-out/generalization claims.

## Fixed scope proposed for approval

- Task: `tasks/dev-train/tox-cross-section-empty-substitution/public.yaml`, version 1,
  dev-train; upstream base `02e9ed73da6a0f97f9167e957e1168d6116942ce`.
- Model: `gpt-5.4-2026-03-05`, xhigh, 25,000 desired output tokens.
- Credential file: `C:\Users\geonj\Documents\PatchLoop\.env`; existence and Git
  ignore status checked, secret contents not read for this preparation.
- One fresh repetition, invocation-wide cap USD 3.00; no comparison arm or continuation.
- 40 model calls, 100 actions, four accepted edits, 1,800 seconds.
- Working baseline: segmented-v1, result-or-size-v1, brief-v1, optional probes with
  policy none, repair-recheck, protected-v1 inspection, per-call-v1 cost admission.
- No runtime, prompt, public check or task-package changes before the fresh solve.
- Stop on cost admission failure or count/transport/billing/cleanup uncertainty.
  Zero SDK retries; no automatic repeat, extra funding or evaluator-image acquisition.

## Prepared inputs

Source: `C:\pt\preparations\tox-next-repair-20260930-v1\prepared-source.json`.
Public source content hash:
`sha256:a10f8ffa21022a45ce3db40785e9eaa2d5b355aa42f227bed5bacc07f113f7d8`.
Dependencies: `C:\pt\preparations\tox-next-probes-20260930-v1\prepared-probe-dependencies.json`.
Resolved only the public project's declared runtime dependencies, using source root
`src`; no build hook, provider or Docker container was executed during preparation.

Existing local images were inspected successfully:
- evaluator `sha256:ffd1129e4be4692becf5011c874858918864d586267002a2917195726542de57`;
- probe `sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de`.

Revalidate identities and clean runtime/task inputs immediately before an approved
invocation. Use a fresh external state root, retaining append-only dev-run-v1 evidence.

```powershell
$env:PATCHLOOP_STATE_ROOT = 'C:\pt\runs\tox-next-repair-20260930-v1'
uv run --locked patchloop dev `
  --provider openai `
  --task tasks/dev-train/tox-cross-section-empty-substitution/public.yaml `
  --model gpt-5.4-2026-03-05 --reasoning-effort xhigh --max-output-tokens 25000 `
  --context-policy segmented-v1 --segment-boundary-policy result-or-size-v1 `
  --planning-policy brief-v1 --enable-probes --probe-policy none `
  --repair-recheck --repair-inspection-policy protected-v1 `
  --completion-cost-policy per-call-v1 `
  --prepared-source C:\pt\preparations\tox-next-repair-20260930-v1\prepared-source.json `
  --prepared-probe-dependencies C:\pt\preparations\tox-next-probes-20260930-v1\prepared-probe-dependencies.json `
  --env-file C:\Users\geonj\Documents\PatchLoop\.env `
  --max-cost-usd 3.00 --repeat 1
```

## How to judge the result

Record an actual submitted patch, public regression results, isolated acceptance,
safety, settled/uncertain cost and wall time separately. The allowed edit area is
`src/tox/config/loader/ini/**`, at most two files/80 diff lines; no dependency,
public API or test-file changes. Public checks passing alone do not prove correctness.
Keep private evaluation outside the coding agent. All results are official=false
and claim-ineligible. If a concrete failure occurs, distinguish agent reasoning,
check coverage, environment and runtime-contract causes before selecting a fix.
No second experiment or agent feature is preauthorized by the outcome.
