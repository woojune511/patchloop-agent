# Public caller preparation

## Problem and decision

The [public caller diagnostic](2026-10-18-astroid-caller.md) reproduced a failure
through the original caller setup that three saved candidates left unchanged.
The caller was unavailable in the solver's original dependency bundle, and its
source was outside repository read/search scope. The successful helper probe
used a different setup. This matters because missing caller evidence and an
overbroad interpretation of a helper result can both prevent a correct repair.

Keep transition rules, two evidence references and all resource limits. Add an
explicit, generic public caller preparation path to the existing dependency and
probe mechanism. Do not tune retention again, add a task-specific reproduction
recipe, or treat access to a caller as proof that a model uses it correctly.
If the relevant caller is already available, this preparation is unnecessary;
if acquisition succeeds but the same failure is still ignored, judgment remains
the next question. These are distinct from dependency/import failure.

## Change

`--resolve --caller-requirement package==version` prepares explicitly pinned public
callers and their dependencies. `--runtime-profile` exposes existing reviewed
profiles through the preparation CLI. Operator pins stay separate from repository
requirements. The exact workspace distribution alone is excluded during both
resolution and offline installation, so current source remains under test.
Other dependency checks remain enabled. The release-version substitution is
marked unverified, and no image is downloaded or built.

The normal descriptor binds selected wheel origins/hashes, source identity,
exclusion and installed bytes. The normal sandbox provides read-only caller
source and imports. Its conditional tool description identifies available callers
and directs inspection of their entry points, actual arguments, cwd, import paths,
environment and input layout before testing failure and normal controls. No
caller-specific expected result, repair hint, copied implementation or private
material is injected. No solver network, shell or installation capability is added.

This enables public caller inspection and reproduction within the existing probe
caps; it does not automatically reconstruct an issue's input or prove equivalent
environment, semantic coverage, version compatibility or end-to-end success.
The model still has to establish those facts from observed public evidence.

## Local validation

Evidence root: `C:/pt/analyses/public-caller-preparation-20261018-v1/`.
Tests use synthetic caller and leaf wheels. Real uv resolution is redirected to
only those local fixtures with `--no-index`; production public URL admission is
tested using their recorded hashes. No provider/count API or external package
download is involved. Installation is real uv, offline, with all non-workspace
dependency checks retained.

The caller sets its import path and reads an environment condition, then calls
the current project with a relative input path and a strict argument. A reduced
helper succeeds while the original missing-file case fails. A helper-only edit
still leaves that caller failure; an edit to the actual route changes it. The
normal-file control succeeds in every state. Observations include source,
distribution version, implementation origin, actual arguments, environment,
cwd and input-file existence. This tests capability and failure discrimination,
not a model repair outcome or the Astroid task's correctness.

Results at runtime content hash `20fb1541d4b2aa5c2f5af6e67f74546ae8762f74c4325988535dc7202075bf0a`:

- Focused tests: 23 PASS, one explicitly opt-in Docker case SKIP, 66.39 seconds.
  Invalid pins, changed caller bytes, missing non-workspace dependencies and an
  accidentally selected workspace wheel are rejected. Both legacy metadata
  adapters and the CLI are covered. No validation or resource limit was relaxed.
- The opt-in Docker case separately passed in 18.17 seconds, executing three
  synthetic source states on the existing pinned Python 3.12 image. Setup checks
  passed, actual Python was 3.12.13, and cleanup was confirmed for all three probes.
  The same observations were also verified in fresh local Python processes.
- Related preparation/probe/replay/setup regression: 261 PASS, 401.22 seconds.
- Evidence selection, handoff, budget and documentation checks: 100 PASS,
  232.12 seconds. These broader groups exceed the focused two-minute target;
  the focused group remains below it.
- Both append-v1 and segmented-v1 mock smokes delivered caller discovery and
  reached `EVALUATOR_PASS`, safety `NOT_RUN`, cost zero. Their hash-chained
  journals bind the same runtime content hash as above.
- Ruff and whitespace checks passed. Six caller-free tool-schema configurations
  exactly match the prior implementation. Transition/notes/context/budget and
  sandbox implementation files are byte-identical. All 1,160 pre-existing closed
  history/report/archive files and the user's pre-existing AGENTS edit are preserved.

The full repository suite, new Astroid execution, model uptake and repair-quality
comparison were NOT_RUN. There were zero provider/count calls, zero billed cost,
no network package download and no image acquisition. This adds a locally tested
capability, not evidence of improved repair success. Original caller/version/input
selection and environment equivalence must still be established for each public
task before interpreting its probe as a reproduction.

`before.json`, `boundary-verification.json`, `sandbox-validation.json`,
`mock-smoke-receipts.json`, test logs and the hash-chained
`runs/run_dev_publiccaller18.jsonl` retain validation and preservation evidence.
