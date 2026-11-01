# Public path-contract comparison of the submitted model candidate

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run, public-source local diagnosis
- Origin Date: 2026-10-28, Asia/Seoul
- Verification Status: EXECUTED; candidate-only public counterexamples confirmed
- Version Label: public_path_contract_v1
- Scope: saved development candidate, official=false, claim-ineligible

## Problem and discriminating question

The [preceding model run](2026-10-28-caller-completion-repair-results.md) read the
caller, made one edit, passed its original/control calls and1,231 public tests,
and submitted normally, but failed isolated acceptance. It did not exhaust its
budget. That gap matters: completion and the selected original failure no longer
distinguished a correct library repair from a workaround for that caller.

The user asked to proceed with the proposed public path/return-value contract
review and a short original-versus-candidate comparison. This authorized local
diagnosis, not new paid model work or a target repair. The previous allocation
remains closed. No private evaluation details, hidden tests, reference patch or
earlier operator repair were used to derive cases or expected outcomes.

Leading hypothesis: the new fallback makes the caller succeed by interpreting
a search directory itself as a namespace, violating the public resolver contract.
Alternatives were that both versions preserve the contract, or that any discrepancy
already occurs in the base. Explicit/implicit equivalent path forms, negative
leaf searches, ordinary packages and namespace portions distinguish these cases.

## Public source basis

Paths below refer to the saved public candidate at
`C:/pt/caller-completion-repair-run-v1/repair/workspaces/run_dev_3e21775752a54cae/repo`:

- `astroid/modutils.py:363-374`: path is an optional list of search locations;
  omitted path uses sys.path, and missing modules raise ImportError.
- `astroid/interpreter/_import/spec.py:130-143`: the finder searches by appending
  the module name to each root. Lines339-364 document the same path contract and
  traverse child modules through the preceding spec's search locations.
- Candidate `astroid/modutils.py:646-669`: the new fallback instead matches the
  full module name against a path entry's trailing components and returns that
  entry itself as a namespace. It returns the first match and does not iterate
  sys.path when path is None.
- Public `tests/unittest_manager.py:131-159` exercises parent roots, namespace
  children and rejection of missing members; lines175-184 reject an unrelated
  namespace/file combination. `tests/unittest_modutils.py:207-223` covers ordinary
  file/builtin resolution and a missing name.

Prepared pylint2.12.2 source is at
`C:/pt/calleruptake18/preparation-v2/B/site-packages/pylint/lint/expand_modules.py`.
Its lines19-27 explicitly describe an initializer-based path assumption as wrong
for namespaces. Lines60-61 put this computed directory in additional_search_path.
Lines91-118 use namespace classification to omit the hypothetical initializer and
enumerate real files with list_all. This explains how the fallback can restore
processing for this caller without preserving general search-root semantics.
This connection is source-based interpretation, not new instrumentation of the
old original call.

## Frozen comparison

Base: public task commit `d2a5b3c7b1e203fec3c7ca73c30eb1785d3d4d0a`.
Candidate: submitted patch
`sha256:141dc0f8e373a23b7379661de8c08b3b0f07c6fa010f2d7bbb8b18b0ed74967f`.
The accepted mutation was replayed onto a fresh public source snapshot with
preimage/postimage/diff verification. Both variants execute the identical new
operator-authored program with Python3.9.25 and the same prepared dependencies,
image and profile. Original/control captures were already audited and are reused
as historical evidence, not relabeled as new executions.

Fixtures include `R/ns/member.py` with no initializer, `R/pkg/__init__.py`, and
two namespace portions under separate roots. The program records public
file_info_from_modpath, the lower spec.find_spec and Python PathFinder outcomes
on identical effective roots. It compares errors, type, location and namespace
paths, not differing spec-name conventions. Source docstrings and directory
layout establish the expectation; PathFinder supplies a comparison, not a new
benchmark acceptance oracle.

External plan: `C:/pt/caller-path-contract-analysis-v1/plan.md`.
Command: `uv run --locked python C:/pt/caller-path-contract-analysis-v1/run_compare.py`.
Maximum two probes,120s invocation, zero provider calls. New single-use output
is `C:/pt/caller-path-contract-analysis-v1/run-v1`; stop without retry on drift,
incomplete capture, unexpected diagnostic error, deadline or uncertain cleanup.
The manifest was journaled before execution. Compilation, Ruff and a separate
native agent's static source/script review preceded dispatch. The reviewer shared
the task context; this is not blind or cross-family evaluation.

