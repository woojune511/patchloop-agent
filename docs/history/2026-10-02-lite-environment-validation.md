# SWE-bench Lite corrected-image validation

Date: 2026-10-02. Operator controls at `26f09d92`; official=false.
Follow-up to [environment preparation](2026-10-02-swebench-lite-environment-preparation.md)
and [original dev20 calibration](2026-10-02-swebench-lite-dev20-calibration.md).

## Question, authorization and intervention

Eight original images could not calibrate because of incompatible dependencies
or missing system libraries. Public-only preparation established corrections,
but did not establish original or isolated private evaluation compatibility.
The user explicitly approved the proposed eight image builds and original/hidden
revalidation. This scope contains no paid model run, solver change or task admission.

Built exactly the frozen recipes: NumPy 1.26.4 for five pvlib tasks; pytest 7.4.4
for two pydicom tasks; upstream pydicom-data 1.0.0 for pydicom-1413; and the pinned
Ubuntu libGL/libXrender dependency closure for PyVista. Each parent existed locally
at its exact digest. All recipe/dependency hashes, resulting local RepoDigests and
parent layer ancestry were verified. Builds ran sequentially, with the 12 GiB free
disk reserve retained. Original images and packages were not replaced.

New external draft packages differ only in `environment.yaml`. Public tests,
private tests, reference patches and vendored grader bytes are unchanged. New
native input rows differ only in image identity; original evaluation scripts and
test patches are unchanged. Evaluation remained network-disabled, with two CPUs,
2 GiB memory, bounded timeouts and at most two concurrent tasks.

## Results and changed decision

All eight corrected images passed original/native base/reference calibration and
registered private base/reference calibration. Every required original test was
accounted for. Base controls remained unresolved; reference controls resolved.

| Task | Required original cases | Reference public check | All-layer readiness |
| --- | ---: | --- | --- |
| pvlib-1072 | 19 | PASS | Ready |
| pvlib-1154 | 98 | FAIL: old NaN expectation | Blocked |
| pvlib-1606 | 11 | PASS | Ready |
| pvlib-1707 | 31 | PASS | Ready |
| pvlib-1854 | 282 | FAIL: old TypeError expectation | Blocked |
| pydicom-1139 | 41 | PASS | Ready |
| pydicom-1413 | 304 | PASS | Ready |
| pyvista-4315 | 115 | PASS | Ready |

PyVista reports 116 cases including its existing skip; all 115 required cases
are accounted for. Base public checks pass on all eight corrected images.

All six eligible reference submissions completed actual isolated EvaluationEngine
evaluation: hidden tests, public regressions, scope policy and safety policy all
passed. These known-reference controls validate the environment and integration;
they are not fresh coding-agent repair results.

The fixed dev20 roster therefore has six additional calibrated tasks, with the
prior twelve retained. Fully calibrated readiness is **18/20**, not a fresh solve
rate. The two failures remain in the cohort and are not replaced. None of these
twenty external drafts has been admitted for paid execution. No solver ran in this
follow-up; provider calls and provider cost were zero. The earlier mini pilot
remains 1/3 fresh solves at its separately recorded cost.

## Remaining public-contract conflicts

Environment correction exposed a different problem in two tasks. Both conflicts
are demonstrable from the public issue and unchanged base tests alone:

- **pvlib-1154:** the issue requires zero diffuse irradiance when GHI is zero.
  `test_reindl` still expects NaN in that case. The reference returns zero, so
  the old public check has one failure and 97 passes.
- **pvlib-1854:** the issue requests accepting a single `Array` in `PVSystem`.
  `test_PVSystem_multiple_array_creation` still expects that input to raise
  `TypeError`. The reference accepts it, leaving one failure and 280 passes.

These are not remaining import/library failures or new agent failures. The
original and registered hidden controls accept both reference patches, but the
current required public gate rejects them. No test was removed, rewritten or
weakened to manufacture readiness. The two tasks stop before EvaluationEngine
reference submission. Their initial failed controls remain immutable.

The decision changes from investigating image compatibility to investigating how
public regression selection should handle base tests that contradict a requested
behavior change. The question is now grounded in two observed contracts; it does
not justify changing prompts, supplying private test changes, or launching a paid
comparison. Environment corrections remain useful for the other six tasks.

## Build networking exception

The frozen commands used `--pull=false --network=none`. Package installation RUN
steps were offline, but BuildKit's image resolution/export was not: all builds
contacted registry metadata/auth, and the PyVista FROM stage logged acquisition of
the pinned parent blob `sha256:762bedf4b1b784c3de6c5022c5307d63123d3b7cdd59211317e37e9d477deaa0`
(about 30.44 MB). This did not meet the proposal's fully offline build intent.
The logs and exception are preserved; no further builds were launched after this
was noticed. No alternate base version, dependency download or image push occurred.
Resulting parent identities and ancestry still match the frozen inputs.

Do not treat `--network=none` for RUN as an offline guarantee for BuildKit itself.
Any future strictly offline build requires a separately verified builder/content
store path; this follow-up does not implement one. Actual evaluation containers
remained network-disabled throughout.

## Evidence and validation

External root: `C:/pt/analyses/lite-dev20-environment-validation-20261002-v1`.

- `build.py`, `build-*.log`, `images.json`: approved frozen recipes, full build
  logs, parent ancestry and resulting immutable image identities.
- `prepare.py`, `prepared.json`: separate draft packages in `C:/pt/ld20ep01`.
- `calibrate.py`, `calibration.json`: original/native and registered controls;
  original logs and workspaces are under `C:/pt/ld20ec01`.
- `engine_controls.py`, `engine-results.json`: isolated reference submissions
  and verdicts, with workspaces under `C:/pt/ld20ee01`.
- `runs/`, `artifacts/`, `engine-artifacts/`, `final-summary.json`: hash-chained
  journals, immutable evidence and complete twenty-task disposition.
- Separate journal entries bind the BuildKit network exception and both public
  issue/test conflicts. Historical reports, packages and failures are preserved.

Focused adapter validation: **27 passed** in under three seconds. The initial
attempt had nine setup errors because the default Windows pytest temporary root
was inaccessible; a fresh explicit temporary root passed. Both XML results are
retained. No test/code change was needed for this host-path problem.

The final audit verified **245 artifact references across seven journals**, all
twenty original package hashes, the eight unchanged non-environment package file
sets and native inputs, and absence of owned containers. Documentation validation
passed all five tests; Ruff and whitespace checks passed.

Only current status, this follow-up record and the history index change in the
repository. The prior full suite and mock evidence remain separate; no runtime
change required repeating them. The new Docker controls above directly validate
the corrected environment and its important success/failure boundaries.
