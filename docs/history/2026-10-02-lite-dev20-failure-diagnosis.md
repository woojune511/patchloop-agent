# Lite dev20 failure diagnosis

Date: 2026-10-02. Operator-only follow-up to the
[closed batch](2026-10-02-lite-dev20-results.md). This record does not alter its
verdicts, tests, submitted patches, or historical evidence. It is not solver guidance.

## Question and evidence

Why did ten submitted patches fail original evaluation despite all twenty final
public regression checks passing? Distinguish an ineffective repair, incomplete
behavior/compatibility, unavailable diagnostic tools, and grading requirements
that are stricter than the reported symptom. This matters before attributing the
entire gap to model capability or choosing another prompt experiment.

Execution head: `3077f81afe3d85e301e3af99b09bf4c117425f52`.
Analysis starting head: `c02149ad8c710f4267a5dfc0dbc014e82a7f848d`.
Read the public issues and submitted diffs first, then original evaluation reports
and failing assertions, validated child journals, tool results, and public source.
No reference patches were read for this diagnosis. Private outcomes are operator
evidence only and must not become solver prompts or task-specific repair hints.

Evidence roots:

- `C:/pt/analyses/lite-dev20-registration-20261002-v1`: closed summaries/predictions.
- `C:/pt/ld20live01/<index>/runs/<run_id>.jsonl`: original agent actions/results.
- `C:/pt/ld20native01/logs/evaluation/lite-dev-controls-agent/agent/<instance_id>`:
  original reports and test output.
- `C:/pt/analyses/lite-dev20-failure-diagnosis-20261002-v1`: `audit.json`, operator
  drivers, content-addressed artifacts and `runs/run_dev_litedev20diagnosis.jsonl`.

The operator compared base versus submitted source for four tasks using existing
pinned images, read-only source mounts and network disabled. No provider calls,
paid solve repeats, image acquisitions, hidden-evaluation repeats or runtime edits.
The first CTE replay had an operator quoting SyntaxError; both failed attempts are
retained. A separately recorded corrected diagnostic executed the public example.

## Per-task findings

| Task | Submitted change and observed failure | Interpretation |
| --- | --- | --- |
| pydicom-1139 | Added iteration/membership. Original tests successfully traverse names; the remaining failure expects `AttributeError` from direct `next(person_name)`, while the patch raises `TypeError`. | The reported iterable behavior is present. Exact exception compatibility causes the original FAIL; this is not evidence that iteration was unimplemented. |
| pydicom-1413 | Added `write_OLvalue`, but the OL writer registry still points to `write_OWvalue`. Public replay with OL byte data containing a backslash, and with the agent's integer-list case, raises the same `MultiValue` TypeError before and after. | Confirmed ineffective repair: the new function is disconnected, and byte conversion remains unchanged. Ordinary bytes already succeeded on base; that narrow example cannot establish a repair. |
| pydicom-901 | Removed import-time stream handler and forced log level. Original tests require a null-handler default plus debug handler selection; the latter still raises an argument-count TypeError. | The reported side effect was addressed, but the evaluated logging API/default contract is incomplete. The public issue does not explicitly specify every added API expectation. |
| astroid-1268 | Added `visit_unknown` returning an empty string. Original evaluation expects `Unknown.Unknown()`. | Removes the reported AttributeError but loses a meaningful representation. Exact representation is an additional evaluation requirement, not stated verbatim in the issue. |
| astroid-1333 | Added namespace fallback in builder file-open error handling. Original module-path lookup still raises ImportError for a package without `__init__.py`. | Wrong/incomplete repair layer: changing the later builder does not cover the tested path-resolution entry point. No separate end-to-end pylint replay was performed. |
| astroid-1866 | Caught TypeError during format inference. Original evaluation still crashes on ValueError for an invalid format code. | Partial exception handling: the reported exception is covered, a related invalid-format case is not. |
| sqlfluff-1517 | Returns the original segment sequence when delimiter matching encounters an empty element. Original evaluation no longer reports the dropped-elements crash, but rejects the entire SQL rather than reporting only the extra delimiter tail. | Crash avoidance loses partial parse/error-location behavior. The public issue explicitly leaves ignore-versus-lint behavior open; the original expected diagnostic is more specific. |
| sqlfluff-1625 | Exempts no-join SELECTs containing a dotted reference. Public replay fixes both reported TSQL examples, but also suppresses the ANSI alias warning. Original CLI output still expects that warning and updated rule wording. | Requested case fixed, surrounding rule/CLI compatibility incomplete. A passing TSQL example alone is insufficient. |
| sqlfluff-1733 | Broadened a `clean_indent` condition in L003. Both public base/submitted replays still indent `my_id` by nine spaces instead of eight, matching the original failure. | Confirmed ineffective repair of the reported behavior; rule interaction was not successfully reproduced by the agent. |
| sqlfluff-1763 | Writes a temporary file then replaces the target inside `persist_tree`. Operator replay preserves the original on an encoding error and still creates/updates UTF-8 files. Original tests directly call an absent `_safe_create_replace_file` helper and swallow the resulting exception. | Implementation-dependent grading mismatch. The file-writing behavior tested by our public replay works; the original FAIL remains. This replay does not prove the full dbt CLI flow, every filesystem edge case, or general correctness. |

