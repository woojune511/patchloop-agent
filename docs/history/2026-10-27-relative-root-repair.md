# Relative search-root normalization repairs the task from clean source

## Material Passport

Date: 2026-10-27. ARS run/validate. Status: COMPLETED. official=false,
claim-ineligible. The user authorized the next relative/absolute search-root
comparison and resolver-only repair experiment. This is an operator-authored
repair from the unchanged task base, not a new response from the benchmark model.
Ten public probes, one public regression and one isolated evaluation completed.
No provider calls, credential reads, image pulls/builds or evaluator retries.

## Problem, hypothesis and controlled change

The [selection diagnostic](2026-10-27-namespace-selection-diagnostic.md) showed that
the previous candidate could exit 0 without selecting or parsing the child file.
Both module-path resolution and module-spec lookup failed before AST construction.
The builder guard only handled the nonexistent initializer left in the selection.
This motivated changing the repair location rather than adding more builder cases.

The observed caller passed `"."` as a search root. Astroid
`modutils._get_relative_base_path` converted the filename to absolute/real paths
but only normalized the search root's case. The hypothesis was that this mismatch
prevented cwd-relative resolution and therefore proper namespace/file selection.
If equivalent absolute-root resolution also failed, or normalization left the
caller selecting only the initializer, that would weaken or refute sufficiency.

The candidate starts at task base
`d2a5b3c7b1e203fec3c7ca73c30eb1785d3d4d0a` and changes only this line in
`astroid/modutils.py`:

```diff
-    path_to_check = os.path.normcase(path_to_check)
+    path_to_check = os.path.normcase(os.path.abspath(path_to_check))
```

It contains none of the earlier builder guard, namespace stream, encoding or
docstring edits. `abspath` performs lexical normalization; it does not replace
the root with its symlink target. Existing absolute/real filename comparisons and
the callback's original pathname remain. Non-normalized absolute roots containing
dot segments or trailing separators are also normalized; universal path semantics
or platform equivalence is not inferred from this one Linux task experiment.

## Sealed procedure

Task: `dev-train/current-dev20/13`, Astroid-1333. The plan, exact one-line mutation,
five helper programs, operator hash, dependency/source identities and stop rules
were sealed before execution in a hash-chained `dev-run-v1` journal.
All rows used fresh prepared source and the existing pinned public probe runtime.
Before/after source bytes and the full candidate patch were stored in CAS.

Each caller used the bounded selection/parsing observation from the preceding
diagnostic. After the target had finished and wrappers were restored, a separate
public resolver comparison invoked `modpath_from_file("src/project", path=[root])`
with `root="."` and the equivalent absolute fixture root. Placing these queries
afterward prevents them from warming state before the full caller observation.

The first unchanged-base row had to fail relative resolution and return
`["src", "project"]` with the absolute root before any candidate row ran.
The five input conditions each ran on base and normalized source:

| Input | Candidate expectation |
| --- | --- |
| Empty files, missing initializer, directory target | Empty output, exit 0 |
| Original `import os` child, missing initializer | Select/parse child, no F0010, report unused import |
| Invalid-syntax child, missing initializer | Select/parse child and report E0001, exit 2 |
| Same invalid child targeted directly | Preserve the direct-file diagnostic |
| Same invalid child in ordinary package | Preserve the package diagnostic |

The helper checks also require relative/absolute resolver equivalence. Direct and
ordinary-package caller output/outcome/exit/exception are compared exactly between
states. These are additional public diagnostics, not an alteration of the task's
private acceptance rules or new original-case/finish eligibility receipts.

The 48-event/11,000-result-byte observation limits and 120-second per-probe deadline
remain. Drift, incomplete helper capture, uncertain cleanup or a refuted initial
mechanism stops further dispatch. Public regression follows only if all candidate
checks pass, then at most one opaque acceptance evaluation. No hidden-feedback
repair iteration is permitted or performed.

## Executed public results

| Observation | Unchanged base | Normalized source |
| --- | --- | --- |
| Relative root `"."` | ImportError | `["src", "project"]` |
| Equivalent absolute root | `["src", "project"]` | Same |
| Empty missing-initializer directory | Synthetic initializer selected; F0010, exit 1 | Actual empty child selected; empty output, exit 0 |
| Original `import os` directory | F0010, exit 1 | Child parsed; C0114/W0611, exit 20 |
| Invalid child through directory | Child omitted; F0010, exit 1 | Child parsed; E0001, exit 2 |
| Invalid child directly | E0001, exit 2 | Identical |
| Invalid child through ordinary package | E0001, exit 2 | Identical |

The normalized missing-initializer path was observed end to end:
module path `src.project` -> `PY_NAMESPACE` spec -> `is_namespace=True` ->
`get_module_files(list_all=True)` includes `src/project/file.py` -> child
`get_ast/file_build` entry. The nonexistent initializer is no longer selected.
For the invalid source, file_build raises AstroidSyntaxError and Pylint emits
E0001. This is a successful diagnostic of invalid code, not a repair failure.
Likewise exit 20 on `import os` is the real missing-docstring/unused-import output,
not the old F0010 crash or a requirement that every nonempty file exit zero.

All ten helper executions completed without overflow/truncation, with confirmed
cleanup and unchanged fixture inventories/candidate hashes. Paired target arguments,
fixture content/modes, environment and caller sys.path match. Internal resolved
module names, namespace specs and child selections are expected to change.
Direct-file and ordinary-package caller outputs remained identical.

