# Request-continuity live pilot

Status: CLOSED; one authorized run completed, repair not accepted.
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

Run `run_dev_b4614e40c1714e81` executed once from 13:03:44 to 13:09:32 UTC.
The request hash is
`sha256:e80cfae546a347b95506a0c4efffbb00e50a8159aa6c323059f14faf8137224f`.
Execution checkout `e258f7cf38c03bbb0e029b1cd602714089624201` adds only the plan to
implementation `a64ff0f669e3934ccf9fa83f6186eea6920ccf35`. Runtime, task, prepared
dependencies and existing images retained their bound identities.

The model reached original execution, observation, its first applied edit and
submission. It did not repair the task: the original candidate replay raised
`FileNotFoundError`, delivery was `unverified_delivery`, and independent task
acceptance was FAIL. Safety was PASS, separately. The public regression passed.

| Measurement | Result |
| --- | --- |
| Model / input-count / tool actions | 20 / 20 / 22 |
| Read/search actions | 16, all after initial original acquisition |
| Accepted edits / submission | 1 / 1 |
| Probe executions | Original acquisition, pre-edit observation, automatic candidate replay |
| Invalid batches / protocol corrections / incomplete responses | 0 / 0 / 0 |
| Settled cost / invocation cap | USD 0.544587150 / 1.20; billing and counting known |
| Supervisor wall time | 347.78 seconds; no timeout or retry |
| Input / cached-input / output tokens | 699,673 / 279,552 / 46,340 |
| Reasoning output / largest response | 41,002 / 21,699 tokens; correction allowance unused |
| Frozen post-submission public checks | Missing initializer ERROR; present initializer NOT_RUN |

Cached input is a subset of input; reasoning output is a subset of output. The
largest response was below the 40,000-token normal ceiling. Neither the invocation
cap nor the model-call/edit/time limits ended this run.

### Public action evidence

1. Sequence 21: the first model action was a valid `run_probe`, with null
   `call_path`, replay and correction references and a new `original_requirement`
   program. It executed two captured calls on the unchanged base. The declared
   failure matched: `bug_has_error=true`, `control_has_error=false`; desired
   behavior did not match. Issue-to-caller equivalence remains model-authored and
   unverified. The actual caller used an absolute package path and a direct-file
   control, despite the prose describing relative paths.
2. Sequence 84: `observe_original` executed before editing. The builder was entered
   once at the missing initializer and raised `AstroidBuildingError`. The other
   prediction, that `modpath_from_file` would not be entered, was contradicted by
   32 entries across the selected original call. Entry coverage was complete
   (31,314 call events and 112 selected events); detail sampling omitted 77 events.
   This is bounded path evidence, not confirmation of the full repair hypothesis.
3. Sequence 259: the only edit changed `AstroidBuilder.file_build` in
   `astroid/builder.py`. Missing package initializers became empty UTF-8 source
   rather than immediately raising the building error. The submitted patch hash is
   `sha256:bd29ca15825acb800a1e2aa9af1ff8e3ac7a2d5941de2ea5d9e9a17ad54296e0`.
4. Sequence 266: automatic replay on that candidate observed a complete capture of
   the bug call raising `FileNotFoundError`; the direct-file control returned.
   The helper then rejected the unexpected exception before producing observation
   JSON. Host comparison was `not_compared`, with
   `declared_call_unobserved_or_incomplete`; this is not evidence that no target
   call ran. There was no timeout or cleanup failure.
5. Sequences 280 and 296: required public regression passed, then the model
   submitted without a second edit. Independent acceptance returned FAIL.

### Feedback, remaining resources and decision

The final model input retained the current candidate replay, action/diff identity,
and explicit `builtins.FileNotFoundError` outcome. Thus the evidence was not simply
absent after context rollover. However, completion exposed `target_failure_count=0`,
no original-failure diagnostic and repair-path `not_needed`, alongside an overall
`unverified` result. The gate became `ready_to_submit` after the public check.
The finish assessment described the exact original reproduction as not rerun,
although automatic replay had run and failed. It also treated public-check PASS as
support for the repaired behavior. The host preserved the unverified-delivery label.

Before the final model call, three edits, 21 model calls, 79 tool actions and
1,499 active seconds remained; `replace_text` and `run_probe` were offered.
USD 0.694627800 remained then, with completion and correction reservations still
funded. Final unused invocation capacity was USD 0.655412850. These observations
weaken insufficient total budget as the explanation for stopping after one edit.
They do not prove that another available action would have produced a repair.

Keep the implemented request-contract corrections: this run crossed the previously
missing execution/edit stages without invalid requests. Do not attribute that
progress to each bundled fix or claim a solve-rate improvement. All 20 wire requests
matched the offered read-batch capacity, but no single-action-only gate occurred.
Rejected-draft recovery, the acquisition preparation ceiling and its reserved
dispatch route were NOT_EXERCISED because their triggers did not occur.

The next question is whether an observed target exception is being reduced to an
unspecific unverified state instead of a concrete repair obligation, and how that
interacts with the model ignoring delivered failure evidence. Inspect that decision
path before adding a gate or increasing limits. The patch also leaves a downstream
source-stream requirement unresolved, as the separate public execution shows.

### Frozen public assessment and operator deviation

The original assessor stopped before creating any target execution because the
CLI result was encoded as Windows CP949. Strict CP949 decoding parsed it and
round-tripped to the exact original bytes. Preserve the original result and frozen
assessor. A separately hashed derivative changed only that one file read to
`encoding='cp949'`, retaining the same patch, two programs and shared 120-second
deadline. This added no model call and did not change the solve or its request.

The first frozen program then ran for a total assessment duration of 9.49 seconds.
Its program/dependency/patch/setup identities matched, setup passed and cleanup was
confirmed. It exited 1: Pylint tokenization called `node.stream()`, which reopened
the still-missing initializer through `Module._get_stream`; crash reporting then
tried to open that file again. The frozen grader reports ERROR for a failed or
incomplete receipt, even when identities match. Preserve that verdict rather than
converting it to a completed behavioral FAIL or PASS. The stop rule prevented the
present-initializer check. No further target execution followed that ERROR.

This public stack explains why turning the builder's missing file into empty source
was insufficient for this submitted patch. It is distinct from private acceptance,
whose internals were not opened or returned to the solver.

### Durable receipts and closeout

- Frozen request/authorization/command:
  `C:/pt/request-continuity-live-ready-v1/{request.json,authorization.json,command.ps1}`.
- Settled result, usage and public assessment:
  `C:/pt/request-continuity-live-v1/{process-result.json,cli-result.json,public-assessment.json}`.
- Encoding deviation: `assessment-decoding-adjustment.json` under that result root.
- Reproducible public-only analysis: `analyze_result.py` under the preparation root;
  `analysis.json` under the result root, CAS
  `sha256:a88b33f92704650af27cab83e45e12e28a350268c536eb217cdb32c1b8d5b9fe`.
- Append-only, hash-chained operator and solver journals remain under the result
  root's `runs/`; analysis verifies the referenced public CAS hashes.

This allocation is closed. No retry/resume/replacement run, cap increase, provider
judge, private-context injection or runtime change occurred. This is one fresh
stochastic solve on an exposed task, not a controlled estimate of individual
mechanism effects, generalization or overall repair quality. Core70/quick450/Ruff
and isolated mock receipts from the unchanged implementation are reused; closeout
checks documentation only: `test_documentation_layout.py` 5 PASS in 0.10 seconds;
`git diff --check` passed. No Docker containers remained after assessment.
