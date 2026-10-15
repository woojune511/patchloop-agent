# OpenSandbox A/B: pre-dispatch integrity stop

Date: 2026-10-16. Exact-manifest execution was authorized, but neither row ran.
This follows the [frozen design](2026-10-16-host-plan-design.md) and
[provider-free bridge](2026-10-16-host-plan-bridge.md); their records are unchanged.

## Approved scope and observed stop

The user authorized O1-A then O1-B once each, USD 11 total / 5.50 per row,
twenty new generations and twenty input counts total / ten each per row,
with the existing tool, edit, time and pre-assessment E/U/R limits unchanged.
The exact manifest remains `C:/pt/hostplanready01/manifest.json`, SHA-256
`cde5f592dd10215f7c02225e407b21d52e0f45042d24f611bf623adb0344a3df`.

The fetched [official standard pricing](https://developers.openai.com/api/docs/pricing)
still lists GPT-5.4 at USD 2.50 input, 0.25 cached input and 15 output per million
tokens for short contexts. The fixed 60,000-input-token limit is within that tier.
No substitute model or changed cost basis was selected.

Read-only `validate_manifest()` then rejected a changed bound `runner.py` before
`collect()` was invoked. A follow-up byte comparison found actual changes to
`dev/runner.py`, `dev/model.py`, `dev/tools.py` and `.agent/guide.md`, not line-ending
normalization. At that observation, HEAD still matched the approved connector
commit `05734233c1c35623a453266b592022fa50a1ab63`; the implementation and manifest
hashes matched, but the runtime hash did not. The changed bound files' HEAD bytes
matched the frozen bindings, while their working-tree bytes differed.

The concurrent working-tree changes add a required `finish_task.assessment`, alter
completion guidance and change the tool contract. These are substantive changes
to conditions that the plan-only experiment holds fixed. They were not made,
reverted, staged or adopted by this attempt. The initial status had only the
pre-existing AGENTS.md edit; the source changes appeared during preflight.

## Evidence and decision

The immutable receipt is `C:/pt/hostplanattempt01/preflight-stop.json`, SHA-256
`4c566351a113b29aac6696f092b8713a8affaddf2d6ca62fab3aa015c28177c5`.
Its `run_dev_hostplanpreflight` hash-chained journal records exact approval,
official pricing verification and the integrity stop. It includes the observed
binding hashes and source diff; the reserved `C:/pt/hostplanlive01` was not created.

| Axis | Result |
| --- | --- |
| O1-A / O1-B | NOT_RUN / NOT_RUN |
| New generation / input count / metadata calls | 0 / 0 / 0 |
| Cost | USD 0 |
| Docker/image readiness and credential-content reads | Not reached / 0 |
| Target checks, public terminal diagnostics, isolated evaluations | 0 / 0 / 0 |
| E / U / R / P / I / safety | NOT_RUN for both rows |
| Repair or planning comparison | NOT_RUN; no model outcome to interpret |

The integrity stop was applied without retry, prompt tuning, manifest rewriting,
replacement runs or source rollback. Approval is not evidence of execution, and
this infrastructure stop is not evidence for or against the planning instruction.
Executing the original design requires an isolated environment that preserves the
approved runtime and bindings; adopting the new finish contract would instead
change the experiment. This record authorizes neither a replacement nor a rerun.
