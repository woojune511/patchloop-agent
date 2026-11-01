# Live diagnosis mode: contract delivered, no diagnostic action returned

Date: 2026-10-26. Follow-up to the [local change](2026-10-26-diagnosis-mode.md).

## Material Passport and question

- Origin: academic-research-suite / experiment-agent, mode run;
  version `diagnosis-mode-live-v1`.
- Evidence: live-executed and public receipts analyzed; `official=false`,
  `claim_eligible=false`. No independent reproducibility rerun.
- Runtime commit: `ebd0aff7d3691bace189785ca7d66ef98f36f620`.
- Runtime hash: `sha256:6e57fa53d69fb0dc138c5562b0a1346c401ce12d194921d1fc6e64294ab1a995`.
- Run: `run_dev_d5a051b1ed8f4536`.

The [previous pilot](2026-10-26-diagnosis-request-live.md) returned an incompatible
diagnosis request and never executed it. This prevented testing whether observing
the failed call path could guide a repair. The present question was whether a
host-selected diagnosis schema, short description and precise invalid-field
feedback permit valid diagnosis followed by an evidence-based F0010 repair.

The intervention restricts question/source/replay/purpose to null and requires
symbolic call_path while diagnosis is pending. The original identity and current
source remain host-bound. The alternative outcomes recorded before dispatch included
no request, irrelevant function selection, unusable trace, ineffective repair and
resource exhaustion. Construction, execution, diagnosis uptake, original behavior,
submission and independent acceptance were separate decision criteria.

## Frozen execution scope

The current user request authorized one fresh invocation, not reopening any prior
allocation. The request and stop rules were recorded before dispatch.

- Task: `tasks/dev-train/current-dev20/13/public.yaml`, exposed dev-train Astroid-1333.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh; credential file
  `C:/Users/geonj/Documents/PatchLoop/.env`.
- Normal output ceiling 40,000; one protocol-correction allowance 25,000;
  repeat 1; invocation cap $1.20.
- Limits: 40 model calls, 100 actions, four accepted mutations, 1,800 active
  seconds; operator supervision 1,920 seconds.
- Segmented context, result-or-size boundaries, brief planning, probe policy none,
  repair-recheck, protected inspection, bounded reproduction acquisition and
  completion-recovery-v1 unchanged. run_probe recommendation unchanged.
- Prepared source, dependencies, existing probe/evaluator images, probe profile and
  two frozen post-submission public checks unchanged. The latter share 120 seconds
  and require a submitted patch. No image acquisition or Docker Desktop launch.
- Zero SDK retries; stop on count, transport, billing, cleanup or source uncertainty.
  No retry, resume, replacement, forced diagnosis or limit increase.

Relative to the previous request, only the state_root field changed; the runtime
contains the documented intervention. This is a descriptive historical comparison,
not a paired causal estimate. The fresh model trajectory and generated repair differ.
Preflight reverified the same-commit local evidence (focused 96 PASS, quick 366 PASS,
Ruff PASS and isolated mock evaluation) without rerunning those suites. Official
model/pricing verification was reused from earlier in the same conversation;
its original verification timestamp was retained.

## Observed sequence

| Stage | Observation |
| --- | --- |
| Model call 1 | Original probe omitted python_source; preflight rejected `/python_source` before execution |
| Call 2 | Supplied a 1,503-character program; receipt linked the corrected field to the rejected action; original failure acquired |
| Source inspection | 28 read/search actions before the first accepted mutation, including one after the rejected mutation |
| Call 30 | replace_text had identical old/new text; contract rejected it and left the diff empty |
| Call 32 | First accepted mutation changed `_spec_from_modpath` in `astroid/modutils.py`; 31,472 output tokens, including 30,751 reasoning tokens |
| Automatic original replay | Same F0010 remained; control remained healthy; host and authored judgments agreed; changed lines 631-633 were not observed |
| Call 33 | Correct pending-mode schema delivered; 16,380 output tokens, all reported as reasoning; max_output_tokens with no action |
| Call 34 | Same schema; reserved 25,000-token protocol correction; all reported as reasoning; max_output_tokens with no action |
| Terminal | VERIFICATION_INCOMPLETE, stop cause INCOMPLETE_RESPONSE; no diagnostic request, check, submission or evaluation |

