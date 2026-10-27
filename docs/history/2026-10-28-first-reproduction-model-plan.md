# First reproduction: model-only checkpoint comparison

Status: implemented, locally validated and sealed; paid collection NOT_RUN.
Official=false. The new allocation is pending exact cap confirmation.
This is a development-exposed first-request diagnostic, not a repair trial.

## Problem and question

The [description comparison](2026-10-28-first-reproduction-description-results.md)
did not reach the complete observation objective in either arm, at different stages.
Long-description A produced a valid in-process request and reproduced the original
F0010, but selected only error-presence booleans without positive processing
evidence. Short-description B failed host request validation before execution.
Neither exhausted output. Continuing to change instructions would leave model
configuration as an untested alternative explanation for request construction.

Ask whether changing the model snapshot changes valid callable/observation
construction at this same public checkpoint. Use the recorded long description
because it has produced an executable reproduction, without claiming it is optimal.
The earlier [model comparison](2026-10-27-model-setting-results.md) began from a
saved repair candidate, tested a different stage, and did not establish full-model
superiority. It is not a substitute for this comparison.

## Intervention and fixed conditions

| Item | Selection |
| --- | --- |
| Task | dev-train/current-dev20/13, Astroid-1333 |
| Public checkpoint | run_dev_3e21775752a54cae, before prepared-input event 65 |
| A / B | gpt-5.4-mini-2026-03-17 / gpt-5.4-2026-03-05 |
| Reasoning / order / repeats | xhigh / A then B / one new run each |
| Credential location | C:/Users/geonj/Documents/PatchLoop/.env |
| Description | Recorded long run_probe description in both arms |
| Input / ordinary / correction output | 60,000 / 40,000 / 25,000 tokens |
| Remaining model / tool / edit limits | 16 / 34 / 3; no edits in this diagnostic |
| Remaining solver / evaluation reserve | 1,903 / 390 seconds |
| Proposed new arm / total cap | USD 4.41415320 / USD 8.82830640 |
| Stop | First settled original probe, explicit stop, or terminal failure |

Both arms reconstruct the same public messages and completed read/search evidence.
Historical opaque reasoning is excluded. Neither receives the preceding pair's
response, code, selected observation, repair, private test or evaluator material.
This is a public reconstruction, not a byte-identical historical resume.

Remove only the model-specific derived `completion_cost` forecast from the common
first-request state: retaining the mini forecast would misdescribe the full arm.
Retain the actual remaining dollar cap, counters, task/source evidence and all
other state. This symmetric projection differs from the earlier description trial
and is disclosed; within this new pair, first API requests differ only in model ID.
Host cost accounting and completion reservation remain active, using each model's
actual rate table. The fork binds that model, pricing and model-configuration hash
before writing its envelope. Historical settled usage is never repriced.

Preserve tool schemas, host verification, public environment, thin/segmented
policies and remaining action/time budgets. Protocol correction may precede the
first settled probe. Host rejection itself ends the arm, so correction after
tool-validation feedback is not tested. No edit, regression, finish or isolated
evaluation is scheduled. Adding feedback opportunities is a different experiment.

## Admission and authorization

