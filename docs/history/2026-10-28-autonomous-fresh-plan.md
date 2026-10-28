# Clean-original autonomous repair preparation

## Material Passport

- Date: 2026-10-28. ARS experiment-agent, code experiment preparation.
- Status: PREPARED_NOT_EXECUTED; exact new command confirmation pending.
- official=false; claim_eligible=false. One development task, no causal estimate.
- Runtime is unchanged from the successful required-check continuation.

## Question and reason

The [required-check continuation](2026-10-28-required-public-check-repair-results.md)
received actual failed results, made two edits and passed all 11 public cases,
the original caller, regression and isolated acceptance. It started with a saved
patch whose F0010 case already passed, plus operator-selected public counterexamples.
That establishes one assisted repair, not a clean-start repair.

Test whether the current normal `run_dev` can reproduce and repair Astroid-1333
from original source, preserve actual target processing, verify and submit under
the same original total resource limits. This is the smallest remaining end-to-end
question. Do not add another runtime change or increase limits before observing it.

A failure could occur during acquisition, source exploration, request construction,
repair, verification or completion. Record the earliest unsupported transition
using public evidence instead of presuming the last successful mechanism explains
it. An isolated rejection after public PASS remains failed task repair. Passing
this one development task does not establish a success rate or generalization.

## Exact proposed invocation

- Task: `tasks/dev-train/current-dev20/13/public.yaml`, Astroid-1333.
- Model: `gpt-5.4-2026-03-05`, reasoning xhigh, one execution.
- Credential file: `C:/Users/geonj/Documents/PatchLoop/.env`.
- Fresh invocation cap **USD4.50**, with no inherited spend or reopened allocation.
- Twenty responses including at most one protocol correction, forty tool actions,
  at most three accepted edits. Input60K, output40K/correction25K.
- Total2400 seconds with390 seconds reserved for isolated evaluation;
  initial solver allowance2010 seconds.
- Existing thin policy, segmented context, protected inspection, bounded original
  acquisition, repair recheck and completion-recovery reservation are retained.
- Prepared original source and pinned public dependencies are reused by verified
  identity. Source base is `d2a5b3c7b1e203fec3c7ca73c30eb1785d3d4d0a` with an empty diff.

The explicit read-only registration `caller_source_roots={"pylint":"pylint"}`
retains the successful continuation's caller access through the ordinary runner.
This is supported configuration, not an automatic default: empty roots disable
caller file reads. The old mini-model fresh request omitted it; this experiment
is not a controlled comparison against that historical run.

The registered full-model rate gives a 60K-input/40K-output envelope of USD0.75,
and 60K-input/25K-output envelope of USD0.525. Nineteen maximum normal responses
plus one correction would cost USD14.775. **Twenty responses are a count ceiling,
not a guarantee within USD4.50.** Existing admission counts actual inputs and
reserves completion; it may lower output or stop within the fixed cap.

## Input and outcome boundaries

The model receives the public issue, original code through registered tools,
prepared public dependencies/caller source access and current-run observations.
No saved candidate, checkpoint, prior observations, 11-case operator packet,
operator repair, reference patch or private evaluator content is injected.
`resume_run_id` is null and cross-run history search is disabled.

No supplemental registry is registered. Thus the recently added operator-supplied
required-check mechanism is **NOT_EXERCISED** here. This is a whole-agent clean-start
test, not an ablation of that mechanism. Operator-prepared dependencies/caller
registration remain environmental assistance and are disclosed.

Record separately: unchanged-base F0010 reproduction; comparable candidate replay;
failure absence and positive intended-processing evidence; current-diff public
checks; natural failure delivery/revision if needed; normal finish and patch
delivery; isolated task acceptance and safety; counts, cost and elapsed time.
If no repair fails naturally, revision uptake is NOT_EXERCISED. Do not manufacture
failure or repeat to obtain that trajectory. Isolated output never feeds the solver.

## Preparation evidence

The ordinary runner constructed one initial request with a deterministic synthetic
count/stop adapter, network/target execution blocked and no credential-file read.
The actual counted/dispatched input and tools agree. Its diff is empty, the only
registered visible check is `base-regression` at NOT_RUN, prior results/source
spans are absent, caller scope is offered, and tools are search/read/stop/probe.
The output ceiling is40K. This is structural evidence, not a live token count or
proof that model generation will succeed.

The initial local stub used an obsolete sandbox method name, then omitted required
encrypted-continuation metadata. Both preparation issues were confined to the
offline audit; the interrupted offline journal remains preserved. The corrected
v2 audit passed. No runtime behavior changed and no real provider/target retry ran.

Read-only preflight passed in7.70 seconds: tracked runtime/task identities, clean
prepared source, dependency inventory and caller identity, pinned local images and
credential-file existence. It did not read credentials, start Docker, pull/build
images, count tokens through the provider or execute the target.

Focused validation covered ten distinct cases across bounded selections: caller
registration/recovery2, mock isolated smoke3 and documentation5. All passed after
correcting stale smoke-test assertions for stage-specific segmented prompts and
omitted automatic-action `memory_update`. The initial selection had seven passes
and one assertion failure; checking all three context modes exposed the omitted
field assertion. Final smoke/docs selection passed8 in16.485 seconds. Ruff and
PowerShell/Python syntax checks passed. Runtime bytes and the sealed manifest
remain unchanged; only those test expectations and documentation changed.

A shared-context read-only reviewer independently checked all11 bindings, initial
input isolation, caller scope, limits and direct normal-run entry, with PASS.
The reviewer also confirmed the test-only corrections preserve isolated acceptance,
same-policy recovery invariance and cross-policy recovery rejection checks.

## Sealed package and stopping

- Package: `C:/pt/autonomous-fresh-plan-v1`.
- Manifest: `sha256:db006cc81bda32aa3574e5d4d1d1c9fbbbe43fb9f9df5c380469cbc221303479`.
- Command: `& 'C:/pt/autonomous-fresh-plan-v1/run.ps1'`.
- New live result root: `C:/pt/autonomous-fresh-run-v1` (absent at preparation).
- Request audit: `first-request-audit.json`, with exact `first-request.json` hash
  `sha256:ec2e440336db90d0b5b48db46b8922c3887915f28d69dcad75357864493bec4f`.
- `execute.py` verifies bound files/runtime and a new absent result root, enforces
  the one-shot journal lock, and calls the normal runner directly.
- `monitor.py` reads only the new run's public progress; `collect-result.py`
  collects public terminal/accounting receipts without additional target execution.

Zero SDK retries; count/transport/billing/execution/cleanup uncertainty stops the
invocation. No automatic resume or repeat and no image pull/build. A settled failure
is a result, not authorization for another try. The user's latest request follows
the proposed preparation step; exact new command confirmation is still pending.
All historical allocations remain closed.
