# Prepared public caller check

## Decision

The new generic caller preparation can run installed Pylint 2.12.2 against current
Astroid source and reproduce the public missing-initializer failure. The saved
E1J1 candidate passes its original helper probe but leaves the real caller failure
unchanged. Both base and candidate pass the initializer-present control.

This closes a capability gap left by the [copied caller-boundary diagnostic](2026-10-18-astroid-caller.md)
and the [synthetic preparation validation](2026-10-18-public-callers.md). It supports
using the public caller to distinguish helper success from repair success. It does
not establish that a model will acquire, interpret or act on that evidence.
Keep the implemented preparation, transition rules, two evidence references and
all budgets. No additional retention rule, prompt, repair or paid run is adopted.

The remaining question is model evidence uptake: when this caller is available,
does the solver inspect the relevant setup, execute the original failure/control,
and respond to the counterexample instead of accepting the helper result? A later
bounded comparison must separate availability, actual use, interpretation and task
correctness. This operator-authored check supplies no model observation of those
steps and is not authorization or a frozen specification for that comparison.

## Why this diagnostic

The earlier diagnostic used selected public Pylint functions because Pylint was
not importable in the old bundle. Configuration, default checkers, console dispatch
and report formatting were excluded. A real prepared caller could have failed to
import, failed to reproduce the issue, or invalidated the normal control. Any of
those outcomes would weaken the proposed acquisition path before a model test.

Choose the saved E1J1 implementation because its successful helper probe supported
an overbroad end-to-end claim in the previous run. Replaying that exact candidate
is sufficient to test the distinction; no new repair or other candidate is tried.
The original closed comparison and diagnostic records remain unchanged.

## Frozen preparation and execution

- Public task: [Astroid-1333](../../tasks/dev-train/current-dev20/13/public.yaml),
  source base `d2a5b3c7b1e203fec3c7ca73c30eb1785d3d4d0a`.
- PatchLoop source commit: `823cca4276b7b55ce276ca0ebea3358dd43ae944`;
  runtime content hash `20fb1541d4b2aa5c2f5af6e67f74546ae8762f74c4325988535dc7202075bf0a`.
- Generic preparation: caller `pylint==2.12.2`, source root `astroid`, existing
  `python39-v1` profile, and the pre-existing compatibility supplement
  `setuptools==80.9.0`. The supplement was selected before target execution.
- Nine public PyPI wheels were resolved/downloaded with recorded origins, sizes
  and hashes, then installed offline through the normal preparation path. Only
  the workspace distribution was excluded, preserving current Astroid source.
  No image pull/build, provider/count API, private evaluator or solver run occurred.
- The dependency descriptor hash is
  `e3069d021e80410a049f1e4a9b1fa5c487d8d419712fce25239c217396e7fcdd`.
  Its lock and installed inventory bind the package selection and bytes.
- Two independent workspaces contain unchanged base and the exact saved E1J1
  mutation. Candidate diff hash:
  `62c5f3ba5a0cdd11a035fe453003b659a3e6c3f75538cb3afae9188cf11e5da9`.
  Only `astroid/interpreter/_import/util.py` differs.

Seven probes were frozen: import/entry-point capability, then base missing input,
base normal control, base saved helper, candidate saved helper, candidate missing
input and candidate normal control. Capability and baseline gates precede the
candidate. Each condition runs once; timeout, truncation, cleanup uncertainty or
identity drift stops the diagnostic. No retry or outcome-based retuning occurred.

Every probe retains 30 seconds, one CPU, 512 MiB, eight PIDs, 8,000 source characters,
32,000 source bytes and 12,000 output bytes, with no network or child process and
read-only source/dependencies. This seven-probe operator diagnostic is separate
from a solver's action allocation; no production limit was changed.

The caller program creates `root/src/__init__.py` and empty
`root/src/project/file.py`, changes cwd to `root`, sets argv to
`["pylint", "src/project"]`, and invokes the installed console entry
`pylint:run_pylint` in-process. The public issue explicitly allows empty `file.py`.
The normal control only adds an empty `src/project/__init__.py`.
Actual Pylint configuration discovery, default checker loading, dispatch and
reporting run; no caller function or reporter is copied or replaced.

