# Agent trace comparison: repair gains and verification closure

Date: 2026-10-06. Read-only, provider-free investigation; official=false.

## Question, scope and method

The user requested a comparison of the last two experiments and concrete future
improvements. This review covers the previous full 20-task panel (59d90f6b,
C:/pt/pv1dev20 and C:/pt/pv1d20live05), the corrected current panel (e3aa7080,
C:/pt/cd20p06c and C:/pt/cd20live06c), and the latest two-task search supplement
(a28aa364, C:/pt/s2p06 and C:/pt/s2live06). The intervening interrupted panel is
not treated as another independent full measurement. Previous reports remain
immutable; this is a separate analysis of saved evidence.

Read saved public issues, source observations, public action decisions/plans,
edits, check/probe output and exact final model-input projections. Validated
journal chains and recorded hashes; used only existing acceptance summaries.
No raw model reasoning, hidden test contents or reference patches were read. No
new model calls, task replays, evaluator runs or runtime changes were made.

All 20 delivered public issues and repository/base identities match. Model, effort,
limits and common policy settings also match, but runtime, task permissions, probe
environments, evaluation reservation, helper protection and scheduling changed.
Row 17's public check wrapper also changed. There is one fresh attempt per task per
panel, not a randomized feature ablation. Distinguish stronger observed behavior,
improved infrastructure and hypotheses about their causes.

## Results and efficiency

The previous full panel has 9 PASS / 11 FAIL. The corrected panel has 11 PASS /
7 FAIL / 2 NOT_RUN. Compare only the 18 tasks evaluated in both:

| Same 18 tasks | Previous | Corrected |
| --- | ---: | ---: |
| Acceptance PASS | 8 | 11 |
| Acceptance FAIL | 10 | 7 |
| Model calls | 175 | 222 |
| Settled USD | 2.79057885 | 4.23602205 |
| Search calls | 95 | 183 |
| Read calls, including rejected | 63 | 94 |
| Accepted edits | 22 | 30 |
| Edits touching tests | 0 | 7 |
| Required-check executions | 22 | 24 |
| Probe calls | 2 | 5 |
| Selected-test calls | 0 | 0 |

There are three FAIL-to-PASS gains and no regressions within these matched 18.
Calls rose 26.9%, cost 51.8%, input tokens 56.7% and output tokens 48.9%.
Success improved on this exposed subset; efficiency did not improve by these
measures. Seven test edits include revisions, not seven independent new tests.

The supplement completed both previously unassessed tasks, with two agreeing FAILs
and USD 1.07327790 cost. Preserve that separate result; do not convert the original
NOT_RUN records into a uniform all-20 measurement. SQLFluff-2419's earlier success
was not reproduced. Incomplete coverage, different concurrency and changed query
sequences prevent a whole-panel speedup or general no-regression claim.

## Improvements actually visible in actions

**Pvlib-1707: the test capability was used productively.** The old run's test edit
was rejected because tests were forbidden; its source workaround passed 30 public
tests but failed acceptance. The new run masked the final IAM result at incidence
angles of at least 90 degrees, added scalar/array/Series coverage, identified a
test-expectation dtype error and corrected it. Repair recheck passed 31 tests and
acceptance passed. This demonstrates an executed test-and-repair loop. The source
fix also changed; no old-source failing test run was recorded, so this does not
isolate the causal effect of allowing tests.

**Pydicom-1413: better identification of the responsible layer.** The old candidate
patched the writer to handle a MultiValue symptom. The new trace followed the value
upstream and corrected backslash splitting of binary VR data in DataElement's
setter. Its public plan explicitly revised the writer hypothesis; acceptance
changed to PASS. However, the promised OL bytes/round-trip regression disappeared
from the plan after the edit. It submitted after the same 212 public tests, without
adding the promised case. Better diagnosis can coexist with incomplete verification.

**Astroid-1866: a broader relevant exception case was repaired.** The old patch
caught TypeError only; the new patch caught TypeError and ValueError and passed
acceptance. Its proposed regression was rejected because pytest.param(...) is a
computed AST call under the literal-only additive-test contract. The agent did not
rewrite it into a literal case or independent test. Both runs used the same broad
1,378-test suite. The improvement is a different successful candidate, not evidence
that the attempted test or probe capability caused the gain.

