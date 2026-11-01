# Public empty-output repair on the saved mini candidate

## Material Passport

Date: 2026-10-27. ARS run/validate, official=false and claim-ineligible.
Status: COMPLETED. The user authorized proceeding from saved-mini verification.
This is a local operator-authored intervention on that candidate, not a new mini response or a
fresh model solve. No provider calls, credential reads, image pulls or builds.
Production PatchLoop runtime/defaults and historical candidate bytes are unchanged.

## Question and public cause

The [saved-mini verification](2026-10-27-mini-candidate-verification.md) resolved
the original F0010/exception under a corrected input/cache boundary, but exposed
C0112 and exit 16 for the public issue's empty-file example. That issue explicitly
describes empty output for empty files. This gap matters because the earlier
no-F0010 predicate could pass while the public expected result remained unmet.
The separate prior acceptance FAIL was not used to infer a private failure cause.

Public source establishes the mechanism:

- Astroid `builder.py:292` constructs a namespace module with `doc=""`.
- `rebuilder.py:107-121` represents absent docstrings in parsed source as `None`.
- Pylint `checkers/base.py:2222-2269` distinguishes missing from explicitly empty
  docstrings. An empty string takes the C0112 branch. `None` on an empty module
  takes the empty-body exception and requires no docstring.
- Astroid `interpreter/objectmodel.py:165-166` also uses `Module.doc` for inferred
  `__doc__`, so the intervention changes that public value from `""` to `None`.

The single new repair changes `doc=""` to `doc=None` in namespace construction.
It retains mini's empty byte stream and UTF-8 encoding and the earlier seed's
missing-initializer guard. The full candidate is therefore inherited work plus
one operator-authored line, not a one-line repair from the original repository.

A broader alternative would change namespace/path classification so the caller
does not choose a nonexistent initializer. This experiment does not establish
that the inherited guard is the right general solution. It tests the demonstrated
docstring-representation defect without bundling a second path intervention.

## Sealed local procedure

Task: `dev-train/current-dev20/13`, Astroid-1333, base
`d2a5b3c7b1e203fec3c7ca73c30eb1785d3d4d0a`.
The plan, test source, three caller programs, candidate lineage, stop conditions
and operator hash were sealed in `dev-run-v1` before any target execution.
Each row used a fresh prepared workspace and identical recorded seed/mini edits.
The operator line was applied only to fresh external copies. Source pre/post
images and full patches were stored in the content-addressed artifact store.

All caller programs execute the complete `pylint.lint.Run` target. Fixture inputs
are separate from HOME/cache outputs; neither arbitrary input changes nor the old
strict-identity verdict is ignored. Capture expectations apply to each target
call's stdout/stderr, not unrelated helper dependency warnings.

| Program | Frozen expectation | States |
| --- | --- | --- |
| Empty fixture, missing initializer | Empty target stdout/stderr, exit 0, no unexpected exception | mini, operator |
| Original nonempty fixture | No F0010/C0112 or unexpected exception; standalone control unchanged | mini, operator |
| Real initializer and standalone with explicit `""` docstrings | C0112 remains in both real-file calls | mini, operator |

After the target calls, each helper checked a separately constructed namespace's
`doc` and inferred `__doc__` against absent-docstring semantics, empty parsed-source `doc=None`, and
preserved name/path/package/file absence/stream/encoding. This is a direct public
representation check, not an independently sampled benchmark requirement.
The nonempty standalone control separately retains C0114.

The three input conditions each ran once per state, six probes total, with a
120-second deadline per probe. One public regression was permitted after all
operator public checks passed; one separate isolated acceptance was then permitted.
Infrastructure, incomplete capture or uncertain cleanup stops further dispatch.
Expected semantic baseline failures remain in the record. No hidden-feedback
repair iteration was planned or performed.

## Public results

| Observation | Saved mini | Operator candidate |
| --- | --- | --- |
| Empty missing-initializer call | C0112, exit 16 | Empty output, exit 0 |
| Empty standalone control | Empty output, exit 0 | Identical |
| Nonempty original directory call | C0112, exit 16 | Empty output, exit 0 |
| Nonempty standalone control | C0114, exit 16 | Identical diagnostic and score output |
| Real initializer with explicit empty docstring | C0112, exit 16 | Identical |
| Real standalone with explicit empty docstring | C0112, exit 16 | Identical |
| Namespace doc / inferred `__doc__` | `""` / `""` | `None` / `None` |
| Name, path, package, file absence, empty stream, UTF-8 | Preserved | Preserved |

All twelve target calls had complete capture and no unexpected exception.
Selected original/control inputs matched between states for each program, and
all three control outputs/outcomes/exit codes matched. The six probes completed
in **72.899 seconds**. With the public regression, total elapsed was **85.818 seconds**.
The public regression returned **1,231 passed, 69 skipped, 15 xfailed** on the
sealed operator candidate; this check's own pytest time was 8.40 seconds.

The explicit-empty-docstring row's expected caller behavior passed in both states.
Its mini row's aggregate test result is false only because the separate namespace
representation check still found `""`. It is not a new failure of the real-file
negative control. The complete outputs above preserve that distinction.

Independent public audit rechecked all six receipt hashes, current workspace
patches, selected inputs, control comparisons and observed metadata. It identified
a limit in the frozen `isolated` predicate: absence of F0010/C0112 plus normal
execution can allow other diagnostics/nonzero SystemExit values. The actual
recorded operator call satisfies the stronger empty-output/exit-0 condition, but
the predicate should not be reused as a general no-error oracle. Metadata was
measured on separately constructed namespace objects, not object-level tracing
inside Pylint. These limits do not alter the recorded caller outputs.

