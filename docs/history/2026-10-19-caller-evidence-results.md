# Exact caller evidence at a saved Astroid failure: A/B results

Date: 2026-10-19. Twelve paid continuations and all permitted submitted-patch
assessments completed. Allocation closed; official=false, claim_eligible=false.

Supplying the exact public caller observation produced relevant initial
investigation in all six B continuations, but did not produce a successful repair:
S, T and Q were **0/6 in both arms**. Five patches per arm were submitted; every
submitted patch failed agreeing registered/native acceptance and the original
public caller case. All ten normal controls passed. The two cost-stopped rows
were unsubmitted and remain NOT_RUN for repair assessment, not graded FAIL.

## Question, intervention and fixed conditions

Earlier Astroid-1333 failures left acquisition and evidence-conditioned judgment
confounded. This investigation supplied an already observed public caller failure
and control at exactly the same failed state, to distinguish initial delivery and
uptake from repair. The [frozen plan](../../.agent/plans/caller-evidence-checkpoint.md)
and [preparation](2026-10-19-caller-evidence-ready.md) remain unchanged.

- Execution commit: `0500869de1843fcd8146d1f668df15979fd3cac3`.
- Runtime: `sha256:90f3b4f2467cb802e89bd27997e69bc8233e041db18105c7f0a557b5586693f7`.
- Execution manifest: `sha256:fa8712802529d20f44b535940c4d691ac848cd48ef0274cd2032883c97aca95d`.
- Task: `tasks/dev-train/current-dev20/13/public.yaml`; source base
  `d2a5b3c7b1e203fec3c7ca73c30eb1785d3d4d0a`.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh; six continuations per arm, order
  A1 B1 B2 A2 A3 B3 B4 A4 A5 B5 B6 A6.
- Both arms restored `run_dev_f1a28479931d443f` through event 341 in the same
  Pylint-2.12.2-capable environment. A kept its original first input. B added the
  saved public caller program, actual arguments/environment, failure and control
  only to the first new input. Subsequent requests used ordinary context handling.
- Total limits stayed 40 model calls, 100 actions, four accepted edits and 1,800 s,
  including the inherited 330 s evaluation reserve. Remaining allowance was 16
  calls, 76 actions, four edits and about 1,200 s solving time. Segmented-v1,
  result-or-size-v1, two question references and 24,000 retained source characters
  stayed fixed; no cap transfer, retry, replacement, reinjection or new solver rule.
- Each row retained its USD 0.88 logical cap, including USD 0.37263270 inherited
  usage; new-row allowance USD 0.50736730. Approved new invocation cap:
  **USD 6.08840760**. Old debits were not charged again.

The immutable preparation manifest still says paid_authorized=false. The separate
`packet/authorized-inputs.json` and authorization journal bind this user's exact
approval and the dispatch-time price review; preparation was not retroactively edited.

## All assigned rows and outcomes

G concerns new model-initiated caller acquisition; supplied observations do not
count. D/J/action use below concern the first complete decision (event 352, request
350 in each row). `U` means UNKNOWN with inadequate original-caller evidence,
not an incorrect judgment. `S` means supported relevant investigation under the
frozen broad rubric, not proof of a correct fix. B4/B6 were less specific than
B1/B2/B3/B5, but relevant investigation without a prescribed phrase qualifies.

| Row | G | Initial D | Initial J/action | Submission | Registered/native | Missing/present caller | Q | New USD |
| --- | --- | --- | --- | --- | --- | --- | --- | ---: |
| A1 | Not acquired | Not supplied/acquired | U/U | Yes | FAIL/FAIL | FAIL/PASS | 0 | 0.36654270 |
| B1 | New caller execution* | Complete | S/S | No: cost cap | NOT_RUN | NOT_RUN | 0 | 0.48160410 |
| B2 | Not acquired | Complete | S/S | Yes | FAIL/FAIL | FAIL/PASS | 0 | 0.15985110 |
| A2 | Not acquired | Not supplied/acquired | U/U | Yes | FAIL/FAIL | FAIL/PASS | 0 | 0.25943625 |
| A3 | Not acquired | Not supplied/acquired | U/U | No: cost cap | NOT_RUN | NOT_RUN | 0 | 0.50468565 |
| B3 | Not acquired | Complete | S/S | Yes | FAIL/FAIL | FAIL/PASS | 0 | 0.35046060 |
| B4 | Not acquired | Complete | S/S | Yes | FAIL/FAIL | FAIL/PASS | 0 | 0.17656230 |
| A4 | Not acquired | Not supplied/acquired | U/U | Yes | FAIL/FAIL | FAIL/PASS | 0 | 0.34534335 |
| A5 | Not acquired | Not supplied/acquired | U/U | Yes | FAIL/FAIL | FAIL/PASS | 0 | 0.45523335 |
| B5 | Not acquired | Complete | S/S | Yes | FAIL/FAIL | FAIL/PASS | 0 | 0.27511575 |
| B6 | Not acquired | Complete | S/S | Yes | FAIL/FAIL | FAIL/PASS | 0 | 0.29457705 |
| A6 | Not acquired | Not supplied/acquired | U/U | Yes | FAIL/FAIL | FAIL/PASS | 0 | 0.30180405 |