All three gain tasks made zero probe and selected-test calls in both panels.
Their costs and call counts increased. Tool availability and tool use must not be
substituted for demonstrated mechanism or quality effects.

**Infrastructure and regression handling improved separately.** The full baseline
had five probe attempts: three gateway rejections on SQLFluff-1733 and two executed
probes failing on missing pytest. The corrected run executed nine probes without
those gateway rejections; SQLFluff-1517 reached the actual public bug. Pydicom-901
preserved initialization that the old patch had accidentally removed, avoiding
nine self-induced failures. SQLFluff-1625 reduced failed check attempts from two
to one, without improving final acceptance.

The later search fix removed per-file Git subprocess overhead. The independent
same-output synthetic comparison established 128-to-1 Git calls per query. All 36
supplement search intervals were below 0.74 seconds; both tasks reached submission.
That is a concrete execution improvement, not proof of correct repairs.

## Recurrent failure mechanism: regression PASS replaces the original question

All seven unchanged failures ended with passing public checks. All seven final
inputs still offered probes and selected tests, at 145--967 elapsed seconds against
the 1,470-second solver cutoff. There is no evidence that a general tool block or
deadline forced those submissions. This does not prove that every possible check
would have fit the remaining cost and time.

| Task | Public trace evidence | What remains unverified |
| --- | --- | --- |
| Pydicom-1139 | Added containment/iteration test; 38 to 39 passing tests; still FAIL | New tests did not establish the entire required behavior; a counterexample to simply adding more tests |
| Pydicom-901 | Fixed initialization correctly; 95 tests pass | Import-time logger handler/level preservation and duplicate-output scenario |
| Astroid-1268 | Changed return from empty string to node.name; same broad checks | Direct Unknown().as_string() behavior; public issue does not specify an exact expected string |
| Astroid-1333 | Two working pre-edit investigations, then manager.py edit; 1,231 tests pass | The edited entry point on the task scenario; no post-edit probe |
| SQLFluff-1517 | Reproduced double-semicolon failure, edited parser, passed 166 tests | The same double-semicolon input on the new candidate |
| SQLFluff-1625 | Valid concern v1 remains unresolved in final input; finish says resolved | Issue query/dialect variants; patch lacks the dialect guard claimed in the finish explanation |
| SQLFluff-1763 | Changed to pre-encoding validation; 146 tests pass | Original-file bytes remain intact after a real encoding error |

SQLFluff-1517's pre-edit failure was still delivered as a historical observation.
SQLFluff-1625's concern was successfully stored and remained unresolved. These
cases weaken a generic context-loss explanation: information delivery alone did
not produce appropriate verification or a sound submission explanation.

The supplement makes the same problem especially clear. SQLFluff-1733 reproduced
the nine-space CTE indentation before editing. Its first patch caused KeyError in
three existing tests; the next patch fixed that regression and all 506 tests passed.
The plan narrowed from the original indentation bug to fixing KeyError, then said
passing the recheck would finish the fix. No post-edit probe tested the CTE input.

At its final input, the original issue, historical probe findings and recent probe
outputs were delivered; run_probe and run_tests remained available. It had 609
solver seconds, five model calls and approximately USD 0.303 left before the final
call. A global resource closure was not the recorded cause of choosing finish.

Its two attempts to store concern v1 were rejected as unknown_concern_id: creating
a new concern requires null. The receipt explained the correction, but the agent
repeated the ID and stored no concern. This is recoverable interface friction,
not evidence of a missing issue or corrupted memory. SQLFluff-1625 independently
shows that successfully retaining a concern is not sufficient either.

The final completion guidance explicitly distinguished submission eligibility from
untested behavior, while its structured next_action suggested finish_task. This
is a plausible competing completion cue, not an established cause. Existing
brief-plan instructions already say unresolved requirements survive unrelated
PASS results. Another generic reminder is not a new evidence-based intervention.

## A concrete output-contract miss: SQLFluff-2419

The public issue explicitly illustrates `Use 'COALESCE' instead of 'IFNULL'.`
and the corresponding NVL message. The old successful and new failed candidates
differ only in the dynamic description expression:

