# Caller-source access and the unused execution path

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: public run-evidence analysis and static capability audit
- Origin Date: 2026-10-27
- Verification Status: ANALYZED / STATICALLY CHECKED; new live execution NOT_RUN
- Source: closed [R1 trial](2026-10-27-repair-entry-single-results.md), checkout `d13065f1`

The user asked how caller source could be accessed and why the model kept
searching instead of obtaining execution observations. This investigation reads
the actual dispatched requests, public action receipts, current tool source and
hash-verified public dependency files. It does not interpret opaque reasoning,
import target modules, invoke Docker/target execution, read credentials or call
a provider. No runtime behavior is changed. Two read-only role audits used the
same source evidence; they are not a blinded experiment or independent causal test.

## Main finding

Caller source was available, and its access route was explicitly described in the
model request. The model continued using repository search, which cannot search
the prepared caller dependency. The concrete failure is a failure to switch
evidence-acquisition methods after the current search scope was exhausted.
Why the model did not make that switch remains a hypothesis, not an observed
internal reasoning process. The original-call selector was also unused, but
repeating the already observed failure would not itself fetch the missing source.

## Source location and actual capability

`read_file` resolves a safe relative path inside the current workspace and requires
a Git-tracked regular file (`patchloop/dev/tools.py:3388`). `search_files` lists
the same workspace's tracked files (`tools.py:3447`). Neither searches dependency
mounts. Whole/page reading changes the returned extent of a selected file; it does
not expand this filesystem scope.

Pylint is a pinned public caller, `pylint==2.12.2`, in the prepared dependency
bundle. The file `pylint/lint/expand_modules.py` exists under the host bundle's
`site-packages`, is 5,329 bytes, and matches descriptor hash
`sha256:9c0cb3b70696a3669bf79faa575f508d8c399b706115ea4cf320b7ee9cdf4d8b`.
The probe mounts prepared dependencies read-only at `/opt/patchloop-dependencies`
(`patchloop/sandbox/probes.py:522`). It can read that public file using ordinary
Python, without importing Pylint or executing the target.

The first actual dispatched `run_probe` description is 4,294 characters. It
explicitly names the Pylint version, dependency mount, `importlib.metadata`,
`inspect.getsource` and bounded file reads. The public supplementary program also
names `pylint.lint.pylinter` and wraps its `expand_modules` callable. Consequently,
the explanations "caller source was absent" and "the access method was never
provided" are contradicted by the source and dispatched request.

A valid source-inspection body for the currently offered helper contract is:

```python
from pathlib import Path
p = Path("/opt/patchloop-dependencies/pylint/lint/expand_modules.py")
check_setup("caller_source_present", p.is_file(), True)
print(p.read_text(encoding="utf-8"))
```

This known file fits the 12,000-byte probe output limit; an arbitrary larger file
would need explicit bounded lines and continuation. The diagnostic request uses
`question`, `python_source` and `memory_update: null`. It does **not** accept the
generic replay/purpose/call_path fields removed from this experiment's schema.
Static helper validation passed for this example. It was not executed in a
container; capability, actual successful tool execution and model uptake remain
distinct claims. Caller source is for diagnosis and does not become an editable
Astroid workspace file.

## What the model selected

The public action timeline shows:

1. Response 1 searched `pylint/**` for `def expand_modules`: zero files searched.
2. Responses 2 and 3 widened the glob to repository Python files: 205 files each,
   no matching spans. At response 3, the authored note explicitly said the
   expansion logic was not in Astroid and that the Pylint caller was needed.
3. Responses 7 and 8 nevertheless searched `pylint/**/*.py` and `**/pylinter.py`:
   again zero files searched. Other responses inspected Astroid source and tests.
4. The original selector and helper were offered in every request from responses
   1 through 14. Response 14 selected another read of already supplied modutils
   lines. With two normal responses left, response 15 offered only edit/stop so a
   later response could consume an edit result. The model stopped.

