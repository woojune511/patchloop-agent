# Request-continuity live pilot

Status: authorized fresh one-run execution; preparation in progress.
Date: 2026-10-26. official=false; claim-ineligible.

## Material Passport

- Origin: academic-research-suite / experiment-agent, run.
- Version: request-continuity-live-v1.
- Current human instruction: "실험해보자", following the implemented request fixes.
- Scope: a new run under the previously selected task/model/limits; no prior
  allocation is reopened. No retry, resume, replacement run or cap increase.

## Question, baseline and intervention

Can the model execute the original caller and reach its first applied edit after
stage-valid request construction, single-action generation where required,
rejected-draft retention and reserved original acquisition?

The [closed baseline](2026-10-26-completion-feedback-live.md) reached neither
original execution nor an applied edit: one invalid probe, 33 inspections, two
edits rejected as a batch, then no tool in the funded correction. The [analysis](2026-10-26-completion-feedback-analysis.md)
motivated [implementation a64ff0f6](2026-10-26-request-continuity.md). Its runtime
hash is `sha256:9632249097a22a6e8d8e63adf5df3d5000510f9e7da778360341afc9353799bd`.
Local core70 and quick450, Ruff and isolated mock evaluation passed. Reuse those
receipts; do not rerun the broad tests during live preparation.

This combines four related contract fixes in one descriptive fresh solve on an
exposed task. It does not isolate their individual causal effects. A fresh caller
is stochastic and need not match earlier authored callers byte for byte. No prior
patch, caller, operator analysis or model reasoning is seeded into the solver.

## Exact execution scope

- Task: `tasks/dev-train/current-dev20/13/public.yaml` (Astroid-1333, dev-train).
- Model: `gpt-5.4-mini-2026-03-17`, xhigh, standard service.
- Credential: `C:/Users/geonj/Documents/PatchLoop/.env` (never print its contents).
- Repeat 1; invocation-wide cost cap USD 1.20. Ordinary/correction ceilings:
  40,000/25,000 tokens; the existing finalization floor stays within that cap.
- Limits: 40 model calls, 100 actions, four accepted edits, 1,800 active seconds;
  1,920-second operator supervision. Zero SDK retries.
- Segmented-v1 / result-or-size-v1 / brief-v1; probes with policy none;
  bounded-v1 acquisition; protected-v1 inspection; repair-recheck;
  completion-recovery-v1. Input/context bounds and prepared dependencies unchanged.
- Same task bytes, prepared source, installed probe/evaluator identities and two
  frozen public post-submission checks as the baseline. Those checks share 120
  seconds, require a settled submission and remain outside solver context.
- Preparation: `C:/pt/request-continuity-live-ready-v1`.
  State/results: `C:/pt/request-continuity-live-v1`.

Run `uv run --locked --offline python C:/pt/request-continuity-live-ready-v1/supervisor.py`
from the repository, then the corresponding `assess_submission.py`. The immutable
request records the exact CLI, hashes, source inventory and current authorization.
Preparation inspects existing Docker images only; no startup, pull or build.
Count/transport/billing/cleanup or frozen-source uncertainty stops the invocation.

## Measurements and decision rules

Track preparation actions versus actual dispatch/rejection, first original result,
stage-valid probe shapes, model-facing parallel flag, first proposed/applied edit,
any invalid batch and draft retention on correction/rollover. Absent triggers are
NOT_EXERCISED, not failures or successes of conditional mechanisms.

Judge comparable unchanged-base failure, current original behavior, F0010-free
control, public regression, submission, frozen public checks, independent acceptance
and safety separately. A replacement exception is not a repair. Record exact cost,
tokens, time and first unmet stage. Model uptake needs public actions/results;
delivered fields or reserved budget alone do not establish it. Continued exhaustion
with valid modes/drafts present weakens the sufficiency of this intervention.
Unused budget does not authorize another run, and one success gives no general
solve-rate or held-out improvement claim.

## Execution result

Pending. The result, artifacts and limitations will be recorded here when the
single invocation settles; unexpected usage remains unknown rather than zero.
