## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: validate
- Origin Date: 2026-10-25
- Verification Status: ANALYZED; selected observations reproduced locally
- Version Label: judgment-callpath-analysis-v1
- Scope: one exposed dev-train task; official=false, claim_eligible=false

## Validation report

The [judgment pilot](2026-10-25-judgment-correction-live.md) classified F0010
correctly but retained it after four accepted mutations. This investigation asks
whether those changes executed on the failing input and whether the agent received
evidence against its repair hypotheses. This matters because another output or
edit allowance cannot establish that the selected code influences the failure.

The result favors an unexercised repair branch over a repaired result ignored
downstream. The failing directory reaches two edited functions, but exits before
their changed behavior. The third function runs during Pylint initialization and
the control, not as the failing directory's package callback. The helper test's
core assertions also pass on the unchanged source. This does not establish a
successful repair or a general cause of model failure.

## Evidence and diagnostic design

Historical evidence is run `run_dev_ba8ee369693d4c84` under
`C:/pt/judgment-live-v1`. Read only public task/source, tool decisions, results and
dispatched public state. No private reasoning, hidden test, reference patch or
evaluator content was used. The runtime remains `94c72388`; documentation HEAD
before this investigation was `74f75a82`.

Alternatives were: changed branches never execute; a changed return value is
ignored later; or stale/unrelated code is imported. Read-only source inspection
was followed by three bounded operator probes: unchanged base and saved final
source, then a final-source trace filtered to the fixture's call path. The third
probe was justified because bounded event rows in the first pair filled with
checker initialization; their line sets and counts remained complete.

Each program retains the original setup, two `pylint.lint.Run` calls and v4
observer. It adds launch-thread tracing around each target call and equivalent
helper path assertions afterward. This is new instrumentation, not the historical
model's probe or another solve. Original source, dependency and journal files are
unchanged. Each probe has the existing 30-second sandbox bound; actual probe
durations total 30.817 seconds. Provider calls, image acquisition and evaluator
runs: zero. Network remains disabled in the sandbox.

The existing Python 3.9 image, prepared Pylint 2.12.2 dependencies and profile are
identical. Both source snapshot hashes match their historical counterparts:

- Base: `sha256:0e2fa0c1ea4ffd5be3f72f9a6df3ec011475cc80bae58056574121403589afaa`.
- Final: `sha256:f4f24af0661cd6a4779eb61abd3cd08d1bd65aa7ac1a30d870b45ae0a04b0b2d`.
- All three new probes and five historical probes share normalized actual
  conditions `sha256:d50e9bc224f44825513a583b5d7af6ca8a18feeaff8cb15cc3fcbdd01cb883e6`.

The original failing/control result remains `true/false`, with consistent host
judgments. Condition equality establishes comparability within this recorded
setup; it does not establish equivalence to every original user's CLI environment.

## What was already recorded and delivered

Historical `action_finished.result.output.public_execution` already measured
changed-line entries. Its scope is the launch thread across both calls, including
Pylint initialization; it is not per-target branch or return-value evidence.

| Candidate replay | Observed changed lines in modutils.py | Executable changed lines not observed |
| --- | --- | --- |
| After edit 1, sequence 116 | None | 631-633 |
| After edit 2, sequence 180 | None | 631-633 |
| After edit 3, sequence 300 | 264 | 269-273, 635-637 |
| After edit 4, sequence 365 | 264, 323 | 269-273, 635-637 |

Coordinates belong to each candidate. The test file was outside the probe's source
snapshot, so its trace status was unknown, not measured nonexecution. Registered
and selected test traces also reported unsupported Python options; test PASS did
not provide changed-branch coverage.

The negative line evidence was present in `public_execution_summary` at model
calls 8, 11, 12, 19, 20 and 23, with current diff/file hashes and replay action IDs.
The first three original failures were also delivered before the next edit. Thus
the evidence was not lost from model context. The pilot's `public-analysis.json`,
`judgment-analysis.json`, `delivery-analysis.json`, `collection.json` and
`closeout.json` omitted this field; the narrower summaries must not be read as
proof that execution feedback was absent. This follow-up preserves the old files
and records the missing interpretation separately.

