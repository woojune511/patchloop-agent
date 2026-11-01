## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run
- Origin Date: 2026-10-24
- Verification Status: ANALYZED (execution and artifact integrity audited; no reproducibility rerun)
- Version Label: invoke24-live-v1

# Fresh native-call pilot: diagnostic observed, no repair

## Question and frozen scope

The [previous fresh solve](2026-10-24-repair-live.md) passed a string where pylint
expected a list and inspected the returned object for diagnostics printed on
stdout. The [native adapter and per-call capture](2026-10-24-capture.md) removed
the extra argument container and exposed actual streams. Its local 2x2 experiment
required both corrected arguments and consuming captured output to discriminate
the missing-init failure from its normal control. Fresh model uptake and repair
were still untested, which motivated this sample.

The prospective question was whether a fresh model could acquire that original
failure, validate a repair hypothesis and submit a correct patch. Remaining
alternatives included semantically wrong inputs, ignored output or an unsound
predicate, an incorrect repair, and resource/infrastructure failure. The user
approved the exact prepared scope with "승인할게". This authorized one new solve;
no previous allocation was reopened.

- Task: `tasks/dev-train/current-dev20/13/public.yaml`, Astroid-1333 dev-train.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh, 25,000 requested output ceiling.
- Credential file: repository `.env`; invocation-wide cap USD 0.88; repeat 1.
- Limits: 40 model calls, 100 actions, four edits, 1,800 active seconds and
  1,920 seconds outer supervision. Two post-submission public checks shared
  at most 120 seconds.
- Policies: segmented-v1, result-or-size-v1, brief-v1, probes/none, bounded-v1
  original acquisition, repair-recheck/protected-v1 and completion-recovery-v1.
- Runtime commit: `773b5bb36c7a2c0c7fe789992b57583e5932e08c`.
- Runtime hash: `sha256:cfb716fbb8c84eb7fd4dfffb4cfeab89ac9e8ed220df16e6ca406f5a55adbb25`.

Docker 29.8.0, prepared source/dependencies, the existing probe and evaluator
image digests, current pricing and tracked runtime/task identities passed
preflight. No image was pulled or built. The task, model, cap, policies and offline
environment matched the historical repair pilot. Interface and guidance changed
together; one exposed-task sample is not a controlled causal improvement estimate.
No prior solver context, operator program or repair hint entered the fresh agent.

Executed from `C:/Users/geonj/Documents/PatchLoop`:

```powershell
uv run --locked --offline python C:/pt/invoke24-live-ready-v1/supervisor.py
uv run --locked --offline python C:/pt/invoke24-live-ready-v1/assess_submission.py
```

## Results

Run: `run_dev_fc5da9c1c21e49b5`. The supervised CLI completed with process exit 0
in **436.434 seconds**; task terminal was **COST_CAP_REACHED**. Cost was
**USD 0.788843550**, fully settled. There were 30 model calls, 32 input counts
and 28 executed actions. No transport/count/billing uncertainty or hard timeout
occurred. The single probe returned with complete capture and confirmed cleanup.

| Stage | Observation |
| --- | --- |
| Original requests / preflight rejections | 1 / 0 |
| Original probe dispatches / returns | 1 / 1 |
| Native caller arguments | Correct single list argument; `do_exit=False` |
| Actual F0010 diagnostic capture | Present on stdout; stderr empty |
| Declared failure / desired JSON comparison | mismatched / mismatched |
| Normal-input control | Not constructed or executed |
| Search / read actions after the probe | 15 / 12 |
| Accepted edits / required checks / finish | 0 / 0 / 0 |
| Submitted patch / delivery state | None / none |
| Independent acceptance / safety | NOT_RUN / NOT_RUN |
| Post-submission public missing / control checks | NOT_RUN / NOT_RUN |

The post-submission command exited 1 at its `stop_remaining` assertion because
the invocation had closed at the cost gate. It dispatched no public check and
created no normal assessment result. A separate `assessment-not-run.json` receipt
preserves this guard outcome and absence of a submission. The command was not
changed or retried, and NOT_RUN is not an evaluated task failure.

