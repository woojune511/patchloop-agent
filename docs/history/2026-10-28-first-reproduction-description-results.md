# First reproduction description A/B: long admitted, short rejected

Status: A and B each executed once; all new usage settled; allocation CLOSED.
Official=false. This is a development-exposed public-checkpoint diagnostic, not a
clean-start repair or held-out result.

## Question and fixed conditions

The [prepared comparison](2026-10-28-first-reproduction-description-plan.md) asks
whether removing irrelevant helper/replay/repair instructions helps construct the
first original reproduction request. The preceding fresh run exhausted both output
ceilings before producing a usable request, so this was the immediate bottleneck.

A used the recorded 8,958-character description; B used the 4,408-character first
reproduction description. Both reconstructed the same public pre-dispatch checkpoint
at event 65 of `run_dev_3e21775752a54cae`. Historical opaque reasoning was omitted
symmetrically. First requests differed only in `run_probe.description`; parameters,
public inputs, host validation, mini/xhigh, 40K/25K output, 60K input, remaining
resources and completion reservations were identical. Each arm stopped at its first
settled probe result, including preflight rejection. No model received the other
arm's result, previous patch or evaluator material.

The user requested execution after the concrete plan and USD 8.82830640 pair cap
were presented. Credential location remained the repository `.env`. No credentials
were printed or copied into target execution.

## Execution prerequisite correction

The initial launcher stopped before creating a result root or making any credential,
count, model or target call: its tracked-file checker received `patchloop` and
`diagnostics` directory names, while the checker requires literal tracked filenames.
This was a collector defect, not a model failure. The original zero-cost attempt is
preserved in the v1 preparation journal.

Commit `2e646394` changes only the collector's file enumeration and its test. The
actual tracking/HEAD guard is preserved. Nine owner tests passed in 13.37s, including
a real temporary Git check that accepts clean files and rejects modified/untracked
ones; Ruff passed. V2 was resealed. Comparing manifests found only
`implementation_hash` and `result_root` differences: requests, runtime, model,
resource limits and pair cap remained exact. No uncertain provider call was retried.

## Observed results

| Measure | A: long description | B: short description |
| --- | ---: | ---: |
| New model / input count calls | 1 / 1 | 1 / 1 |
| Input tokens | 20,262 | 19,440 |
| Output tokens | 29,927 | 1,561 |
| Reported reasoning output tokens | 29,299 | 516 |
| Model response seconds | 211.711 | 11.812 |
| Host request validation | admitted | CONTRACT_ERROR |
| Probe executions | 1 | 0 |
| Declared target calls started | 2 | 0 |
| Original F0010 | observed | NOT_RUN |
| New cost USD | 0.147276 | 0.0216045 |

Total new cost: **USD 0.1688805**. Both responses completed without output exhaustion.
Description length fell 50.8%, but total first-request input fell only 822 tokens
(4.1%). Neither smaller output nor faster response establishes a useful request.
Times above cover model responses, not whole-arm wall time.

### A: real failure reproduction, incomplete processing witness

A called `pylint.lint.Run` in-process through `observed_target`. The fixture had
`src/__init__.py` and an empty `src/project/file.py`, but no project `__init__.py`.
The directory call entered the target and captured the actual missing-init F0010,
with exit code 1. A direct-file control entered the target, captured empty output
and exited 0. Both captures were complete; fixture hashes matched, and cleanup was
confirmed. Host declared-failure comparison matched and desired comparison mismatched.
This supports reproduction of the public missing-init failure on the unchanged base.

However, A selected `diagnostic_rules=null` and a handwritten F0010 substring test.
It recorded only error presence, with no positive evidence of intended-file
processing. The paired host diagnostic-rule mechanism was not exercised. These
selected fields would not by themselves distinguish a no-op repair from real
processing. No repair or post-edit result is available to resolve that limitation.

### B: request construction failure before execution

B returned a complete tool-call envelope, but the host reported two invalid fields:

- `purpose.entrypoint="pylint"` lacks the required dotted Python callable path.
- `purpose.diagnostic_rules` contains `LOADFILE`, which does not match the required
  stable diagnostic-code format with digits.

Additional static concerns in the submitted request include numeric values in the
diagnostic Boolean objects, an incomplete per-call role pair, invented codes and
`subprocess.run` instead of the injected in-process wrapper. These are not observed
execution failures: host admission stopped first. B's code was never executed.

The prepared diagnostic deliberately stops at the first settled probe receipt, so
B did not receive this tool-validation feedback in a subsequent response. Its
ability to correct that request remains untested; no resource limit caused this stop.

## Interpretation and decision

This pair does **not support shortening as a reproduction improvement**: A obtained
real failure evidence and B failed admission. One trajectory each cannot establish
that shortening causes worse performance. Long-description A also succeeded where
the historical run failed, so that old failure cannot be attributed to description
length alone. Shared public-context reconstruction and model variability are plausible
explanations; neither is isolated by this A/B.

Keep request validity, actual target execution, failure reproduction and positive
processing coverage as distinct outcomes. Compact instructions remain implemented,
but their live quality benefit is unestablished. The unresolved issue is constructing
the correct callable/observation contract, including useful processing evidence.
Any feedback-driven correction or model-setting comparison needs a separate scoped
design. Do not spend the unused allocation or claim F0010 repair, submission,
regression PASS or isolated acceptance from this diagnostic.

## Evidence and closeout

- Executing commit: `2e646394`; runtime unchanged from `ce30adf4`:
  `sha256:bc07573f50542452e0ba9f0fa47298f07c5542d4575958013dbb723bd0447080`.
- Plan: `C:/pt/first-reproduction-description-plan-v2/manifest.json`;
  hash `sha256:fe6ca866731d56bcec3c0ec01fc9fe82dc67f76943d8102ff023ca9ef320fa00`.
- Result root: `C:/pt/first-reproduction-description-run-v2`;
  `result.json`, `analysis.json`, group journal and separate A/B journals.
- Actual first-count and dispatch hashes match each sealed request exactly.
  Both response model IDs match the configured snapshot. All new count/model/action
  starts have completed receipts; A's probe dispatch has a completed receipt.
- Both arm chains and the shared cost journal validate. Summed new provider costs
  equal the row costs, shared ledger and final result. Inherited historical costs
  are not included in new cost. Opaque reasoning bodies were not inspected; only
  response metadata and reasoning-token counts were used.
- No edit, regression check, finish or isolated evaluation was performed. No image
  was pulled/built, no automatic provider retry occurred, and no repetition was added.
