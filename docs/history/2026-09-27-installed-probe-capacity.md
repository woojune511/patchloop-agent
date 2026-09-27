# Separate installed probe dependency capacity

## Failure and policy

The fixed pilot's complete public dependency installs succeeded but exceeded a
single 256 MiB bound: toqito 385,689,041 bytes and darts 574,281,919 bytes. Compressed
wheel transfer, installed storage and resident execution memory are different costs.
Reusing one constant for transfer and installation prevented legitimate bundles
from reaching execution even when downloads fit the original bound.

Added explicit --installed-limit-mib, integer 256 through 1024, default 256.
Nondefault limits are stored as installed_byte_limit in the prepared descriptor.
The manifest hash binds the selection, and verification/snapshot copying enforce
that limit again. Missing fields preserve old descriptors and default serialization.
Invalid limits fail before creating output. Changing a descriptor's limit after
admission invalidates its identity.

Download capacity stays 256 MiB; wheel count 128 and file count 15,000 are unchanged.
Public source snapshots stay at 128 MiB. Docker execution remains 512 MiB memory,
one CPU, eight PIDs, 30-second probe execution, no network and read-only mounts.
A larger installed bundle does not grant more resident memory or execution time.

## Concrete preparations and evidence

Selected installed caps are 512 MiB for toqito and 768 MiB for darts, above observed
installed bytes while keeping a finite operator choice. Both were prepared afresh:

- `C:/pt/prepared/original-toqito-1538-probe-0927-v4`, source root toqito, same
  reviewed PICOS generated-wheel receipt and clean original task source.
- `C:/pt/prepared/original-darts-3065-probe-0927-v5`, source root darts, clean
  original task source and its public runtime requirements.

No prior failed preparation was overwritten. No dependency or task was omitted.
Canary programs and receipts are retained under
`C:/pt/analyses/installed-limit-probes-20260927-v1`, journal
`run_dev_installedlimitprobes`. They use public base behavior, not hidden tests:
toqito's existing downarrow entropy and darts' ordinary static-covariate roundtrip.
These diagnostics are not registered agent checks or repair-performance evidence.

## Validation

Focused capacity/preparation/resolution/generated-wheel/project/setup-adapter suite:
142 passed in 55.792 seconds on final runtime, including capacity, small-file reads,
concurrent growth and package/import-root separation. Ruff passed. Final mock
smoke `run_dev_b6d13d2a2b454cc8` at `C:/pt/installed-limit-smoke-0927c` reached isolated
EVALUATOR_PASS, safety NOT_RUN, zero paid cost. The full repository suite was not
repeated. No provider/count request or evaluator image acquisition/build ran.

Inventory also now bounds each read to the file's actual size plus one byte, instead
of requesting the whole remaining bundle allowance for every tiny file. Concurrent
size changes are rejected. Both large preparations initially started before this correction. Toqito completed
with the older inventory loop. The operator stopped only the still-running darts v2
process and preserved its incomplete output/journal, then started v3 with final code.
The final canaries use final-code verification; no broad timing claim is inferred.

## Public import-path correction

Darts v3 published successfully but its actual probe failed while pandas imported
stdlib logging: /workspace/darts on sys.path exposed darts/logging.py as top-level
logging. Using the entire repository as the snapshot/import root (v4) would include
218,446,116 tracked public bytes, above the unchanged 128 MiB source cap; v4 was
prepared but not executed. Its public datasets alone occupy 174,913,877 bytes.

New preparations now distinguish selected package trees from import search roots.
A selected tree containing __init__.py stays in the snapshot but is not itself added
to sys.path. The resulting import_roots field is descriptor-bound and restricted
to selected roots; older descriptors keep their behavior. Darts v5 selects the darts
tree (~6 MiB) and root files, while importing from /workspace. No repository-specific
name condition or larger source snapshot limit was added.

Toqito's first canary timed out with no output. A diagnostic with flushed import
milestones passed, then the original uninstrumented code also passed (entropy
1.0000000000000002). The initial timeout remains unexplained; cache/startup effects
are hypotheses. These successful selected executions are not a cold-start latency
or arbitrary-probe reliability guarantee.

Final selected public canaries execute through DockerProbeSandbox, with exact
source/dependency/profile/runtime hashes and independent snapshots. MontePy imports
its public source and constructs a Cell. Darts v5 imports from /workspace/darts,
then static-covariate transform/inverse-transform preserves values and covariates.
Both exit 0, with no timeout or cleanup failure. These are environment canaries,
not original benchmark grading or proof that arbitrary probes fit the limits.

The final runtime hash is
`850942479181d7ce55199c21f08aa0221edd9bbaaa71098ca13ce6521b51b1de`.

Toqito also passed the original uninstrumented entropy canary on this final runtime.
All three final canaries exited 0 without timeout/cleanup failure, and the owned
probe-container listing was empty. The earlier timeout remains in the same journal.
Final documentation checks: five passed. A no-dispatch successor draft is stored as
execution-draft.json in the canary evidence root after committing this change;
it binds the committed runtime and selected descriptors but authorizes no spend.