| Candidate | Description expression |
| --- | --- |
| Previous PASS | `f"Use 'COALESCE' instead of {context.segment.raw_upper!r}."` |
| Supplement FAIL | `f"Use ``COALESCE`` instead of ``{context.segment.raw_upper}``."` |

The new expression introduces double backticks where the task shows single quotes.
This is a directly observable mismatch to the public example. Both runs passed
the public regression check and neither examined/asserted the actual messages.
It is the visible candidate difference and a strong diagnostic lead, but no hidden
failure cause is inferred and no counterfactual replay was executed in this review.

## Priorities and what would change the decision

1. **Close the already-known behavior on the current candidate.** First diagnose
   saved failures with the exact already-authored public reproduction on the
   submitted patch, particularly SQLFluff-1517/1733. This is a proposed bounded
   provider-free follow-up, not an execution performed here. If it still fails,
   task verification could have falsified submission; if it passes, examine a
   different public boundary rather than merely requesting more probes. Measure
   candidate defects found and corrected, not probe counts. A regression test,
   selected test or probe may supply the evidence; blanket automatic replay is
   not justified by these traces.
2. **Keep task correctness distinct from submission eligibility.** Trace the exact
   expected input/output through edits and unrelated regression repairs. For a
   proposed intervention, consider removing the unconditional finish suggestion
   before adding another plan, model reviewer or gate. Compare that narrowly
   against the existing guidance only after confirming the saved-case gap. Retain
   current limits; a different next-tool choice alone is not success evidence.
   Exact message assertions for IFNULL and NVL are a concrete public case; do not
   invent expected strings for ambiguous tasks such as Astroid-1268.
3. **Reduce demonstrated interface friction with focused local work.** Make a
   rejected pytest.param test easy to express as an allowed literal case or
   independent test. Make new concern creation versus existing-ID update harder
   to confuse. Test these exact public examples provider-free before changing the
   API or admission rules. Preserve existing-test protection: SQLFluff-1625's
   rejected fail_str-to-pass_str fixture rewrite was correctly blocked.
4. **Turn inspection into discriminating evidence.** Searches nearly doubled on
   matched tasks, while selected tests remained unused. The search optimization
   fixes latency, not choice of investigation. Prioritize a concrete unresolved
   input/output distinction after enough source evidence exists; do not impose
   an arbitrary read cap. More context or notes is not supported as the primary
   remedy when relevant observations were already delivered.

Keep the successful source-ownership diagnosis, regression repair loop and search
fix. Do not automatically expand the panel, increase budgets, adopt a mandatory
probe gate, change the baseline or execute a paid follow-up. Runtime policy changes
and actual improvement from these proposals remain untested.

## Evidence and validation

Analysis root: C:/pt/analyses/trace-compare-20261006-v1.

- execution/execution-comparison.json: all 42 run journals/envelopes, panel and
  paired counts, tokens, action intervals and rejection summaries; hashes retained.
  Intervals are unioned within a task, then summed; these are not panel wall time.
- execution/conditions-comparison.json: actual first-input task and repository
  identities, public capability declarations and changed check wrapper.
- gains/public-trace-evidence.json: exact actions, plans, checks and hashes for
  the six gain-task runs.
- gaps/prior.json, gaps/current.json, gaps/context-summary.json and
  gaps/verification-findings.md: fourteen failed-task traces and final tool/context
  delivery; detailed action IDs and journal sequences.
- supplement-evidence.json: SQLFluff-1733 corrected/supplement and SQLFluff-2419
  previous/supplement public actions, final delivered context and rejected receipts.
- final-context.json: exact final delivered completion guidance, budgets, plan,
  notes and probes for supplement SQLFluff-1733. Input artifact hash is verified.
- Existing [panel report](2026-10-06-corrected-dev20-results.md) and
  [search supplement](2026-10-06-search-once-supplement.md) retain original metrics.
- New evidence is external and immutable, with append-only hash-chained analysis
  journals. Documentation validation and the final commit are bound in closeout.json.
  No runtime source changed; no solver/evaluator test or live execution was needed.
