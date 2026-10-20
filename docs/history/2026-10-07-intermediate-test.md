# Intermediate selected-test execution

Date: 2026-10-07. Source baseline: `6ccfda36`. Official=false, claim-ineligible.
This resolves the intermediate-outcome question in the
[timing analysis](2026-10-07-selected-test-timing.md). The user authorized one
execution of the original selected public test file on the third-edit candidate.
No paid solve, original-run continuation or private evaluation was performed.

## Question and reconstruction

The timing analysis found one remaining edit after SQLFluff-1733 thin repeat 1's
third mutation. Its selected-test result on that diff was unknown. The diagnostic
asks whether repeating the existing selection there would have revealed the task
failure while repair capacity remained. A PASS would weaken that proposed benefit;
an assertion FAIL would establish earlier detection, not successful correction.

Reconstructed a separate local checkout at public base
`a1579a16b1d8913d9d7c7d12add374a290bcc78c`. Applied only the original accepted edits
admitted at sequences 255, 267 and 356: L036, the added test, then L003. Each
preimage, unique replacement anchor, postimage and complete successive diff hash
matched the immutable journal. The final reconstructed diff was exactly
`sha256:59679012118d519810c25430eb177c6fe0fb5480b986b452b6c2e8bd676d2987`.
The original final workspace was not modified or resumed.

The current public task matched the saved public context exactly. Reused its
registered `public-pytest` suite and original whole-file target
`test/rules/std_L016_L36_combo.py`: three existing tests plus the added full-default
`sqlfluff.fix(sql)` CTE assertion. No test source, expectation, selector or wrapper
was changed. This was not narrowed to the added node.

## Executed result

**4 PASS, exit 0**, with one existing dependency deprecation warning. Pytest took
0.54 seconds; the complete gateway action took 17.540 seconds. All four functions
in the selected file executed successfully, including the full-output assertion
expecting eight spaces before `my_id`.

One registered public check launch used the already-installed pinned image
`swebench/sweb.eval.x86_64.sqlfluff_1776_sqlfluff-1733@sha256:b440a9c4befe45341ce69f1d4166335b749a28ea8414fdd61dcf715b92d9375e`.
The original 300-second suite timeout remained unchanged, within a fresh
330-second operator deadline. This was not a resumption of the solver's recorded
remaining time. The container had no network, read-only source/root, pull disabled,
and confirmed owned-container cleanup. Timeout, truncation, deadline exhaustion
and cleanup-failure flags were all false. No daemon start, image pull/build,
retry, replacement launch or collection-only run occurred.

## Combined evidence and decision

| Candidate | Task-specific selected behavior | Required public regressions |
| --- | --- | --- |
| Third edit, `59679012...d2987` | **4 PASS**, newly executed whole file | Saved sequence 362: **1 FAIL / 505 PASS** |
| Fourth edit, `94b0aeeb...f25f3` | Prior operator execution: added node **FAIL**, five spaces versus eight | Saved sequence 378: **506 PASS** |

The third-edit candidate therefore preserved this task assertion while still
failing an existing L036 fixture. Reverting L036 produced the final candidate,
which passed the required regressions but failed the task assertion. The new
result does not convert the earlier candidate into a correct patch or cancel its
saved regression failure. The final whole file was not executed here; the prior
final observation covers its added node. No hidden failure cause is inferred.

Earlier automatic revalidation at the third-edit point would have returned PASS
for this selection in the checked environment. The proposed rule therefore has
no demonstrated earlier task-failure feedback on this trajectory. Revalidation
after the fourth edit could identify the known failure only after all four edits
were consumed. This weakens the proposed repair-success justification for that
rule; it does not establish that automatic revalidation is useless elsewhere.

Keep current and defer the automatic selected-test prototype and paid comparison.
The remaining engineering problem is to produce a revision that preserves both
the original task behavior and existing L036 behavior. Repeated PASS reminders,
larger context or detecting this final failure do not by themselves provide that
revision. Any further intervention needs evidence about the incorrect final
repair hypothesis or repair-capacity use, rather than another adjacent prompt
comparison. No new runtime feature or solver-quality improvement is claimed.

## Evidence and validation

- Preparation/execution helper: `C:/pt/stest01/check_intermediate.py`.
- Frozen plan: `C:/pt/stest01/plan.json`, hash
  `sha256:eabc9117fe7861ebe427748ce0683238ea315e7ed6114fa2e75d497a549b1de6`.
- Reconstruction identities: `C:/pt/stest01/reconstruction.json`.
- Result: `C:/pt/stest01/result.json`, hash
  `sha256:b80b9faa091ac35d6c192ed1905fb3b72e47aade412ed86dfb24c186df55f4e0`.
- Full public receipt hash:
  `sha256:ae78d167d51ee8ad5c628314a2097b868ba611f546450c44505e2b6f0217f60c`.
- Append-only journal: `C:/pt/stest01/runs/run_dev_intermediateselected.jsonl`;
  registered action journal: `C:/pt/stest01/selected/runs/run_dev_selectedintermediate.jsonl`.
- All 151 bound files and all 1,807 tracked-file hashes in each original and
  reconstructed workspace remained unchanged across execution.
- Independent read-only reviews verified reconstruction, readiness, both journal
  chains and the completed result. Documentation layout/link checks passed 5/5;
  Ruff and whitespace checks passed. No runtime code changed, so the broad suite
  and mock smoke were not repeated.
  Runtime content remained
  `sha256:b3c8e80c0656fb4954eebcb5d30de411d4b0fa687a150ef3308883487bb08208`.

No output was supplied to a solver or granted required-check credit. Provider
calls and new private evaluations were zero. Closed reports, original task
workspaces and original journals retain their previous bytes and outcomes.
