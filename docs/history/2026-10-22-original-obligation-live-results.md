# Bounded original acquisition: live Astroid pilot

Date: 2026-10-22. One development-exposed task; official=false and
claim-ineligible. The separately approved USD 0.88 allocation is closed.

## Question and fixed conditions

The [previous fresh solve](2026-10-22-original-case-live-results.md) submitted
after regression PASS without acquiring an original caller case, and failed
both the public caller assessment and independent acceptance. The
[local obligation controls](2026-10-22-original-obligation.md) then established
bounded acquisition and truthful delivery for scripted actions. The remaining
question was whether the model could acquire a faithful unchanged-base failure
and complete a verified repair under the same resource limits.

This was one fresh ON pilot, not a matched A/B comparison. The user approved the
prepared command and exact task/model/credential/repeat/cap scope before dispatch.
No operator case, repair hint or audit feedback entered the solver.

- Runtime commit: `119f08796e9690227fb67cde4567dd70ccdbf362`.
- Runtime hash:
  `sha256:07c5217f67a3ac8e447b4af568c3967ba0e2e291334f99cb047924677a05a498`.
- Task: `tasks/dev-train/current-dev20/13/public.yaml`, Astroid-1333.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh, 25,000 desired output tokens.
- Policies: segmented-v1, result-or-size-v1, brief-v1, probes enabled with
  policy none, repair-recheck, protected-v1 inspection, per-call-v1 cost,
  and the new `reproduction-acquisition bounded-v1` option.
- Limits: one solve, USD 0.88 total, 40 model calls, 100 actions,
  four accepted edits and 1,800 active seconds.
- Source: Astroid base `d2a5b3c7b1e203fec3c7ca73c30eb1785d3d4d0a`, with the
  previously prepared source and Python 3.9 dependencies including Pylint 2.12.2.

The frozen plan allowed at most two post-submission public caller checks sharing
120 seconds, with no model calls. It required skipping them without a submission,
stopping after this solve, and stopping on identity, counting, transport, billing
or cleanup uncertainty. No evaluator image was acquired and no retry occurred.

## Observed result

Run `run_dev_a27ef20245fb4e7c` ended with **COST_CAP_REACHED** after 693.707
wall-clock seconds, including 691.837 active seconds. Process exit 0 means the
runner returned its result; the repair was not completed. Settled cost was
USD 0.866304600. The remaining USD 0.013695400 could not fund the minimum next
provider request and grants no further invocation.

| Measurement | Result |
| --- | --- |
| Model calls / exact input counts / tool actions | 34 / 38 / 40 |
| Original-purpose requests / actual executions / acquired cases | 2 / 0 / 0 |
| Other probe executions | 1, setup failure |
| Source searches / reads | 20 / 16 |
| Accepted edits | 1 |
| Registered visible checks / finish / submission | NOT_RUN / NOT_RUN / NOT_RUN |
| Independent acceptance / evaluator safety | NOT_RUN / NOT_RUN |
| Post-submission public caller checks | NOT_RUN: no submitted patch |
| Original obligation in dispatched model contexts | Present and unverified in 34/34 |
| Final delivery state | Not emitted: finish was never reached |

Both original-purpose requests were rejected before Python execution with
`reproduction requirement_quote must occur in the public issue` (journal
sequences 20 and 33). The supplied quote had eight backslashes where the public
sentence had four. Both requests retained the same purpose and program bytes.
The second authored rationale attributed the block to a note citation and removed
its note update, while the probe's quote defect remained.

Both durable requests consumed the two-attempt acquisition allowance. The next
dispatched context showed `stage=released`, `reason=original_attempt_limit`,
`acquisition_status=setup_blocked`, and `status=unverified`. The same obligation
identity remained in every dispatched context. Release did not manufacture a
case or verification credit; later investigation counts include work after release.

The later helper probe (sequence 394) failed its setup comparison: actual cwd
was `/tmp`, expected cwd was `/workspace`. Its target behavior was not established.
The tool invocation returned a receipt successfully, but that receipt records
probe status failed, exit 1, no stdout, and confirmed container cleanup. These
are distinct from a passing diagnostic or task acceptance.

The final action changed `get_source_file` in `astroid/modutils.py` from
`os.path.exists(base)` to `os.path.isfile(base)`. Its full, unsubmitted diff is
`sha256:74b9cc1a6ed57fee15e821e1aa87f188658c19ccee9b971a55fd44432062112a`.
It was neither checked nor submitted, so its correctness is unknown. The next
request was denied by cost admission before dispatch. No saved-patch evaluation
or additional caller execution was substituted for the missing submission.

## Interpretation and decision

The live run supports retention of the unmet original obligation and correct
non-credit for rejected/setup-failed probes. It does not demonstrate faithful
acquisition, an improved repair, or the new finish/delivery branch: that branch
was never reached. The local delivery and replay controls retain their prior
scope. Keep the option off by default; do not adopt it from this result.

The immediate acquisition failure was an input-contract error repeated without
correction. Counting those rejected admissions exhausted the reserved opportunity
without any original-caller execution. Later source investigation and the final
edit left insufficient funding for verification under per-call-v1. This observed
sequence does not isolate the causal effect of bounded acquisition: there is no
matched live OFF arm, and the earlier solve used a different runtime.

A delegated static audit also found that the unexecuted requests declared
`expected_json={"f0010": true}`, encoding the reported failure rather than the
desired corrected behavior. Their explicit `Run` argument was a string, and
their observation reduced caught exceptions and outputs to a broad error-token
boolean. These are unexecuted caller/oracle concerns, not observed target failures
or false verification. Correcting the quote alone has not been shown sufficient.
The reviewer saw the public call/result pairs and relevant source, with shared
prior context; this was not a blinded independent experiment or a paid judge.

The next questions are whether requirement binding, caller arguments and desired
expectations can be made reliable before the acquisition allowance is consumed,
and whether verification remains funded after prolonged inspection. Separate
these questions in local controls before proposing another paid comparison.
No runtime change, new live allocation or queued follow-up follows this pilot.

## Evidence and integrity

- `C:/pt/original-obligation22-live-ready/`: immutable request, command,
  source inventory, explicit authorization, and frozen public assessment programs.
  Request hash:
  `sha256:22d82b687bd6c8641fa2fdb54d3f93727ac2a34e178872f2f9ff9251ee2e20c9`.
- `C:/pt/original-obligation22-live/`: CLI/process results, `result.json`,
  `obligation-retention.json`, `public-assessment.json`, `unsubmitted.patch`,
  `post-run-integrity.json`, and the public probe audit under `artifacts/`.
  Result hash:
  `sha256:e1c0d6cb605c25c8c0c4c2c6384e1493c7a70d8316b77b28e96e5f3518d62136`.
- Solver journal: `runs/run_dev_a27ef20245fb4e7c.jsonl`, 509 events.
  Operator journal: `runs/run_dev_originalobligationliveoperator.jsonl`.
  Both use append-only, hash-chained dev-run-v1 records.

All 106 bound source/task/grader files, prepared source/dependencies, runtime
identity, solver journal chain, and 164 content-addressed objects present at
collection passed integrity checks. All provider calls and input counts settled;
billing and counting are known. The one executed probe confirmed cleanup. No
private checks, reference patch, evaluator internals or raw reasoning were added
to solver context or this report. The assessment wrapper was syntax-checked but
not invoked because there was no submission. This closeout changes documentation
only; earlier local regression results are not counted as checks of this patch.
