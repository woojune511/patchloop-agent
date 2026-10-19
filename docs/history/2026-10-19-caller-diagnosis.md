# Why the B caller capability did not become qualifying evidence

This provider-free follow-up diagnoses the six B trajectories from the
[frozen comparison](../../.agent/plans/caller-uptake-comparison.md), using saved
actual requests, public decisions/programs/results and the already completed
[saved-patch assessments](2026-10-19-caller-saved-assessment.md). It supplements
the immutable [original results](2026-10-19-caller-uptake-results.md); no solver,
probe, native assessment or provider input-count request was rerun.

## Question and conclusion

The B arm made the public caller available but produced no qualifying autonomous
uptake and no successful submitted repair. The important distinction is whether
the capability was not delivered, relevant evidence was never acquired, acquired
material was lost, or conclusions exceeded what the delivered evidence supported.
This determines whether the next engineering target should be delivery/retention
or investigation and completion judgment.

The observed bottleneck is **acquiring the original caller connection and keeping
conclusions within the tested scope**. Actual input delivery worked. B1/B4 never
probed, B2/B3/B6 exercised internal APIs, and B5 invoked Pylint with changed input
and message settings. B3 promoted internal success into an original-repro claim;
B5 declared the original repro verified while its complete altered program and
output were in the immediate input. This is not evidence that a qualifying
original-caller counterexample was acquired and forgotten. It also does not
measure judgment conditional on receiving an adequate caller counterexample.

## What was actually delivered

B's added treatment was installed `pylint==2.12.2` and the generic
`run_probe.description` in [probe_callers.py](../../patchloop/probe_callers.py).
Environment discovery was carried in that description, not a separate injected
caller trace. It explicitly described source inspection, actual arguments/cwd/
`sys.path`/environment, setup checks, the same-caller normal control, and the
limited scope of reduced helper calls. The public issue, common to both arms,
already contained the reported F0010, full layout, `cd root_dir` and the corrected
relative command `pylint src/project`. Thus "no injected trace" does not mean the
issue's reported failure or reproduction instructions were absent.

The new mechanical audit checked all 190 B requests, rather than prepared input
templates or installation records alone:

| Row | Actual requests | Exact caller disclosure / probe available | Segment changes after initial | Completed probes |
| --- | ---: | ---: | ---: | ---: |
| B1 | 18 | 18 | 2 | 0 |
| B2 | 35 | 35 | 3 | 2 |
| B3 | 31 | 31 | 3 | 1 |
| B4 | 32 | 32 | 3 | 0 |
| B5 | 37 | 35 | 5 | 2 |
| B6 | 37 | 37 | 8 | 2 |
| Total | 190 | 188 | 24 | 7 |

Every request carried the identical complete issue object, including the relative
command, cwd, parent initializer, missing child initializer and reported F0010.
Every advertised probe carried exactly one full copy of the caller addition.
The two exceptions are B5 requests 455/471: the existing completion horizon
temporarily restricted tools to edit/stop, then check/edit/stop, with 7/6 model
calls remaining. This was a real late restriction, not a missing B installation.
The caller probe was available in all earlier B5 requests and reopened at request
487, when B5 actually invoked it. It was available throughout the other five rows.

All seven completed probes delivered their full nonempty stdout/stderr and exact
program to the next actual request. Input presence establishes availability to
the model, not attention or understanding. The logs cannot determine whether the
long description was overlooked or consciously deprioritized; no public decision
claims that Pylint was unavailable in B.

## Where each trajectory diverged

Sequence numbers below belong to each row's public audit JSON, not global turns.
Request ordinals are one-based model calls within the row.

