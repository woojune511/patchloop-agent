# OpenSandbox requirement closure and current runtime audit

Date: 2026-10-16. Existing records and source only; official=false.
Decision: **KEEP_RUNTIME_BASELINE**. The submitted task patch is incomplete, but
no current PatchLoop delivery, search, probe-verdict or finish-contract defect is
demonstrated. No model, count, diagnostic, target-test or evaluator execution.

## Selection and question

Selected OpenSandbox-816 from the three failures in the
[public probe audit](2026-10-15-probe-audit.md). Its public issue explicitly names
two repair obligations, and the submitted patch plus an existing public control
can distinguish helper behavior from backend behavior. This avoids relying on
the unresolved inferred expectation in the [isort audit](2026-10-16-isort-requirement-audit.md).
This is a purposive investigation, not a performance sample or a new experiment.

The previous [OpenSandbox diagnosis](2026-10-01-opensandbox-public-diagnosis.md)
already established a backend gap. This follow-up asks where the actual solver
lost that obligation and whether the current harness caused it. Alternatives:
missing task/source delivery, a misleading tool result, forced completion, or
model-authored narrowing of the task despite available evidence.

Original run: `run_dev_75ec90f0be654c84` at
`C:/pt/runs/fixed-batch-20261001-v1/original-opensandbox-816`.
Task base: `fb78091f947f62ae2c71a372af42425a764aacee`.
Historical runtime: `sha256:dfd10fb7c338ce8a3548eacf5210bf3241254e3aaae9efc13aef23b2cf0a44c5`.
Current source audited at `b1fb4ee326cae472a8f456f7f9f2dde541a81137`.
Historical behavior is not a current-head model-performance measurement.

## Explicit requirement and actual patch

The [public issue](../../tasks/dev-train/original-opensandbox-816/public.yaml)
requires rejecting symlink components in `ensure_valid_host_path`, and aligning
host-volume validation with the PVC `realpath(strict=True)` standard. This second
obligation is explicit, unlike an operator-derived positional control.

The submitted diff adds 27 lines only to `validators.py`. It checks native path
components before the existing allowlist check. `docker.py` is unchanged: its
`_validate_host_volume` still forms `resolved_path` with `normpath`, then calls
the helper only when `allowed_prefixes` is truthy and the subPath changed the path
(lines 1479-1488). Thus helper correctness does not establish backend coverage.
Submitted patch hash:
`sha256:5295695164a555a65c6373515dfdf9ecf3c1deadafebc617044fe9ba00896493`.

Existing public receipts, re-read rather than re-executed, support a concrete
backend defect. Shared validation followed by backend validation accepts a
symlinked subPath without an allowlist on the submitted patch. The old local
control adds one unconditional helper call before backend filesystem operations
and rejects that case, while clean controls remain accepted. That program invokes
the two functions in the order shown by `_validate_volumes`; it does not execute
the full request/mount lifecycle. A deterministic inter-stage path replacement
also distinguishes the control; it is not evidence of real-world race timing.

Do not overstate the failure. With a configured allowlist, the existing composed
static-symlink cases are already rejected by the submitted patch. The patch has a
real local effect. The control establishes a missing backend check, not a complete
strict-canonicalization repair or an atomic mount guarantee. PVC itself catches
`OSError` after its strict resolution (docker.py:1678-1682), so neither the public
source nor these receipts justifies a new expectation that every resolution or
permission failure must be rejected. Existing automatic directory creation also
needs preservation. The exact private failing assertion remains uninspected.

## The narrowing occurs in model-authored decisions

Numbers are original journal sequences. All ten dispatched request artifacts
were hash-verified against prepared, counted and dispatched identities. Every
request contains the unchanged full issue. The host-validator source read at
31/32 is present verbatim in every subsequent request, including edit and finish.

| Input/action/result | Actual evidence and observable decision |
| --- | --- |
| Initial response / plan 16 | Explicitly plans both symlink rejection and PVC realpath alignment, including reading the PVC validator. |
| Read 31/32, next decision 45 | Reads docker.py:1462-1545. The model correctly says the host validator only re-calls the helper for subPath joins. |
| Search 71/72 | Literal `realpath(strict=True)` search returns zero spans from 147 files, without truncation. Actual PVC calls split `realpath(` and `strict=True` across lines 1650-1654. |
| Input 75 -> response 80 / plan 83 | Original issue, host source and initial two-part plan remain available. The new plan removes PVC alignment from required behavior and labels helper-only repair an untested assumption. |
| Input 88 -> edit 97 | Describes host validation as relying on the helper and edits only that helper, without establishing that all backend paths invoke it. |
| Input 101 -> plan 109 | Recasts the remaining task as current-diff regression compatibility: if the suite passes, submit. No observation has resolved the helper-only assumption. |
| Input 115 -> probe 126/127 | Despite finish eligibility, chooses a useful helper probe: clean sibling accepted; intermediate symlink rejected. Both assertions pass; three setup comparisons match. |
| Input 131 -> finish 141 | Full issue, host source, exact probe program/setup/stdout remain present. Final plan says remaining work is none and submits the same diff. |

