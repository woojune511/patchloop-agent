# First reproduction model comparison: request completion without target execution

Status: A and B each executed once; all new usage settled; allocation CLOSED.
Official=false. This is a development-exposed first-request diagnostic, not a
clean-start repair, benchmark acceptance or held-out result.

## Question and conditions

The [prepared model comparison](2026-10-28-first-reproduction-model-plan.md) tests
whether changing the model helps construct a valid first original reproduction.
The preceding description pair reached different failures: long mini reproduced
F0010 without positive processing evidence, while short mini failed validation.
The model setting was therefore an unresolved explanation, not a preselected cure.

A used gpt-5.4-mini-2026-03-17 and B gpt-5.4-2026-03-05, both xhigh, each once.
Both received the recorded 8,958-character long description and the same public
checkpoint before event 65 of run_dev_3e21775752a54cae. Historical opaque reasoning
was omitted. The mini-priced completion forecast was removed symmetrically from
the first visible state, while host reservation and actual accounting remained
active. First API requests differed only in model ID; real first input counts
were identical at 19,947 tokens. No previous response, repair, selected diagnostic
or private evaluator material entered either request.

The user explicitly approved manifest
`sha256:63b8481dea550eefe078e51755cf340ab116f4dee8033c7aaacc149210efa7f9`,
new USD 4.41415320 per arm / USD 8.82830640 total, with the repository `.env`.
Input 60K, ordinary/correction output 40K/25K, remaining model/tool limits 16/34,
solver time 1,903s and evaluation reservation 390s were retained. Both actual model
response IDs match their snapshots. No ceiling was narrowed by cost admission.

Each arm ended at its first settled probe, explicit stop or terminal response
failure. Existing protocol correction before a probe was allowed. Tool/execution
feedback after the first settled probe was not returned for another response.
No edit, regression, finish or isolated evaluation was scheduled or performed.

## Results

| Measure | A: mini | B: full |
| --- | ---: | ---: |
| New model / input-count calls | 2 / 2 | 1 / 1 |
| Input tokens per response | 19,947; 15,947 | 19,947 |
| Output tokens per response | 40,000; 25,000 | 21,356 |
| Reported reasoning output | 40,000; 25,000 | 20,288 |
| Model response seconds, summed | 376.641 | 249.692 |
| New active seconds | 382.744 | 261.382 |
| Complete tool request | no | yes |
| Host request admission | NOT_RUN | admitted |
| Probe executions | 0 | 1 |
| Actual declared target calls | 0 | 0 |
| Original F0010 reproduction | NOT_RUN | NOT_RUN |
| Positive target processing | NOT_RUN | NOT_RUN |
| New cost USD | 0.3019677 | 0.3702075 |

Total new cost was **USD 0.6721752**; group wall time was 648.943 seconds.
Mini benefited from 15,616 and 10,240 cached input tokens; full reported zero cached
input. Actual cost includes those cache differences and each model's rate table.
The historical USD 0.08584680 per reconstructed arm is excluded from new spending.

### Mini: output exhausted before a tool request

Both responses ended incomplete with `max_output_tokens`. Output-item metadata
contains reasoning only, with zero tool calls. The first received the full 40K
allowance; its ordinary protocol correction received the full 25K. Neither reached
a probe or mutation. Correction used ordinary segmented reconstruction after an
`encrypted_item_bytes` transition. No opaque reasoning body was inspected.

Inputs stayed well below the 60K ceiling. This is an observed request-construction
failure, not evidence that the public issue was reproduced or a patch failed.
All count and usage receipts settled, so this is a known negative result rather
than transport/billing uncertainty. The pair properly continued to B.

### Full: valid tool envelope, invalid helper configuration before target entry

Full produced one run_probe request. Request validation accepted it, and the Docker
probe process ran with cleanup confirmed. Its outer tool receipt is `succeeded`,
meaning the operation returned a result; the nested probe result is `failed`,
exit code 1. These must not be collapsed into successful reproduction.

The authored program chose the installed `pylint.run_pylint` console entrypoint,
created the missing-init fixture, isolated HOME/PYLINTHOME under output roots, and
passed eight public setup comparisons. It then constructed:

```python
target = observed_target(..., expected_exceptions=(SystemExit,))
```

`observed_target` accepts only Exception subclasses in this tuple
(`patchloop/dev/probe_call_capture.py`, lines 34-42). SystemExit is a BaseException
subclass outside Exception and is already handled separately by the actual call
wrapper (lines 89-105). The redundant setting therefore raises
`ValueError: invalid observed_target settings` before either target invocation.
The four input paths and environment keys were not the failing setting.

The shared long description says that `call.exit_code` contains the observed
SystemExit code and illustrates `expected_exceptions=(ValueError,)`. It does not
state the Exception-subclass restriction or explicitly say that SystemExit is
already handled and must be excluded from the tuple. This is an undocumented
helper constraint, not evidence that the model ignored an explicit prohibition.
The different same-call positive-processing requirement was explicitly described.

The public source starts that construction at line 43 and supplies SystemExit at
line 51; actual `target()` calls at lines 56 and 60 were never reached. Recorded
calls and exception-call frames are empty. Both desired and declared-failure
comparisons are `not_compared`, with `declared_call_unobserved_or_incomplete`.
Neither F0010 nor file processing was observed. Setup PASS is not target execution.

The selected observation also has a separate static limitation: rules are null;
it records target F0010/path absence and W0611 presence only on the direct-file
control. Its desired JSON does not require positive processing for the problematic
directory call. A directory no-op while the direct-file control still works would
not be excluded by these selected fields. This is a property of the authored
observation, not an executed no-op experiment or an actual repair result.

## Decision and limits

Changing the model cleared the response-construction barrier **in this pair**,
but did not meet the prespecified valid reproduction/processing objective. Full
progressed to a concrete helper API incompatibility; it did not reproduce or repair
F0010. There is no basis here for a default-model adoption or a repair-gain claim.

The next useful intervention is to resolve the narrow SystemExit helper-contract
inconsistency locally, while preserving a distinct positive witness for the same
problematic call. Another model comparison or a larger context ceiling would not
address the full arm's observed failure. Do not treat a manual correction as model
recovery: the ability to use this execution feedback requires a separately scoped
feedback trial, because this pair deliberately stopped at the first settled probe.
Removing the redundant exception option would avoid this specific guard; whether
the later calls reproduce the issue is untested, and that change alone would not
repair the independent positive-processing gap.

Each model ran once. The previous long-mini success also differs by the common
cost-forecast projection and a new stochastic trajectory; it is not a matched
repeat proving that either projection or randomness caused the changed result.
Stable model superiority, correction after tool feedback, complete observation
coverage, clean-start repair, submission and independent acceptance remain unresolved.
Unused allowance is closed and does not fund additional probes or repetitions.

## Evidence and closeout

- Executing commit: `e974094c61f576da678edcc681b0fdbbdc60ae18`.
  Runtime unchanged at
  `sha256:bc07573f50542452e0ba9f0fa47298f07c5542d4575958013dbb723bd0447080`.
- Plan/launcher: `C:/pt/first-reproduction-model-plan-v1/manifest.json` and `run.ps1`.
  Read-only source/image/dependency preflight was READY before approval/dispatch.
- Result root: `C:/pt/first-reproduction-model-run-v1`; `result.json`, `analysis.json`,
  separate A/B journals and shared journal. Public authored source: `B-probe.py`;
  hash `sha256:8136ef9e52902adae48d83a8b360a3c03ae89464d438c6bf6b4198f100049701`.
- Independent metadata audit PASS: first sealed requests and all counted/dispatched
  requests agree, effective 40K/25K ceilings hold, usage matches rates, arm/group
  cost totals agree, and no count/provider/action/probe remains unresolved.
  Source and arm hash chains validate; no historical bytes were changed.
  `analysis.json` hashes the group prefix through comparison_finished; later audit
  and closure events extend that chain and do not change the inspected prefix.
- Local preparation validation: 14 owner/fork/ledger checks in 21.15s, quick 577
  PASS including isolated mock, Ruff PASS; final documentation checks 5 PASS.
  These establish collector mechanisms, not model quality.
- No retry, extra repetition, code edit, submission, regression or isolated
  acceptance was executed. No image was pulled/built or Docker Desktop started.