These categories are explanatory, not a replacement acceptance policy. In
particular, 1139 and 1763 must not be silently converted into benchmark passes.
The result remains **10/20 original resolved**, not a revised 12/20 score.

## Recurring mechanisms

### Public regression success was insufficient task verification

Every failed task eventually submitted after its registered public check passed.
Six of ten made no `run_probe` request. Pydicom-1413 made one successful pre-edit
probe, but never reran it after adding the disconnected writer. A repeat of its
own failing list case would have exposed the unchanged behavior.

The four failed tasks that requested probes made eight requests in total:

- 1413: one executed baseline diagnostic; exit zero describes successful script
  execution, while its output explicitly reports the list write failure.
- 1517: one failed before behavior execution because the generic Python probe
  image lacks `pytest` required when importing this source tree.
- 1625: four failed imports (`sqlfluff`, then `pytest`, `tblib`, and `pluggy`).
  Adding source paths and dependency stubs did not reach the intended behavior.
- 1733: two rejected snapshots. The source tree includes tracked symlink
  `test/fixtures/linter/sqlfluffignore/path_c`; generic `_snapshot` rejects its
  `120000` mode before executing the probe. The dependency-prepared branch can
  omit symlinks, but these runs used the generic branch.

Thus seven of eight requested probes produced no task-behavior observation, across
three tasks. Existing dependency-complete registered-check images could run the
operator's SQLFluff reproductions. This is a concrete diagnostic availability
gap, distinct from evaluator infrastructure failure: original grading completed
and registered/native verdicts agreed for all twenty tasks.

Do not infer that mandatory probes would solve the benchmark. All ten successful
tasks also used zero probes. Task difficulty confounds this comparison, and no
intervention was tested. The narrower observation is that available probes failed
the agent when it chose to investigate these SQLFluff behaviors.

### More reasoning did not guarantee a discriminating observation

The failed ten consumed 175 model calls and USD 3.82357785; the successful ten used
70 calls and USD 1.18766610. Astroid-1333 and SQLFluff-1625 each used 35 calls;
1733 used 22. The batch had no terminal budget/transport failure. These are
descriptive differences, not evidence that additional reasoning hurts performance.
Several difficult investigations ended in a plausible local edit without a
successful before/after demonstration on the reported behavior.

### Original acceptance and reported symptom are different questions

Exception types, exact representations/diagnostics, logging defaults, CLI output
and implementation-specific helper calls account for some failures. Original
grading stays authoritative for the benchmark score; a failure analysis must also
say whether the reported bug survives. Treating all ten as equally ineffective
patches would hide both useful repairs and genuine ownership mistakes.

## Decision and next question

Keep the runtime and original acceptance baseline. No new paid run is queued.
Replace the earlier shorthand “ten incorrect repairs” with “ten original-unresolved
submissions with mixed causes.” The analysis supports investigating the existing
probe path before adding broad planning, memory, or mandatory-check instructions.

Smallest next provider-free diagnostic: determine how a registered public probe can
use the task's already-prepared public dependencies and source roots, including
repositories with non-runtime fixture symlinks. Preserve network isolation, cost
boundaries, and complete separation from hidden evaluator files. Inspect the
existing dependency-preparation contract before introducing a new tool or image.
Success would mean the same agent-authored public probes reach real task code;
it would not yet demonstrate a better repair rate.

A separate question is whether post-edit reproduction improves decisions when a
probe actually works (1413 supplies a concrete example). That needs a bounded
comparison with fresh evaluation conditions, not hidden-test answers injected
into these exposed tasks or an automatic paid retry of the closed allocation.

Validation scope: evidence/journal inspection, four base/submitted public behavior
comparisons, documentation layout tests and diff checks. Full dbt CLI replay,
all-ten public end-to-end reproductions, an agent intervention and causal repair
improvement remain unexecuted.