The first narrowed plan predates the two result handoffs at inputs 115 and 131.
It is therefore not explained by those handoffs deleting the original requirement.
The PVC strict-resolution block was never acquired: no delivered docker.py source
range reaches lines 1641-1682, although the method's beginning was read. This is an
exploration omission, not pruning of previously read resolution code. A zero-result
literal search does not establish source absence. The record
supports the sequence of decisions, not a claim that the search miss psychologically
caused the narrowing or that a different query would ensure a correct repair.

The visible regression reports 108 passes. The model's subsequent statement that
changed lines were not exercised is stronger than the `unknown` line mapping:
unknown mapping is not proof of absence. Nonetheless it selected a direct helper
probe, whose result is valid within its scope. The error is expanding that scope
to completion of a separately named backend requirement.

At the final input, three edits, 31 model calls, 91 actions, 1,422 displayed solver
seconds and USD 2.45554 of the invocation cap remain. Read/search/replace/probe
and stop remain offered alongside finish. This is no observed forced-stop case;
displayed headroom does not guarantee a future call or successful repair.

## Comparison with the current implementation

| Suspected harness defect | Current source and evidence | Judgment |
| --- | --- | --- |
| Issue lost or summarized away | `runner.py:1495` supplies the public task; `model_state.py:143-144` copies it; `conversation.py:217-225,278-284` preserves/checks immutable segmented task content. Actual historical issue survives all ten requests. | Not demonstrated. |
| Search silently misses a literal match | `tools.py:254` promises literal text; `tools.py:2853` tests the query against each line. The searched string does not occur in the inspected docker.py bytes. | An unsuitable query, not a violated search contract. No semantic-symbol search was promised. |
| Probe completion becomes task correctness | `probe_observation.py:36-47,95-100` separates completed execution from `behavior_verdict=not_assessed`; actual final input retains this distinction. | No semantic PASS promotion. |
| Ready status incorrectly certifies all requirements | `tools.py:2359-2365` requires a tracked diff and required checks on that diff. `runner.py:590-596` says eligibility is not proof of untested behavior. | Eligibility contract satisfied; semantic completeness is not its guarantee. |
| Finish advice forces the decision | Both final inputs offer further investigation; input 115 takes the probe despite finish advice. Scope narrowing begins before ready status. | Advice may influence closure, but is not established as the originating cause. |
| Plan storage corrupts intent | Actual model response supplies each narrowed replacement; delivered plans are labelled `model_authored_unverified`. Original task remains separate. | Observable self-authored requirement narrowing, not a demonstrated storage defect. |

Existing tests were read, not run: `test_dev_model_state_v24.py:137-142` checks
immutable task protection; `test_dev_probe_observation_v28.py:148-171,194-205`
documents non-verdict observations, no required-check credit and finish eligibility.
Current `dev/model.py` already distinguishes checked behavior from assumptions.
These static comparisons do not prove the entire runtime correct or identify the
causal effect of plans, memory, prompts or model variability.

## Decision and stopping point

The narrower failure mechanism is **an explicit requirement becoming an untested
helper-sufficiency assumption, then disappearing from the completion criterion**.
It is supported by the exact public decisions and the incomplete final diff.
The recorded harness inputs did not lose that requirement or require submission;
current-source inspection found no corresponding contract defect.

The task-level minimum candidate is to validate the concrete backend host+subPath
path independently of the existing conditional allowlist branch. The old one-call
control supports that bounded correction, but a complete repair must also resolve
the explicit PVC-alignment requirement while preserving directory creation and
compatible error behavior. No complete repair has been implemented or newly tested.

For PatchLoop itself, **no runtime source correction is justified by a reproduced
implementation-contract violation**. Preserve prompts, memory/context limits,
search behavior and finish gates. A requirement checklist or mandatory probe would
be a new design hypothesis, not a bug fix established here. No adjacent A/B or
additional task investigation is queued. This closes the requested existing-record
audit with a task-patch defect and a baseline-preserving agent decision.

## Evidence and verification

External root: `C:/pt/opensandboxclosureaudit01`; append-only hash-chained journal:
`runs/run_dev_opensandboxclosureaudit.jsonl`. `analyze.py` parses saved public JSON
and source; it never imports or executes OpenSandbox. Original run and old public
diagnostic journal chains verify. Ten request identities, the submitted patch,
pre/post-image and unchanged backend source agree; 37 bound files remain unchanged.
Historical validators.py CRLF bytes were bound separately from the normalized LF
content matching the mutation hash. Original scores and records are unchanged.

- `audit.json` file hash:
  `sha256:80d48919399840caaf59f20bde82575255d13ce0f55d507ea3d4b3b53b64b069`.
- Canonical artifact:
  `sha256:e29ba7c91c6619f2744d5635fab027c93d2b0b96064aa602f24494b329299903`.
- `interpretation-amendment.json` narrows the extraction field
  `pvc_implementation_source_acquired=false` to the strict-resolution block:
  the beginning of the PVC method was delivered. The original artifact is preserved.
- An initial extractor read omitted the historical checkout's `repo` directory.
  Correcting that read path and parsing the saved stdout as its JSON array did
  not run any target program. The failed read and later scope receipt are distinct
  from new behavior execution.

Only this follow-up, current status and the current history index change. Static
link/size/whitespace and preservation checks apply. Model/count/diagnostic/target
test/evaluation calls remain zero; added provider cost is USD 0. Runtime suites and
mock smoke are not run for this documentation-only investigation. The user's
unrelated AGENTS.md changes are preserved.
