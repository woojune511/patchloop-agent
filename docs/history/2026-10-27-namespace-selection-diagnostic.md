# Missing-initializer success conceals omitted child-file selection

## Material Passport

Date: 2026-10-27. ARS run/validate. Status: COMPLETED. official=false,
claim-ineligible. The user authorized the proposed six local diagnostic runs:
unchanged base and saved operator candidate across three public inputs.
No new repair, provider call, credential read, evaluator run, image pull or build.
Production runtime/defaults and historical candidate/evidence bytes are unchanged.

## Question and alternatives

The [operator docstring repair](2026-10-27-namespace-doc-repair.md) produced empty
output and exit 0 on the original directory call while isolated acceptance still
failed. The next question was whether that successful exit meant the actual child
file had been analyzed. This matters to repair correctness: removing an error
while skipping work can satisfy a narrow diagnostic predicate.

Leading hypothesis: namespace/path resolution still fails before AST construction,
so only a nonexistent initializer is selected; the inherited builder guard makes
that selection look successful. Alternatives were selection followed by an early
initializer failure, an invalid diagnostic marker, or a later failure to report
an error despite attempting the child. The test records selection and parsing
separately, rather than inferring skipped work solely from missing output.

Child traversal is an additional public semantic diagnostic. It is not silently
promoted into the original issue's explicit acceptance rule or a hidden-test
requirement. The earlier empty-output result and acceptance FAIL remain intact.

## Frozen design and observation

Task: `dev-train/current-dev20/13`, Astroid-1333; base
`d2a5b3c7b1e203fec3c7ca73c30eb1785d3d4d0a`.
The saved operator patch adds the earlier missing-initializer guard, mini's empty
namespace stream/UTF-8 encoding and the operator's `doc=None` adjustment.
Both states were restored into fresh prepared workspaces; no new candidate was
authored. The exact full diff was checked before and after every probe.

The plan, helper programs, source identities, limits and interpretation criteria
were sealed before execution in an append-only hash-chained `dev-run-v1` journal.
Each helper used the same fixture child contents, `def broken(:\n    pass\n`,
with a real `src/__init__.py`. HOME/cache were outside the fixture input directory.

| Input | Purpose |
| --- | --- |
| `src/project`, initializer absent | Test whether the invalid child is selected and parsed |
| `src/project/file.py`, initializer absent | Direct-file positive control for the syntax marker |
| `src/project`, initializer present | Ordinary-package positive control with the same child |

Each input ran once on base and once on the saved operator candidate, six fresh
probe containers total. The existing public probe image/dependencies were reused.
The helper purpose was `helper`, not `original_requirement`: no original-case
acquisition, finish eligibility or benchmark acceptance credit was produced.

Observation wrapped the actual `pylint.lint.pylinter.expand_modules` alias,
Astroid `modpath_from_file`, `file_info_from_modpath`, `is_namespace`, and
`get_module_files` during expansion, plus fixture-local `PyLinter.get_ast` and
`AstroidBuilder.file_build`. It preserved one original call, the returned object,
and raised exceptions, then restored the wrappers. Event IDs link nested calls.
Actual expansion-time cwd/sys.path and resolver search arguments were retained;
those differ from the state before Pylint's `fix_import_path` context.

Limits were 48 events, eight path sets, 24 paths per set, 11,000 serialized result
bytes and a 120-second row deadline. Any observation truncation, cleanup uncertainty,
infrastructure failure or candidate drift stopped further dispatches. This is
bounded instrumentation for the pinned public API, not a general tracing guarantee.

## Observed results

| Input | State | Child selected / file_build entered | Caller result |
| --- | --- | --- | --- |
| Missing initializer directory | Base | No / No | F0010, exit 1 |
| Missing initializer directory | Operator | No / No | Empty output, exit 0 |
| Direct child file | Base | Yes / Yes | E0001 syntax error, exit 2 |
| Direct child file | Operator | Yes / Yes | Identical E0001, exit 2 |
| Ordinary package directory | Base | Yes / Yes | E0001 syntax error, exit 2 |
| Ordinary package directory | Operator | Yes / Yes | Identical E0001, exit 2 |

The missing-initializer path was the same in both states:

1. `modpath_from_file("src/project", path=...)` raised ImportError.
2. Pylint fell back to module name `project`.
3. `file_info_from_modpath(["project"], path=...)` raised `No module named project`.
4. Pylint's ImportError fallback treated it as non-namespace. `is_namespace` was
   not called within the observed expansion. `get_module_files("src/project",
   list_all=False)` returned an empty list.
5. Expansion selected only `src/project/__init__.py`. `file.py` never reached
   either `get_ast` or `file_build`.
6. Base failed to load that nonexistent initializer. The saved candidate returned
   a synthetic namespace AST for it and completed with empty output/exit 0.

