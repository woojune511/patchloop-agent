# Requirement-evidence judgment: bounded comparison results

Date: 2026-10-16. Allocation closed at **USD 4.346523 of USD 19.20**.
All sixteen fresh solves submitted. Previous B and current C each accepted 0/8.
C made one additional post-PASS probe and search; neither version made a post-PASS
edit. All runs are development-exposed, official=false and claim-ineligible.

## Question and decision

The [previous comparison](2026-10-16-submission-assessment-results.md) found seven
assessment-only exits in B. The [public exit audit](2026-10-16-assessment-exit-analysis.md)
identified unfinished verification plans and regression PASS treated as stronger
evidence than it supplied. This matters because an explanation can describe an
insufficient completion judgment without changing the resulting repair.

The user approved the [new protocol](../../.agent/assessment-gap-comparison.md):
compare previous B with guidance that connects public requirements to evidence,
retains unfinished verification, and requires a reason that remaining gaps do not
affect completion. It adds no mandatory probe, extra model call or semantic gate.
The question was whether that standard changes actual verification/repair and
independent acceptance. Already-sufficient verification, explanation-only closure,
resource limits and extra verification without a correct repair were alternatives.

The prespecified quality criterion was not met: acceptance stayed 0/8 versus 0/8,
with no late repair. There is one observed additional-verification trajectory in C,
but no established reliable increase or quality gain. The requested judgment contract
remains implemented; this result adds no forced action, runtime change or paid follow-up.
Unused funds do not authorize another experiment. The unresolved issue remains the
sufficiency of requirement-specific evidence, including unsupported closure of plans.

## Frozen scope and preparation

| Version | Frozen commit | Launcher arm |
| --- | --- | --- |
| Previous B | `a18976699ed16533516b4347df935e0dea51d161` | A |
| Current C | `b34e911d88acab74e431120c8e39760cc2656c25` | B |

The reused launcher calls these arms A/B; this report calls the versions B/C.
Thus report row C2-19 is raw artifact row `B2-19`, and report B2-19 is raw `A2-19`.
The manifest binds that mapping. Historical B runs are not pooled with this fresh B.
C bundles the five runtime files changed by the guidance commit; it is exposed from
the start, so effects before and after first PASS must be distinguished.

- Exact `tasks/dev-train/current-dev20/{7,10,13,19}/public.yaml`: pydicom-1139,
  pydicom-901, astroid-1333 and sqlfluff-1763; two fresh solves per task per version.
- `gpt-5.4-mini-2026-03-17`, xhigh, desired output 25,000, standard/global;
  credential path `C:/Users/geonj/Documents/PatchLoop/.env`.
- Current policy, segmented-v1, result-or-size-v1, brief-v1, 24K retained source,
  probes enabled, probe-policy/recheck none, repair-recheck, protected-v1, per-call-v1.
- Each row: USD 1.20, 40 model calls, 100 actions, four accepted edits and 1,800
  seconds including a 330-second registered-evaluation reserve. Two workers; waves
  previous-B1, current-C1, current-C2, previous-B2. Native grading retains its separate
  600-second bound. No transfers, replacement rows, retries or resume.
- Equal task packages, prepared source/dependencies, existing image identities and
  native grader bindings. Fixed worktrees and isolated imports protect the comparison
  from unrelated changes to the main checkout. No historical patch or outcome,
  comparison protocol, private test or reference patch enters solver context.

Manifest:
`sha256:c6347da2905205d1d2e465e84f1ec4aff027f036f4f627834fc2446c4beaf0a1`.
Exact human approval was bound before dispatch. Preparation verified clean tracked
runtime/task files and raw HEAD byte equality, two-arm environment identity, mock
submissions, actual two-worker import origins, and all four public import/operation/
selected-test canaries. The new checkout's two dependency files were restored from
CRLF checkout conversion to exact HEAD bytes; refreshing their index left no diff.
The unsuccessful intermediate inspections remain preserved beside the successful one.

Preparation tests: 69 PASS in 26.71 seconds, including 64 builder/launcher/observer/
replay/postprocessor tests and five documentation checks. Both exact-arm mocks reached
isolated EVALUATOR_PASS at zero cost. Ruff passed with formatting-only exclusions
for inherited inspector I001/E501 and the freeze helper's exact approval quote E501.
Prices matched the [official model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini).
No evaluator image was pulled or built. Final preflight passed before paid launch.

