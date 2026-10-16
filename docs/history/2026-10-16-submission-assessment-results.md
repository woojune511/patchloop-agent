# Submission assessment: bounded comparison results

Date: 2026-10-16. Allocation closed. Every run is `official=false`, claim-ineligible
and development-exposed. No further paid run, retry, resume or budget transfer follows.

## Problem and question

Public PASS had repeatedly been followed by failed independent acceptance. The user
requested an agent-authored submission judgment after PASS, while preserving the
requirement that any subsequent edit receive fresh public checks before finish.
The question was whether this judgment produced additional verification or repair
and improved acceptance. Alternatives included assessment-only completion, an
additional check that did not resolve the task, and insufficient remaining resources.

The user approved the exact [proposal](../../.agent/submission-assessment-comparison.md):
four previously public-PASS/independent-FAIL tasks, two fresh runs per arm, USD 19.20
total. The proposal remains unchanged as a frozen design input; its earlier pending
approval text is superseded by this execution record and the bound approval receipt.

## Frozen conditions and preparation

- A: `7d483d239236df9a27f7542064ea6f46ec168396`; B:
  `a18976699ed16533516b4347df935e0dea51d161`. B bundles the required nonblank
  `finish_task.assessment`, prompt and completion guidance. No forced extra call.
- Exact `tasks/dev-train/current-dev20/{7,10,13,19}/public.yaml`, unchanged packages,
  prepared source/dependencies and existing pinned evaluator/probe images across arms.
- `gpt-5.4-mini-2026-03-17`, xhigh, 25,000 desired output tokens, standard/global;
  credential path `C:/Users/geonj/Documents/PatchLoop/.env`.
- Current policy, segmented-v1, result-or-size-v1, brief-v1, 24K retained source,
  ordinary probes/selected tests available, probe-policy/recheck none,
  repair-recheck enabled, protected-v1 and per-call-v1.
- Each fresh row: USD 1.20, 40 model calls, 100 actions, four accepted edits,
  1,800 seconds including 330 seconds reserved for registered evaluation.
  Native grading uses the existing separate 600-second subprocess bound.
- A1, B1, B2, A2 waves; four fixed tasks per wave, two workers. Independent states,
  no historical patch, comparison protocol, prior outcome or private oracle context
  supplied to solvers. No count/transport/billing/cleanup uncertainty or identity drift
  occurred; no retries, resumes, replacement rows or transfers were used.

Manifest:
`sha256:0c0324d149827fd7db13c289055ae54d3ee15aab095b315a177bb60a1d52c773`.
The exact user approval was bound to this manifest before dispatch. Preparation
verified raw HEAD/runtime bytes, clean task packages, isolated imports and real
two-worker origins. Both mock submissions passed. All four public import, operation
and selected-test canaries passed; A/B environment identities matched. No image
was pulled or built. New preparation checks: launcher 29, builder 15, observer/replay
6 and postprocessor 14 PASS. New helpers passed Ruff; the inherited inspector and
running canary retained only documented I001/E501 formatting exclusions.

Snapshot reconstruction was also checked against a real historical public trace,
without rerunning its solver or graders. Windows checkout newline normalization
was limited to restoring exact HEAD bytes in the two new worktrees.

## Results

All 16 intended solves submitted and completed both graders. All 16 final public
checks and safety verdicts passed; all 16 registered/native acceptance verdicts
were FAIL and agreed. ERROR and NOT_RUN are both zero. Cleanup and billing/counting
are known for all rows. Live panel elapsed time was 2,017.440 seconds, including
wave preflight and final native grading, excluding preparation/offline observation.

| Measure | A: before, 8 runs | B: assessment, 8 runs |
| --- | ---: | ---: |
| Final public PASS | 8/8 | 8/8 |
| Independent acceptance PASS | 0/8 | 0/8 |
| Independent acceptance FAIL | 8/8 | 8/8 |
| Finish assessment present | 0/8 | 8/8 |
| Runs with verification after first public PASS | 0/8 | 1/8 |
| Runs with attempted/accepted edits after first PASS | 0/8 | 0/8 |
| Only finish action after first PASS | 8/8 | 7/8 |
| Total accepted edits, all before first PASS | 13 | 13 |
| Model calls | 119 | 122 |
| USD | 2.13061335 | 2.16051420 |