| Row | Observed path and decision | Diagnosis |
| --- | --- | --- |
| B1 | 15 repository reads/searches, then `check_modpath_has_init` edit (210), public suite, finish (244). No caller inspection/probe. Finish says the change matches the report and no material gap remains. At its input, 23 calls and about $0.611 remained. | Missing caller acquisition and unsupported completion; not forced by exhausted call/cost/time limits. |
| B2 | Internal probes at calls 8/24 (results 112/322). One inserts `src` into `sys.path`; the other passes absolute directory/missing-file paths directly to `ast_from_file` without the real caller's named/source arguments. Edit 437 changes directory handling; finish 466 calls it a direct repro match after the suite. | Reduced-helper observations drive the repair without establishing caller equivalence. Their successful transport is not qualifying caller uptake. |
| B3 | First probe at call 23 (325) returns `PY_NAMESPACE` and `file=None` through module-name APIs. Decision 349 changes note n4 and the plan toward tests only; 402 adds a passing regression; 431 claims the public failure is guarded. | Positive internal evidence is generalized beyond its entry/setup. The original failure was never reproduced. |
| B4 | 30 repository reads/searches, then directory callback edit 403. At 422 the plan reduces remaining verification to the required suite; 438 closes after PASS. Probe was still available, with 9 calls and about $0.341 at the finish input. | Caller acquisition is omitted and the plan's original repro obligation is narrowed to suite completion. |
| B5 | First helper probe at call 32 (432); installed Pylint only at call 36 (494), after editing and suite PASS. Finish 505 treats the changed invocation as the original repro. | Caller acquisition was late and non-equivalent; a directly observed scope error remains even with complete immediate delivery. |
| B6 | Helper probe 170 stops on an incorrect `sys.path[0] == ''` assumption (actual `/workspace`); helper probe 335 then changes the search path and returns mixed internal observations. A candidate public-suite failure is repaired, but the row ends without submission after an incomplete output/cost cap. | No qualifying caller evidence in observable actions; resource/incomplete-output limitation remains separate. Keep frozen uptake UNKNOWN, not a sixth completed non-use result. |

These are decisions recorded publicly, not reconstructions of private reasoning.
Source-only inference could have been sufficient if it established the actual
caller link; running Pylint was not required merely for its own sake. None of
these rows obtained that substantive caller source/setup connection. B5 inspected
the `Run` signature to invoke it, but did not inspect the relevant caller body or
establish equivalent inputs and observations.

## B3: a narrower result becomes the task conclusion

Result 325 is a valid observation about a constructed tree with the temporary
root inserted into `sys.path`, `file_info_from_modpath(['src', 'project'])`, and
`ast_from_module_name('src.project')`. Request 332 contains its full program and
output; decision 334 immediately searches for a regression-test pattern. After
the handoff, request 347 retains the question and exact output but omits the
program. Decision 349 rewrites n4 to say the remaining work is likely a test,
and the plan follows that conclusion. Request 361 carries this interpretation
with `model_authored_unverified` and `behavior_coverage=not_assessed` labels.

The preserved question/output still explicitly identify the internal API scope;
the original relative Pylint command and helper-scope warning remain in the same
input. At 402/431 the claim expands to the repro already being handled and its
public failure guarded. Therefore the problem is not that the runtime certified
the note as fact. The model uses a labeled interpretation as sufficient reason
to stop seeking the caller connection. The intervening program omission is real
and could reduce setup detail, but does not establish loss of an original-caller
failure: none was acquired, and the reduced entry point remained visible.

## B5: complete delivery does not prevent a verification error

Decision 489 explicitly recognizes that the suite has not exercised the
user-facing repro. Its program correctly constructs both layouts, checks cwd
and workspace source, and calls the installed `pylint.lint.Run`. However:

- It passes absolute `str(project)` / `str(control)` paths instead of the issue's
  relative `src/project` argument.
- It adds `--disable=all`, `--reports=n`, `--score=n`. It checks only that captured
  output lacks `F0010`; its seven passing setup checks do not check arguments,
  enabled diagnostics, child analysis, caller origin/version or effective config.
- The target output is empty with status 0. The control also has status 0, with a
  cache-write warning. There is no observation establishing that the expected
  child or the original failing call was analyzed. Absence of a message under
  altered reporting settings is insufficient to establish task correctness.

Result 494, the entire program, the original issue and full caller-scope warning
are present in request 503 despite a segment transition. Decision 505 nevertheless
states that the user-facing repro is verified and closes the task. This supports
a concrete **delivered-program/result interpretation error**, not transmission
loss. It does not prove whether the absolute path, disabled diagnostics, or their
combination was decisive for the empty output; this diagnosis did not run a new
factorial reproduction. Nor did B5 observe and ignore the true failing caller
result: its only Pylint invocation used the altered conditions.

