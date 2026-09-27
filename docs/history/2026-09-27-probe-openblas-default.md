# Bounded OpenBLAS default for public probes

## Observed failure and correction

The original-input readiness diagnostic reproduced a MontePy import failure:
OpenBLAS attempted 16 threads and exhausted the eight-task probe PID budget.
The same import and Cell construction passed with OPENBLAS_NUM_THREADS=1.

The launcher now sets that default for all public probes, independent of host
settings and task identity. The value is included in the hashed probe profile and
execution-policy receipt. The single CPU, PID limit, process restrictions, memory,
image, and dependency bundle remain unchanged. This configures OpenBLAS only; it
is not a promise about every numerical backend or a restriction on mutable Python
environment variables. Existing sandbox limits remain authoritative.

## Validation and retained failure

With no environment assignment in the submitted probe, the same MontePy source
import and base Cell construction passed, exit 0, without timeout or cleanup failure.
Evidence: `C:/pt/analyses/original-pilot-openblas-20260927-v1`, append-only journal
`run_dev_originalpilotopenblas`. No repair behavior or hidden assertion was tested.

Focused sandbox/dependency/provenance/gateway/docs suite: 79 passed in 50.678s.
Additional contracts/environment/setup/delivery/evaluation-resume regression group:
141 passed in 195.013s; this broader group exceeded two minutes. Final documentation
checks: five passed. Ruff passed. Runtime bytes stayed fixed during these checks.
Real Docker isolation/replay passed. The first thread-bound test printed THREAD_LIMIT
6, then failed to start one new worker after joining the six previous workers.
An unchanged-source rerun passed. A transient resource-release race is a hypothesis,
not an established cause; the first failure is retained, not reported as a clean
first-pass result. Receipts: `C:/pt/validation/openblas-docker.xml` and
`C:/pt/validation/openblas-docker-retry.xml`; raw results under `C:/pt/obdocker1` and
`C:/pt/obdocker2`.

Mock smoke `run_dev_2405e1dca7584908` at `C:/pt/openblas-smoke-0927` reached isolated
EVALUATOR_PASS, with safety NOT_RUN and zero paid cost. No provider/count request,
image acquisition or build ran. The full repository suite was not repeated.

## Successor draft and remaining work

Runtime hash: `6b5d1f94db40c39895b97795c38240f8450f9b1ccb5a77ed0ebad60ba47d6432`.
The new evidence root contains a successor `execution-draft.json`, canonical artifact
hash `f656386eddbef1f6525da5a82044200678d5bb8018daace75c019ece0ff0c96e`.
It supersedes the earlier draft, binds the new profile/runtime, and retains
`authorized=false` and `dispatch_ready=false`. Its preparation commit is pending;
a final paid manifest must bind the committed source after all blockers clear.

MontePy's tested public entry point is ready under the default profile. Arbitrary
lazy imports and repair correctness are not established. Toqito still lacks a
required binary wheel; darts still exceeds the installed dependency byte cap.
Next investigate a bounded public source-package build path before changing the
preparation contract; do not remove dependencies or substitute the evaluator image.
