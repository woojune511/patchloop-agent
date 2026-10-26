# Captured target-exception live pilot

Status: CLOSED; one authorized run ended without submission or repair.
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

## Execution result

Run `run_dev_b43b14dd7b2741ad` ran once from 13:48:03 to 14:02:58 UTC.
Execution commit `d7abe20083ee8064fd67efd1c43e6d00c41e9833` adds the scoped plan to
implementation `b26bd729`; the runtime and 128 bound source/task files stayed fixed.
Request hash: `sha256:6a2be5edc6f6b01266e851578dab3ce8566d28d95a8a39d7da897736f1d5a928`.

The model acquired the original failure/control, completed a pre-edit path
observation and applied two edits. Both candidates still raised `FileNotFoundError`
on the original call. The host retained that failure and did not offer finish.
The run ended `INCOMPLETE_RESPONSE` after the final correction produced no tool.
There was no submission, public regression run or independent evaluation.

| Measurement | Result |
| --- | --- |
| Model / input-count / tool actions | 36 / 36 / 37 |
| Read/search actions | 30 total; 29 before first edit |
| Applied edits / submissions | 2 / 0 |
| Probe executions | Original, pre-edit observation, two automatic candidate replays, one model-requested duplicate replay |
| Settled cost / cap | USD 1.071262200 / 1.20; billing and counting known |
| Wall time | 894.56 seconds, no timeout |
| Input / cached input / output tokens | 1,092,934 / 403,456 / 116,421 |
| Reasoning output / largest response | 109,115 / 25,208 tokens |
| Maximum dispatched input | 56,786 tokens |
| Incomplete responses | 3; two normal responses and the final correction |
| Public regression / frozen public checks / acceptance / safety | NOT_RUN / NOT_RUN / NOT_RUN / NOT_RUN |

Cached input is a subset of input; reasoning is a subset of output. The unspent
USD 0.128737800 is not authorization for another attempt. The terminal is an
incomplete response, not exhaustion of the full dollar, 40-call or wall-time cap.

### What the public evidence shows

1. Sequence 106: the first original probe returned the declared
   `bug_has_error=true, control_has_error=false`. It used relative `src/project`
   and a normal-file control. The helper reported F0010 presence from captured
   stdout/stderr. Mapping this authored case to the full issue remains unverified.
2. Sequence 312: selected-call coverage and details were complete, with 31,321 call
   events and 15 selected events. `_build_namespace_module` was not entered;
   `AstroidBuilder.file_build` was entered once and hit the missing initializer.
3. Sequence 421: the first patch redirected a missing initializer under an existing
   directory to `_build_namespace_module`. Its automatic replay (428) captured
   `FileNotFoundError`. The model then requested the same frozen replay (445),
   which repeated the exception; it did not collect a new post-edit call path.
4. Sequence 456: a normal response exhausted its admitted 19,880-token ceiling
   without a tool. The reserved 25,000-token correction returned an 895-token
   response and applied a second edit (471), assigning `namespace_module.file = path`.
   The next automatic replay (478) still captured `FileNotFoundError`.
5. Sequence 494: one further read inspected `astroid/builder.py:113-150`. A normal
   response (505) exhausted 8,620 tokens without a tool. With the one reserved
   correction already consumed, the final correction (516) had 6,144 admitted
   tokens and also returned no tool. No third edit was attempted.

The initial desired ceilings remained 40K/25K. Actual dispatch ceilings were lower
when admission reserved future minimum checks/finish and, before its use, the
single correction allowance. `provider_call_started.output_ceiling` binds the
actual value; pre-admission prepared requests still show the desired value.
This run alone does not establish that those reservations were excessive.

### Mechanism result and limitation

All five completed probe/helper executions exited passed/zero. Thus the new
**nonzero-helper target-exception preservation branch was NOT_EXERCISED**. No
live efficacy claim for that change follows from this run.

Existing negative-evidence behavior was observed: current `FileNotFoundError`
appeared in every post-first-edit model input, `needs_mutation` remained active,
finish was absent, and full host completion stayed `unverified` / `UNKNOWN`.
The final current candidate retained one target failure. This prevented a false
completion but did not produce a repair. The patch hypotheses did not establish
where the remaining exception was raised; replaying the same failure is not a
post-edit path diagnosis.

Before the first edit response, 29 model calls and USD 0.648690600 had already
been spent. Long exploration and later responses with no executable action are
observed resource costs; this is not proof that every inspection was useless or
that a larger context would solve the task. No context/output/cost increase or
further implementation was made during the run.

The next question is how to turn a preserved exception into a discriminating
post-edit diagnostic and a supported revision before funding shrinks. The local
classifier fix remains supported by its regression tests; its live nonzero-helper
condition remains unresolved. The allocation is closed, with no retry or resume.

## Evidence integrity

- Hash-chained preparation/operator/solver journals and CAS artifacts are under
  the two external roots above; old experiment roots were not modified.
- `analysis.json`: `sha256:c8d128c081bf4fac1c5e2e1be527a1e6703790add4d30386b9c5b336ad8a615c`.
- `analysis-boundaries.json`: `sha256:21ba65f1b466b9bb57ac92af61f4fad6992462a65035396264ab8c2dfb30611e`.
  This separate supplement reads compact repair-state fields and actual dispatched
  ceilings. The initial analysis's null nested completion fields mean that the
  compact input omitted `reproduction_review`; they do not mean failure evidence
  was absent. The initial artifact remains unchanged.
- Post-submission public assessment recorded NOT_RUN/no_submission without any
  target execution. Analysis did not open private evaluator artifacts or model
  reasoning text. No source edits or evaluator feedback were sent to the solver.
