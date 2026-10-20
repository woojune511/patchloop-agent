# Thin tool disclosure and SQLFluff-1733 public diagnosis

Date: 2026-10-07. Source baseline: `fdf05eaa`.
This follows the [closed current/thin comparison](2026-10-07-thin-comparison-results.md).
The user authorized the two next priorities: a factual tool-availability correction
and diagnosis of the submitted SQLFluff-1733 candidates using public examples.
No new paid solve, continuation, replacement or private evaluation was authorized
or executed. The closed sixteen-row result and historical records remain unchanged.

## Why these problems were selected

Thin abandoned one task on its first turn because edit and submit tools were not
offered. Those tools really were absent, but they become eligible after source
evidence and successful checks respectively. Thin omitted current's explanation
of that transition. The observed public summary supports correcting the incomplete
operating instructions without loosening execution gates or adding decision advice.

Separately, all three submitted SQLFluff-1733 candidates failed both acceptance
and the frozen public example despite required-check PASS. We distinguished four
explanations: the repair hypothesis was sufficient but incorrectly implemented;
the hypothesis covered only part of the rule interaction; a decisive public test
was unavailable; or evidence was not revalidated after edits. Source, exact public
programs, diff-bound receipts and the final delivered inputs can distinguish them.
Private tests, reference patches and raw model reasoning were not used.

## Implemented correction

[thin_policy.py](../../patchloop/dev/thin_policy.py) now states that availability
depends on current evidence and remaining budgets, that read/search can deliver
the evidence needed to reconsider an edit, and that finish requires a nonempty
scoped patch with required checks passing on that diff. Temporary absence does
not imply an unsupported capability. It does not promise that every observation
unlocks an edit, or that limits disappear.

The scheduler, gateway, schemas, current-policy prompt, default policy and
advisory-field removals are unchanged. No finish/probe gate or automatic replay
was added. The [reference](../../.agent/thin-policy-reference.md) carries the same
text. This small disclosure change is an operating-contract correction; no live
quality benefit has been established.

The new [transition tests](../../tests/test_thin_policy_runner.py) exercise both
read and search: an empty search leaves edits unavailable; delivered editable
source makes edits eligible; a patch alone cannot enable finish; a required-check
PASS on that patch enables finish. They also verify fact preservation while thin
continues to omit the advisory message and next-action field. Existing default
serialization and scarcity-parity checks passed.

## What the public evidence establishes

| Submitted candidate | Source change | Frozen WITH first-target indent | Plain SELECT |
| --- | --- | ---: | --- |
| Current repeat 1, row 1 | L003 removes extra indent-buffer segments | 5 spaces, expected 8 | Preserved |
| Thin repeat 1, row 8 | Same effective L003 change plus a public regression test | 5 spaces, expected 8 | Preserved |
| Current repeat 2, row 14 | L039 skips an indent meta segment | 9 spaces, expected 8 | Preserved |

The first two candidates treat normalizing the L003 helper as sufficient for the
complete formatter. Their source change addresses leftover whitespace, but the
full public pipeline still emits five spaces. Thin initially changed L036 to
copy target indentation; later regression-driven edits reverted that L036 change,
leaving the L003 repair and the new test. Current repeat 2 instead targeted a meta
segment's effect on L039's newline state, but its final default output still had
nine spaces. None of these local changes establishes a complete rule-interaction
repair. Existing [public loop diagnosis](2026-10-07-public-verification-failure-diagnosis.md)
already distinguishes the L003/L039 cycle from a simple desired-indent error;
the new candidates were not given another instrumented loop execution here.
Row 1 and row 8 have identical final L003 ASTs, and row 8's final L036 bytes match
base. Row 14's remaining whitespace-segment boundary behavior is a plausible
explanation, not a confirmed internal trace of that final candidate.

All **eleven solver probes** across these three runs used the empty baseline diff.
Restricted L003/L036 execution, sequential rule application and manual rule loops
are useful mechanism observations, but they are not a run of the final candidate
through the default fixer. The relevant baseline failure outputs survived in the
last actual model inputs. This weakens a simple context-disappearance explanation.
It does not show that the solver received and ignored a full-reproduction failure
on its final patch: that final observation was made only after submission.

Thin wrote a meaningful test invoking `sqlfluff.fix(sql)` without restricting the
rule set and asserting the complete expected output. Explicit selection passed
at journal sequence 281 on intermediate diff `945e1aaf...014e6`. Two further
source edits followed. The final input still retained that old PASS, while its
current diff was `94b0aeeb...f25f3`; the runtime did not relabel the old result as
current. This is evidence of a useful test being available but not re-executed.

The added function lives in the existing file `test/rules/std_L016_L36_combo.py`.
Its name does not match `tox.ini:105`'s `python_files = *_test.py`, so default
filename discovery does not include it. The final registered rules run still
reported 506 tests. This collection explanation is based on the public config,
filename and saved run; a separate collect-only invocation was not performed.

## Smallest decisive public check

We replayed only this existing selected-test node against row 8's unchanged final
candidate:

`test/rules/std_L016_L36_combo.py::test__rules__std_L003_L036_with_first_select_target_moved_to_new_line`

