# Integrated test-selection follow-up

Date: 2026-10-30 KST. Paid allocation: **CLOSED**, all usage settled.

## Question and frozen conditions

The user requested a fresh integrated experiment after the
[selection and host-latency changes](2026-10-30-test-execution-visibility-and-latency.md).
Check whether the current agent actually executes added/changed tests, preserves
task correctness and regressions, and changes total time, host time or API cost.
The previous [three-task result](2026-10-30-integrated-dev3-results.md) is the
observed development baseline, not a causal control or a general success rate.

Tasks 3 (pvlib1154), 13 (Astroid1333) and 18 (SQLFluff1733) each start fresh once.
The first and third exposed omitted new tests; Astroid was selected after its
earlier recovery from a public regression. Model: `gpt-5.4-2026-03-05`, xhigh, 25,000 desired
output tokens. Current/brief-v1, segmented-v1/result-or-size-v1, public-checks-v1,
ordinary probes, repair recheck, protected inspection and per-call cost admission
remain fixed. Limits: 40 model calls, 100 actions, 12 accepted edits and 1,800
seconds per task, including a 330-second evaluation reserve. No old patch, agent
state or operator solution is seeded.

The user approved USD4 per task, USD12 total, maximum two workers;
credential file `C:/Users/geonj/Documents/PatchLoop/.env`. No cap transfer or
automatic retry; count, transport, billing, continuation or cleanup uncertainty
stops new batch admissions while already admitted calls settle. Earlier
allocations were closed; this run used a new explicit approval.

