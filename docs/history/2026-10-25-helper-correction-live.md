# Helper pilot: first repair, rejected call-path diagnosis

Date: 2026-10-25. Follow-up to [helper correction](2026-10-25-helper-correction.md).

## Material Passport and selected question

- Origin: academic-research-suite / experiment-agent, run mode.
- Version: `helper-correction-live-v1`; `official=false`, `claim_eligible=false`.
- Verification: one live execution, saved public receipt/context analysis and
  static request inspection. No independent repeat or acceptance evaluation.
- Runtime commit: `e4f0b83108f944f5a98e20f2c82474be814c943a`.
- Runtime hash: `sha256:455ebad690711975660a4775374ad9d7589fcad92f54543b4984e650fcbe8dc5`.

The [previous run](2026-10-25-callpath-live.md) failed in helper code before its
intended diagnostic, then spent remaining opportunities on source inspection and
made no repair. The current intervention clarifies helper APIs and provides one
same-question source correction for a confirmed preflight error before the first
accepted mutation. The question was whether the actual model would obtain useful
diagnostic evidence, reach a first repair, and resolve the original F0010.

The predeclared alternatives included no eligible helper error, irrelevant
diagnosis, ineffective repair, and resource/trajectory limitations. Absence of an
error would leave correction NOT_EXERCISED, not prove prevention. No historical
helper source, repair hint or diagnosis was seeded into the solver.

## Frozen scope

The current user experiment request, within the continuing exact scope, authorized
one new invocation. Previous allocations stayed closed. Task:
`tasks/dev-train/current-dev20/13/public.yaml` (Astroid-1333), model
`gpt-5.4-mini-2026-03-17`, xhigh, credential file
`C:/Users/geonj/Documents/PatchLoop/.env`, repeat 1, invocation cap USD 1.20.

Normal output remained 40,000 tokens and independent protocol correction 25,000.
Limits remained 40 model calls, 100 tool actions, four accepted mutations and
1,800 active seconds, with 1,920-second operator supervision. Context remained
segmented-v1/result-or-size-v1, planning brief-v1, probes enabled with policy none,
repair-recheck, protected-v1 inspection, bounded-v1 original acquisition and
completion-recovery-v1 cost admission. The run_probe recommendation stayed enabled.

Only runtime and the fresh state root changed from the preceding request. Prepared
source/dependencies, task hashes, existing images and trusted probe profile were
identical. The two frozen post-submission public checks retained a shared 120-second
bound and were conditional on a submitted patch. No retries, resume, replacement
solve, image acquisition or cap changes were permitted.