*B1 wrote a new Pylint `Run` program after the intervention; it did not copy/replay
the supplied profiler. It obtained new current-patch F0010 counterevidence. The
question was informed by supplied evidence, so this is not unprompted discovery or
a treatment-independent acquisition contrast. Its Run API/nonempty child and lack
of a normal-control run also do not certify the entire frozen caller protocol.

Every submitted patch had a current-diff `base-regression` PASS and registered
safety PASS. Native evaluation used the full submitted patch; the two public caller
checks used the bound source-only projection with original tests restored. A1 was
tests-only, so its caller projection was the unchanged base. All 20 caller checks
and ten native evaluations completed without ERROR, disagreement or cleanup
uncertainty. Normal controls analyzed the real child; failed cases still emitted
F0010 and did not analyze it. S_B-S_A = T_B-T_A = Q_B-Q_A = 0.

## What the public trajectories establish

**Acquisition and initial transport.** No A continuation obtained the original
caller trace. A's namespace-helper observations did support continued investigation,
so its six ineligible J judgments must not be presented as six reasoning failures.
B's exact observation was present in every first actual dispatched request; all
six first request hashes matched the frozen B input. B1/B2/B3/B5 immediately focused
on `ast_from_file` or its missing-source fallback; B4/B6 investigated nearby loader
paths. The rubric counts all six as supported initial use. This is a permissive
action/scope measure, not a six-to-zero causal improvement in reasoning ability.

**Later delivery and provenance.** The packet did not disappear immediately after
the first response. It remained in historical observations throughout the first
segment, then its raw call/environment/control tuple left readable input at a
handoff. Exact tuple present/first absent request sequences were:

| B row | Last present request | First absent request |
| --- | ---: | ---: |
| B1 | 378 | 394 |
| B2 | 394 | 410 |
| B3 | 377 | 393 |
| B4 | 421 | 437 |
| B5 | 390 | 405 |
| B6 | 406 | 425 |

Notes/plans retained different subsets. B6 still had an explicit plan for a missing
initializer, module name `project` and `source=True` at its final decision. B2/B5
initially attributed the supplied caller fact to the inherited helper action
`call_UDpHtAAOljgHmzsHSQgiM3sP`; that action did not establish the caller fact.
Those notes remained marked model_authored_unverified, but the citation was wrong.
After source edits, base observations were historical, not current candidate proof.

`retention-followup.json` records each request's omitted source ranges, source-note
delivery/currency and new probe-output retention for both arms. It verifies the 24k
ceiling and at most two selected call IDs per historical reference packet (each
reference expands to call/result entries). It does not equate a missing whole raw
output with loss of all relevant semantic facts or assert causality from omitted
lines. A never acquired the exact trace, so that absence is not retention loss.

**Judgment, verification scope and implementation.** Three examples distinguish
these failures from mere initial delivery failure:

- B3's probe decision 366 changed `sys.path` to include root/src while the original
  caller tuple was still present in request 364. Later it switched to directory
  source classification. Its finish decision 485 described a pre-edit namespace
  helper result as validation of the current patch. The helper's environment and
  currency did not support that claim.
- B5 initially recognized the absent-file/source=True path, then compared
  `ast_from_module_name` with different context_file values. Its positive helper
  test at decision 392 was chosen while the original tuple remained in request
  390. The final probe used a directory and default arguments, not the missing
  initializer / `modname='project'` / `source=True` call. It nevertheless claimed
  direct coverage of the reported failure. Later tuple loss can contribute, but
  cannot alone explain scope drift that had already started with the tuple present.
- B1's current-patch caller probe (action
  `call_NpQJFVqUfZNrSBesYaH2CKWv`, result 537) still emitted F0010. That output was
  delivered in request 544; decision 546 explicitly acknowledged that its patch
  was insufficient and continued investigation. It then hit the row cost cap.
  This is successful use of fresh counterevidence without a completed repair.