The successful mutation added a missing-init branch that returns PY_NAMESPACE from
the PKG_DIRECTORY branch of `_spec_from_modpath`. Its predicted effect was to avoid
loading a missing `src/project/__init__.py`. The frozen original call contradicted
that effect. The changed-line observation does not establish whether the whole
function was entered; there was no diagnostic trace to resolve the path.

Both original executions returned `bug_has_error=true, control_has_error=false`.
The failure input was the directory `src/project`, and the control was
`src/project/file.py`. Captured F0010 output and host/authored JSON agreed in both
executions. The run did not replace the original with an easier test after mutation.

The two actual prepared diagnosis schemas had the same tool hash, four null-only
fields, required symbolic call_path and an 805-character description. Both copies
of the preparation state agreed with the offered read/search tools. This supports
contract delivery and state projection. With zero returned diagnosis requests,
live admission, host construction, diagnostic execution, precise diagnosis-field
correction and trace-guided repair are NOT_EXERCISED. Helper recovery is also
NOT_EXERCISED. Zero rejected diagnosis requests is not evidence of valid model use.

## Resources and outcome

- Settled cost: **$0.999174600 of $1.20**; unused $0.200825400. Allocation closed.
- Wall time: **773.569 seconds** (12 minutes 53.569 seconds); no hard timeout.
- 34 model dispatches, 35 input-count calls, 33 tool actions; one accepted mutation.
- Tools: 17 searches, 11 reads, two mutation requests, three run_probe actions
  (one preflight rejection and two actual original executions).
- Tokens: 1,325,934 input, including 752,128 cached; 113,869 output, including
  101,820 reasoning. Reasoning counts are included in output, not additive.
- Required checks, selected tests, finish, frozen post-submission checks,
  independent acceptance and safety: **NOT_RUN**. No submitted patch.

The configured 40,000 normal ceiling was an upper bound, not a guaranteed grant.
Before call 33, settled cost was $0.762499800 and future reservation was
$0.339804000, including $0.157500000 for the one correction; current admission
funded 16,380 output tokens. Call 34 received the full reserved 25,000. The two
diagnosis-stage calls spent $0.236674800 and returned no action. Termination followed
the second incomplete response, not the invocation cost, call or time cap.
This does not show that reallocating the unused balance would have produced a
useful action, or that the current reservation is optimal.

## Decision and limits

Retain the schema correction as a locally verified contract fix. This pilot does
not establish live diagnosis or repair effectiveness. It narrows the observed
bottleneck to action generation before diagnosis execution, despite successful
delivery of the narrower contract. The earlier incompatible-field rejection did
not recur because no request was returned; it was not tested by a valid request.

The next unresolved question is why the diagnosis state still produces no action,
after a late first repair and substantial earlier exploration. Public delivered
state, action-selection requirements and resource allocation can be inspected
before another implementation or paid comparison. Shorter descriptions alone were
insufficient in this trajectory; model behavior, remaining context complexity and
budget allocation are not disentangled. No provider reasoning content was read.
Do not infer a general repair gain, regression or optimal cap from this one run.
No additional live run or continuation is authorized by this record.

## Evidence and validation

Preparation: `C:/pt/diagnosis-mode-live-ready-v1`.
Execution and append-only hash-chained dev-run-v1 journals:
`C:/pt/diagnosis-mode-live-v1`.

| Artifact | SHA-256 |
| --- | --- |
| request.json | `1dd14ee8d1c94e55e4cbda654aaf22e6b602d9b4f07dc557acbb11a874fbfa73` |
| collection.json | `c65d347cc83b2e33d652c8f037283508849107746d03a717fd1cdb667c53eb68` |
| public-analysis.json | `e53162fc2f15571bae2e36efb61b2db66584473065c6a509675ae204df179575` |
| schema-analysis.json | `d9b1e38c88080d8e37fd0ad95324106695aaae26a0e2bda4647eef579cc41e13` |
| Candidate diff, not submitted | `1ac127d0b6c304ac53f23ba4724953b59e25e665926f2b00bae9253af9d6ad57` |

All provider starts settled, costs matched CLI accounting, and action_id/input_hash
pairs matched. The initial collection verified 167 content-addressed objects,
journal chains, sealed inputs and unchanged runtime. Later analysis artifacts and
the documentation commit are bound by the separate closeout. Post-run audits made
zero provider calls and zero target executions. The conditional public assessor
recorded NOT_RUN because there was no submission.

Documentation validation and final provenance are recorded in closeout.json.
No runtime code changed during this experiment. Closed historical reports,
unrelated working-tree edits and all failed-run evidence were preserved.
