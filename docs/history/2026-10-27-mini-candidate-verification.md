# Saved mini candidate: identity corrected, acceptance still fails

## Material Passport

Date: 2026-10-27. ARS validation/local execution; official=false, claim-ineligible.
Status: COMPLETED. The user asked whether reproduction identity came from the
benchmark or PatchLoop, and authorized verification of the saved mini candidate.
No model calls, credential reads, new candidate edits or image pulls/builds occurred.
Nine bounded public probe runs and one separate isolated evaluator run completed.
This follow-up preserves the prior experiment's receipts and verdicts.

## Authority and question

`same_call_conditions` is a PatchLoop observation/diagnostic condition, not the
original SWE-bench acceptance rule. `probe_invocation.conditions` extracts selected
call arguments, input tree hashes, environment and execution identity.
`diagnostics/exception_frame_repair.py:case_support` requires this equality for both
original and control, alongside complete observations, expected diagnostic behavior
and unchanged control output. It guards against apparent repair after changing the
tested input; it does not define the benchmark's answer.

The [SWE-bench evaluation guide](https://www.swebench.com/SWE-bench/guides/evaluation/)
describes applying a generated patch and running required tests, with a resolved
instance meaning those tests passed. The previous diagnostic's `supported=false`
was therefore not a benchmark FAIL: that comparison had not run isolated task
acceptance. This follow-up runs the prepared local task package's separate evaluator;
it is not an official leaderboard submission.

The question was selected because the [model comparison](2026-10-27-model-setting-results.md)
produced an unchanged first-call input, normal mini execution and public regression
PASS, yet its control snapshot differed by two entries. Generated output mixed
with input was a plausible explanation; an actual fixture change was an alternative.
The saved candidate also needed testing beyond the single no-F0010 predicate.

## Fixed candidate and local procedure

Candidate hash:
`sha256:a08485418d8117b4dd8507346f7aeed8e66ff0e1e46a0efd33dcee8449cc4bcb`.
Its two model-authored additions are empty `file_bytes` and UTF-8 `file_encoding`
in namespace-module construction, on top of the first saved candidate's guard.
Every probe used a fresh workspace restored from the existing prepared base source
and hash-verified recorded edits. Base, first seed and mini remain distinct states.
All nine final workspace diff hashes matched those states; none had untracked files.

The local plan was sealed before execution in
`C:/pt/mini-candidate-verification-v1/results/runs/run_dev_minicandidateverification.jsonl`.
Each row had a 120-second deadline and used the existing pinned public probe image.
No original runtime, observer version or historical helper was modified.

| Program | Source states | Purpose |
| --- | --- | --- |
| Shared-root inventory | seed, mini | Preserve original fixture/call sequence; list bounded relative paths and file hashes before/after each call |
| Isolated input/cache | base, seed, mini | Snapshot fixture inputs only; keep HOME/cache in sibling output directories |
| Empty-file variant | base, mini | Exercise the public issue's explicitly described empty files under the new input boundary |
| Independent control | base, mini | Run control alone in a fresh sandbox, avoiding same-process state reuse |

The inventory adds observations and therefore has its own program hash; it is not
relabeled as the old frozen program. The new isolation program is likewise a new
calibration, with the same actual target arguments `src/project` and `standalone.py`
and the same prepared dependency/runtime identities. Independent control receipts
are control comparisons only: their operator-authored failure JSON is a
counterfactual, not an observed control failure or original-failure acquisition.

## Public observations

The mini first call added exactly these paths to the captured root:

- `cache/pylint/` (directory)
- `cache/pylint/project1.stats` (file)

It did not change any existing fixture path or file-content hash. The seed's
crashing first call added neither entry. The subsequent control created its own
`standalone1.stats`. The formerly inferred cache explanation is now directly
observed in this separate inventory run. The prior root-entry counts included
directories as well as files; they were not counts of changed source files.

With cache/state outside the fixture snapshot, base, seed and mini had matching
selected input conditions. Base reproduced F0010, seed retained an unexpected
exception, and mini removed both. Mini's complete original/control capture,
unchanged control and exact new input conditions satisfied every existing
`case_support` component. The separately launched control also matched base in
input conditions, stdout/stderr, outcome and exit code.

The empty-file variant revealed a remaining public behavior difference:

| Observation | Base | Saved mini |
| --- | --- | --- |
| Missing-initializer directory | F0010, exit 1 | C0112 Empty module docstring, exit 16 |
| Empty standalone control | Empty output, exit 0 | Empty output, exit 0 |
| Existing no-F0010 case predicate | Refuted | Supported |
| Issue's stated empty-output expectation | Unmet | Still unmet |

The public issue says all files may be empty and describes empty output with the
older working version. Thus the C0112 difference is public task evidence, not a
requirement invented from hidden tests. The existing predicate only detects F0010
and unexpected target exceptions; `supported=true` cannot stand in for all public
expected behavior. No new acceptance criterion was silently inserted into the old
experiment. Directory traversal coverage is not established by these checks.

## Separate isolated acceptance

The existing `EvaluationEngine` applied the sealed mini patch to a fresh prepared
workspace and ran the current development task package in its existing pinned
Docker image. The operator wrote a new manifest and patch artifact; there was no
model `finish_task` call or continuation of the closed paid experiment.

| Verdict | Result |
| --- | --- |
| Acceptance | **FAIL** |
| Regression | PASS |
| Scope | PASS |
| Safety | PASS |

Evaluation completed, `scope_compliant_success=false`, saved candidate unchanged.
Private specifications, test identities, reference patches and raw evaluator logs
were not exposed to the coding/model context. Only the verdict/identity summary was
read. Consequently the private acceptance failure is not attributed specifically
to C0112; that is a separately observed public shortcoming.

The wrapper initially compared a raw public YAML hash with the normalized public
spec hash and stopped before dispatch. That host-authored preflight error was
corrected to compare public spec structures; the failed receipt remains preserved.
Evaluator dispatch/finish counts are exactly one each, with no evaluation retry or
uncertain external execution. No new provider cost was incurred.

## Decision and evidence limits

The original-call F0010/exception improvement is verified under the new declared
input boundary. The old strict-identity negative result remains unchanged and is
now explained by an observation-boundary defect. Keep identity verification, but
separate task fixture inputs from explicitly generated output/state and record
relevant changes. Do not simply ignore arbitrary mismatching paths.

The mini candidate is a partial repair, not an accepted solution: the local
acceptance verdict is FAIL and the public empty-output expectation remains unmet.
The next repair should be driven by a discriminating public test of that behavior
and the complete original caller, rather than larger model/context/output budgets
or relying on a regression PASS. No production change or further paid run is made
by this verification task.

ARS methodological fallacies: 11/11 checked. This is a deterministic saved-patch
diagnosis, not a fresh-solve trial or model comparison; no significance, population
accuracy, model superiority or held-out generalization claim is supported. Nine
probe rows are diagnostic conditions, not nine independent model successes.

## Evidence and validation

- Public result: `C:/pt/mini-candidate-verification-v1/results/result.json`,
  `sha256:5685fa122cbb55b5be3c5d4f481536f51c4f18ba47039d1d22345723dba2baeb`.
- Public analysis: `C:/pt/mini-candidate-verification-v1/results/analysis.json`,
  `sha256:97976cb55c61c86d29e9b597e638687e2c37f553b4d1ec2c4e75d03558c4d936`.
- Local operator: `C:/pt/mini-candidate-verification-v1/verify.py`,
  `sha256:df942eae61b5c8e544da9f0a1e2c10f04cc48a00c7af8d51d07864155804e110`.
- Safe acceptance summary: `C:/pt/mini-candidate-acceptance-v1/summary-final.json`,
  `sha256:580bba2ac79a3fb5d8aa6ebda038dc4bc319891f3b7b46f56d3bc6719a050f56`.
- Isolated evaluation artifact identity:
  `sha256:a10faf81394ffaf45669805764b1020b393189cabcfbe82bc1935db73a9ab040`.
- Evaluation manifest identity:
  `sha256:681258cd6ab95781b0129e6f0f98b7f859f9fef587295f106c50a537bb6e7b85`.

Public rows completed in 94.28 seconds. Receipt artifacts and journal chains were
checked, and a separate reviewer recalculated both supported case verdicts,
independent control equality and all nine candidate diffs. Runtime remains
`sha256:5753dbef010721c721db788aa01525fc269ad12093b46e45ffc2ffd158c929f3`.
Only result documentation changes in the repository; no runtime tests are rerun
for this documentation-only follow-up.
