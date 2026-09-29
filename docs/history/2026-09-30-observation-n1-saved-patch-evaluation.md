# N1 saved patches: independent evaluation and public-action interpretation

Date: 2026-09-30. Every result is official=false. Follow-up to the immutable
[partial comparison](2026-09-29-observation-comparison-results.md) and
[boundary correction](2026-09-29-observation-boundary-fixes.md).

## Question and authorized scope

Did the two submitted N1 patches actually solve the registered task, despite neither
arm addressing the selected optional-probe setup failure? The original evaluations
stopped at receipt integrity checks, before evaluating either patch. The user
authorized separate saved-patch evaluation and comparison with the public action
record. No model generation, repair, continuation or new A/B comparison was authorized
or performed. Closed allocations remain closed.

## Execution and provenance

Evidence and script: `C:/pt/analyses/observation-n1-reevaluation-20260930-v1`.
Executing HEAD: `a443d4b`. The unchanged EvaluationEngine evaluated both exact saved
patch byte streams against `tasks/dev-train/anyio-interrupt-runner-cleanup-v3` in
separate fresh workspaces from the hash-bound prepared source. The local pinned
Linux/amd64 evaluator image was inspected; no image was pulled/built and Docker was
not started by the diagnostic. Each evaluation had a 900-second cap, with no retries.

The new manifests describe patch-only evaluation under the current runtime, with
model execution NOT_RUN. Their lineage records retain the original manifest, journal
hash and historical receipt references. Both source journals contain exactly two
probe executions, all before their fork markers; neither continued agent ran a new
probe. No probes run in this independent evaluation, and no old receipt is presented
as a current execution. The evaluator's receipt and input-integrity checks are intact.

All files under the original two runs' journal/artifact directories were hashed before
and after evaluation and remained identical. Original EVALUATOR_ERROR records remain
unchanged. New state is external, append-only dev-run-v1 JSONL with CAS artifacts.
This is not an ordinary resume or a retroactive certification of either agent run.

## Results

| Saved patch | Hidden tests | Regression tests | Scope | Evaluation safety | Evaluator time |
| --- | --- | --- | --- | --- | ---: |
| N1A | PASS | PASS | PASS | PASS | 20.720 s |
| N1B | PASS | PASS | PASS | PASS | 20.803 s |

N1A patch: `sha256:43e6b5a9df5be02565e8e48ca29028b464ddbfcdc93ca7668b24a722c3bb0d70`.
N1B patch: `sha256:80c4f9ec37e27d98e7dc8530794c71cee425d5131fda31c4d301da678ec851f0`.
New run IDs: `run_dev_savedpatch_n1a` and `run_dev_savedpatch_n1b`.
Both results have scope_compliant_success=true. Safety PASS concerns the new isolated
evaluation; historical agent/probe safety was not reassessed. These are acceptance
results for the registered development task v3, not official original-benchmark scores
or additional fresh solves. Actual provider calls and new provider cost: zero.

## Public evidence and interpretation

The existing arm-masked primary scores remain unchanged: both arms scored zero for
handling the selected `wrapped_name` probe setup mismatch in their first three new
batches. Acceptance outcomes must not be used to rescore that public endpoint.

Both arms explicitly prioritized the separate, already failing lifecycle check:

- N1A inspected the interrupt/caller path (sequences 114/128/144), repaired run_test
  at 157/162, passed lifecycle at 167 and upstream regression at 179, then submitted
  at 190/194. It made one newly accepted mutation.
- N1B inspected the interrupt path at 114. Its first broad edit was scope-rejected
  at 134, its next accepted edit at 148 failed lifecycle at 153, and a revised
  cancellation handoff at 167 passed lifecycle at 172. Upstream regression passed
  at 186 and submission completed at 197/202. It made two newly accepted mutations.

Thus, this pair shows successful task repair without resolving the selected optional
probe question. The lack of target handling is observable, but is not demonstrated
task-solving failure in this pair. Public decisions support prioritizing the known
lifecycle defect; they do not prove that ignoring the probe was an optimal conscious
choice, that its entire behavioral question was irrelevant, or that it was resolved.

The diagnostic endpoint measured response to a particular non-blocking setup failure
while a mandatory product failure competed for attention. It cannot substitute for
task correctness. Both patches passing does not establish equivalence or a benefit
from the observation catalog; B's extra edits likewise do not establish causal harm.

## Decision

Keep the baseline and the original scores. Do not automatically repeat the entire
exposure panel. Before another causal comparison, use public evidence to establish
why handling its target observation could change the current candidate's correctness,
and distinguish probe setup repair, genuine product contradiction and justified
deferral. Any new eligibility/rubric belongs to a new diagnostic, not post-hoc changes
to the closed panel. No further paid experiment or agent-context change was made.

Validation: both actual Docker evaluations completed; source-byte preservation checks
passed; all five documentation layout/link checks passed. Runtime and collector code
were unchanged, so the full code suite and mock smoke were not repeated for this
documentation-and-evaluation follow-up.