| Task | A acceptance | B acceptance |
| --- | ---: | ---: |
| pydicom-1139 | 0/2 | 0/2 |
| pydicom-901 | 0/2 | 0/2 |
| astroid-1333 | 0/2 | 0/2 |
| sqlfluff-1763 | 0/2 | 0/2 |

Total cost was **USD 4.29112755 of USD 19.20**. B cost USD 0.02990085 more in this
panel. These two samples per task do not establish a general cost effect.

## What happened after PASS

First PASS means healthy receipts for every required public check on the same
nonempty diff. All accepted mutations were reconstructed from public journal
evidence, with every intermediate diff hash verified. First-PASS and final patches
were identical within every row. After all solver/provider activity closed, all
16 first-PASS candidates therefore reused their bound final registered/native
receipts. All transitions are FAIL-to-FAIL. Additional candidate evaluations: zero;
the changed-candidate replay path was locally tested but not live-exercised.

The one additional action was **B2-19**, run `run_dev_481902d63bc647af`. Automatic
repair recheck recorded first PASS at sequence 295. A subsequent model call at
302/303 selected a probe, completed at 309, followed by finish at 323. Thus this
was a choice after receiving PASS, not a previously admitted action in the same
batch. The probe exercised `persist_tree` with unencodable cp1252 output and observed
`False` with the original `SELECT 1\n` file contents preserved. It exited zero with
confirmed cleanup and no timeout/truncation. This is actual additional public
verification, but it produced no further edit and independent acceptance stayed FAIL.

The other seven B runs supplied an assessment then finished without another read,
search, probe, selected test, required check or edit. Their assessments often
acknowledged that verification was limited to the public suite. An assessment is
a declared judgment; it does not prove unobservable internal review or correctness.

Resource exhaustion did not force immediate finish: at first PASS all rows retained
at least seven model calls, one edit, USD 0.50474745 and 1,045 seconds of solver
time. B specifically retained 7-32 calls, 2-3 edits, USD 0.60465270-1.05986355 and
at least 1,105 seconds. Time values use durable elapsed-time bounds, not precise
instantaneous measurements. There were no mutations after PASS, so the obligation
to recheck a post-PASS edit was not exercised. B2-19 and A2-13 did repair earlier
public failures and obtain fresh PASS before submission; those edits precede first PASS.

## Decision and limits

The required assessment was exposed in all eight B submissions, and an additional
verification action was observed in one. The prespecified quality criterion was
not met: no acceptance gain, no late repair and no change in first/final correctness.
The requested judgment contract remains implemented, with no measured quality-gain
claim. This result does not justify forcing more actions, tuning the same cases or
automatically launching another comparison. A next investigation needs new evidence
about a concrete public failure mechanism. It remains unresolved whether this
contract helps different tasks or models; this selected four-task development panel
does not support significance, generalization or held-out performance claims.

## Immutable evidence

- `C:/pt/assesscmp16prep01/`: manifest, exact approval, inspections, environment and
  mock/spawn/canary receipts, validation and hash-bound execution/observation helpers.
- `C:/pt/assesscmp16live01/result.json`: complete 16-row results; per-row hash-chained
  journals and artifacts; wave-native assessments and panel closure.
- `C:/pt/assesscmp16post01/closure.json`: locked, reconciled solver/provider closure.
- `C:/pt/assesscmp16post01/result.json`: all 16 reconstructed observations and reused
  first-PASS grade receipts; `summary.json`: derived per-row/arm/task tables.
- `C:/pt/assesscmp16prep01/closeout.json`: final artifact hashes, also bound into the
  append-only `run_dev_assessmentprep` journal.

The unfrozen report-only emitter initially treated a non-action result string as
an action object. It was corrected to filter action events first; its original
source remains `summarize_comparison-v0.py`. No solver, probe or grader was rerun,
and no frozen input/helper or historical experiment was changed by that correction.