## Results

Both probes completed with confirmed cleanup, no timeout/truncation and unchanged
source. Durations were11.378s and6.842s, totaling18.220s of probe execution; this
excludes operator design and preparation. Provider calls0, new billed costUSD0.
Stdout sizes were5,047/5,321 ASCII characters, below the12K capture bound.

| Public case | Base | Candidate | Interpretation |
| --- | --- | --- | --- |
| Parent root, explicit path | Correct namespace | Same | Preserved |
| Parent root via sys.path, path=None | Correct namespace | Same | Preserved |
| Parent root via sys.path, path=[] | ImportError | Same | Existing empty-path discrepancy |
| Namespace directory itself as explicit root | ImportError | Returns that directory as namespace | New false positive |
| Same leaf root via sys.path, path=None | ImportError | Same | Correct negative control |
| Same leaf root via sys.path, path=[] | ImportError | Same | Correct negative control |
| Namespace child module | Correct source file | Same | Preserved |
| Ordinary package | Correct initializer file | Same | Preserved |
| Two valid parent roots | Both namespace portions | Same | Preserved |
| Two leaf roots, forward order | ImportError | Returns first leaf only | New false positive |
| Same leaf roots, reverse order | ImportError | Returns other leaf only | New false positive |
| Absent module name | ImportError | Same | Preserved |

The three candidate-only discrepancies are three manifestations of one faulty
rule, not three independent bugs or an estimated failure rate. The lower resolver
and PathFinder continue to reject all three. The divergence is introduced solely
by the candidate's new wrapper fallback. Both variants share the empty-list case;
it is excluded from the count of new regressions.

For example, if the search root is `/R/ns`, looking for `ns` searches for
`/R/ns/ns`. Its absence must not become success merely because the supplied root
ends in `ns`. The candidate accepts `/R/ns` itself, while the equivalent implicit
path and unchanged resolver reject it. Reversing two such roots demonstrates
which invalid path the first-match rule chooses.

## Decision and limits

The suspected public-contract regression is confirmed. The original replay's
F0010 absence and real processing evidence are still valid for that fixture, but
they cannot certify this repair. The1,231-PASS existing public suite did not catch
these new public counterexamples. No positive sample count establishes semantic
coverage, and no budget increase addresses the observed path reinterpretation.

Retain the caller-read and reservation mechanisms; reject this candidate as a
complete library repair. The repair hypothesis needs to preserve both caller
behavior and resolver semantics: valid roots still resolve, invalid roots remain
errors, and equivalent explicit/implicit inputs should have consistent meaning.
This result alone does not justify another mandatory runtime gate or task-specific
prompt. A next bounded revision could receive the concrete public failure and
choose further investigation and tests, preserving original verification and all
caps. That would be operator-assisted counterexample feedback, not a clean-start
model solve. Such a revision is NOT_RUN and has no new paid allocation.

Private failure details were not inspected; these counterexamples must not be
claimed to be the isolated evaluator's actual failing tests. No new acceptance
evaluation, full regression suite, target repair or live model trial was performed.
The external diagnostic does not become a registered benchmark test automatically.

## Evidence and closeout

- Parent journal remained hash-identical:
  `sha256:ec8de9ea05dbc3beff7ffc4574c9c931b345eeb77639369f5740f3c950a2825d`.
- Frozen diagnostic manifest:
  `sha256:6f2b5a7729a3f5404d4099143774b8b8d637d5743bd9657686a71238574efad9`.
- Result `run-v1/result.json`:
  `sha256:2025fe629bf0dcf33db4814880a7747d595f6ce6fc45b8e3758d648eccc0533e`.
- Execution journal through completed event6:
  `sha256:579c669074c764f9ffdd1dde8646aaa1f79f808e06168a6c5f84b98a810df2eb`.
- Program/collector: external `probe.py` and `run_compare.py`; their hashes are
  sealed in the manifest. Raw receipt references are in the result and journal.
- Static review and independent public receipt audit:
  `C:/pt/caller-path-contract-analysis-v1/static-review.md`, hash
  `sha256:73c026770b5d3df3162262b82968db01f0df4f8e409fd711ded7dd8dc1de7745`.
  The audit confirms receipt hash/size, exact stdout-to-result rows, comparison
  flags, shared fixtures/program/environment/dependencies and source immutability.

Only current status, the history index and this follow-up are changed in the
repository. Documentation controls passed five tests; `git diff --check` passed.
Older evidence and source/candidate bytes remain immutable.
