# Saved candidate comparison: file selection fails before the builder

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run, provider-free public-source diagnostic
- Origin Date: 2026-10-28, Asia/Seoul
- Verification Status: VERIFIED for saved-call parity and selected processing paths.
- Version Label: file_processing_compare_v3
- Scope: Astroid-1333 dev-train/current-dev20/13, official=false, claim-ineligible.

## Question and controlled change

The [repair trial](2026-10-28-post-reproduction-repair-results.md) removed F0010
on its third edit but still produced no processing witness. This blocked repair
completion despite remaining context, output, money and time. The unresolved
mechanism was selection omission versus later AST/check omission. The user asked
to execute the proposed local comparison; no new provider allocation was used.

Compare candidate2 (accepted parent mutations138/156) with candidate3 (also248).
Only the final builder patch differs. Reconstruct both from the prepared base
with preimage/postimage/diff verification. Preserve the exact original program,
binding, fixtures, arguments, environment, Python3.9 image and pinned dependencies.
Observe existing frames without replacing functions or consuming generators.
Filter to fixture-related expansion, classification, enumeration, AST and checking.

Source journal: `C:/pt/post-reproduction-repair-run-v1/repair/runs/run_dev_3e21775752a54cae.jsonl`,
259 events, hash `sha256:3523fbf47b6b49cee0a40830a8efeeb69da9d233c8e1e6ee708373c35332b7d0`.
Baseline commit: `7e03d26675fc0e4ce4c169f5b3cde840a69b613e`.
Candidate hashes: 2=`sha256:6a65d2fdc52da10cd79f5de7a3d7f6921aee2bd72541a36003d8ecab38e1db9b`;
3=`sha256:638b6bf8c47e304832d8760813c6bbf271b15845ad5226c444cccc6211e734c8`.

No model, benchmark evaluation, public regression or target-source repair is run.
Planned maximum: two probe dispatches, 120-second local invocation deadline,
existing 30-second per-probe timeout and 12,000-byte output cap. Stop on incomplete
capture, changed identity, observer overflow or uncertain execution/cleanup.
Trace serialization is bounded to8,000 bytes with explicit omission accounting.

## Execution and preparation anomalies

1. `uv run --locked python -m diagnostics.file_processing_compare --output C:/pt/file-processing-compare-v1`
   stopped before preflight/dispatch: the derived manifest used the wrong artifact
   store root. Preserve the directory and its failure receipt; zero probes ran.
2. The same command with output `C:/pt/file-processing-compare-v2` executed candidate2
   successfully, then the parser incorrectly required setup_checks=passed. The exact
   original program calls no check_setup; both saved and new receipts correctly say
   not_checked with an empty check list. Its fixture proof comes from call snapshots.
3. Correct that parser expectation and reuse the settled candidate2 receipt by hash,
   exact execution/input/diff identity and closed journal shape. Execute only candidate3:
   `uv run --locked python -m diagnostics.file_processing_compare --output C:/pt/file-processing-compare-v3 --reuse-candidate2 C:/pt/file-processing-compare-v2`.

Final command exits0. No candidate was executed twice. Total probes2, provider calls0,
new billed costUSD0. Probe durations13.698s/8.659s, total22.357s; this excludes operator
preparation and parser repair. Raw captures8,852/9,159 bytes are complete below12K.
Cleanup is confirmed for both. Original parent journal and saved candidate remain unchanged.
Each collector invocation has its own120-second deadline. Recovery recreated that
deadline; combined active journal intervals total29.324439s, while the first v2
freeze through v3 completion spans172.852930s including parser repair. This is not
evidence of completion within one uninterrupted120-second allocation.

## Observed mechanism

| Stage in failing call | Candidate2 | Candidate3 |
| --- | --- | --- |
| file_info_from_modpath(['project']) | ImportError | same |
| expand_modules fallback | namespace=false, directory=true | same |
| get_module_files('src/project', list_all=false) | sees file.py, returns [] | same |
| Selected descriptors | src/project/__init__.py only | same |
| file_build(missing init) | AstroidBuildingError | empty Module, body length0 |
| Actual checker | no failing fixture AST checked | empty init AST checked |
| Original F0010 / W0611 | true / false | false / false |

The enumeration source skips directories without __init__.py when list_all is
false. Here the trace shows file.py in that directory, the false argument and an
empty return. Thus file.py disappears before AST construction in both candidates.
The last edit leaves upstream selection unchanged and changes exception handling
into checking an empty module. It cannot restore an omitted selected descriptor.
The exact underlying reason module-name/search-path resolution raises ImportError
was not instrumented further in this comparison; no complete repair is inferred.

Normal-package controls select both init and file.py, construct file.py's AST
with body length1 and enter/return from _check_astroid_module successfully. They
retain W0611. This positive coverage supports interpreting the absence of the
failing file's AST/check events. Mere complete=true without positive coverage
would not establish absence. Selected calls18/20 all close; excluded nonfixture
calls12/12; observer errors0, dropped calls0, no trace replacement or truncation.

Entire original call dictionaries equal the saved seq164/256 captures, including
input snapshots, args/argv, cwd/environment, stdout/stderr, exception and exit code.
Image/profile/dependencies and source snapshot hashes also match. The fixed program
hash remains `sha256:3a1c39fc32cb99a61159ceb623602c7dab4dd7d4eea70dda31b1e4fb365a3a66`.

## Decision, validation and limits

Focus the next repair hypothesis on module resolution/namespace traversal. Do not
accept empty-AST error suppression as processing success. The existing original
criterion caught the omission; this result does not justify another runtime gate
or larger context/output limits. Earlier path evidence versus an extra edit are
separate live hypotheses, neither tested here. The previous paid allocation is closed.

Ten focused diagnostic tests pass in0.932s; Ruff passes. The quick suite reports
645 PASS /3 FAIL in202.30s, including passing isolated mock smoke. The three failures
are in unchanged code/tests: two malformed-purpose cases call .get on str/list in
helper_recovery._original_calls; one behavior-diagnostic assertion expects the old
call=target(['path']) example. They are reported, not silently counted as green or
repaired as part of this operator diagnostic. No broader rerun was performed.

This is local diagnosis of two saved development candidates, not live model uptake,
a clean-start solve, hidden-test acceptance, or a general repair-gain measurement.
W0611 is the selected same-call processing witness beyond the issue's explicit
error-absence expectation. Public regressions, finish_task and isolated acceptance
remain NOT_RUN for these candidates in this comparison.

## Evidence

- Collector: `diagnostics/file_processing_compare.py`.
- Observer: `diagnostics/probes/astroid_processing_trace.py`.
- Tests: `tests/test_file_processing_compare.py`.
- Result root: `C:/pt/file-processing-compare-v3`, with immutable result/manifest,
  raw receipt objects, reconstructed workspaces and hash-chained journal.
- Manifest hash: `sha256:8770f902af9c9ac0f1a07a5d003eb3ee6ec20d865fbf95d0cb89236b8fc7d1f5`.
- Result hash: `sha256:162a1be6d4858ea2e64491dafa8f218b38d95432083d857498e1044a741785e6`.
- Collection journal through event5:
  `sha256:9488f4bfc23ef08e3bf29dd3c37c1e111c0af50a53f6b63643b686e682b461e6`.
- Prior preparation/parser records remain at file-processing-compare-v1 and v2.
