# Actual callable signatures and bounded argument correction

Status: implemented and locally validated. Official=false.
No provider dispatch, Docker benchmark execution or new paid experiment.
Implementation baseline: `3c184f93`.

## Problem and decision

The [helper follow-up](2026-10-28-helper-first-reproduction-results.md) returned
`TypeError: too many positional arguments` before entering `pylint.run_pylint`.
The model set sys.argv and also passed a positional list to this zero-parameter
entrypoint. Helper construction had passed, but neither F0010 nor the desired
processing observation ran. The response was within its token limits. This is a
concrete failure of adapting the request to the public callable, not evidence that
larger context or output limits are needed.

The old description included a generic list-argument example, while the wrapper
already inspected the actual signature internally. Its error could be returned
without a dedicated opportunity to correct that original request. We expose this
existing information and reuse the existing bounded pre-target correction path,
rather than add a retry loop, tool or argument-coercing adapter.

This addresses the observed request defect. Whether the model will use the new
information is unresolved. Failure despite a delivered signature would weaken the
information-gap explanation; an entered target failure would require behavioral
diagnosis, not another argument-correction allowance. The prior diagnostic's
first-result stop rule also prevented feedback by design and remains unchanged.

## Change

Fresh v9 wrappers expose `target.signature()`, returning the actual callable's
signature string (at most 256 characters) or None when unavailable/oversized.
Resolution does not invoke the declared target. A zero-parameter CLI should use
`target()` after setting sys.argv. None does not imply a zero-parameter callable.
Both first-original and general descriptions now explain this distinction.

Every invocation records its actual signature and explicit `binding_error`.
The latter means Signature.bind raised TypeError with an available bounded
signature, before `target_started`. A target's own TypeError, unknown signature,
resolution failure or input-snapshot error cannot be promoted to that evidence.
Signature metadata is not an input-identity condition. The largest supported
entrypoint with call-path hooks fits the unchanged 8K host-code allowance; model
code keeps its separate limit. V1-v8 observers retain their exact bytes.

Before the first accepted edit, a settled v9 original request may create
`original-argument-correction-v1` only when every recorded call proves no target
entry and at least one has an explicit binding error. Action/input/program/diff
and execution receipts must agree, with confirmed cleanup and no uncertain return.
It shares the existing single helper-correction opportunity. Legacy rows do not
retroactively create the new opportunity.

The next model context receives the failed source, actual signature, arguments
and argv. Only changed source with the exact question, purpose and call-path
request, a new action ID, or stop is allowed. The original-only small schema stays
active. Any correction attempt consumes the allowance, including a rejected
request. Another binding failure cannot replenish it. All calls must enter with
complete captures to settle argument correction; original behavior and verification
remain separate obligations. Settled pre-target attempts remain audited but do not
become failed reproduction cases for the corrected program.

Scheduler and direct gateway both retain original-attempt/rejection quotas. The
forecast reserves the current correction and one prospective original replay, plus
repair/check/finish work, without reserving acquisition again. Model/tool counts,
ordinary and protocol-correction output allowances, time and dollar caps remain
unchanged. Existing action_id + input_hash recovery reuses durable probe returns;
uncertain execution never receives a blind retry. Surface v68 records the changed
serialization/behavior contract, not a separate runtime activation process.

## Local validation

The focused command is:

```powershell
uv run --locked --offline pytest @tests/argument-correction.txt --basetemp C:/pt/<unique>
```

The final focused run passed **123 tests in 55.564 seconds**, including isolated
mock evaluation. Current contract/description pins passed **20 tests in 1.250s**;
documentation passed **5 tests in 0.110s**. Ruff and diff checks passed. Controls
use trusted local fixture subprocesses and scripted model responses; no credentials
or benchmark inputs are needed. They cover signature-guided zero-argument/keyword
calls, error classification, exact feedback delivery, one correction, quota and
cost/time reservations, durable recovery, legacy observers and isolated mock
evaluation. Current contract pins change only for the intentional descriptions
and v68 fields; historical pins remain unchanged.

The recovery-cost control retains 40K ordinary output, a separate 25K protocol
correction, and three successor model calls. Its fixture reserves 182 seconds:
two 35-second probe windows, one 22-second public check and three 30-second model
windows. Those are fixture-specific checks of unchanged accounting, not new live
settings. A corrected request leaves the first failed request in the audit and
acquires exactly one baseline case; it does not mark the original obligation verified.

JUnit receipts and hashes are preserved in the append-only dev-run-v1 journal
`C:/pt/original-argument-correction-local-v1/runs/run_dev_argumentcorrection.jsonl`.

The initial selection ran 122 tests in 57.171s: 121 passed, one existing helper
budget fixture failed. The fixture funded 25K output while requesting 40K ordinary
output. Both unmodified HEAD and the new policy rejected that allocation identically.
Funding was aligned to 40K while retaining the separate 25K protocol-correction
allowance; its two affected controls passed. This was a fixture correction, not a
runtime relaxation. The full quick suite is intentionally not rerun for this
bounded task; the new tests are registered there for broader future integration.

The decision is to keep signature inspection and one explicit feedback correction
under existing limits. Local mechanism success does not demonstrate actual-model
uptake, F0010 reproduction/repair, public-task correctness or isolated benchmark
acceptance. The next live question is reaching and observing the original call
after this specific request error; no execution is authorized by this record.