## Actual failing path

The refined final-source trace records this sequence for `src/project`:

1. `get_python_path` returns `/tmp/patchloop-case/src/project`. The fixture root
   and its `src` parent are absent as absolute import roots. The additional path
   list contains relative `.` and the project directory itself.
2. `modpath_from_file_with_callback("src/project", ...)` cannot derive a nonempty
   module path. It raises `ImportError` at final line 325 before the callback or
   changed return at line 323. Static source explains why: `.` is compared with
   an absolute filename without being made absolute; the exact project root
   yields an empty relative path and is skipped.
3. Pylint `expand_modules` catches that error and falls back to `modname="project"`.
   A directory input makes it construct `src/project/__init__.py` at lines 70-71.
4. `_spec_from_modpath(["project"], path=...)` is called, but `find_spec` raises
   `ImportError` at final line 621, before the changed namespace branch at 635-637.
   The search roots do not provide the parent that would resolve this name.
5. `expand_modules` catches the error, sets `is_namespace=False`, and appends the
   synthetic init path. `get_ast` and `ast_from_file` pass it to `file_build`.
   Opening the missing file raises `FileNotFoundError`, then `AstroidBuildingError`;
   Pylint emits F0010. The normal file control has no F0010.

The descriptor is not always wrong merely because Pylint constructed an init path:
a successful PY_NAMESPACE lookup would skip it. Here the lookup failure prevents
that branch. The stderr cache-directory warning belongs to the control and is not
the missing-init F0010 cause. `exit` versus `do_exit` affects termination after
checking and does not explain this path.

Exact public sources inspected are under the saved final repository's
`astroid/modutils.py:261,312,604`, `astroid/manager.py:103`,
`astroid/builder.py:115`, and the prepared dependency directory's
`pylint/lint/expand_modules.py:19,62,89`, `pylint/lint/pylinter.py:1166`.
The dependency directory is
`C:/pt/calleruptake18/preparation-v2/B/site-packages`; the saved final repository is
`C:/pt/judgment-live-v1/workspaces/run_dev_ba8ee369693d4c84/repo`.

## Why each mutation failed

| Mutation | Reachability and discriminating result |
| --- | --- |
| 1: missing-init PKG_DIRECTORY becomes PY_NAMESPACE | `_spec_from_modpath` enters once for the failing directory but raises before this branch. Historical line traces already showed no changed-line entry. The selected finders normally create PKG_DIRECTORY only after finding an init file; an actual namespace can already return PY_NAMESPACE through PathSpecFinder. |
| 2: add namespace helper test | This changes no production behavior. It supplies `['src','project']` and `path=[fixture_root]` directly, bypassing Pylint's failed name/path derivation. Equivalent core type/location/file-path assertions pass on both unchanged and final source. This diagnostic did not run the original unittest harness. |
| 3: change `check_modpath_has_init` namespace handling | Its new missing-init body, final lines 269-273, is never entered in either original target call. During the failing Run it is called 31 times outside the `src/project` input path; early recorded arguments are Pylint checker initialization. The control additionally invokes it with an empty package prefix, so only the setup and successful return execute. |
| 4: strip terminal `__init__` from a returned module path | The failing directory reaches this function but raises before its return. Changed line 323 does run elsewhere in initialization/control; that does not establish use for the failing input or execution of the stripping arm. Pylint constructs the missing init filepath after this failed module-name lookup. |

The fourth edit therefore illustrates why a global line hit cannot substitute for
target-path evidence. All three edited functions execute somewhere inside Run,
but no new repair behavior is used on the relevant failing branch. The traces do
not support the alternative that a corrected namespace result was returned for
the directory and then ignored downstream.

## Why failure feedback did not produce a better next action