The registered `run_tests` path returned **FAIL, exit 1**, with one exact-string
assertion failure: `my_id` had five leading spaces rather than eight. Pytest
reported one failed test in 0.61 seconds. The public tool action itself succeeded;
there was no timeout, truncation, deadline exhaustion or failed cleanup. Workspace
base, diff and observed source hashes, prior journals and public receipts were
unchanged. No result was delivered back to the closed solver and no required-check
credit was granted.

The first preparation at `C:/pt/thdiag01` failed to establish image identity and
remained NOT_RUN with zero launches. The initial helper did not preserve the cause
of that failed inspect, so it remains unknown. Subsequent independent inspection
verified the same already-installed digest. A fresh bound plan in `C:/pt/thdiag02`
then admitted exactly one selected-test launch with a 90-second deadline, read-only
workspace mount, network disabled and pull policy never. No Docker Desktop start,
image pull/build, post-dispatch retry, additional node or collection run occurred.

This falsifies the assumption that the intermediate selected-test PASS remained
valid for the submitted candidate. It also contradicts a broad claim that the
agent could not express or execute a useful public test. Row 8 did react to real
public regression failures before submission; the problem is not universal failure
blindness. It returned to passing those regressions without rechecking its own
task-specific full-behavior assertion.

## Decision and remaining question

Keep current as the selected policy. The thin disclosure is implemented and
locally validated, but its effect on voluntary stopping and actual repair success
is NOT_RUN. No repeated paid prompt comparison follows from this result.

For SQLFluff-1733 the next useful verification action was already available: rerun
the exact added node, or the full public example, on the final diff. The runtime's
diff currency was accurate; existing suite PASS did not cover that obligation.
Before adding another policy mechanism, any future design should answer whether
it helps the agent carry this specific check across a revision. A global mandatory
probe rule or larger context/cost cap is not justified by this one case. Additional
edit capacity might matter for row 8, which used four slots, but both current
failures retained edit and verification capacity; capacity alone is insufficient.

## Evidence and validation

- Follow-up state: `C:/pt/thfollow01/runs/run_dev_thinfollowup.jsonl`.
- Public probe/input audit: `C:/pt/thfollow01/probe-audit/report.json`, file hash
  `sha256:bdd25f13912dd51f9f0c231cb3eab57d7c9d7c7b410e34ba44906dbee94e3fce`;
  its own `run_dev_thin1733probeaudit` journal binds 44 input hashes.
- Selected-test plan: `C:/pt/thdiag02/plan.json`, file hash
  `sha256:0b46374d21e309d5e001dfe28c3b1ce8074f4c5e2aec473013aa3e222fea5d0d`.
- Selected-test result: `C:/pt/thdiag02/selected-result.json`; public receipt hash
  `sha256:e3cbb84af5b6c4df47244343562e04268b85b6d2bf22e6dcb749cc0e4d339768`.
- Candidate diagnosis: `C:/pt/thdiag02/findings.json`, file hash
  `sha256:111a3839df78232eb84332d3525d7e5659c603294418c0f0463248425157a65f`.
  Its journal head is
  `sha256:362951501c256f11a64708ad64db7c2f54ed43bec067576451c00e1ded9a3611`.
- Focused validation: 8 PASS in 30.334 seconds,
  `C:/pt/thfollow01/focused/result.xml`; Ruff and task validation PASS.
- Actual mock CLI runs reached isolated acceptance PASS: current
  `run_dev_832e418c2fa546d9`, thin `run_dev_3750ec7b54a448da`. Each used four
  mock model calls, five actions and one edit, cost zero; safety is NOT_RUN.

The complete local fast suite used four file-grouped workers with real-Docker
opt-ins disabled: **4,680 PASS, 1 FAIL, 19 SKIP in 4,543.05 seconds (75m43s)**,
recorded in `C:/pt/thfollow01/fast-suite.xml` and `fast-suite.log`. This host used
Windows and Python 3.14.5; hosted Windows/Linux CI was not run. Skips retain their
platform, explicit-opt-in, planning-policy and dependency conditions.

The sole failure was the unchanged
`test_real_local_timeout_retains_partial_output_and_leaves_no_readers`: the child
process timed out at 0.3 seconds without a captured `partial` line. This test
implicitly needs child startup and first output to fit that window. The entire
capture test file then passed **28/28 in 0.768 seconds** in isolation, including
that case, with no source change (`C:/pt/thfollow01/capture-recheck.xml`). A
load-sensitive startup/capture timing explanation is plausible, not proven. The
original full-suite failure remains recorded; this is not an all-green full-suite
claim. No timeout or test expectation was weakened, and the broad suite was not
repeated merely to obtain a pass.

Documentation layout/link tests passed 5/5; whitespace checks passed. Runtime
bytes stayed fixed throughout validation at
`sha256:b3c8e80c0656fb4954eebcb5d30de411d4b0fa687a150ef3308883487bb08208`.
There were zero actual provider calls and zero new private task evaluations. The
single Docker launch was the public selected test above; mock evaluation is
separate from live evidence. User-owned AGENTS.md changes are excluded from this
change, and the closed comparison's result hash remains unchanged.
