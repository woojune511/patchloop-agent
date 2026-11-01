# SQLFluff16: one saved-patch replay with improved assertion capture

2026-10-31 (KST). Completed operator evaluation; no live model or solver repair.

## Question and fixed scope

The [previous audit](2026-10-30-sqlfluff-operator-evaluation-audit.md) found genuine
behavioral failures but missing saved assertion tracebacks. After the
[capture correction](2026-10-30-operator-failure-capture.md), the user authorized
one replay of the latest submitted patch to identify its exact failed assertions.
This resolves an attribution gap before proposing more agent interventions.

Freeze submitted patch `ab250268` from `run_dev_1249575172444847`. Use current
capture code `b247345d`, the same prepared base and installed pinned evaluator
image. Compare with the original evaluation. No patch edits, model calls, image
pull/build, grading/test changes or retries. Stop on infrastructure, identity,
deadline or cleanup uncertainty; one evaluation has a 720-second outer deadline.

Use the regular `EvaluationEngine` in a fresh external workspace: required public
checks, original test view for isolated grading, then policy checks. Create a new
manifest with current task identity and a new CAS copy of the exact patch. Old
model fields are patch lineage, not a new model invocation. Old probe receipts
remain with their original run; this replay performs zero probes. Its safety
result describes this evaluator execution, not another agent run.

## Observed result and decision

- Completed exactly once in **51.529 seconds**.
- Required public check: **167 PASS / 1 deselected**.
- Independent task acceptance remains **FAIL**; safety and scope policy **PASS**.
- All **three** failed assertion blocks were recognized and retained: **4,467
  bytes**, zero omitted/truncated/unclosed blocks. Their source lines and printed
  actual/expected differences are directly available in the operator receipt.
- The original stdout is 1,426,059 bytes. Its 24,000-byte tail still omits the
  beginning; separately retained failure blocks preserve the relevant evidence.
- No timeout, infrastructure or cleanup uncertainty. Model calls and new API cost
  are **zero**. All **159** protected original evidence files retain their hashes.

The existing capture correction works on this real output, and the verdict is
unchanged. Exact assertion attribution replaces the earlier uncertainty for this
new replay; it does not recover old missing bytes or rewrite historical records.
No larger logging mechanism or another replay is justified by this result.

Detailed private assertions and values remain only in the external operator
report, not solver context, public task guidance or new public tests. A mismatch
against fixed private criteria does not by itself establish an additional public
requirement, a particular recovery strategy or deficient model reasoning. Any
solver change still needs independent public evidence; no repair or general
acceptance improvement was demonstrated here.

## Reproduction and evidence

- Source execution: `fbfdd213ca28fdfb0eb27e65c533a22c0d72188d`.
- Replay code: `b247345d`; runtime hash remains
  `sha256:47057ca997eaa2ba5c3c566aa76df16ae9c4e2bdb41b47f08d68da05b0ff2fd9`.
- Patch: `sha256:ab25026869f0d02dec7a32bb34c06140b7fdec55cb0ce337f6c6565b4e46c82b`.
- Adapter: `sha256:94949d0098e5482be501868e5cd105176e49f672bcb4ea05211727a0b92103fe`.
- Fresh root: `C:/pt/sqlfluff16-log-replay-20261031-v1`.
- Journal: `runs/run_dev_sqlfluff16logreplay20261031v1.jsonl` (`dev-run-v1`).
- Pre-dispatch plan CAS:
  `sha256:8c5c480999dea41d43e5807046fb2ee458d5defa41184e10030d5bbbb6a8a8d1`.
- Private check receipt:
  `sha256:cc8e4aa97b823bda014adc9e4a03150ca64cc22349839f913ec1a76a6fbedeab`.
- Decoded operator report CAS:
  `sha256:af87708319ea9aa0d98993b7120c375d2ec559af0e7cf4443cc2ec0559592a8a`.
- Exact values: external `operator/assertion-evidence.json` and `.md`; original
  failure slices: `operator/failure-1.txt` through `failure-3.txt`.

The execution plan verifies that only the task adapter and its declared hash
changed since the submitted run. Registered commands, private criteria and
original test content are unchanged. A separate documentation validation receipt
records the bounded current status, links and unchanged HTML scripts. No runtime
code changes or additional mock/live executions were needed for this follow-up.
