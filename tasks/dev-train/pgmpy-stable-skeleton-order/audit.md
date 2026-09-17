# pgmpy stable skeleton: development admission

## Scope and reproduced defect

This new `dev-train` package is development-only (`official=false`). It does not
alter a historical manifest, held-out package or previous run. It is not an official
SWE-bench result or a statistical estimate of causal-discovery quality.

- Public issue identity: `pgmpy/pgmpy` #3137, selected from the existing labeled
  `2026_03` SWE-rebench metadata cache. Selection provenance and the limitation on
  current remote dataset identity remain at
  `C:\pt\analyses\fresh-devtrain-selection-20260917-v1`.
- Repository: `https://github.com/pgmpy/pgmpy.git`.
- Exact base: `da98466c0a79cb416562e450d85699aedc10f422`.
- Existing image:
  `swerebench/sweb.eval.x86_64.pgmpy_1776_pgmpy-3137@sha256:59c70ad80ed211d327d106b792c5cebae78ffe35932a7540c5dd1e871cd573c0`.
- Edit scope: `pgmpy/causal_discovery/**`, at most two files and 120 diff lines;
  no public API, dependency or test changes.

At this base, `stable` and `orig` remove edges immediately while later calls read
neighbors from the same live graph. Removing an earlier edge can erase a valid
separator for a later edge in the same conditioning round. The public requirement
is stable round semantics, not a prescribed patch. Neighbor availability must be
refreshed between rounds; sorting traversal order or keeping the initial graph
forever does not satisfy that requirement.

## Public and private checks

The public contract uses a deterministic symmetric CI callback on three nodes.
Across all six column permutations it checks exact edges, separating witnesses,
node identity and input column order at depth limits zero and one. The unchanged
base passes all six zero-depth observations and fails all six one-depth observations.
These CI tables exercise algorithm behavior without claiming to model sampled data.

The public regression selects seven existing upstream cases: original/stable
skeleton construction, both variants' independence-based construction, collider
orientation, and both temporal-separator implementations. All seven pass on the
unchanged base. Statistical/data-download tests and unrelated estimators are not
silently included in this bounded selection.

The isolated evaluator makes 150 deterministic observations over renamed nodes,
all relevant column permutations, conditioning depths up to two, per-round neighbor
refresh, required/forbidden edges, enforcement disabled, temporal ordering, and
original/parallel preservation (`n_jobs=1`). Its oracle enumerates admissible CI
witnesses using immutable edge sets and relations, independently of production's
NetworkX traversal. It checks input preservation, exact nodes/edges and valid
separating-set entries; multiple valid witnesses are accepted. Required undirected
edges are represented in both directions to avoid adding an unrelated base behavior
change to this task. No upstream solution patch, test patch or hidden benchmark
tests were used to author the task, reference, alternative or oracle.

## Real isolated admission controls

The production `EvaluationEngine` receives canonical submitted diffs and creates
fresh evaluation workspaces. Public and private imports are bound to `/workspace/pgmpy/`.
Each evaluation uses the existing image without network and has confirmed cleanup.

| Control | Trials | Acceptance |
| --- | ---: | --- |
| Independently authored batch-removal reference | 3 | PASS 3/3 |
| Independently authored per-round graph-copy alternative | 1 | PASS |
| Comment-only baseline equivalent | 1 | FAIL |
| Sorted traversal with live neighbors | 1 | FAIL |
| One stale snapshot for all rounds | 1 | FAIL |
| Ignore conditioning-depth limit | 1 | FAIL |
| Change original-variant behavior | 1 | FAIL |
| Ignore required-edge enforcement | 1 | FAIL |
| Drop separating-set witnesses | 1 | FAIL |
| Correct patch plus forbidden upstream test edit | 1 | FAIL |

All seven semantic controls fail private acceptance. Three pass the public checks:
stale snapshots, changing `orig`, and ignoring required edges. This demonstrates
additional private discrimination, not complete coverage. The forbidden-test-edit
control passes behavioral checks and fails scope. Safety passes all 12 evaluations.
The comment-only control is baseline-equivalent, not an exact unchanged-base private run.

The 12 evaluations execute 36 Docker checks. The matrix invocation also observes the
public base contract and takes 215.874 seconds including that observation and workspace
setup. A separate unchanged-base upstream check brings registration to 38 real checks.
No retry, provider/input-count call, Docker start, image pull or image build occurred.

## Source and runtime identity

The allowlisted preparation API fetches the exact base once. All execution and
evaluation workspaces thereafter use independent local clones with network calls
forbidden. Source validation confirms the descriptor, clean checkout and independent
Git objects. Selection and preparation have the same commit and tree. Their content
hashes differ only through CRLF/LF line endings in 701 files; byte comparison finds
no other content difference, and the earlier checkout remains unchanged.

- Prepared descriptor:
  `C:\pt\analyses\pgmpy-registration-20260917-v1\source\prepared-source.json`.
- Descriptor hash:
  `sha256:3b2eaf5ac852994c0c79c5206c92a674b1fea8826bbb0b42d0d9be60471ae87b`.
- Executable task hash:
  `sha256:a7f6d3274b9f59a8008171316ff29cc0e19cee0f88277f28d3891c1e83808c40`.
- Runtime hash after adding only the exact pgmpy URL to the repository allowlist:
  `sha256:7f00205e97f3a879189b1e6a37f4f5542b2592b2b38a1221b4318393fc4b8e95`.

Models, tools, planning/context policies and limits are unchanged. Public/private
projection, tamper failures and prepared-source/evaluation focused validation passes
47 tests in 25.095 seconds. Full-suite JUnit with durations, existing CSV runtime mock
smoke, preserved-file checks, scratch restoration paths and final commit binding are
retained at `C:\pt\analyses\pgmpy-registration-20260917-v1`.

Full regression covers all 120 test files: 2500 pass, eight skip and zero fail, in
633.354 seconds wall time (1950.784 seconds summed JUnit). Skips are four explicit
real-Docker opt-ins and four unsupported planning/context combinations. The existing
CSV mock reaches `EVALUATOR_PASS` under both context policies in 8.828 seconds. All
eight actual inputs retain exact public task/diff/check state and exclude source
preparation information. That smoke validates runtime plumbing; the real pgmpy task
is validated by the isolated control matrix above.

These task-authoring controls are not coding-agent attempts. Future model analysis
must use public traces and aggregate private verdicts, never private case details or
reference patches. A paid observation requires its own frozen invocation; this
registration creates no cost reservation and reopens no closed experiment group.