## Execution, behavior and correctness

All sixteen rows completed registered and native grading. All final public checks
and safety states are PASS. Both acceptance paths returned FAIL for every row and
agreed; ERROR and NOT_RUN are zero. Grader agreement checks harness consistency,
not two independent datasets. Billing, input counting and cleanup are known for all
rows. No stop condition fired. The live panel took 2,203.218 seconds (36m43s), including
wave preflight and final native grading, excluding preparation and offline analysis.

| Measure | Previous B, 8 runs | Current C, 8 runs |
| --- | ---: | ---: |
| Final public PASS | 8/8 | 8/8 |
| Independent acceptance PASS / FAIL | 0 / 8 | 0 / 8 |
| Assessment present | 8/8 | 8/8 |
| Only finish action after first PASS | 8/8 | 7/8 |
| Runs with actual verification after first PASS | 0/8 | 1/8 |
| Post-PASS probes / searches | 0 / 0 | 1 / 1 |
| Post-PASS attempted / accepted edits | 0 / 0 | 0 / 0 |
| First-PASS and final patch identical | 8/8 | 8/8 |
| Pre-PASS probes: executions / exit zero | 3 / 2 | 1 / 1 |
| Pre-PASS runs with a probe | 2/8 | 1/8 |
| Runs changing test files, before first PASS | 4/8 | 2/8 |
| Accepted edits, all before first PASS | 13 | 11 |
| Model calls | 117 | 123 |
| USD | 2.11196805 | 2.23455495 |

There were no separate selected-test calls in either version. A changed test file
does not establish test execution: previous B1-10 added a test in test_filereader.py,
while its required check selected test_misc.py and test_dataset.py. Probe exit zero
is an execution result, not a task-correctness verdict. One earlier B probe exited
one; it was neither a transport nor cleanup failure. The pre-PASS counts do not
show a general increase in verification in C. C cost USD 0.12258690 more in this panel;
the small sample does not establish a general cost effect.

| Task | Previous B acceptance | Current C acceptance |
| --- | ---: | ---: |
| pydicom-1139 | 0/2 | 0/2 |
| pydicom-901 | 0/2 | 0/2 |
| astroid-1333 | 0/2 | 0/2 |
| sqlfluff-1763 | 0/2 | 0/2 |

First PASS means healthy required-check receipts on the same nonempty candidate.
After every solver/provider activity closed, the observer reconstructed all accepted
mutations and verified each intermediate diff hash. All first/final patches matched,
so sixteen first-PASS candidates reused their own bound final grading receipts.
All transitions are FAIL-to-FAIL; additional candidate evaluations are zero. The
changed-candidate replay path was locally tested, not exercised by this live panel.
All final candidates retained public PASS. Because no post-PASS edit occurred, this
panel did not exercise rechecking a later edit or demonstrate a late repair.

## Actual exposure and completion decisions

All eight C runs received the new requirement/evidence and unfinished-verification
instructions in their saved post-PASS requests. Artifact SHA256, canonical request
hash and provider dispatch were checked. Their public state requested plan review,
offered probe/selected-test/edit tools, and left exploration and protected mutation
completion available. At first PASS C retained 7-34 calls, 2-3 edits, at least
USD 0.62883930 and at least 1,115.690 solver seconds. These are durable time bounds,
not exact instantaneous measurements or guarantees about future provider availability.
Missing guidance or forced resource closure does not explain the seven immediate exits.

Each immediate exit still used a new model decision and assessment. It is not evidence
that the model did no internal deliberation. The public declarations show why it
treated the existing evidence as sufficient; their validity is a separate question.

