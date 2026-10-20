# Astroid public caller diagnostic

## Decision

The original caller evidence gap is now concrete. A public Pylint caller-boundary
reproduction produces the reported missing-initializer parse error on the base
and all three saved implementation candidates. Their local helper results did not
establish a repair of this path. Prioritize making the public caller/setup
observable through bounded evidence acquisition; do not further tune retention or
add another general warning from this result.

This follows the [saved-log audit](2026-10-18-astroid-next-fix.md) and the
[closed comparison](2026-10-18-repair-mechanism-results.md). No runtime intervention
was adopted. The next uncertainty is whether a solver, given this missing public
evidence, would choose the relevant repair and use the counterexample correctly.
That evidence-uptake/model comparison remains NOT_RUN.

## Question and controlled diagnostic

Question: does the public directory caller reach the repair branches selected in
the saved runs, and do those candidates prevent its parse error? Alternatives were
a missing caller/setup connection, a helper failure that actually explains the
original path, and an environment or diagnostic failure that prevents assessment.

Public task: Astroid-1333, base
`d2a5b3c7b1e203fec3c7ca73c30eb1785d3d4d0a`. The public report specifies
`pylint src/project` from `root_dir`, an existing `src/__init__.py`, and an absent
`src/project/__init__.py`. Empty `file.py` is explicitly allowed by the report.

Public Pylint v2.12.2 caller functions were fetched and byte-hashed from the
upstream tag. The executable function ASTs were preserved; only docstrings,
formatting/comments and the decorator for a free-called static method were
removed. Type-only dictionary aliases and a message-recording sink replaced the
unavailable Pylint type/reporter dependencies. The selected functions are:

