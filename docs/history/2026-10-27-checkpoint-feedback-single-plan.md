# Sealed single-A post-edit feedback delivery trial

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: execution preparation and read-only preflight
- Origin Date: 2026-10-27
- Verification Status: PREPARED / PREFLIGHTED; live NOT_RUN
- Delivery implementation: `054dfc7b`; single-row selection: `dc6b9ebc`

The [previous A trial](2026-10-27-first-edit-checkpoint-results.md) produced an
accepted repair, but its next request reached 65,982 input tokens and the generic
handoff produced the same request. The model never received the successful original
verification. This matters independently of repair quality: host success did not
establish an informed model completion. The [delivery change](2026-10-27-checkpoint-feedback-delivery.md)
references exact source already visible in the request and consumes actual handoff
state. Its local checks passed; actual API token admission and live uptake remain open.

Run only A once from the same saved public post-helper/pre-first-edit checkpoint.
Its first request is unchanged; the new model may nevertheless choose a different
patch. The closed A result is a historical baseline, not a concurrent control or
evidence of a causal repair gain. No operator patch, later experiment result,
private evaluator detail or opaque model reasoning is supplied to this trial.
Starting before the edit exercises the current edit-to-verification-to-response
path. A post-edit-only replay would isolate uptake further but would skip that path.

## Exact scope and decisions

- Task: Astroid-1333, `dev-train/current-dev20/13`, official=false.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh.
- Credential file: `C:/Users/geonj/Documents/PatchLoop/.env`.
- One A trial, $1.20 row and invocation cap; no B and no repeat.
- Fresh allowances: two ordinary responses, one correction, two model tools,
  one accepted edit, zero helpers and zero optional original-call selections.
- Input limit 60K; ordinary/correction output ceilings 40K/25K.
- Model plus intermediate verification 600s. Fresh baseline and candidate original
  checks share at most two host actions. Final public and isolated checks each 390s.
- Correction requires at least 30 usable seconds after verification reserve.
- Count immediately before dispatch; zero SDK retries. Count, transport, billing
  or execution uncertainty stops the invocation. No automatic retry or extra trial.

The collector binds selected order, request set and total cap in the manifest.
Default pair preparation remains A/B at $2.40; single-A preparation cannot dispatch B.
Neither the delivery implementation nor this selection changes the first request,
model, row resources or public evidence. At most one source edit is allowed; after
it only `stop_task` is offered. This diagnostic does not test the product's full
`finish_task` submission path or iterative repair after feedback.

Read the public request artifacts and journal to judge these outcomes separately:

1. **Delivery:** an accepted edit produces fresh original verification on its exact
   diff, and the next actual provider request contains that verification without
   changed status, missing evidence or stale diff. Inspect the counted/dispatched
   request identity and whether lossless handoff is exercised. Merely building a
   request or passing host checks is insufficient.
2. **Completion:** the next model response acknowledges the observed outcome and
   calls `stop_task` without claiming unperformed checks. Honest failure is protocol
   completion, not successful repair. Input/output/time limits are separate failures.
3. **Task repair:** original-call status, each call's identity, public controls and
   regression, isolated acceptance/scope/safety. A passed control or no F0010 alone
   does not establish task acceptance.

If no edit occurs, delivery is NOT_EXERCISED; do not repeat automatically. If the
next request still exceeds 60K after one rebuilt context, the delivery intervention
has not solved this trial's admission problem. If feedback is dispatched but the
model misstates it, investigate interpretation rather than labeling transport fixed
as full completion. A passing trial supports this saved-evidence flow only; keep
general adoption and fresh-task quality claims out of scope.

## Sealed artifacts and local evidence

- Manifest: `C:/pt/checkpoint-feedback-single-plan-v1/manifest.json`
- Manifest SHA-256: `e3bc2fd08b1808c7e5b8e024bf71aa2a266c7607e2f8dbbc49195c5b465f660e`
- Exact command: `& 'C:/pt/checkpoint-feedback-single-plan-v1/run.ps1'`
- Script SHA-256: `145a17e9bcf0c214622ed26735e63ac686d07c58ffaba81a3e5dd735cbcb9d0a`
- Result root: `C:/pt/checkpoint-feedback-single-run-v1` (absent before execution).
- Preflight: `C:/pt/checkpoint-feedback-single-plan-v1/preflight.json`.
- Fresh restoration: `C:/pt/checkpoint-feedback-single-restore-v1/summary.json`.
- First A request SHA-256: `c81196f67abd9e475e6c87e8c5f4df4472ff85670564f07a662e85035f95a095`.
- Runtime SHA-256: `56dfa72cfef3e3bb1850826322e75d4e146a5bdd8f1ee91b49c7c7818f8b9d48`;
  diagnostic code and evidence are separately byte-bound in the manifest.

Local validation: 23 preparation/collection tests PASS/1.83s; 24 delivery/checkpoint/
documentation tests PASS/19.47s; 472 quick tests PASS/129.97s including isolated mock;
Ruff and diff checks PASS. The focused runs total 21.30s. Quick coverage took just
over two minutes and was run once; no separate repeated mock smoke.

Preflight checked the current manifest/code/task/source bindings, the unchanged
initial A request, saved candidate hash, 14 source reads (13 coalesced context spans),
both local pinned images, script syntax, credential existence and absent result root.
Credential contents were not read. No Docker startup, pull or build occurred.
Provider/input-count/credential-read/target-execution counts are zero. Local synthetic
token boundaries and JSON character savings do not establish live API token counts.
All previous allocations remain closed. Exact paid approval for this manifest is pending.
