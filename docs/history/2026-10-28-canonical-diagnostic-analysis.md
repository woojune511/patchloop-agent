# Empty-module repair and input/output identity contamination

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent, analysis and validation
- Date: 2026-10-28 KST
- Status: ANALYZED; bounded public operator diagnosis EXECUTED
- Source live run: `run_dev_9733c1d801864fcf`, unchanged and closed
- Runtime: `c9efc5c4` implementation / `dc063926` documentation at analysis start
- No provider calls, credentials, private tests or reference patches

## Question and decision

The [live result](2026-10-28-canonical-diagnostic-fresh-results.md) left two concrete
questions: did the empty-module patch restore intended analysis, and what changed
the second invocation's selected input inventory from 14 to 16 entries?
These matter because more consistent code judgments did not produce task acceptance,
and an unexplained identity mismatch prevented comparable verification credit.

The leading explanations were omission of child-file analysis and generated cache
state inside the selected input root. Alternatives were genuine restored traversal
with an unrelated acceptance failure, and modifications to actual fixture files.
Observing the child being analyzed or changed fixture content would weaken the
respective leading explanation. The smallest diagnostic used the saved public
program and candidate with inventory differences and bounded function observations.

Both leading explanations were supported in this fixture. The two symptoms are
related to the empty-module behavior but are distinct defects: insufficient behavior
verification and input/output identity contamination. The exact private acceptance
failure remains outside this analysis.

## Method and evidence integrity

Two fresh public Docker probes used the existing pinned Python 3.9 image, public
Pylint 2.12.2 dependencies, prepared unchanged source and saved one-edit candidate.
Neither source checkout was modified. The candidate changes only builder.py.
No image pull/build, network, model/count request or private evaluation was used.

The operator program preserves the original fixture, environment, arguments and
order of its first two target calls. It adds read-only inventory observations and
a bounded same-thread Python profile for get_ast/file_build. A third call explicitly
targets the existing bad/src/project/file.py after both original calls. This third
call is a diagnostic control, not an original-case replay or a new solver result.
It inherits the preceding calls' cache state.

For both conditions, the first two input counts/hashes, captured streams and source
snapshot hash exactly match their saved live receipts. The function-event counts
are 4/8/4 per condition, below the 24-event cap. All three call captures are complete;
no probe timeout, truncation or cleanup failure occurred. These observations plus
the unchanged caller source support the path interpretation, without treating a
profile return event with None during exception unwind as a normal return.

Probe durations sum to 28,373 ms (16,668 base + 11,705 candidate). Preparation v1
failed before target execution because a gateway purpose field was passed to a
lower-level binding API. That failed record is preserved. The corrected v2 launched
the two probes once each; the program and results are outside the repository in
hash-chained dev-run-v1 evidence. There was no retry of a target execution.

## 1. The patch suppresses the diagnostic without restoring child analysis

| Input | Base | Candidate |
|---|---|---|
| Directory without initializer | Attempts missing initializer; F0010, exit 1 | Processes empty initializer AST; no output, exit 0 |
| Directory with initializer | Processes initializer and file.py; W0611 | Same initializer and child processing; W0611 |
| Explicit bad/file.py | Processes one-statement AST; W0611 | Same one-statement AST; W0611 |

For the candidate's problem-directory call, the only observed target path is
bad/src/project/__init__.py. file_build/get_ast return a package with body length
zero and file_bytes length zero. There is no get_ast/file_build call for its child.
The identical child source contains import os; direct-file invocation produces
W0611, as does directory traversal through the control with an initializer.

Pinned public caller source explains this result. Pylint expand_modules constructs
the initializer path, falls back to is_namespace=False when discovery fails and
uses get_module_files(list_all=is_namespace). That traversal skips initializer-less
directories in the nonnamespace path. The patch does not change this selection.
It changes only the downstream failure into string_build("", modname, path=path).
The resulting empty package can be tokenized from BytesIO(b"") and walked normally,
but contains no child source to analyze. Empty namespace modules are not universally
wrong; here the missing child selection is the concrete problem.

Useful source pointers:

- Pinned Pylint: expand_modules.py 62-117; pylinter.py 1059-1065 and 1175;
  utils/utils.py 163; checkers/base.py 2231.
- Candidate Astroid: modutils.py 484-491; builder.py 123-133, 164-168, 202-215;
  nodes/scoped_nodes/scoped_nodes.py 541-543; rebuilder.py 152.