- `get_python_path`, `_modpath_from_file`, ignore matching and `expand_modules` from
  [expand_modules.py](https://raw.githubusercontent.com/pylint-dev/pylint/v2.12.2/pylint/lint/expand_modules.py).
- `_patch_sys_path` and `fix_import_path` from
  [utils.py](https://raw.githubusercontent.com/pylint-dev/pylint/v2.12.2/pylint/lint/utils.py).
- `should_analyze_file` and `get_ast` from
  [pylinter.py](https://raw.githubusercontent.com/pylint-dev/pylint/v2.12.2/pylint/lint/pylinter.py).

The public single-process/no-stdin call chain connects those functions; argument
files are analyzed and the `.py` child qualifies. No ignore pattern matches the
fixture. Configuration discovery, checker/plugin initialization, CLI dispatch and
report formatting are excluded. Thus this is a source-grounded caller-boundary
reproduction, **not a full CLI run**. The sink records `parse-error`, which the
same Pylint source maps to F0010; it does not print a fabricated CLI transcript.

All executions used the existing clean Python **3.10.22** probe image and the
unchanged prepared Astroid dependencies. Pylint importability was actually false.
No package installation, image pull/build or evaluator image was used. Python
3.9.1 from the issue was not reproduced. This environment limitation qualifies
the result; it does not turn the new observation into private acceptance evidence.

Frozen before target execution: base and three exact saved candidates, each with
missing/present initializer, plus one untraced baseline parity check: **nine probes**,
one execution per condition, no model/count calls. Each retained the existing
30-second, one-CPU, 512-MiB, eight-PID, 8,000-character and 12,000-output-byte caps,
network isolation and confirmed cleanup. Baseline failure, normal control and
trace parity had to validate before candidate execution. No new repair was tried.

## Results

| Source state | Missing project initializer | Initializer present |
| --- | --- | --- |
| Unchanged base | `parse-error`: unable to load `src/project/__init__.py` | Both initializer and child ASTs built; no error |
| E1J0: conditional package-spec conversion | Same parse error | Both ASTs built; no error |
| E0J1: filesystem namespace check | Same parse error | Both ASTs built; no error |
| E1J1: namespace helper extension | Same parse error | Both ASTs built; no error |

E0J0 had only a test addition, so its unchanged implementation is represented by
the base. The three reconstructed candidate diff hashes match the saved action
receipts exactly: `1ac127d0...`, `fa4cb018...`, `62c5f3ba...`, respectively.
The untraced base matches the traced base's behavior. Nine probes completed cleanly
in 60.260 seconds of summed probe duration; that execution success is distinct
from the four observed missing-initializer failures. All nine owned containers
were confirmed absent.

## What the caller adds to the diagnosis

For the missing-initializer fixture, the public caller puts `root/src/project`
at the front of `sys.path`; it does not insert the root used by E1J1's helper probe.
The resulting module descriptor is named `project` and points at the synthesized,
nonexistent `src/project/__init__.py`. Every tested implementation then calls
`AstroidManager.ast_from_file(..., source=True)` and reaches `AstroidBuilder.file_build`.
The module-name fallback is not entered in the observed trace. The missing-file
exception is handled by the copied `get_ast` as `parse-error`.

This distinguishes failure emission from repair ownership. The builder raises
because it receives a nonexistent source file; that alone does not justify changing
the builder. Upstream file/module classification and the caller's path setup must
be accounted for before assigning the repair to a namespace helper.

The observed route explains why the earlier evidence was insufficient:

- E1J0's conversion needs a returned package-directory spec with no initializer.
  The missing-case trace records no successful finder/spec return, and the caller
  reaches its failed-lookup path. The patch's condition was not established for
  this input. Normal-package conversion still succeeds in the positive control.
- E0J1 changes the package predicate but leaves the caller's descriptor and
  source-file build unchanged. Its previously observed local argument mismatch
  remains a separate evidence-present mistake; it was not a repair of this route.
- E1J1's saved successful probe inserts `root` into `sys.path` and tests a file-to-
  module helper. The actual caller boundary has different path setup and still
  opens the missing initializer after that candidate. The previous end-to-end
  claim is now contradicted by a public caller-boundary execution, within the
  stated environment. It still does not reveal the private evaluator's cause.

Public source provides a narrower remaining source hypothesis: the caller passes
`.` among explicit search paths, whereas `_get_relative_base_path` compares absolute
filenames to a merely case-normalized search path. In this fixture `.` cannot
match that absolute prefix; the exact project-directory path also yields an empty
relative module list. This is consistent with the observed fallback name `project`.
Relative-search-path handling is a useful next task-source discriminator. No path
normalization patch, release comparison or unique-cause counterfactual was run,
so this report does not claim a completed Astroid repair.

## Implication for PatchLoop

The original sandbox could run Astroid helpers, but it could neither import the
named caller nor read its source through the repository-only read/search tools.
The operator supplied newly acquired public caller code for this diagnostic.
The old logs cannot be reclassified as if that evidence had already been delivered.
This supports addressing reproduction/caller-evidence access before another
retention change. A targeted preparation should make the public caller/setup
observable without adding repair hints, private material or unrestricted shell.

Judgment still matters: copying a file layout is not enough when entry arguments,
path setup or asserted outcome differ. The prior E1J1 assessment exceeded its
known execution scope even without the newly acquired caller code. However, no
model has been shown this new counterexample; whether it would ignore adequate
evidence, and whether acquisition changes repair success, remain untested.

## Evidence and validation

External record: `C:/pt/analyses/astroid-caller-diagnostic-20261018-v1/`.
`public-source-provenance.json` binds upstream URLs and bytes; `protocol-v2.json`
binds conditions, programs and candidate hashes; `gate.json`, per-condition JSON,
CAS receipts and `result.json` bind the observations. The append-only
`runs/run_dev_astroidcaller18.jsonl` records preparation and all executions.

Two preparation errors were rejected before any target run: an 8,112-character
draft exceeded the unchanged source cap, and a saved-action status decoder left
candidate workspaces at base. The drafts/superseded protocol were retained; AST-
equivalent formatting and exact `succeeded` receipt decoding corrected preparation.
The executed programs are 7,925/7,926 characters and all candidate hashes verified
before the nine-run protocol began. No outcome was used to tune a repair or relax
a limit.

Revalidated 420 historical inputs, prepared source/dependency integrity, unchanged
candidate workspaces and exact container cleanup. Documentation layout/link tests:
five passed; Ruff and whitespace checks passed. Runtime code/tests, transition
rules, reference count and budgets are unchanged. Full runtime suite/mock smoke,
full CLI, Python 3.9, private evaluation and model evidence uptake are NOT_RUN.
New provider/count calls and billed cost: zero.