The [official model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
confirmed the snapshot/xhigh support, and [standard pricing](https://developers.openai.com/api/docs/pricing)
confirmed input/cached-input/output rates of $0.75/$0.075/$4.50 per million tokens.
The exact same runtime's local evidence was reverified and reused: 64 focused PASS,
346 quick PASS including isolated mock evaluation, Ruff PASS and five documentation
checks. This reuse did not create new live repair evidence.

## Observed result

Run `run_dev_ad2f36ee45664396` ended `VERIFICATION_INCOMPLETE`.

| Measure | Result |
| --- | --- |
| Model / input-count / tool calls | 33 / 35 / 33 |
| Search / read / probe / mutation actions | 16 / 12 / 4 / 1 |
| Probe executions / rejected requests | 2 / 2 |
| Helper requests, helper errors, helper corrections | 0 / 0 / 0 |
| Accepted mutations | 1 |
| Original baseline / candidate | F0010 present / still present; comparable |
| Call-path diagnosis requests / executions | 2 / 0 |
| Registered checks / selected tests / submission | NOT_RUN / NOT_RUN / NOT_RUN |
| Frozen public assessment / independent acceptance / safety | NOT_RUN / NOT_RUN / NOT_RUN |
| Settled cost / unused allocation | $0.979441500 / $0.220558500 |
| Process wall time | 556.779 seconds |

Call 2 reproduced the directory failure while the file control had no F0010.
Both per-call captures were complete and host/authored judgments agreed. Calls 1
and 3-29 performed 28 source inspections. The first accepted mutation came at
call 30 after completion-horizon closure offered only replace_text and stop_task.

The mutation changed `astroid/modutils.py::_spec_from_modpath`: when a package
directory had no initializer, return a namespace spec instead of a source spec.
The automatic replay used the same frozen original program and comparable
caller/input/environment identities. It still observed F0010 for the directory
and none for the file control. Changed-line collection observed no entries into
the changed executable ranges 631-633 and 635-636. This refutes the predicted
original-call effect; it does not establish that the whole function never ran.

The original-failure path gate then activated. The actual dispatched public state
included distinct original `replay_action_id` and latest `failure_action_id` fields.
The model tried to diagnose the path, but neither request executed:

1. Call 31 used the latest automatic failure action as replay_action_id instead of
   the delivered original root. The path admission gate rejected it. Static
   inspection also finds line 270 outside the requested manager function's 250-269
   range, but that was latent behind the identity error, not the reported rejection.
2. Call 32 produced no action: it exhausted the affordable 6,969-token output
   ceiling. Metadata reports all 6,969 as reasoning output; reasoning content was
   not inspected. The one protocol correction was then dispatched.
3. Call 33 used the correct replay root and returned an action within 11,727 of
   its 25,000 available output tokens. It requested line 272 for
   `check_modpath_has_init`, whose AST range is 261-271. A second watch included
   lines 324-325 outside `modpath_from_file_with_callback`'s 308-323 range.
   Source preflight rejected the out-of-function line request.

Two rejected diagnostic requests exhausted that bounded opportunity. This was
the terminal cause: seven model-call slots and $0.220558500 remained, with no
terminal blocking-resource flag. The protocol correction returned an action; it
did not exhaust its 25K allowance. The new helper correction never activated.

## Resource and interface implications

The 40K normal setting is a ceiling, not every call's funded allowance. The
completion reserve admitted 8,308 tokens for call 31 and 6,969 for call 32 while
preserving future minimum calls and the separate protocol correction. Call 33
received the reserved 25K and produced a request, but that request was invalid.
Increasing only output capacity therefore does not address the observed final
line-range error; a causal benefit from another budget remains unmeasured.

Call 31 offered one source-preparation read/search, which the model did not use.
After its rejected request, completion-horizon closure offered only run_probe and
stop_task, although the nested path state still said preparation_available=true.
Thus a path-local allowance was not a currently offered read opportunity. This
distinction and manually composed replay/function/line identities merit examination
before another paid pilot. No runtime correction was made during or after this run.

## Decision, limits and evidence

The honest incomplete return and original-failure feedback worked: the unsuccessful
candidate was not submitted. The model made one repair, versus none in the earlier
trajectory, but it used no helper and did not fix F0010. This run neither validates
nor rejects the new helper correction's live effectiveness. Call-path diagnosis
was requested but remains unexecuted by the live model.

This is one stochastic trajectory on an exposed development task. The historical
comparison is descriptive; first-repair counts, prompt exposure and lower cost do
not identify a causal benefit. Local mechanism PASS, returned probe status,
original-case evidence, submission and independent acceptance are separate claims.
There is no solve-rate/generalization estimate, no significance test, and no basis
for declaring the whole function unexecuted from changed-line observations alone.

The next question is how to make the already selected replay identity and current
function/line constraints usable without another manual request error, while
retaining bounded execution. This does not justify an automatic paid repeat.

Evidence roots:

- Preparation: `C:/pt/helper-correction-live-ready-v1`, request hash
  `sha256:b4fd4993050300df72dbd8b65b7ff440fc55922f4ab98fd03f1caf7a34dddcf2`.
- Run: `C:/pt/helper-correction-live-v1`, collection hash
  `sha256:b44c02def83d4710ed0c8df6f6d25f24bc8bf5be219c3801aa42e49a702ead4a`.
- `public-analysis.json` hash
  `sha256:db9d0516090acdbccc59a6ad10546008edc780654b8250fc5a26a052f5091c78`.
- `request-analysis.json` hash
  `sha256:b309e87675521c0453709e2e34e694bd9418f03059f5cec77f5309770f515c1e`.

Hash-chained journals, action/input identity pairs and 162 content-addressed objects
passed collection integrity checks; final closeout includes subsequent audit records.
Runtime/task/prepared inputs stayed fixed. Both executed probes confirmed cleanup;
billing and counting settled. No submission meant the conditional public assessment
and independent evaluator did not execute. Analysis added no provider or target
execution and inspected no private evaluator contents or provider reasoning.
Allocation is closed; unused funds do not authorize continuation.