Implementation: `ce3f8391`; execution HEAD `09456e92` adds only the recorded scope.
Runtime hash: `sha256:8b0298620632ad5e6a2ffc2ad2ffbc71524e0c8600ad87cc9ead1b5ceb041578`.
The existing batch scheduler and registered isolated
evaluator are reused. The external launcher differs from the preceding run only
in fresh result paths and reading its directly frozen `manifest.json`.
All source/dependency/image and credential-shape preflights passed without a model
call. Seven synthetic assessment controls passed. No image was pulled or built.
The [official pricing page](https://developers.openai.com/api/docs/pricing) was
checked: standard GPT-5.4 input/cached-input/output USD2.50/0.25/15 per million,
under the runtime's 60K input limit. The client pins the default service tier and
zero SDK retries; actual input is counted immediately before each dispatch.

Preparation: `C:/pt/integrated3-selection-20261030-v1/manifest.json`.
Manifest hash: `sha256:099ffe2bb2ca22a864dda0a791a049de0895514de193f0789cbdbe33bf0cf6d5`.
Separate new result root: `C:/pt/integrated3-selection-run-20261030-v1`.
Requests, preparation receipts and the frozen runtime identity are bound there;
the preparation journal is append-only, hash-chained `dev-run-v1`.

## Assessment

For every added/changed public test file, distinguish explicit selection, partial
node selection, directory discovery and actual execution evidence. A command PASS
or visible advisory field alone is insufficient. If a run adds no test file, do
not count that as proof that new-file omissions were fixed. Inspect only public
actions, delivered context and public outputs; do not inspect hidden checks,
reference patches or private evaluator details.

Record independent acceptance and safety, public regression outcomes, submitted
diff, test choices, model calls, settled cost and whole-task/batch time. Separate
provider wait from tool/host work and record any remaining unclassified interval.
Keep operator follow-up checks separate from the agent's own decisions.

Keep the changes if useful selection behavior appears without a concrete
correctness/reliability regression; investigate specific failures if omissions
persist. Three exposed tasks with one run each do not establish causal speed gain,
test-selection probability or generalization. No further run is automatic.

## Results

All three submitted and passed independent acceptance and safety. Every public
delivery state remains `unverified_delivery`; independent acceptance is separate.

| Task | Acceptance / safety | Accepted mutation actions | Model calls, prior → current | Elapsed, prior → current | Current cost |
| --- | --- | ---: | ---: | ---: | ---: |
| 3: pvlib1154 | PASS / PASS | 3, including undo | 9 → 27 | 278.272 → 1,412.784 s | USD2.530811 |
| 13: Astroid1333 | PASS / PASS | 1 | 26 → 20 | 808.135 → 689.186 s | USD1.7017085 |
| 18: SQLFluff1733 | PASS / PASS | 2 | 18 → 17 | 724.194 → 684.461 s | USD1.1915175 |

Two-worker batch wall time was **1,415.837 s (23 min 36 s)**, versus 1,005.053 s
previously, an increase of 40.9%. Cost was **USD5.424037**, versus USD3.80521,
an increase of 42.5%. All 64 model calls settled; 65 input counts completed, with
every actual dispatch matching its selected count's request hash and input count.
All rows stayed within USD4, total below USD12; no API retry, stop or undispatched row.
Preparation and operator analysis are outside these timings and added no model or
benchmark-test execution. No Docker container remained running afterward.

### Public test-selection behavior

- **pvlib:** The final patch created `pvlib/tests/test_irradiance_reindl.py`.
  The fixed required check passed its 98 tests and still omitted this new file.
  This time the model explicitly selected the new file with `run_tests`: **1 PASS**
  on the final submitted diff. Selection feedback reached the model before that
  choice and then recorded the explicit-file receipt.
- **SQLFluff:** The model modified the existing `test/rules/std_L016_L36_combo.py`,
  whose name remains outside the directory check's `*_test.py` collection pattern.
  After fixing a public regression (2 FAIL/504 PASS → 506 PASS), it explicitly
  selected that file with `run_tests`: **4 PASS** on the final diff. Delivered
  feedback progressed from not confirmed to discovery unknown to explicit file.
- **Astroid:** The existing `tests/unittest_modutils.py` changed; the required
  directory check passed 1,232 tests, with 69 skips and 15 xfails. No separate
  `run_tests` was selected. Feedback correctly remained `discovery_unknown`;
  neither directory selection nor the total count certifies each added testcase.

The previously omitted types of files were explicitly exercised in pvlib and
SQLFluff. This is observed use of the selected configuration, not proof that the
new feedback caused the choices. Only pvlib created a new test file in this run;
do not report three successful new-file opportunities or a general omission rate.

### Newly exposed failure: restoring an added test

pvlib's first patch encountered `public regression input drift:
pvlib/tests/test_irradiance.py` (exit 2), before pytest ran. The registered public
wrapper requires the original test file's entire SHA256 before applying its
GHI=0 expectation projection. That check rejected the test function addition that
the gateway had allowed; this was not a failed test assertion. The model attempted
to move its newly added `test_reindl_zero_ghi` function from the old test module to
a separate file. Seven related edit requests were rejected by test-preservation
validation, leaving the original candidate unchanged. The model eventually used
receipt undo, which restored an empty diff and triggered a passing baseline
recheck; it then reapplied the repair with a separate test file and explicitly ran
that file. The empty-diff PASS is not repair evidence.

The first rejected move was reconstructed from public mutation receipt bytes only.
Removing the run-authored function returned the existing file to the exact original
bytes and AST; whitespace/line-ending mismatch was ruled out. `file_edits.prepare`
calls the earlier replacement validator, whose `validate_test_addition` rejects
the lack of added cases before execution reaches `_check_test`'s existing exact
HEAD-restoration exception. Thus a permitted restoration path is blocked by an
earlier duplicate check. This is a concrete validation-order defect, not evidence
that all run-authored test changes should bypass original-test preservation.

This defect was diagnosed from public receipts and current source without changing
the runtime during execution. It is **not yet fixed**. The repeated edit attempts explain
part of pvlib's additional work; the exact time recoverable by fixing it is untested.

### Timing interpretation

| Task | Provider dispatch-to-return | Input counting | Action interval union | Manifest to evaluator receipt | Unclassified |
| --- | ---: | ---: | ---: | ---: | ---: |
| pvlib | 1,180.770 s | 20.423 s | 120.092 s | 22.409 s | 69.090 s |
| Astroid | 552.890 s | 18.687 s | 53.069 s | 25.823 s | 38.717 s |
| SQLFluff | 414.228 s | 11.908 s | 141.755 s | 71.824 s | 44.746 s |

Parallel action intervals use their union. There is no evaluator-start event, so
manifest-to-receipt is a proxy interval, not exact evaluator execution time.
Unclassified time includes preparation and context/host work and is not a pure
host-speed metric. Provider waits occupied 84%, 80% and 61% of the respective rows.
Different repairs, checks and model-call counts prevent causal speed attribution.
The earlier local Git/source-validation speedup remains valid; this integrated
run **did not produce an end-to-end speed or cost improvement**.

## Decision and evidence

Keep the selection feedback and batched source tracking. Explicit missing-file
selection was observed and all three repairs passed independent evaluation. The
next concrete implementation tasks are to make exact original-file restoration
consistent across validation layers and reconcile allowed additions with the
public adapter's whole-file fingerprint. Preserve original tests, the adapter's
declared projection and atomic rollback.
No new gate, capability or isolated feature experiment is warranted by this result.
Unused allowance is closed; another paid run needs its own exact scope.

- Result: `C:/pt/integrated3-selection-run-20261030-v1/result.json`,
  `sha256:1f2456633348c0925ed38efbf23b3b19a32c289a8c81cf638524741975506888`.
- Batch completion journal hash:
  `sha256:45639dd69c8f1a964ba8972f27ca9f3488c77a2529003a680fad6e60513e9b5c`.
- Accounting summary: the same root's `summary.json`; separate analysis journal.
- Public test-selection audit: preparation root's `test-selection-audit/result.json`,
  result CAS `sha256:bca89d85a1482966396a672bdf16cd02597103414abdbdfcaec870d3a1f21cbf`.
- Rejected restoration reconstruction: `test-selection-audit/rejected-test-move-corrected.json`,
  CAS `sha256:099ed1dacaf19486b94a6e7d0403acb791b631de6509a46414fb7de7405bafc2`.
  Its initial source-line citation typo is corrected in a separate append-only record.
- Public adapter error and undo/rebuild path: `test-selection-audit/pvlib-recovery-path.json`,
  CAS `sha256:7d5f8dc3e90dcc08b2aa15fdddefa6a8f34204116059c581b7f49328bbe09160`.
- Timing comparison: `C:/pt/integrated3-selection-timing-20261030-v1/comparison.json`,
  CAS `sha256:13def9ea241dae0e146248a9eecac009d2474e6b6801d063c4e30bd6ce761c5d`.
- Analysis preserved all solver and batch journals. No private evaluator contents,
  reference patches or raw model reasoning were inspected. Runtime bytes remained
  identical to the prepared manifest. Source/Ruff/mock validation from the linked
  implementation record remains applicable; this turn changes only documentation.
- Final documentation checks: 6 PASS / 0.22 s. HTML static QA: 51 unique IDs,
  61 valid local links/fragments, unchanged JavaScript. Browser visual QA was not run.
