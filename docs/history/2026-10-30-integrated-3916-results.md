# Integrated development: pvlib1154, pydicom1694 and SQLFluff1517

Date: 2026-10-30 KST. Allocation: approved, preflight passed, execution pending.
official=false; development-exposed tasks only, claim-ineligible.

## Question and selection

The user approved tasks 3, 9 and 16, each fresh once under the proposed USD12 total
cap. Exercise the current agent after the [two validation fixes](2026-10-30-test-validation-fixes.md)
and use observed failures to choose the next improvement. No one-factor ablation,
saved-patch continuation or private-feedback injection is part of this run.

- **3, pvlib1154:** the latest integrated run passed but encountered a public-wrapper
  rejection followed by seven restoration-related rejections. Check whether the
  current model completes without those conflicts, preserving test execution and
  task correctness. Its earlier 27 calls / 1,412.784 seconds / USD2.530811 are a
  descriptive baseline, not a matched causal control.
- **9, pydicom1694:** the [older dev20 run](2026-10-29-repair-dev20-results.md)
  stopped with public regression FAIL after three accepted edits and completion
  exhaustion. Check whether the current complete configuration reaches a correct
  submission, rather than treating additional edit slots as success evidence.
- **16, SQLFluff1517:** that same older run passed public checks but failed independent
  acceptance. Check task correctness alongside public regression and added-test use.

For tasks 9 and 16 the historical configuration had thin policy, 20 model calls,
40 actions, three edits and different output/time limits. Current policies and
limits below differ together. Neither a changed outcome nor one sample identifies
which feature caused it or establishes generalization.

## Authorized execution scope

- Exact checked-in public packages: `tasks/dev-train/current-dev20/{3,9,16}/public.yaml`.
- Model `gpt-5.4-2026-03-05`, xhigh, 25,000 desired output tokens.
- Credential file `C:/Users/geonj/Documents/PatchLoop/.env`; never logged or passed
  to repository/evaluator subprocesses.
- One fresh run per task, order 3/9/16, maximum two workers. No old patch, source
  repair, notes, operator diagnosis, model state or evaluation detail is seeded.
- Fixed caps USD4 per task and USD12 invocation-wide, with no transfers. Count actual
  input immediately before dispatch; zero SDK retries. Count, transport, billing,
  continuation or cleanup uncertainty stops new admissions while already admitted
  calls settle. No replacement, automatic retry, resume or additional evaluation.
- Current/brief-v1, segmented-v1/result-or-size-v1, public-checks-v1, ordinary probes,
  no automatic probe replay, repair recheck, protected-v1 inspection, per-call-v1
  cost admission. Limits: 40 model calls, 100 actions, 12 accepted edits and 1,800
  seconds per task, including the existing evaluation reserve.

Implementation HEAD: `f24382615e454d77908a276af98592bf082d670d`.
Runtime: `sha256:d3c4d806ddc25b6cbd06a2b9d44cc844e1d675df29309d5e120d1e7ecf0e2132`.
The existing bounded scheduler and isolated evaluator are reused. The external
launcher differs from the previous run only in fresh paths, task order, the common
dependency-root selection and pricing-source URL. The current runtime stays frozen.

The [official model page](https://developers.openai.com/api/docs/models/gpt-5.4)
was checked on 2026-10-30: standard input/cached-input/output USD2.50/0.25/15 per
million tokens. Runtime uses the global endpoint, default service tier and counted
60K input bound. Documentation MCP returned a challenge error, so verification used
the official web page; this was not a provider count or generation request.

Fresh preparation: `C:/pt/integrated3-3916-20261030-v1`.
Separate result root: `C:/pt/integrated3-3916-run-20261030-v1`.
Existing public source/dependency descriptors are reused read-only after fresh
source, task, runtime, image and credential-shape preflights. No image acquisition
or Docker Desktop startup is authorized. The preparation journal binds requests,
launcher, descriptors and manifest; the user's current approval binds this allocation.

## Assessment fixed before dispatch

Record independent acceptance/safety, current-diff public results, explicit test
selection versus directory discovery, accepted mutations, rejected actions, model
calls, provider wait, total time and reconciled cost. Inspect public source/action/check
evidence for causes; never expose private test content or evaluation feedback to the
solver. Submission and public PASS are distinct from task acceptance.

The validation fixes remain selected unless a concrete regression is observed.
Use a repeated public failure, unfinished repair or acceptance failure to select the
next investigation. Faster completion without correctness is not an improvement;
more edits/probes or one successful submission alone are not improvement evidence.
All older allocations remain closed. This scope permits no follow-up run beyond
the three approved attempts; unused funds confer no additional execution rights.

## Preparation and outcome

All three source, task, runtime, local-image and credential-shape preflights passed
without a provider call. Each task reserves 330 seconds for evaluation inside the
1,800-second total. Documentation checks passed 6/6. No runtime changed after its
1,208-PASS quick suite. The operational review confirmed fixed non-transferable
allocations, shared stop admission and zero SDK retries.

Frozen manifest: `sha256:e457af9adc50e714c18c6aa4d41cc926ef7f521d809efedc8496270007156325`.
The new `approval.json` and preparation journal bind the user's direct request to
this scope. The three authorized attempts are pending; results will be recorded
here without changing the frozen runtime or older reports.