## The missing connection, visible in existing separate evaluations

The already saved public caller assessments of all five B submissions enter:

```text
pylint src/project  (cwd = constructed root)
  get_ast(filepath='src/project/__init__.py', modname='project')
  ast_from_file(filepath='src/project/__init__.py',
                modname='project', source=True, fallback=True)
  file_build(path='src/project/__init__.py', modname='project')
  F0010 / missing file
```

This is the unestablished connection between the directory argument and the
missing initializer file, including an explicitly supplied module name and
source flag. A direct directory call or a successful `src.project` module-name
load does not establish this branch. The preserved B5 assessment uses the same
source diff hash as its solver probe and submitted patch; the original relative
input still fails while the present-initializer control passes. B3's source-only
projection is empty because its submitted change contains only added tests.

These assessments were **not solver inputs** and were not rerun here. They
corroborate the overbroad completion claims; it would be incorrect to say the
model ignored their trace. All five B native assessments are separately FAIL;
B6 remains unsubmitted/NOT_RUN. These outcomes do not identify which alternative
investigation would have produced a successful repair.

## Retention and competing explanations

There are real later omissions: the B2 helper programs disappear at requests
134/344, B3's at 347, and B5's first helper at 455. Their questions and outputs
remain. This audit does not equate full-program omission with no semantic loss,
nor claim retention is universally adequate. It specifically finds no acquired
original-caller evidence subsequently lost. B5's final judgment has the stronger
complete-program/result delivery evidence described above.

B6 provides a narrower counterexample to an explanation that all contrary
observations are forgotten. Its public cache-path failure at 484 is fully in
request 494. At 510 the complete log is omitted, but note n3, the unresolved
concern, plan and two source/test references preserve its meaning. Decision 526
corrects the source flag and the automatic recheck at 536 passes. B6 still does
not obtain the original caller path; the final output ceilings of 10,652 and
1,389 tokens and cost stop prevent a completed result. This is not a repair
success or an adequately observed caller-judgment trial.

The completion guidance also already says that required-check PASS establishes
eligibility, not correctness, and advises using a probe if it could change the
judgment. That message is present in the finish inputs. B4's plan nevertheless
shrinks from a repro-specific test to the suite alone; B3 keeps a broader claim
despite explicit unverified-note labels. Missing admonition, missing installation,
or total tool denial do not explain these completed trajectories. Attention to
the disclosure, investigation cost and prompt salience remain plausible
contributors, but their causal effects were not isolated by these logs.

## Decision and evidence limits

Keep the baseline, transition rules, two references and all budgets unchanged.
No runtime patch or new paid comparison is justified by this analysis alone.
The next concrete design target is the link from the current public question to
the actual caller arguments/environment, then from the observed scope to a
completion claim. A useful proposed check must distinguish "the original failure
path is now safe" from "a different helper succeeds / the message was absent."
More retained context cannot supply a caller connection that was never acquired.
Any later intervention must demonstrate that distinction before another success
claim; merely recording another plan/note or making a probe mandatory is not an
established solution.

The review is a single operator, retrospective, aware of arm/outcome, on one
development-exposed task. Frozen pre-grade uptake labels remain unchanged. The
new mechanical counts are exhaustive for B; semantic explanations are supported
case diagnoses, not randomized causal estimates or general model-quality claims.
Opaque reasoning stays opaque; only sanitized public exports were inspected.

External evidence: `C:/pt/callerdiagnosis19/` contains the provider-free extractor,
`inputs-before.json`, `request-audit.json`, per-row decision/probe extracts,
`diagnosis.json`, preservation/validation receipts and a separate hash-chained
`dev-run-v1` journal. Event sequence/hash and source-file hash bind excerpts to
`C:/pt/calleruptake18/packet/audit-public/`. The original panel journal, sealed
annotations, collection and prior assessment receipts remain unchanged.

This change contains only the follow-up report and current/index pointers.
Documentation layout/link tests are the applicable validation; full runtime tests,
mock smoke, new caller/native evaluations and provider calls are not rerun.
The preexisting user edit in `AGENTS.md` remains outside the commit.
