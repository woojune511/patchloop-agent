# Cost-cap continuation of the two 48k SQLFluff runs

Date: 2026-10-06. CLOSED; official=false, claim_eligible=false.
Execution commit: `389b6b33c55920bc2d93b8164773709301a95c0d`.
Preparation: `C:/pt/sretcp01`; authorization: `C:/pt/sretca01`;
continuations: `C:/pt/sretcl01`; assessment and closeout: `C:/pt/sretce01`.

## Question and decision

The [24k/48k comparison](2026-10-06-source-retention-results.md) left both 48k
SQLFluff runs unsubmitted after exhausting USD 1.20. This censored correctness:
one had an unassessed patch, while the other had not edited. The user requested
continuation and approved a separate additional USD 2.40 allocation with
"진행해줘" after reviewing the prepared scope.

Additional budget enabled both submissions, but both patches failed registered
evaluation, independent native evaluation, and the frozen public example. Neither
continuation exhausted its new cost, remaining call, or active-time allowance.
Thus cost admission explained the original non-submissions, but more money did
not make these two trajectories correct. Untested repair hypotheses remain an
observed problem; the result does not support another automatic budget increase.

Keep the 24k default and close this allocation. The original eight rows and their
NOT_RUN outcomes remain unchanged. These are two supplementary continuations of
one exposed development task, not fresh solves or a new equal-budget comparison.
No general model/context-capacity or SWE-bench accuracy conclusion follows.

## Exact continuation

Parent rows 3 and 5 used `tasks/dev-train/current-dev20/18/public.yaml`,
gpt-5.4-mini-2026-03-17/xhigh, 25,000 desired output tokens and repository `.env`.
Each continued once in a separate state root, serially, with USD 1.20 additional.
The previous unused funds were closed, not transferred. Source retention stayed
48,000 characters. Model, tools, checks, notes, source observations, accepted
mutations and encrypted conversation history were restored without repair hints.

Calls/actions/edits and active time were not reset. The rows retained 4/7 model
calls, approximately 430/367 solver seconds and 330 evaluation seconds each.
The stopped request was counted afresh; time spent on its original failed
admission was retained. Provider-free restoration compared actual first inputs
with their originals: only cost allowance and elapsed-time fields differed.
The live collector checked the prepared first-input fingerprint before counting.

Ordinary resume still rejects changed envelopes and does not reopen terminals.
The optional parent-configuration restoration path preserves mini pricing, 48k
retention, evaluation reserve and probe replay settings. Existing full-model
observation comparisons retain their previous explicit configuration.
Preparation passed 36 relevant tests across focused checks, including six new
tests in 19.57 seconds, plus Ruff. Synthetic stops were not agent-quality evidence.

## Results

| Parent row | Additional calls | Additional USD | Cumulative USD | New actions | Registered / native / public |
| --- | ---: | ---: | ---: | --- | --- |
| 3, B1 | 1 | 0.02423475 | 1.21253955 | Finish existing patch | FAIL / FAIL / FAIL |
| 5, B2 | 3 | 0.18928545 | 1.37240910 | Edit, regression check, finish | FAIL / FAIL / FAIL |

Both submitted; both registered safety results were PASS. All four provider calls
and five new input counts settled without uncertainty. Additional cost totaled
USD 0.21352020; the remaining USD 2.18647980 is closed. Continuation wall time was
371.06 seconds, including setup and registered evaluation, excluding subsequent
native/public assessment. Native assessment took 20.42 and 20.00 seconds and
agreed with both registered failures. No evaluation ERROR or cleanup uncertainty
occurred; no Docker containers remained at final inspection.

B1 submitted its inherited L003 `_coerce_indent_to` patch without another edit or
check. Its existing check on that exact diff had passed 506 tests. B2 independently
made the same kind of repair: edit the first indentation segment and delete the
remaining indentation segments. Its newly executed regression check also passed
506 tests. Both patches changed only `src/sqlfluff/rules/L003.py`.

Neither executed a public behavior probe or selected test after its source edit.
At both finish decisions, `read_file`, `search_files`, `replace_text`, `run_probe`
and `run_tests` were still available alongside finish, with no closure reason.
The runs ended at 37/40 and 36/40 model calls. Therefore these submissions were
not forced by another resource-limit stop.

The unchanged operator public program assessed each exact submitted patch after
the solver finished. Both produced five leading spaces before `my_id`, where the
issue expects eight. Passing unrelated regression assertions did not establish
the claimed behavior. This is stronger evidence than the earlier unassessed
patches, but it does not itself locate every underlying agent failure mechanism.

## Evidence and limits

The approved preparation manifest file hash is
`sha256:73e84d94d3216c702a3ac6153f7656bfdd3cdd42a418e25a17dad689048bbdd9`.
`sretcl01/result.json` records live usage and terminals; `sretce01/assessments.json`
records registered/native agreement and public output. `sretce01/summary.json`
records new public actions, available finish tools, usage, patch identities and
parent preservation. `sretce01/closeout.json` binds these files and operator scripts.
Each root has append-only hash-chained journals. Original parent journals and
envelopes were verified unchanged against the approved manifest.

The same frozen public program/calibration and native harness identities were
reused. Evaluator internals, native results and operator public output never entered
solver context. There was no automatic probe replay, retry, image pull/build,
cross-run memory, new task, or additional paid continuation. The remaining
question is how the agent should falsify its chosen repair before accepting
regression PASS; this result schedules no further experiment or prompt change.
