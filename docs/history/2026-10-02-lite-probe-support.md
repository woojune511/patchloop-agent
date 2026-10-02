# Public probe support for legacy SQLFluff sources

Date: 2026-10-02. Provider-free follow-up to the
[Lite dev20 diagnosis](2026-10-02-lite-dev20-failure-diagnosis.md).
The original allocation, patches, hidden tests and 10/20 verdict remain unchanged.

## Problem and decision

Seven agent-requested probes across SQLFluff-1517, -1625 and -1733 failed before
task behavior: missing dependencies or a tracked fixture symlink. The existing
prepared public dependency option already supplies source roots, offline wheels
and omission of symlinks, but the closed batch did not bind a descriptor. Attaching
the evaluator image would violate the clean-probe boundary and was not used.

The existing operator setup.py adapter could not prepare these public sources:
it required pyproject.toml, omitted plugin entry points, and its workspace-metadata
callback did not accept the common preparer's `lock_directory` keyword. Additionally,
the public package imports `pkg_resources`, absent in the pinned clean Python image
and not declared in install_requires. Merely installing declared dependencies
would therefore not establish usable lint/fix behavior.

The selected intervention repairs this existing preparation path. It does not add
agent installation commands, a new execution backend, compulsory probes, or hidden
feedback. Alternatives were an incorrect saved probe program or a remaining sandbox
restriction; unchanged program replay tests these after preparation works.

## Implementation

- Permit literal setup.py metadata with absent or tool-only pyproject.toml; bind
  its absence and setup hash. Generated pyproject output preparation verifies
  the setup-only metadata and skips nonexistent build declarations.
- Accept the common root lock-directory argument in the adapter callback.
- Preserve validated literal plugin entry points as dist-info metadata. Setup
  code/build hooks are never executed, and no console executables are generated.
- Add an explicit operator `--supplemental-requirement` option for public-index
  compatibility dependencies. These intersect source requirements and are recorded
  separately from them; no automatic extra, URL/self dependency or pip option.
- Prepare three source-bound bundles using `src` and explicit
  `setuptools==80.9.0` for the public pkg_resources import. The ordinary CLI resolver
  and default generic probe profile are unchanged. Future runs must explicitly bind
  their task's descriptor with `--prepared-probe-dependencies`.

The normal DockerProbeSandbox still uses its pinned clean Python 3.12 image,
read-only public source/dependency snapshots, no network, bounded CPU/memory/PIDs,
and confirmed owned-container cleanup. No evaluator files/environment were copied.
Public wheel resolution/download occurred only in the operator preparation step;
no image was pulled or built. Source-root selection excludes non-runtime fixtures
without following their symlinks or changing original source bytes.

## Executed comparison

Evidence: `C:/pt/analyses/lite-probe-support-20261002-v1`, including the hash-chained
`runs/run_dev_liteprobesupport.jsonl`, three `dependencies-<index>` descriptors and
resolution/install receipts. Indices 16/17/18 map to 1517/1625/1733.
The first preparation launcher used a public.yaml path where a directory was needed;
that operator failure is retained, and the corrected launcher prepared fresh outputs.

Replayed all seven saved public probe programs unchanged on their prepared **base**
sources, not resumed candidate states. Repeated the first program per task in the
generic environment as a current control. An additional operator public API program
per task exercised alias lint, CTE fix and repeated-delimiter behavior without stubs.
These programs used public examples; no hidden/reference inputs or repair hints.

| Task | Generic control | Prepared saved programs | Operator public API program |
| --- | --- | --- | --- |
| 1517 | Missing pytest | 1/1 exits zero; captures the original dropped-elements RuntimeError and its segment mismatch | Executes alias/CTE checks and captures the delimiter RuntimeError |
| 1625 | Missing sqlfluff import | 4/4 exit zero and reach parsing/linting | Exercises actual L031 and CTE behavior without dependency stubs |
| 1733 | Fixture symlink snapshot rejection | 0/2 exit zero, but both import/instantiate Linter and the second parses SQL | Executes and exposes the public nine-space indentation defect |

All three operator programs exit zero. The two 1733 failures are now errors in the
saved programs: nonexistent `Linter.fix_string` and `FileSegment.raw_segments`.
These errors were previously hidden behind snapshot rejection. They were retained,
not rewritten to count as successful agent probes. The 1625 saved programs also
have diagnostic limitations: two inspect direct children of FileSegment and find
no select references; later programs contain dependency stubs. Successful process
execution is not proof of a correct hypothesis or a discriminating observation.

All completed probe launches confirmed cleanup; no timeout or output truncation was
observed. This establishes execution availability for these public entry points,
not full parity with the Python 3.9 registered-check environments, an improvement
in autonomous repair rate, or successful task acceptance.

## Validation and next question

Focused tests exercise the real prepare pipeline with stubbed public resolution and
offline installation, discoverable plugin metadata, descriptor reuse, metadata drift,
unsupported entry points and rejected non-index supplements. Docker observations above
exercise real public wheels and the normal probe launcher. Mock smoke reaches isolated
acceptance with `EVALUATOR_PASS`; its safety state is `NOT_RUN`.

Focused validation: 57 tests passed; documentation layout: 5 passed; Ruff and
`git diff --check` passed. Full four-worker Windows suite: 3,991 passed, 16 skipped,
one failure in 1,081.50 seconds. The failed check-feedback test tried to create a
262-character temporary path (parent directory exists); no changed adapter code
was on that stack. With a short external basetemp, its entire file passed 46/46
without code changes. The first short-path retry named an absent parent directory
and failed fixture setup; both retry XMLs and the original full-suite XML remain
in the evidence root. Do not report the first full invocation as all-green.

Keep the prepared bundles available for explicitly scoped future runs. No paid solve,
resume, hidden evaluation, benchmark rescore or merge was executed. The next unresolved
question is whether an agent uses these now-available observations to correct its
program and repair, including post-edit reproduction. Do not answer it by injecting
the exposed hidden tests or silently repeating the closed dev20 allocation.