All ten finish claims exceeded demonstrated targeted verification, but they are
recorded as scope/currency overstatements, not automatically as strict OVERCLAIM
under the frozen requirement for current contrary caller evidence. A base failure
alone cannot establish that an edited candidate still fails. B1 was the only row
with fresh real-caller failure and a following decision, and it acknowledged it.

The common caller evaluations show two remaining mechanisms. Seven submissions
(A1/A2/A4/A5/A6/B3/B5) still attempted the missing initializer. B2/B4/B6 avoided
that file-open branch but fell back to an unresolved `project` module, producing
`No module named project` and F0010. Avoiding the first bad branch was insufficient
under the actual module name and path environment. Broad-suite PASS did not test
that claim, and helper success with changed inputs did not supply the missing proof.

## Cost, boundaries and validation

New settled usage was **USD 3.97121625**: A USD 2.23304535, B USD 1.73817090;
USD 2.11719135 of the invocation cap remained unused. There were 129 fresh input
counts, 123 dispatches and 123 usage records; every row's billed usage reconciled.
No paid retries, replacements or paid judges were run. B's first input had 32,294
tokens versus A's 26,708 (+5,586); both initially admitted 25,000 output tokens.
Output ceilings later shrank on three B1 calls, two A3 calls and one A5 call.
B1/A3 stopped at row cost admission, not a group billing/transport uncertainty.
Lower total B spend with zero repairs is not an efficiency improvement claim.

Execution used the previously validated commit: 5,382 full-suite passes/20 skips,
37 focused passes, Ruff PASS and mock isolated EVALUATOR_PASS. No runtime, oracle,
transition policy, reference limit or resource budget changed during this study.
Only this follow-up record, the history index and current status changed afterward;
documentation layout/link validation was run for that documentation-only change.
Fourteen bound historical/source/user-edit inputs retained their hashes. The user's
existing `AGENTS.md` edit remains untouched and outside this commit.

Public annotations were sealed before new registered/native/postrun grades were
opened. **Semantic review was performed by one Codex assistant operator, not a
human or independent reviewer. Human semantic review is NOT_RUN.** Mechanical
validation checks lineage, not semantic correctness. Arms and historical outcomes
were recognizable; no blinding, significance, mediation or generalization claim is
made. The supplied environment is the controlled Python 3.9.25/Pylint 2.12.2 setup,
not every environment from the original report. A known-correct positive repair
calibration remains unavailable; normal controls and observed F0010 failures do
not establish sensitivity to every valid repair.

## Decision and durable evidence

Keep the baseline and close the allocation: the favorable local signal rule failed.
The result weakens the explanation that B failed simply because precise evidence
never reached the model. It supports a narrower bottleneck: the original call
conditions were not consistently carried into candidate verification, and partial
mechanism changes were treated as complete repairs. Later retention, interpretation,
implementation and available row budget remain entangled; this comparison does not
identify their separate causal effects or establish a general LLM capability limit.

The next useful question is local: can a candidate's verification be tied to the
same caller/arguments/environment and actual child analysis before a completion
claim, without treating a modified helper case as equivalent? This study does not
authorize another paid panel or adopt another prompt, retention rule or mandatory
gate. In particular, adding more context alone is not justified by these results.

Authoritative external evidence, preserved in place:

- `C:/pt/ce19ready/packet/manifest.json`, `authorized-inputs.json` and
  `runs/run_dev_callerevidence.jsonl`: scope, authorization, audit-before-grades and
  the hash-chained assessment/closeout record.
- `C:/pt/ce19ready/packet/annotations.json`, `audit-public/`,
  `retention-followup.json`: first and later public judgments, event/request hashes,
  material spans and both arms' retention inventory. The retention follow-up is
  explicitly post-grade descriptive work; sealed labels were not revised.
- `C:/pt/ce19ready/packet/result.json`, `assessments/`: all twelve denominators,
  bound submitted/source-only/native hashes, twenty public and ten native receipts.
- `C:/pt/ce19ready/packet/execution-analysis.json`, `execution-closeout.json`:
  per-row cost/tokens/caps, final identity and preservation checks.
- `C:/pt/ce19live/result.json`, `runs/run_dev_checkpointcomparison.jsonl` and arm
  directories: twelve immutable continuations and settled usage. The continuation
  manifest hash is distinct from the top-level execution manifest.
- `C:/pt/ce19ready/validation/validation.json`: pre-execution final-commit full
  validation. Post-study documentation checks are recorded separately.
