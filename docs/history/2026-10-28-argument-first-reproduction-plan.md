# Signature-guided first reproduction and one bounded argument correction

Status: sealed and locally validated; paid collection NOT_RUN. Official=false.
Previous paid allocations are closed. The proposed new cap requires exact approval.

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run
- Origin Date: 2026-10-28
- Verification Status: UNVERIFIED for actual-model uptake and original reproduction
- Version Label: argument_first_reproduction_v1

## Question and intervention

The [previous helper trial](2026-10-28-helper-first-reproduction-results.md) passed
helper construction but supplied a positional list to a zero-parameter CLI after
setting sys.argv. It ended on that first settled result, so no feedback reached
another model response. The [implemented correction](2026-10-28-original-argument-correction.md)
now exposes the actual signature and connects explicit pre-target argument errors
to the existing one-per-run correction allowance.

Test whether the full model reaches and observes the original failing call using
that API, and, if it first produces a qualifying binding error, whether normal
host feedback lets it correct the request once. Start from the same pre-event-65
public checkpoint of run_dev_3e21775752a54cae. This is a fresh public reconstruction,
not a clean-start solve or continuation of the previous generated program.

Use the previous helper-follow-up long description and replace only its generic
list-call paragraph with current actual-signature guidance. Public messages,
source/action evidence, tool parameters and other first-request fields match the
previous B. Opaque historical reasoning and the stale model-priced completion
forecast remain removed as before. Do not inject the old response, invalid program,
chosen diagnostic witnesses, patch, private evaluator or answer hints.

The diagnostic endpoint changes only for a durable first result that the v9 host
classifies as eligible original argument correction. The normal runner then owns
feedback construction, protocol handling, acquisition quotas and cost/time admission.
The second probe result always ends the diagnostic, including rejection or another
error. First-request rejection, non-binding error, mixed target entry or unavailable
correction also ends at the first result. A model stop or ordinary terminal may
end earlier. No failed request is automatically re-executed.

If the first request enters normally, stop after observing that result and mark
argument-correction uptake NOT_EXERCISED. Do not induce an error or add a run just
to exercise the correction. This combines current host/API guidance with a bounded
feedback endpoint; one stochastic run cannot separate their causal effects.

## Fixed conditions and scope

| Condition | Value |
| --- | --- |
| Task | Astroid-1333, dev-train/current-dev20/13 |
| Model / effort | gpt-5.4-2026-03-05 / xhigh |
| Credential path | C:/Users/geonj/Documents/PatchLoop/.env |
| Repeats | B only, once |
| Input / ordinary output / protocol-correction output | 60K / 40K / 25K |
| Remaining model / tool slots | 16 / 34 |
| Original probe results / argument correction | At most 2 / at most 1 |
| Remaining solver / evaluation reservation | 1,903 / 390 seconds |
| Proposed new invocation-wide cap | USD 4.41415320 |
| Output roots | C:/pt/argument-first-reproduction-plan-v1 and C:/pt/argument-first-reproduction-run-v1 |

Argument correction is an ordinary model response with the ordinary 40K ceiling.
The separate malformed-response/protocol correction retains its existing 25K
ceiling and one allowance. These are not two extra argument-retry credits. All
inherited counters and the ordinary completion/verification reservation remain;
the diagnostic does not release future repair/check/finish costs to make admission
easier. The 390-second evaluation reservation is retained but evaluation is not run.

No mutation, public regression checks, finish_task, isolated evaluation or repair
efficacy is in scope. Count immediately before dispatch, use zero SDK retries and
stop on count, transport, billing, target-execution or cleanup uncertainty. Do not
restart/resume automatically, start Docker Desktop, or pull/build an image.
Monitor process liveness and the declared result journals at bounded intervals;
the inherited active deadline remains the hard execution bound.

## Outcomes and decisions

Record each stage separately: generated request, admission, actual signature,
supplied arguments/argv, target_started, complete capture, same-call F0010,
declared-failure match, desired-result mismatch and processing coverage. The public
issue and fixture must correspond to the original call. An outer succeeded tool
receipt, setup PASS or corrected argument binding does not establish reproduction.

On a binding error, verify the failed source/signature/arguments occur in the next
counted model request. Distinguish window opened, response actually dispatched,
changed same-purpose request submitted, request accepted, actual entry and original
failure observed. Keep acquisition quota/release reasons and each probe's host
review. A budget/time block after the window opens is not failed model correction;
a returned second request with another binding error is an attempted but unresolved
correction. A target's own TypeError belongs to behavioral diagnosis.

Check positive processing on the original call's desired observation. W0611 only
from a direct-file control does not prove directory processing. The failing baseline
may lack positive processing, while the desired-result design must require it.
No result from this trial establishes repaired behavior or held-out generalization.

If the model reaches the original call and observes its failure, the next question
can concern repair. If it remains blocked, diagnose the observed stage before
changing model or limits. No automatic repeat or default adoption is planned.

## Preparation evidence and execution

Runtime baseline: `1f69d90d3f1d5e8cf27f77318d1eea361969bc98`.
The new diagnostic profile is `argument` in `diagnostics.first_reproduction_comparison`.
Diagnostic implementation commit: `2ff83024`. The runtime remains the previously
validated `1f69d90d`; this preparation changes only diagnostic code and its tests.
The full diagnostic owner file passed **22 tests in 37.596 seconds**, including
argument error -> delivered feedback -> corrected invocation, repeated binding
failure, and immediate stop after normal entry, target TypeError, unknown signature
or cleanup uncertainty. Ruff and diff checks passed. No broad runtime suite was
repeated; the unchanged runtime's 123-case focused validation is linked above.

Actual-checkpoint preparation used a scripted provider and no target calls. At
synthetic 60K uncached input per response it admitted ordinary 40K then protocol
25K output under the proposed cap. The USD 1.275 synthetic usage is not an API
charge. Short runtime controls separately cover the ordinary 40K argument response
with its prospective replay and independent 25K protocol reserve.

Independent shared-context artifact review confirmed that the new B request has
identical public input, parameter schema, model, effort and limits to the previous
helper B. Only its call paragraph changes (9,230 to 9,356 description characters).
No previous generated program/result or opaque reasoning is added. This is artifact
verification, not blind model-performance evidence. The common public-input hash
is `sha256:0a7bb50b41ed345bdfcfaed414e689bfaf9fbc64f56e86155ba1d2f7fae62ac9`.

Sealed manifest hash:
`sha256:4224bb0d22dd283f8d9508b71a68b9613aab13b6d326bd1a8a5b9072e3697016`.
Runtime hash:
`sha256:321e6bc99e4cd3ef014e5d9bc7947c5f3369dedddc39c1be520a21b6142d47b3`.
The manifest binds the diagnostic implementation, all changed host files, exact
source checkpoint, model pricing configuration and local image identity.

Read-only environment preflight is READY: task/runtime, prepared source,
dependencies and exact local probe image identity pass. No credentials were read,
provider dispatched, target executed, image pulled/built or Docker Desktop started.
Collection repeats these checks and aborts on drift. `preflight.json`, JUnit and
review receipts are linked in the preparation dev-run-v1 journal outside the repo.

Exact planned command: `& 'C:/pt/argument-first-reproduction-plan-v1/run.ps1'`.
`run.ps1` binds that manifest hash and USD 4.41415320 cap. `validate.ps1` checks the
same bindings without provider or target execution. The result directory is absent
and must remain absent until approved collection starts.