Host judgment checks whether the selected F0010 literal appears in captured
output. It does not verify the model's causal hypothesis or make the next edit
relevant. That first responsibility worked; the public decision process did not
use the resulting negative evidence to locate a causal path.

After the first refuted replay and no-hit feedback, the next mutation's public
basis still said the source fix was already in place and the remaining work was
a focused regression. Its `causal_revision` rebutted a test-coverage assumption,
not the failed prediction that the source change would eliminate F0010. Later
edits moved to other helper hypotheses without a new execution diagnostic. The
15 source reads/searches stayed within Astroid/tests; there was no recorded read
of Pylint's input expansion or an additional authored diagnostic probe.

The intermediate 1,232-pass suite and one helper-test PASS did not discriminate
the original failure, and neither applies to the final two implementation edits.
Four accepted mutations (three code edits and one test addition) exhausted the
edit limit. Unused money or a larger normal output cap does not explain why these
specific edits had no effect. The separate output correction already produced the
fourth edit successfully; that edit was still causally misplaced.

This is an inference from public actions and recorded predictions, not a claim
about the model's private reasoning or a controlled estimate of prompt quality.

## Decision and next unresolved question

Keep the original-failure completion gate and host consistency judgment. The
investigation changes the next diagnostic priority: connect the failing input's
actual name/search roots to the chosen file before another speculative helper
edit. Existing no-hit feedback should inform that bounded diagnostic rather than
motivate a universal coverage gate. Function entry, changed branch entry, changed
return value and downstream use are separate facts.

A useful next repair test must fail on the unchanged original caller and exercise
the intended correction on the candidate. An absolute-root helper test that passes
on both versions cannot serve that role. Changing fixture import paths solely to
remove F0010 would change the case and must not be counted as a repair. No runtime
policy, task source, saved candidate, limit or paid allocation was changed here.
Whether a targeted path-normalization repair satisfies the public task and
regressions remains untested; independent acceptance is NOT_RUN.

## Integrity, anomalies and reproducibility

Plans, scripts, full receipts and hash-chained journals are outside the repository:

- `C:/pt/judgment-callpath-v1`: retained pre-dispatch harness error, zero target runs.
- `C:/pt/judgment-callpath-v2`: base/final traces and helper assertions, 22.355 seconds.
- `C:/pt/judgment-callpath-v3`: refined final trace, 8.537 seconds, and read-only audit.
- Audit: `C:/pt/judgment-callpath-v3/audit.json`,
  `sha256:c2f90a93a049f4f4268ce88503f492c281292943ed3769544ef31c01ba0a6e9c`.

The first script passed the public purpose's `kind` field directly to the binding
model and failed before target dispatch; the next script used normal selection.
The final diagnostic saved valid exit-0 results and completion events, then failed
a leftover host assertion requiring seven events for two runs although this pass
had one run and five events. The read-only audit verified the correct sequence,
all referenced artifacts, unchanged inputs, matching snapshots/conditions and
successful target cleanup; no repeat target execution was needed for that error.
These operator errors are not evidence of target failure or model behavior.

Reproducibility verdict: REPRODUCIBLE for the selected baseline/final F0010 and
normal-control observations within the recorded environment. Historical model
trajectory, private acceptance and general repair gain were not rerun or verified.
New frame values describe the new instrumented execution, not an invented
historical trace. Documentation validation is recorded in the external closeout.

Statistical interpretation is not applicable to this deterministic, single-case
mechanism audit; no effect estimate, p-value or solve rate is inferred. Fallacy
scan coverage: 11/11 checked. Simpson's paradox, ecological fallacy, Berkson's
paradox, collider bias, base-rate neglect and regression to the mean are not
applicable to a group/probability claim here. Survivorship is addressed by retaining
all three target runs and both operator errors. Look-elsewhere and forking-path
risks are disclosed as exploratory trace refinement, not confirmatory significance.
Correlation/causation and reverse-causality checks restrict conclusions to observed
ordered control flow; they do not attribute a general causal effect to the host
judgment intervention or to a model policy.
