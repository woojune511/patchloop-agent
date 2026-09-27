# Original AnyIO benchmark preparation

## Problem and change

The adapted task's success cannot establish original benchmark performance. Added
an operator-only preparation driver and explicit public/evaluator input partition,
without changing task packages, coding-agent tools or runtime evaluation.
See [contract](../../.agent/original-benchmark.md) and
[comparison](2026-09-27-anyio-benchmark-differences.md).

The frozen dataset file was hash-checked; original issue input, F2P/P2P lists,
original test patch and reference patch were stored in evaluator-only artifacts.
Patch bodies were transferred as data, not shown to the evaluated agent or used
to design its prompt. The public projection includes only instance/repository/base
and original problem statement. Dataset identity and 1/32 disjoint case counts passed.

Selected upstream harness revision is
`e4907b7a90eafaa1f0a6428fd04fe31cdd8b4284` from
[SWE-rebench's fork](https://github.com/SWE-rebench/SWE-bench-fork/tree/e4907b7a90eafaa1f0a6428fd04fe31cdd8b4284).
Python parser, grading and test-spec sources were pinned in artifacts. This is a
new explicit implementation pin, not a claim that the dataset's historical scoring
used that revision. Parser and scoring execution are still NOT_RUN.

## Live environment observation

Evidence root: `C:/pt/analyses/anyio-original-benchmark-preparation-20260927-v1`.
Journal: `runs/run_dev_originalbenchmarkprepare.jsonl`; artifacts are under
`evaluator-artifacts`. The journal chain and all 10 referenced artifacts verified.

The already-local image digest `063bb968109c70a3fe617d9d30287a3a43d549eb1091b27a030a9af2a74c2320`
matches its expected repository digest. A network-disabled, read-only container
without host mounts reported:

- Python 3.13.13, executable `/opt/conda/envs/testbed/bin/python`.
- pytest 9.0.3, Trio 0.33.0, uvloop 0.22.1; Hypothesis absent.
- AnyIO resolves to `/testbed/src/anyio/__init__.py`.
- HEAD is the original base `cb245dba9883516f2ed4c23899de157183a1cb50`;
  tracked working tree is clean.
- All other queried installation packages are present; versions are in the receipt.

This resolves the Python-version uncertainty for this local evaluator image; it
does not establish historical image equivalence, dependency completeness for every
test, or an original benchmark score. The owned container was removed and a follow-up
container listing was empty. No image was downloaded/built and no dependency was
installed inside it. The separate recent probe bundle remains Python 3.12.

## Validation and remaining work

Focused tests cover public/private partition and rejection of wrong identity or
case membership. Ruff passes. Mock smoke reached EVALUATOR_PASS with safety NOT_RUN
at `C:/pt/original-benchmark-preparation-smoke-0927a`, run
`run_dev_4a4ddcc6786d4a71`; this is unrelated smoke, not benchmark execution.

Actual original tests, reference/base calibration and upstream parser execution are
NOT_RUN. No paid/provider calls were made. Next connect isolated calibration to the
pinned parser, check the 33 required cases and determine how the absent optional
Hypothesis dependency affects the full original command. Do not silently deselect
tests or reinterpret collection/infrastructure failures as agent repair failures.
No general score or held-out claim follows; AnyIO remains development data.