Thus the missing child is an observed selection omission, not merely an inference
from absent E0001, and not a child selected but blocked behind an initializer error.
The direct-file and ordinary-package controls establish that the marker is valid:
`file_build` raised AstroidSyntaxError, `get_ast` returned None after reporting
E0001, and the caller exited 2. A missing AST is expected for this invalid source;
it does not mean parsing was skipped.

All six helper executions completed, with **6/6/6/6/9/9 events**, no overflow,
no helper timeout/truncation and confirmed cleanup. Captured output was at most
4,327 bytes. Fixture path/content/mode inventories were unchanged. Within each
input, base/operator target, fixture inputs, environment and recorded search paths
matched. Total focused elapsed time was **62.562 seconds**.

## Narrowed source explanation and next decision

The trace directly locates the unresolved behavior before the builder repair.
Static public-source inspection further identifies a concrete candidate cause:

- Pylint `get_python_path` stops at the initializer-free directory, and
  `fix_import_path` adds that directory itself to `sys.path`.
- The actual additional search path begins with `"."`, followed by the project
  directory. The working directory is the fixture root.
- Astroid `modutils._get_relative_base_path` normalizes case on the search path
  but compares it directly to an absolute/real filename. For the `"."` entry,
  that prefix comparison cannot match. For the exact project-directory entry,
  the relative module path is empty and the caller skips it.
- This accounts for why the available cwd-relative search root is ineffective
  in the observed resolution attempt. Pylint then falls back to `project` and
  does not discover the child files without `list_all=True`.

The omission and exception chain above are executed evidence. Relative-search-path
normalization as the sufficient repair is still a source-based hypothesis: this
six-row study did not substitute an absolute search root or change resolver code.

Decision: do not continue extending the builder's synthetic-module guard as the
primary repair strategy. The next smallest check is relative versus equivalent
absolute search roots at the public resolver, followed by the complete original
caller on a resolver-only candidate based on clean task source. Preserve direct
file and ordinary-package controls. This selects a repair layer; it does not yet
prove a patch or authorize another paid model run.

For an agent experiment, the useful public evidence is now the selected-file list,
both resolution errors and the unattempted child, not just disappearance of F0010.
Any later model trial must be labeled as assisted by this development evidence;
this operator diagnostic itself demonstrates no model repair gain. No new prompt,
tool schema, mandatory gate, model/context setting or production policy was added.
The cause of the separate private acceptance failure remains unknown.

## Validation, provenance and limitations

An independent worker reviewed the fixed-source wrappers before execution and
rechecked all six receipt hashes, paired conditions and selection/parsing evidence
afterward. Source and result audit remained public-only. Ruff and compile checks
passed for both external files; five documentation checks also passed.
The repository change is documentation only; runtime quick/mock
and the candidate's unchanged regression/acceptance were not repeated.

- Root: `C:/pt/namespace-selection-diagnostic-v1`.
- Operator: `run.py`; helper template: `helper.py`.
- Result: `results/result.json`; full public receipts are linked there.
- Journal: `results/runs/run_dev_namespaceselection.jsonl`.
- Harness commit: `7a60153d`; runtime
  `sha256:5753dbef010721c721db788aa01525fc269ad12093b46e45ffc2ffd158c929f3`.
- Saved candidate: `sha256:f888231b7932f2022077ba46aed96ef71b87603a7fe97eb7c3890d719faaa908`.
- Plan: `sha256:298ab46ea8b34fa2fa112bc719dab4fbab2f1ac774260aa6a9a37312a9fb9b39`.
- Helper: `sha256:4957eaaa194aa2b0568eb71cc5a07beb30dd2c616affe29985f9048399245ac7`.
- Operator: `sha256:a0aeac849597300ac9841a120777612ee2ad7a86c8655d16454af87d05be5c65`.
- Result: `sha256:305e8c541be7be80d615e9ddd9b4dfcdb6da5e351c2c7c8bcc21bfa36424c941`.
- Journal: `sha256:5649973d84445d864b40d190064cf4ca62d07d00e23fc376d2ae72f625365a31`.
- Public Astroid `modutils.py`: `sha256:544f3913f733562771f7529afdbbcf2ab1024b7c2719c822f75bafa8baefac39`.
- Public Pylint `expand_modules.py`: `sha256:9c0cb3b70696a3669bf79faa575f508d8c399b706115ea4cf320b7ee9cdf4d8b`.

Prepared source, dependencies and pinned image identities are bound by the plan,
calibration and each receipt. The wrapper observes selected public calls, not all
Astroid imports, cached-object paths or every possible filesystem configuration.
The six observations are conditions on one development task, not six independent
tasks, statistical replication, generalization evidence or an official score.

Statistical fallacy coverage: 11/11 checked. Simpson/ecological/collider/base-rate,
regression-to-mean and reverse-causality analysis do not apply to this deterministic
single-task comparison. The known-failure selection limits transfer. All planned
conditions and negative outcomes are retained; marker validity is checked by both
controls. Fixed pre-execution criteria avoid post hoc relabeling, but this remains
targeted development diagnosis. No population effect, significance, model quality
or private-test causal conclusion is claimed.
