# Captured target-exception live pilot

Status: AUTHORIZED; preparation in progress, live execution not yet started.
Date: 2026-10-26. official=false; claim-ineligible.

## Material Passport

- Origin: academic-research-suite / experiment-agent, run.
- Version: target-exception-live-v1.
- Current human request: "그럼 실험해볼까", after the implemented classifier fix.
- Scope: one fresh solve with the previously selected task/model/credential/limits,
  restated before dispatch. Prior allocations remain closed; no retry or resume.

## Question and intervention

Does [preserving captured target exceptions after helper failure](2026-10-26-target-exception-preservation.md)
let the model diagnose the remaining original-call failure, revise its patch and
repair Astroid-1333 within the same resources?

The closed [baseline](2026-10-26-request-continuity-live.md) submitted one edit after
public regression PASS, although the bound target raised `FileNotFoundError`.
Its helper's subsequent failure caused the host to report zero target failures.
The fix changes only that classifier boundary. Implementation: `b26bd729`;
runtime `sha256:61887a3ccfabb9db830b1ae63548babb53e411a7bcf5e351a202e0c5511c7f64`.
Reuse the same-runtime local receipts: target21, quick451, documentation5, Ruff
and isolated mock PASS. No broad local rerun is needed for this pilot.

This is a descriptive fresh solve on a development-exposed task. Fresh model
choices are stochastic; the original program and candidate need not reproduce
the prior failure. If no captured target exception followed by helper failure
occurs, classify this specific fix as NOT_EXERCISED. Do not induce it or seed
the solver with a prior caller, patch, operator diagnosis or private evaluator data.

## Exact scope and stopping rules

- Task: `tasks/dev-train/current-dev20/13/public.yaml` (Astroid-1333, dev-train).
- Model: `gpt-5.4-mini-2026-03-17`, xhigh, standard service.
- Credential: `C:/Users/geonj/Documents/PatchLoop/.env`; contents are never logged.
- Repeat 1, total invocation cap USD 1.20, ordinary/correction output 40,000/25,000.
- Limits: 40 model calls, 100 actions, four accepted edits, 1,800 active seconds;
  1,920 seconds operator supervision. SDK retries zero.
- Same segmented-v1/result-or-size-v1/brief-v1 policies, 60K input bound,
  completion-recovery-v1, bounded acquisition, probes, repair rechecks and
  protected inspection. Prepared source/dependencies and local images unchanged.
- After settled submission, the same two frozen public failure/control checks
  share 120 seconds on the exact submitted diff, outside solver context. The
  assessor keeps the CP949 result decoding already used in the baseline.
- Preparation root: `C:/pt/target-exception-live-ready-v1`.
  Execution root: `C:/pt/target-exception-live-v1`.
- No Docker startup, image pull/build, replacement run, retry, resume or cap increase.
  Stop on count/transport/billing/cleanup uncertainty or frozen-source drift.

The preparation request binds the exact CLI, current commit, hashes and human
request. Execute its `supervisor.py` once, then eligible `assess_submission.py`.
Current standard prices were checked against [OpenAI pricing](https://developers.openai.com/api/docs/pricing):
USD 0.75 input, 0.075 cached input and 4.50 output per million tokens.

## Measurements and interpretation

Measure unchanged-base failure/control, first edit, current bound target exceptions,
outer helper status and capture/identity qualification separately. At each triggered
failure inspect model-visible failure state, offered diagnosis/repair actions,
subsequent diagnostic output and actual patch content. A delivered field, available
budget or linkage ID alone does not prove that the model used the evidence.

Record current original behavior, replacement exceptions, public regression,
submission, frozen public checks, independent acceptance and safety separately.
Preserved negative evidence is not whole-case verification. Known failure followed
by an allowed finish would contradict the host mechanism; correct blocking without
a useful repair would show that classification alone is insufficient. No trigger
leaves live efficacy of this fix unresolved. Report cost/tokens/time and the first
unmet stage. One run does not establish a causal gain or general solve rate.