## The call worked, but its observation contract did not

The model called `pylint.lint.Run` through
`observed_target(...)(['src/project'], do_exit=False)`. The selected fixture had
the parent `src/__init__.py`, a valid `src/project/file.py`, and no project init.
This produced the actual missing-init F0010 diagnostic on stdout. Unlike the
previous run, neither list flattening nor failure to collect emitted output
blocked this observation.

The authored comparison values were nevertheless incompatible:

| Field | Declared failure | Actual observation |
| --- | --- | --- |
| outcome | `fail` | `returned` |
| exit_code | `32` | `null` |
| stderr_has_F0010 | `true` | `false` |
| Diagnostic storage | `message` | `stdout_tail`; empty `stderr_tail` |
| Shape | four fields | six fields, also including `exception` |

The desired value used only three fields. Exact frozen JSON equality therefore
could not match either expectation. `returned` describes completion of the
callable, not successful linting. With `do_exit=False`, the adapter observed no
SystemExit and its exit code remained null. The diagnostic was available in
`stdout_tail`, while the boolean tested stderr. No normal-input control was
included. Thus actual failure output was observed, but the declared original
failure/control evidence was not acquired.

This distinction matters: captured output and correct argument placement were
used in a real model-authored program. They did not ensure that the model mapped
the result to a valid semantic predicate. The host preserved both mismatches;
there was no finish call or `unverified_delivery` result in this run.

## Exploration and completion funding

After the probe, all 27 executed actions were reads/searches; no second probe,
mutation or check followed. Two responses were incomplete at their admitted
output ceilings, on model calls 24 and 30: respectively 2,487 and 7,244 tokens.
Provider usage metadata classified all of those output tokens as reasoning;
their contents were not read. These were known, billed incomplete responses,
not transport or billing uncertainty.

The first incomplete response consumed the run's funded protocol correction.
Call 25 received the full requested 25,000-token ceiling and returned a valid
action, but the later sequence still contained only inspection. On the last
model call, the completion horizon exposed only mutation and stop. That response
again exhausted its ceiling without a usable action. The next completion cost
reservation did not fit, producing COST_CAP_REACHED with USD 0.091156450 unspent.
The cap was not exceeded; remaining money did not authorize another solve.

This shows the practical limit of the existing funding policy in this sample:
reserved successor costs and one correction allowance did not guarantee an edit
or a valid final action. It does not establish that additional budget would
repair the task or that a different funding policy would succeed.

## Decision and evidence

The integrated acquisition-to-repair criterion was not met. Retain the narrower
finding that the model used native list arguments and captured the real diagnostic.
The first unresolved issue is a consistent failure/desired observation schema
over the emitted channel, including a normal-input control. A later unresolved
issue is the transition from delivered evidence to a repair after extended
inspection. No new prompt, gate, budget or additional experiment is selected here.

- Plan, exact approval, command and preflight: `C:/pt/invoke24-live-ready-v1/`.
- Request hash: `sha256:e2bb892b7299a5c52b54cf358ffc44823ea4ce29c55eb001a953a7e5c14c821b`.
- Process and public action evidence: `C:/pt/invoke24-live-v1/`.
- Collection hash: `sha256:0ab58e714c441b62828fca26a7c4f4ae945499d179c8241badf2fe65dfc25407`.
- Separate public interpretation: `public-analysis.json` in the result root.
- Post-assessment guard receipt: `assessment-not-run.json` in the result root.

Three journals (4 preparation, 425 solver and 18 operator events at collection)
and 146 CAS objects passed hash verification before collection/closeout events
were appended. All 110 frozen runtime/task files remained unchanged. Action IDs,
input hashes and all dispatched provider calls matched their settled receipts.
Continuation and evaluator artifacts were hashed opaquely; no provider reasoning,
private tests, reference patch or detailed evaluator output was inspected.

The allocation is closed; official=false and claim_eligible=false. No automatic
retry, resume, extra sample, budget transfer or runtime modification occurred.
The prior runtime validation was not repeated. Documentation-only checks and
the final documentation commit are recorded in the operator journal.