| C row (raw row) | Public trajectory and completion judgment | PASS / finish sequence |
| --- | --- | --- |
| C1-7 (`B1-7`) | Added and ran a membership regression test. Assessment treated wider iterable behavior as unnecessary despite the public title. The membership test plan was completed. | 153 / 168 |
| C1-10 (`B1-10`) | Planned a fresh-import logger test; test mutation rejected at 148 for altering existing test/import/helper structure. Plan 158 reduced remaining work to regression PASS. Finished using source removal as sufficient evidence, without a replacement test or probe. | 162 / 177 |
| C1-13 (`B1-13`) | Baseline probe 173 observed directory-loading errors. Plan 444 promised a manager regression test, still visible at finish, but only manager.py changed. Assessment asserted the full suite directly exercised the changed path without issue-specific post-edit evidence. | 461 / 476 |
| C1-19 (`B1-19`) | Changed the unknown-encoding fallback to UTF-8. No focused failure/file-preservation check; assessment treated that branch as the failure point and suite PASS as enough to close the gap. | 262 / 277 |
| C2-7 (`B2-7`) | Added and ran membership/iteration assertions. The requested direct test plan was completed before PASS; extra verification was not a quota. | 93 / 108 |
| C2-10 (`B2-10`) | Source-only logging changes and regression PASS; no direct logger-state test/probe. Assessment considered source behavior sufficient and remaining coverage uncertainty non-material. | 129 / 144 |
| C2-13 (`B2-13`) | Plans 13/32 promised a regression test, then plan 267 replaced it with suite verification only. No test/probe was added. Assessment said the concrete failure no longer reproduced based on suite PASS. | 272 / 287 |
| C2-19 (`B2-19`) | Revisited file preservation after PASS; ran a failure-path probe, searched existing tests, then finished without another edit. | 153 / 195 |

The astroid coverage/reproduction claims exceed the delivered evidence; unknown
coverage does not prove non-execution, but regression PASS alone does not establish
those claims. These observations identify continuing completion-judgment gaps, not
the private cause of each FAIL. The PN rows also show why an immediate exit cannot
automatically be classified as an invalid process: targeted tests had been completed.

C2-19 is the one observed continuation. Its earlier plan 121 promised a file-preservation
test, then plan 149 said PASS would leave only a summary. After PASS 153, actual request
156 (provider dispatch 161) led to decision 163: the regression suite did not settle
whether a failed write preserved the original file. Probe result 167 used cp1252 and
an unencodable arrow; it caught UnicodeEncodeError and observed `after: ORIGINAL`.
All five supplied comparisons matched, exit code was zero, and there was no timeout,
truncation or cleanup failure. Test search completed at 181; finish at 195 cited
the new observation. This is real verification of that constructed failure path,
not merely an assessment promising one, and it supplied evidence for the earlier
test's purpose. It did not change the patch or independent acceptance.

The same broad pattern (one SQLFluff continuation and seven immediate exits) appeared
in historical B. That older evidence is not pooled into the fresh control, but it
limits a claim that this behavior is new or uniquely caused by C. With two samples
per exposed task, the observed 0/8-to-1/8 difference cannot establish a reliable
behavioral effect, statistical significance, generalization or held-out performance.

## Evidence and closeout

- `C:/pt/assessgap16prep01/`: frozen manifest/approval, inspections, readiness receipts,
  tests, and execution/observer helpers. `final-preflight.json` precedes live launch.
- `C:/pt/assessgap16live01/result.json`: sixteen settled rows, final registered/native
  verdicts, and known accounting; per-row journals remain hash-chained and unchanged.
- `C:/pt/assessgap16post01/closure.json`: reconciled solver/provider closure with
  matched count/dispatch receipts and source journal/envelope hashes.
- `C:/pt/assessgap16post01/result.json` and `summary.json`: reconstructed candidates,
  receipt reuse, per-row/version/task metrics and separate evaluation states.
- `C:/pt/assessgap16post01/public-evidence.json`: actual public inputs, decisions,
  plans, actions and check observations; `derived-findings.json` binds input exposure,
  resource bounds, timing and aggregate calculations to those source hashes.
- `C:/pt/assessgap16prep01/closeout.json`: final evidence/report hashes, also recorded
  in the append-only preparation journal. Historical assesscmp16 evidence is unchanged.

No additional solver, paid judge or offline candidate evaluation was run after live
closure. No private specifications, reference patch or individual hidden-test detail
was read for the public trajectory analysis, and no provider reasoning/continuation
content was analyzed. The report concerns observable decisions and bounded outcomes.
No runtime source changed in this turn. Final documentation checks passed 5/5 in
0.17 seconds; operator-only audit/closeout helpers passed Ruff. Historical integrity
verification matched all eleven prior closeout-bound files and sixteen original
helper hashes. The full runtime suite was not repeated for this evidence-only change.