The authored questions repeatedly asked where the caller synthesized an
`__init__.py` path and what arguments it passed. They were not converted into a
helper that reads caller source or records those arguments. The final stop cited
insufficient confirmed source evidence for a safe mutation. Those statements
describe its declared goal; they do not prove a particular hidden motivation.

The zero-file results are particularly diagnostic: changing the query or reading
more of the current Astroid file cannot locate a caller outside that search scope.
A zero-match result after scanning files has a different meaning. Both were
returned as ordinary search results, with a numeric searched-file count, without
a direct source-scope switch or a dependency-file selection.

## Why unused original replay is a separate issue

The initial packet already supplied the 1,531-character original program, baseline
and saved-candidate observations, F0010 capture, normal control output, exception
chains, changed-line observations and five supplementary cases. Its comparison
reported matching call conditions, unresolved F0010 and an unchanged control.
The saved candidate's changed lines 268-270 had no recorded line entries.

`recheck_original({})` reruns frozen arguments and compares baseline/current
evidence (`diagnostics/repair_cycle.py:202`). It cannot select a new diagnostic
focus or fetch caller source. Before any edit, it would primarily refresh evidence
about the same candidate. A fresh run might produce new details, but that was not
measured here. Not choosing this replay is therefore insufficient evidence of an
irrational decision. Not using the available helper to obtain the specifically
requested caller evidence is the more direct missed opportunity.

## Supported explanation and remaining alternatives

- **Established:** repository search and dependency source have different scopes;
  an executable dependency-inspection route was present; the model did not use it;
  repeated searches consumed the response horizon until diagnostic actions closed.
- **Plausible interface explanation:** reading one dependency file requires
  switching to an experiment tool, authoring Python and spending one of two helper
  opportunities. The route is explained inside a long experiment description,
  whereas the obvious source tools cannot reach it. A simpler read path could
  reduce that selection burden. The log cannot establish that description length
  or code-authoring cost caused the choice.
- **Plausible decision explanation:** the model kept insisting on static caller
  evidence and did not operationalize that question. It could also have viewed
  original replay as redundant with supplied failure feedback. The notes support
  the static-evidence preference, not a proven refusal or incapacity to execute.
- **Not supported as the proximate cutoff:** monetary, output or wall-time
  exhaustion. Context recovery succeeded. The response-count policy did affect
  the final menu, so budgets cannot be dismissed entirely. More responses might
  help, or merely extend unsuccessful searching; one trace cannot decide.

The interface hypothesis would weaken if a direct dependency-read surface were
clearly offered and the same model still failed to obtain relevant evidence under
comparable conditions. Conversely, successful inspection through the existing
helper would show that a new surface is not necessary in every run. Neither
counterfactual has been executed in this investigation.

## Recommended next intervention

First make the already registered public dependency sources reachable through a
normal, explicit read/search scope, retaining their package/version/file hash and
read-only status. A zero-file repository search should identify its searched scope
and the available registered caller scope. This removes the need to construct an
experiment merely to read source, while preserving repository mutation boundaries.
It does not require unrestricted shell or filesystem access, a new mandatory
reproduction gate, or more context.

Once the caller source is available, an execution question should name the missing
observable: actual intermediate arguments, cwd/search roots, selected path or branch
entry under the original public input. A helper can test that question; repeating
the same final F0010 alone does not settle it. Keep original before/after behavior
and final acceptance separate from this diagnostic observation.

This is a proposed intervention, not implemented behavior or evidence of a repair
gain. Local scope/identity checks should precede any separately authorized live
comparison. Keep model, supplied evidence and relevant action/cost allowances
fixed or disclose differences, including whether source reads consume helper quota.

## Evidence and boundaries

Derived public evidence and the statically validated example are in
`C:/pt/caller-access-audit-v1/public-evidence.json`, with an artifact receipt in
`C:/pt/caller-access-audit-v1/runs/run_dev_calleraccessaudit.jsonl`.
Original action and request evidence remains under the closed
`C:/pt/repair-entry-single-run-v1/`. No historical artifact was rewritten.
The new audit made zero provider/count calls and zero target executions. No
statistical comparison, repair success, acceptance or generalization is claimed.