Official standard short-context rates, checked on 2026-10-28, match the registry:
mini input/cached/output USD 0.75/0.075/4.50 per million; full 2.50/0.25/15.00.
See [API pricing](https://developers.openai.com/api/docs/pricing) and the
[mini](https://developers.openai.com/api/docs/models/gpt-5.4-mini) and
[full](https://developers.openai.com/api/docs/models/gpt-5.4) snapshot pages.
No service-tier or region override is introduced.

At the 60K uncached input ceiling, actual offline ledger admission gives:

| Reservation, USD | Mini | Full |
| --- | ---: | ---: |
| Initial 40K-output request | 0.225000 | 0.750000 |
| Successor reserve including 25K correction | 0.934956 | 3.116520 |
| Total admission requirement | 1.159956 | 3.866520 |
| Remaining proposed-cap margin | 3.25419720 | 0.54763320 |

After worst-case initial spending, both still admit the full 25K correction with
the remaining successor reserve. Both expose exactly run_probe and stop_task,
reserve six successors and 930 solver seconds, and have no resource rejection.
Correction also requires at least 30 seconds beyond that time reserve; this is
equal entry-time eligibility, not a guarantee against elapsed-time exhaustion.
The four inherited usage rows retain exactly USD 0.08584680 under either model;
they are excluded from new pair spending.

The preceding allocation is closed. The user requested this new comparison;
the exact new positive invocation-wide cap must be confirmed against the sealed
manifest before paid collection. Count immediately before every dispatch, use
zero SDK retries, and stop both arms on count, transport, billing, execution or
cleanup uncertainty. No repeat is funded by unused allowance. Do not pull/build
images or automatically start Docker Desktop.

## Outcomes and decision rule

Record complete tool-call construction, host admission, actual target entry,
complete capture, exact original F0010 reproduction and positive intended-file
processing evidence separately. Audit the semantic relevance of selected public
observations; self-declared matches and invented diagnostic codes do not suffice.

A full-model advantage is reaching valid, interpretable original reproduction with
positive processing coverage where the new mini arm cannot. If both fail similarly,
the current model change is not supported as a solution on this checkpoint; inspect
whether missing public evidence or the observation contract explains the common
failure. If both succeed, the earlier mini failure is not stable under this repeat.
If full only reduces latency/cost or moves to another failure stage, report that
stage separately. One pair cannot establish model superiority, reliable repair,
clean-start completion or held-out generalization. No default-model adoption is
precommitted from a single pair.

## Local evidence and sealed artifacts

- Focused owner/fork/shared-ledger checks: **14 PASS in 21.15 seconds**. Ruff and
  diff checks PASS. The existing pytest-cache permission warning did not prevent
  these checks; all test state used short external temporary directories.
- Quick: **577 PASS**, including isolated mock evaluation. No additional broad
  regression run or live target is needed to validate this diagnostic-only change.
- Both actual-checkpoint preparation arms ran the ordinary runner with inert
  providers. At a synthetic 60K uncached input on both responses, each received
  initial 40K and correction 25K without narrowing. Simulated new costs were
  USD 0.382500 mini and 1.275000 full, sum 1.657500; these are **not API charges**.
  Count/dispatch identity, fresh correction continuity, model/pricing/envelope
  linkage, historical-cost preservation and shared accounting passed.
- Independent offline policy/admission and diff review found no blocking defect.
  Both first descriptions retain 8,958 characters; first requests differ only in
  `model`. The shared parameter schema hash remains
  `sha256:6d5fd9137f0cb9fc4689ad590c450492f90234b520f85af637b85f2ebc3be0df`.
- Plan: `C:/pt/first-reproduction-model-plan-v1/manifest.json`;
  hash `sha256:63b8481dea550eefe078e51755cf340ab116f4dee8033c7aaacc149210efa7f9`.
  Runtime unchanged at
  `sha256:bc07573f50542452e0ba9f0fa47298f07c5542d4575958013dbb723bd0447080`;
  diagnostic implementation hash
  `sha256:498d1b2723b4bd869731390e39153d53d750a461914cd6066affd4981d17a437`.
  Preparation base commit: `97d736cfd9de463b21f09a4debbaad4fb7432aa1`;
  the new implementation must be tracked and clean before collection.
- Common projected public input hash:
  `sha256:0a7bb50b41ed345bdfcfaed414e689bfaf9fbc64f56e86155ba1d2f7fae62ac9`.
  Exact first inputs are `A-first.json` and `B-first.json` in the plan directory.
- `validate.ps1` in that directory passed without provider or target calls.
  `run.ps1` is the exact future collection entry, bound to the manifest and cap.
  Fresh result root: `C:/pt/first-reproduction-model-run-v1`; not yet created.

No real provider input count, model dispatch, credential read or target execution
has occurred for this plan. Local admission and scripted requests do not establish
model uptake, reproduction, repair or benchmark acceptance.