## Separate acceptance and decision

The sealed operator candidate was evaluated once through the existing isolated
task evaluator in a fresh prepared workspace:

| Verdict | Result |
| --- | --- |
| Acceptance | **FAIL** |
| Regression | PASS |
| Scope | PASS |
| Safety | PASS |

Evaluation completed, `scope_compliant_success=false`, with an unchanged candidate.
The host manifest's `agent_submission_status=completed` is synthetic submission
for saved-patch evaluation; no model continuation or `finish_task` occurred.
Private test/spec/reference content and raw evaluator logs were not read into
coding context. Only verdicts and identities were returned. No further edit or
evaluation was made from this private negative verdict.

Decision: the public docstring defect is repaired, but this full candidate is
still not an accepted task solution. The experiment rules out remaining C0112 in
the tested empty fixture as a sufficient explanation for the current acceptance
failure; it does not reveal what private test failed. The broader seed guard's
namespace/path coverage and directory traversal remain unverified. Before another
paid repair experiment, the useful question is which additional public call/path
discriminates the incomplete guard from correct namespace handling. There is no
new evidence for increasing context/output limits or changing production models.

Keep the operator patch as a diagnostic artifact. Do not credit this one-line
intervention to mini, or infer agent improvement from its public tests. Production
runtime and defaults stay unchanged; all prior paid allocations remain closed.

Local maintenance validation: Ruff passed on the two external operator/test files;
the five documentation-layout checks passed. Repository changes are documentation
only, so the runtime quick/mock suite was not repeated. The actual candidate public
regression and isolated evaluation above are separate from those maintenance checks.

## Reproducibility and limits

- Local operator/tests: `C:/pt/namespace-doc-repair-v1/run.py` and `public_tests.py`.
- Result: `C:/pt/namespace-doc-repair-v1/results/result.json`.
- Hash-chained journal: `results/runs/run_dev_namespacedocrepair.jsonl`.
- Candidate workspace: `results/empty-operator/workspaces/verify/repo` under that root.
- Saved mini diff: `sha256:a08485418d8117b4dd8507346f7aeed8e66ff0e1e46a0efd33dcee8449cc4bcb`.
- Operator full diff: `sha256:f888231b7932f2022077ba46aed96ef71b87603a7fe97eb7c3890d719faaa908`.
- Operator source: `sha256:c3d236fb7453bdd8fdb77fee7b9b5274afd21a6f5c46f390935a0c550c13bc6c`.
- Test source: `sha256:6d1907c92d99578cb937f2f216917cb9f6632c2726210bbad76fc84546a75ed5`.
- Plan: `sha256:3f5ecd2974603975a3b464c2a4c6fdb65f0fc211ad2a45a63c649de8b307e226`.
- Result: `sha256:58ad5283427a368ccebb89dddba906074668188f47b705a8fc8fdce4fa4824c8`.
- Journal: `sha256:602c1a3b34799cb7f8ca6c341bd6ee125d66f072d94d49ccd2f7785f1a47f229`.
- Public regression receipt: `sha256:54281a813a1c984d185e9156b882f4122c053cfd9e78f7fb281d07798466f211`.
- Runtime: `sha256:5753dbef010721c721db788aa01525fc269ad12093b46e45ffc2ffd158c929f3`.
- Prepared source: `sha256:16326c5cddf7f836cee378e8c47b01eded3689e3f9cfcd604e086aae6ddd6a20`.
- Dependencies: `sha256:685f01a9d10d047d798a164480ab4a16482b13299debd6ef2377b88a43077450`.
- Public probe image: `sha256:dad5b29e3506c35e0fd222736f4d4ef25d21b219acdd73f7bb41d59996ca8e0d`.
- Regression/evaluation image: `sha256:4014d41119b96aa182d1c2b1299c3ec32a6b36ea9ef03e8e90f053b4a535b2b4`.
- Isolated summary: `C:/pt/namespace-doc-acceptance-v1/summary.json`,
  `sha256:282d38e171f3f907dfe5a0ccbdc8a2ad3dabd34a819f69387fe206dabbe15b85`.
- Isolated manifest: `sha256:4bdedc7e21abfc845f192f8bc3da4b83879ddddc5154c5f649573f9d7850184d`.
- Isolated journal: `sha256:7fbfa5f5d573b63364e6ab54b22b41bd4d2eabe4ef232879a4c3290369ce103b`.
- Opaque evaluation artifact: `sha256:fdc013e60b17053062bc74e0f481b2b360d9372f0e104e8ea1b48eb3b7eea3c0`.
- Harness commit during execution: `43329438930eebadd2e9d57c3436ceb4530f4a29`.

The changed line accounts for the observed C0112 difference under these fixed
conditions. This does not measure model selection quality, a context-budget
effect, fresh-solve probability, general namespace correctness, or traversal of
nonempty child files. The candidate remains a diagnostic artifact and is not
automatically adopted into the coding agent. A larger model budget was unnecessary
to perform this local test; its usefulness for a fresh solve was not measured.

Statistical fallacy coverage: 11/11 checked. Simpson's/ecological/collider/base-rate,
regression-to-mean and reverse-causality analyses do not apply to this deterministic
single-task comparison. Selection bias limits transfer from this known failure;
all six rows are retained, avoiding survivorship/selective-result claims. The plan
was fixed after observing the public symptom and before this comparison, so the
work is targeted development evidence, not preregistered general confirmation.
No statistical significance, solve rate or model-causal effect is claimed.
