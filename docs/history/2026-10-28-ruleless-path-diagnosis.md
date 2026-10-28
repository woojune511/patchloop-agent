# Connect ruleless original failures to bounded path diagnosis and revision

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: implementation and provider-free local validation
- Origin Date: 2026-10-28, Asia/Seoul
- Verification Status: locally verified mechanism; live-model repair untested
- Version Label: ruleless_path_diagnosis_local_v1
- Scope: dev-head, official=false, claim-ineligible

## Problem and decision

The user selected improving PatchLoop's diagnosis and revision behavior, rather
than manually repairing Astroid. The [saved model trial](2026-10-28-post-reproduction-repair-results.md)
already acquired an original failure with `diagnostic_rules=null`. This is legal,
but the existing structured post-edit path diagnosis unconditionally required a
usable host judgment and a rule-mapped call ID. Thus its measured unobserved
changed lines could not activate the smaller diagnosis request. Generic helper
diagnostic opportunities did exist; the failure was not absence of every
diagnostic opportunity or an exhausted context window.

The [local processing comparison](2026-10-28-file-processing-results.md) motivates
observing the actual path: a later edit could suppress the builder exception while
leaving target processing absent. This change does not encode that task's answer.
The intervention is to connect already-supported reproduction evidence to the
existing bounded path mechanism, rather than add another tool or expand limits.

An alternative is that changed code actually executed but was semantically wrong,
or that the failure changed. Those cases do not meet this route's trigger. The
saved candidate1 and candidate3 provide such negative controls; this implementation
does not claim to resolve them. The final edit cap is also a separate bottleneck.

## Implementation

For null rules, require the same acquired original, current candidate, declared
failure, observed value, complete captured call outcomes, invocation identity and
conditions, plus measured unobserved changed Python lines in the last source edit.
Existing rule-based cases still require their usable host judgment.

Without a rule-derived call, offer the captured call IDs and arguments. The model
selects `focus` plus `call_id`; the host supplies changed-function watches and
replays the full frozen program. The call/failure mapping is explicitly
`model_selected_unverified`. No helper code, new oracle, private evidence or
benchmark-specific selection hint is supplied.

Admission fixes the selection in the existing action/input identity. Preparation,
request rejection and execution budgets belong to the candidate/case/failure/
mutation, so another call ID cannot refill them. Recovery reuses completed
receipts and does not repeat uncertain execution. Test-only historical reuse keeps
its existing source/failure proof and preserves consumed allowances.

The next edit retains the diagnosis and prediction linkage. Its automatic original
replay assesses a null-rule prediction through the healthy frozen comparison and
same invocation fingerprint; it no longer demands a nonexistent rule judgment.
Prediction support, original effect, semantic correctness and required-check credit
remain separate. The resulting feedback survives projection into model context.

Small maintenance fixes also stop `helper_recovery` from treating rejected
non-object purposes as dictionaries, and align obsolete tests with the existing
signature-based invocation and separate diagnosis schemas.

## Saved-record controls

Baseline runtime: `7fd3f7dd38fff4467840871608c8592d76ed38bc`.
Source run: `C:/pt/post-reproduction-repair-run-v1/repair/runs/run_dev_3e21775752a54cae.jsonl`,
259 events, SHA256 `3523fbf47b6b49cee0a40830a8efeeb69da9d233c8e1e6ee708373c35332b7d0`.
Only public receipts are re-projected; no target or model is executed.
The frozen before/after sources, reproducible script, manifest, comparison and
hash-chained local journal are in `C:/pt/ruleless-diagnosis-local-v1/`.
`report.md` records the retrospective; `comparison.json` has SHA256
`f54e72ca2c8644c05408ae56b45614874731840ad924abd89d3f75ea00c2a085`.

| Saved prefix | Baseline path state | New path state | Original verdict |
| --- | --- | --- | --- |
| 146, candidate1 | not_needed | not_needed | refuted |
| 164, candidate2 | not_needed | needs_path_diagnosis | refuted |
| 256, candidate3 | not_needed | not_needed | refuted |

At seq164 the offered calls are call-1 and call-2; the measured unobserved range is
`astroid/modutils.py:311-313`. This demonstrates eligibility at that historical
point, not what the model would choose or whether a new run would repair correctly.

## Validation and limits

Core controls cover ruleless eligibility, incomplete/changed captures, identity
drift, unusable canonical judgment, observed changed lines, fixed selection,
no allowance refill, resource reservation, test-only reuse and recovery. A tiny
local fixture reaches diagnosis, recovers a completed call without re-executing,
applies a linked repair and gets a matched automatic original replay. Its prediction
and original-effect feedback appear in the next model context, while semantic
correctness stays unverified and required-check credit stays false.

JUnit receipts are under `C:/pt/tmp/` (times below are recorded suite times):

| Selection / receipt basename | Result | Seconds |
| --- | --- | --- |
| Final reusable core selection, rulelesscore28a | 70 pass | 24.06 |
| New path and existing reuse/canonical controls, rulelesspath28c | 42 pass | 22.304 |
| Call selection and prediction, rulelesspred28a | 31 pass | 18.043 |
| Diagnosis/recovery/revision/context fixture, rulelessassessment28e | 1 pass | 7.508 |
| Helper-purpose controls, helperguard28 | 26 pass | 7.836 |
| Quick with 4 workers, rulelessquick28a | 655 pass, 1 documentation failure | 78.840 |
| Final request/document selection, rulelessfinal28a | 47 pass | 15.687 |
| Final docs, rulelessdocs28b | 5 pass | 0.123 |

The quick failure was the guide's byte limit after two new summary lines. Those
redundant lines were removed, with detail retained in `.agent/repair-path.md`.
The focused document recheck verifies that correction. This is split validation,
not a claim that the original quick invocation had zero failures. Both existing
isolated mock-evaluation smoke tests passed in quick; Ruff and diff checks pass.
An earlier broader construction/context selection also passed 62 tests in 157.476
seconds, exceeding the desired two-minute focused window. It was not repeated;
the final narrow controls above remain under that window.
The reusable core command is `uv run --locked pytest @tests/ruleless-diagnosis.txt
--basetemp C:/pt/<unique>`; it includes the real local recovery/revision fixture.

No provider call, benchmark target execution, benchmark acceptance, hidden-test
inspection, paid continuation or direct Astroid repair was performed in this change.
The first-edit null-rule observation route, changed-failure diagnosis, edit cap,
model settings and all resource ceilings remain unchanged. Live-model use of this
newly reachable diagnosis and improved repair remain the next unresolved question.
