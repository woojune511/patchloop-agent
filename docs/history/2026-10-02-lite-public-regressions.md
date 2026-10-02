# SWE-bench Lite public regression contract correction

Date: 2026-10-02. Provider-free operator work at `1fff2257`; official=false.
Follow-up to [corrected-image validation](2026-10-02-lite-environment-validation.md).

## Problem and decision

Two tasks remained blocked after all eight environment corrections passed original
and registered private controls. Their required base public tests demanded behavior
that the public issues explicitly requested changing. This is a task-preparation
contract defect: a correct repair could not satisfy the submission gate. It recurred
in two of the fixed twenty tasks and prevented meaningful future agent execution.

The user approved correcting public regression selection and revalidating the two
tasks. The public issue and original public test source independently establish
each conflict. Reference/private results exposed the problem but do not determine
which expectation is conflicting or supply a replacement answer.

Excluding the whole test would also discard valid regression assertions. Instead,
retain each test node and project out only the obsolete expectation in the temporary
public check copy. The public policy is recorded in [evidence guidance](../evidence.md).
No solver tool, prompt, runtime gate, image or private evaluator changes.

## Exact public changes

The plan was frozen from `public.yaml` and original public test files before the
new controls. Each new external package changes only `public.yaml`:

- **pvlib-1154:** `test_reindl` checks a vector containing zero-GHI and nonzero-GHI
  cases. Its old NaN expectation conflicts with the issue's requested zero-GHI
  behavior. The temporary assertion selects `ghi != 0` from both the result and
  the unchanged expected vector, retaining all three nonzero-GHI numeric checks.
  It does not insert a zero-GHI answer expectation.
- **pvlib-1854:** `test_PVSystem_multiple_array_creation` retains the existing
  multiple-Array order and module-parameter assertions. Only the final
  `pytest.raises(TypeError)` block for a single Array is replaced with an explanatory
  comment, because the issue explicitly requests accepting that input.

The launcher verifies the full original test-file SHA-256 and unique literal
anchor before applying the projection to its temporary checkout. Drift returns
infrastructure exit 2. Public test selection, test-node counts and numeric values
for unaffected behavior remain unchanged. The original workspace and prepared
source/test bytes are preserved; the effective public check semantics intentionally
omit the two obsolete expectations. Exact before/after strings are in the frozen
plan and public commands, not inferred dynamically by the solver.

Private specs, hidden artifacts, reference patches and image bindings are byte-identical
to the previous corrected-image packages. No hidden test patch or reference repair
was copied into a public check. These public regressions do not establish the new
behavior's correctness; original private acceptance remains responsible for that
final verdict, and public PASS retains its limited coverage meaning.

## Controls and results

Both tasks used their existing corrected immutable images with network-disabled
checks, two CPUs, 2 GiB memory and 300-second timeouts. At most two tasks ran in
parallel. There were no image builds, pulls or provider calls.

| Control, for each task | Public check | Original registered private check |
| --- | --- | --- |
| Unmodified base | PASS | Complete, unresolved |
| Reference patch | PASS | Complete, resolved |
| Deliberate retained-behavior regression | FAIL | NOT_RUN |
| Unexpected public test-file drift | Infrastructure exit 2 | NOT_RUN |

Public base/reference runs retain all 98 tests for pvlib-1154 and all 281 tests for
pvlib-1854. The regression controls start from the reference workspace, then:

- Return zero for every `reindl` result. The retained `test_reindl` numeric
  assertion fails, proving the nonzero-GHI checks still execute.
- Reverse the `PVSystem` multiple-Array order. The retained
  `test_PVSystem_multiple_array_creation` assertion fails, proving that node's
  unaffected order/parameter checks still execute.

Every public execution also verifies that its workspace test bytes and tracked
diff remain unchanged by the temporary projection. All eight planned controls
produced the expected outcomes. Both reference submissions then passed actual
isolated EvaluationEngine hidden, regression, scope and safety checks.

Original/native base/reference results were reused, not rerun: native inputs,
image digests and all private bytes are unchanged from the preceding validation.
The current registered private checks and isolated engine controls were executed
again against the newly bound task packages.

## Outcome and limits

The fixed roster is now **20/20 calibrated**, including the previous eighteen.
This is evaluation readiness using known reference repairs, not twenty new agent
solves or a benchmark score. All twenty packages remain external drafts; live-task
registration and an exact funded batch are separate work. Provider calls and cost
were zero; no merge or paid execution occurred.

The result supports these two public-issue-derived corrections and retention of
the tested regression behavior. It does not justify automatic test suppression,
using private test membership to select public checks, or changing other tasks
merely because a reference fails. Preserve the original failed controls and prior
BuildKit networking exception in their separate records.

## Evidence and validation

External root: `C:/pt/analyses/lite-public-regression-contract-20261002-v1`.

- `freeze.py`, `public-plan.json`: public-only evidence, exact projections,
  controls, resource limits and stop rules frozen before revalidation.
- `prepare.py`, `prepared.json`: public-only package changes in `C:/pt/ld20pc01/p`.
- `calibrate.py`, `calibration.json`: eight real Docker controls, with workspace
  mutation checks and deliberate regression/drift evidence.
- `engine_controls.py`, `engine-results.json`: two isolated reference submissions,
  with workspaces under `C:/pt/ld20pe01`.
- `final-summary.json`: exact twenty-task effective package roster. `runs/`,
  `artifacts/` and `engine-artifacts/` preserve journals and content-addressed evidence.

Focused adapter/documentation checks: **32 passed**, under three seconds. Ruff
and whitespace checks passed. Final integrity verification covered **61 artifacts
across five journals**, all twenty effective package hashes, unchanged private and
environment files for the two follow-ups, and no remaining owned containers.
No runtime source changed; prior full-suite and mock evidence remain separate.
