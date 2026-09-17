# Fromager recursive orphan removal: development admission

## Scope and source

This new `dev-train` package exercises Fromager's public dependency-graph removal
contract. It is development-only (`official=false`), outside frozen historical
manifests and held-out evaluation. It is not an official SWE-bench result.

- Public issue identity: `python-wheel-build/fromager` #1106, selected from the
  existing labeled `2026_03` SWE-rebench metadata cache. Selection provenance and
  its remote dataset identity limitation remain in
  `C:\pt\analyses\fresh-devtrain-selection-20260917-v1`.
- Repository: `https://github.com/python-wheel-build/fromager.git`.
- Exact base: `f82c1e64a027060c3e25090f6a4a4d7f4e3d985d`.
- Existing evaluator image:
  `swerebench/sweb.eval.x86_64.python-wheel-build_1776_fromager-1106@sha256:5a80c46c2118e3119855830851f56270b45b809dc032682852595d4901f99453`.
- Allowed edit: `src/fromager/dependency_graph.py`, one file, 100 diff lines.

The base already cleans removed-parent backreferences. The reproduced defect is
that newly parentless descendants remain in `graph.nodes`. The task retains
shared descendants, exact version selection, reciprocal edges, node metadata,
missing/repeated removal, ROOT, and unrelated components. It requires neither a
particular implementation nor global collection of unreachable cycles.

## Public and private evidence

`orphan-removal-contract` exposes five runnable examples with expected nodes and
edges. The exact unchanged base passes three and fails the chain and diamond
examples. `upstream-dependency-graph-regression` passes all 12 unchanged upstream
tests at the same base. Both import from `/workspace/src`, preventing accidental
validation against preinstalled image source.

The evaluator adds 16 independently authored invariant cases in its isolated
workspace. Its expected removed set is a relational fixed point over the original
edges. It compares retained node identity/metadata and the multiset of both edge
directions, including versions, shared/root references and requirement types.
This oracle is separate from the reference implementation's recursive traversal.
Private material and reference bytes are never added to the public task or agent
workspace. No upstream solution patch, test patch or hidden benchmark tests were
used to author the package.

## Admission controls

The normal production `EvaluationEngine` evaluated canonical submitted diffs in
fresh prepared-source workspaces. Each evaluation ran both public checks and the
private check on the existing image with no network and confirmed cleanup.

| Control | Trials | Acceptance | Purpose |
| --- | ---: | --- | --- |
| Independently authored recursive reference | 3 | PASS 3/3 | Reproducible correct behavior |
| Independently authored iterative alternative | 1 | PASS | Avoid requiring the reference algorithm |
| Comment-only baseline equivalent | 1 | FAIL | Reject the original behavior |
| Immediate children only | 1 | FAIL | Require transitive removal |
| Delete shared descendants | 1 | FAIL | Preserve retained references |
| Keep stale parent links | 1 | FAIL | Preserve reciprocal edges |
| Wrong version selection | 1 | FAIL | Require exact target identity |
| Sweep unrelated orphans | 1 | FAIL | Limit removal to newly affected descendants |
| Correct patch plus upstream test edit | 1 | FAIL | Enforce the declared file scope |

All six semantic controls fail private acceptance. The version-selection control
passes public checks, demonstrating additional private discrimination without
claiming complete semantic coverage. The forbidden-test-edit control passes all
behavioral checks and fails scope. Safety passes all 11 isolated evaluations.
The comment-only control is not labeled an exact unchanged-base private run.

The first operator matrix stopped before any isolated evaluation because it used
`Artifact.sha256` instead of `Artifact.content_hash`. That attempt and its completed
base observation are preserved. A corrected successor reused the base observation
and completed all 11 controls: 33 evaluator checks in 69.120 seconds. Including the
two public base checks, registration executed 35 real Docker checks. No external
provider/input-count call, Docker start, image pull or image build occurred.

## Prepared source and identities

The normal allowlisted fetch prepared the exact base once. Thereafter execution
and evaluation workspaces used independent local clones with network calls
forbidden and no remote fallback. The source remained clean and was revalidated.

- Prepared descriptor:
  `C:\pt\analyses\fromager-registration-20260917-v1\source\prepared-source.json`.
- Descriptor hash:
  `sha256:329a2bd622fa4cb9bbba276b245db53eff88c60f9d02ca6867dfaefa3fa9713c`.
- Executable task content hash:
  `sha256:b6bcba664f652b1253dc8a7822f281ae3d7dc25879279bda0b20be4d1fd4d75c`.
- Runtime content hash after adding this repository to the allowlist:
  `sha256:f14933e59f00bc058971bed4310d03cbf6e66bbe8c5e77e7ff191e2041b09991`.

The only production runtime change is the exact Fromager repository URL allowlist
entry. Policies, tool schemas, prompts, limits and existing task bytes are unchanged.
Local registration/control success does not establish model performance or
generalization. Live execution still needs its own fixed invocation and clean
tracked runtime/task inputs.

Machine-readable admission evidence, focused/full-suite JUnit, both-policy mock
smoke, protected-file checks, scratch restoration mapping and final commit binding
are retained at `C:\pt\analyses\fromager-registration-20260917-v1`.

Focused package/source/evaluation validation passes 41 tests in 23.451 seconds.
Full regression covers all 119 test files: 2494 pass and eight skip, with zero
failures, in 532.962 seconds wall time (1892.528 seconds summed JUnit). Skips are
four explicit real-Docker opt-ins and four unsupported planning/context cases.
Both policies reach `EVALUATOR_PASS` using the existing CSV mock fixture in 8.500
seconds, with eight reconstructed actual inputs matching public task/diff/check
state and excluding source-preparation metadata. This provider-free smoke validates
runtime plumbing; the real Fromager acceptance evidence is the matrix above.