The frozen success object only asks whether F0010 is absent in two calls. The host
now computes that object correctly. It cannot infer that the selected property is
sufficient to establish repair. The 1,231 existing regression passes also did not
reject this candidate. There was no selected positive observation requiring the
child to be analyzed, and no new discriminating test was added by the model.

## 2. The two additional entries are generated results, not changed fixtures

The candidate's first call adds exactly:

- cache/pylint (directory)
- cache/pylint/project1.stats (file, 646 bytes)

There are no removals or changes to existing entries. Base first-call failure
creates neither entry. The next call therefore sees 14 entries on base and 16
on candidate. The complete selected-root fingerprints exactly match the live
58e5934e... and ad31ce43... values. This resolves the uncertainty retained in the
earlier result record. Entries count directories as well as files, not two new
source files.

The static path agrees: successful AST processing sets FileState/base_name;
Pylint generate_reports then persists results. config/__init__.py creates the
cache directory and stats file. The initializer-open failure never reached that
successful state. This is a consequence of the changed behavior.

The helper chose input_paths=[root] for both calls, while root also held HOME/cache.
The host snapshots that root immediately before each call. Consequently the first
call's output becomes part of the second call's asserted input identity. The
comparator correctly detects a byte-level difference, but the selected identity
mixes independent test fixtures with generated results. This does not justify
ignoring all caches: caches that intentionally influence a call remain inputs.
For this cold-fixture test, select the actual fixture directories and make cache
initialization/output scope explicit, or isolate each case's cache state.

## 3. Why the model could finish, and what remains unresolved

Actual requests at sequences 153/168/184 included current patch bytes and
unverified comparability. The later two also included current-diff regression PASS.
The final request still offered reads, search, probes, tests and edits; its budgets
included nine model calls, 25 actions, two edits and about 1,279 solver seconds.
This was neither lost feedback nor a forced budget exit.

The runtime intentionally distinguishes deliverability from verified repair.
Known current failure or pending verification can block finish; unknown evidence
can yield unverified_delivery. This run followed that contract. A model-generated
finish is not host certification or independent acceptance. Here the semantic
oracle did not flag the empty-child result, while the remaining UNKNOWN described
setup identity. No post-edit observed F0010 failure existed to trigger revision.

There is also a separate bookkeeping issue. The target-not-entered option=False
attempt persists as an unverified case. The corrected healthy baseline is another
case. completion_reproduction aggregates both; fixing the second case's identity
alone would not remove the first case's unknown evidence. Preserve failed-attempt
history, but distinguish failed request construction from established baseline
verification obligations. The original requirement must remain pending until a
healthy failure reproduction exists.

Finally, the actual tool description shows target(['path'], option=False), and
the model copied that unsupported argument. This is evidence of a plausible
affordance problem, not proof that the example caused the error. A parameter-free
generic call example and source/signature-based arguments would remove the trap
without adding a new control stage.

## Recommended order, not implemented in this analysis

1. Use a discriminating public observation that checks both failure removal and
   preservation of intended work. Here, child analysis/file selection separates the
   empty-module workaround from restored behavior. Do not hardcode W0611 as a
   universal goal or interpret every silent result as failure.
2. Separate fixture inputs from generated outputs in call identity; retain explicit
   cold/warm cache conditions. Do not disable comparison or rewrite historical evidence.
3. Separate pre-target request-error attempts from healthy baseline obligations,
   retaining links and receipts. Remove the misleading option=False example.
4. Continue to report submission, public verification, comparability and isolated
   acceptance separately. Avoid a universal ban on unknown delivery or an automatic
   context/cost increase; neither follows from this result.

The canonical host computation is retained. Live changed-wording failure delivery
and re-repair are still NOT_EXERCISED, while prior scripted tests cover their wiring.
No runtime fix or further paid solve was performed or authorized by this analysis.

## Evidence paths

- Diagnostic root: C:/pt/canonical-public-diagnosis-v2.
- manifest.json: sha256:c9acb398c74f057d61ae5bf14618779e46742746fb009165874537939f4cb19f.
- summary.json: sha256:9daeffa440838f4e24a6cffab64df7eb2648cd8f1d28210109e412ac1c89739a.
- operator-probe.py, base-receipt.json, candidate-receipt.json and verification.json.
- Journal: runs/run_dev_canonicalpublicdiagnosis.jsonl.
- Preparation-only failure: C:/pt/canonical-public-diagnosis-v1.
- Static audit used only current public source, pinned caller dependencies and
  public live receipts. No private expected behavior or solution was consulted.