A passive Python profiler records bounded calls, arguments, cwd, import paths and
file existence. There are eight observed calls for each missing case and eleven
for each normal control, without overflow. Setup checks verify the pinned caller,
source origins, entry point and fixture; they do not attest semantic completeness.
Pylint uses one process, no stdin, no additional plugins and no configuration file.
HOME and PYLINTHOME use isolated writable scratch locations. Its SystemExit and
stdout/stderr are captured so probe execution and Pylint outcome remain separate.

## Results

| Source | Exact saved helper | Real Pylint: initializer missing | Real Pylint: initializer present |
| --- | --- | --- | --- |
| Base | ImportError; probe exit 1 | F0010 missing `src/project/__init__.py`; Pylint exit 1 | No messages; Pylint exit 0 |
| Saved E1J1 | `namespace_ok=True`, expected module path; probe exit 0 | Identical F0010; Pylint exit 1 | No messages; Pylint exit 0 |

All seven probes completed with confirmed cleanup; summed probe duration was
69.809 seconds. Six probe receipts are `passed`; the base helper's expected
ImportError is `failed`. The four caller observer programs all exit successfully,
including the two which capture Pylint exit 1. Neither probe execution success
nor setup-check success is a repair verdict.

For both missing cases, the observed real caller places `root/src/project` at the
front of `sys.path`, passes module name `project` and the nonexistent initializer
to `get_ast`, then calls `AstroidManager.ast_from_file(..., source=True)` and
`AstroidBuilder.file_build`. No target module-name fallback is observed. Base and
candidate traces are equal after normalizing the temporary root, as are their
F0010 messages. Normal controls reach both existing initializer and child files;
their normalized traces also match.

The exact saved helper instead prepends `root` and checks file-to-module mapping.
Its child contains `import os`, whereas the caller fixture uses the explicitly
allowed empty file; the helper does not read that file's contents. Both helper
arms execute the same unmodified saved program. The helper result is evidence
for its narrower path, while the actual caller remains a concrete counterexample
to the prior repair claim in this environment. It does not reveal the private
evaluator's failure reason or establish the unique source-level fix.

## Environment and claim limits

Actual runtime is Python 3.9.25 on Debian 13, using the already present pinned
image `python@sha256:dad5b29e3506c35e0fd222736f4d4ef25d21b219acdd73f7bb41d59996ca8e0d`.
The issue reports Python 3.9.1 on other operating systems. Current benchmark
source reports Astroid `2.10.0-dev0`; synthetic distribution metadata identifies
the source commit, not a released Astroid version. Release-version compatibility
therefore remains marked unverified even though these concrete inputs execute.

This fresh transitive resolution is not a matched replay of the older Python
3.10/no-Pylint model environment. The wheel lock identifies prepared packages;
the capability probe's `versions` dictionary collapses duplicate names from
image/vendored distribution metadata and must not be treated as an authoritative
map of effective transitive imports. Pylint's exact version and both caller and
project import origins were checked separately.

The console entry runs in the bounded probe process, without the shell launcher.
The passive observer does not replace callees, but this seven-probe protocol does
not include an untraced parity run. Earlier parity evidence belongs to the earlier
copied-function diagnostic. These limits and the controlled HOME/cache environment
remain explicit; the result is a public local reproduction, not historical
environment equivalence, private acceptance or evidence of improved repair rate.

## Evidence and validation

External root: `C:/pt/analyses/astroid-prepared-caller-20261018-v1/`.
`preparation-protocol.json` and `execution-protocol.json` bind conditions and
identities before their executions. The dependency descriptor, exact programs,
per-condition observations/receipts, CAS objects and `result.json` preserve the
results. `runs/run_dev_preparedcaller18.jsonl` is append-only `dev-run-v1` with a
verified hash chain; records distinguish setup, probe, Pylint and cleanup outcomes.

Verified all seven receipt hashes and identities, unchanged workspace diffs,
old/new dependency inventories and prepared source integrity. All 3,163 tracked
repository files were unchanged before this documentation update, including the
user's pre-existing AGENTS edit. All 1,047 previously recorded diagnostic files
are unchanged, and all seven owned containers are absent. Transition/reference/
budget/runtime code and prior closed reports are unchanged.

Documentation layout/link tests: five passed. Ruff and whitespace checks passed.
Full repository tests and mock smoke were not rerun for this documentation-only
follow-up. New repair, model uptake, repair-success comparison and private
evaluation are NOT_RUN. Provider/count calls and billed cost are zero. Public
package downloads were executed; image acquisition was not.