Focused comparison time was **100.340 seconds**. With public regression, elapsed
time was **113.341 seconds**, below two minutes. The registered public suite passed
**1,231 tests, 69 skipped, 15 xfailed** (pytest time 8.46 seconds). Existing public
modutils/symlink tests are part of that suite; no separate new platform or symlink
matrix was run. Direct/package base caller behavior already passed; their aggregate
helper flags were false only because relative-root equivalence was still broken.
These controls are preserved behavior, not additional independently repaired tasks.

## Separate isolated acceptance

After binding the public result, regression receipt, clean base and one-file patch,
the host applied the sealed candidate in a new prepared evaluator workspace.

| Verdict | Result |
| --- | --- |
| Acceptance | **PASS** |
| Regression | PASS |
| Scope | PASS |
| Safety | PASS |

`evaluation_status=completed`, `scope_compliant_success=true`, official=false.
Candidate bytes remained unchanged. There was one dispatch and one completed
evaluation; no model continuation or model `finish_task` occurred. The host
manifest's completed submission status belongs to saved-patch evaluation.
Only opaque verdict/identity summaries entered this context; private test/spec
contents, reference patches and raw evaluator logs were not inspected.

This establishes an accepted operator repair for this local development task.
It does not identify which private tests failed previously, establish a fresh
model solve, improve measured agent solve rate or authorize a leaderboard claim.

## Decision

The relative-root hypothesis is now supported by both the direct counterfactual
and the full caller: one resolver change on clean source restores actual file
selection and passes separate acceptance. Further synthetic-module builder edits
are unnecessary for this demonstrated repair. Preserve the old candidate failures
and their real, narrower public improvements rather than rewriting their verdicts.

The agent-engineering lesson is to test the work selected/performed by the caller,
and align a repair with the earliest demonstrated causal failure. This experiment
does not implement a new prompt, gate, tool or agent policy. Production defaults
remain unchanged. The next model question is whether public selection/resolution
evidence leads it to choose this repair layer without receiving the operator patch;
any such trial is assisted development evidence and needs a new exact paid scope.
All earlier paid allocations remain closed.

## Evidence and validation

- Root/operator: `C:/pt/relative-root-repair-v1/run.py`.
- Result: `C:/pt/relative-root-repair-v1/results/result.json`.
- Candidate: `results/empty-normalized/workspaces/probe/repo` under that root.
- Journal: `results/runs/run_dev_relativerootrepair.jsonl`.
- Harness commit during execution: `916c6dab31b80b975387d245e916bf83e279106a`.
- Runtime: `sha256:5753dbef010721c721db788aa01525fc269ad12093b46e45ffc2ffd158c929f3`.
- Candidate patch: `sha256:bccca60f05bb2728d9d0da07319fd35891bb6c4525e2bf3ea60b3d38b00af1d4`.
- Operator: `sha256:4901178199bd465b49e44b272e7a7ade162ce814834a25613e44baf6f11c4ee5`.
- Plan: `sha256:583ec4804a0c876e355e4a024a9b1b6268a4b7586577ee4f9cac0835b18a17f2`.
- Public result: `sha256:28ce6fc973c7e097178f0c52bd6cbd49ae7af1d80b966a14b1d0ef041e163632`.
- Public journal: `sha256:24ada7a8209f96480f1b3c7052b8de1dbab6cbbb5045e01c1dbcf6ddcf2cf0d8`.
- Public regression receipt: `sha256:979293038e574836cde9b245c54573e1c5c6dacc9bac38bfe9c5d039371dbfc6`.
- Isolated summary: `C:/pt/relative-root-acceptance-v1/summary.json`,
  `sha256:782ce1ae486e6729d7a45f05ba6d9963cb99b959d430bb534fc188d5b12d92a2`.
- Isolated manifest: `sha256:a03f73994f426079954c7bd6380aa343131160a9e1ba6e2a3a7840ab70d7e92d`.
- Isolated journal: `sha256:8ed517cf4da9dc1189f957038a633a29859d059501dbfd0f43ec52d4144ca7d5`.
- Opaque evaluation artifact: `sha256:1bd047fa575e6acde8c40f63d1f4f590d25df48c131431ddaedf8996371ff524`.

An independent public audit rechecked all ten probe receipts, the regression
receipt, CAS hashes/sizes, observation JSON, matched caller conditions and every
workspace's clean base and exact one-line diff. No integrity defect was found.
Run-internal evidence comes from the nested expansion/selection/parsing events;
the broader changed-line feedback also includes the later direct resolver calls
and must not be mistaken for caller-only line coverage.

Prepared source/dependency/image identities and the exact helper sources are bound
by the plan, calibration and public receipts. Ruff passed on the external operator;
the five documentation-layout checks passed. Repository runtime code is unchanged;
runtime quick/mock checks were not repeated
for documentation-only repository changes. Candidate public and isolated checks
above remain distinct from host maintenance checks.

Statistical fallacy coverage: 11/11 checked. No significance/population estimate is
made. Simpson/ecological/collider/base-rate/regression-to-mean/reverse-causality
analyses do not apply to this fixed single-task intervention. Known-failure selection
limits generalization; all ten conditions, including base failures, are retained.
The intervention and criteria were sealed before this run, but follow earlier
development diagnosis. The controlled one-line mechanism supports this local causal
interpretation, not a model-quality effect or a general agent-architecture claim.
