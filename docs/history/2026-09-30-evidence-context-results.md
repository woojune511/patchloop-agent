# Evidence/context assessment: closed results

Date: 2026-09-30 KST. Execution commit b86bddc. official=false.
Follows [collector preparation](2026-09-30-evidence-context-collector.md) and the
[frozen rubric](../../.agent/evidence-context-sampler.md).

## Question and execution

Does removing surrounding plans, prior explanations and completion guidance improve
public-evidence assessment when the evidence itself is unchanged? A includes that
context; B omits it. Both are fresh reviewers with the same neutral question and
single non-executing report schema, not the original coding-agent requests.

The user explicitly approved the new USD 9 total cap for four dev-train checkpoints,
A/B twice each, gpt-5.4-2026-03-05 xhigh, exact repository .env and 30 minutes.
All 16 counts and generations completed in 892.478 seconds (14m52s), eight complete
pairs, no missing cells. All reports were schema-valid. No retries, corrective calls,
resume, tools, Docker, patch execution, evaluator or paid judge. Acceptance and safety
remain NOT_RUN; schema validity is not semantic correctness.

Current official Standard prices were reconfirmed on execution UTC date 2026-09-29:
input USD 2.50/M, cached input USD 0.25/M, output USD 15/M.
[Official pricing](https://developers.openai.com/api/docs/pricing).

## Masked review and results

Randomized public reports excluded arm, repeat/order, cost and latency. Grades,
response excerpts, omission rules and one borderline sensitivity were saved and
journal-bound before label reveal. The reviewer knew the cases and text can hint
at condition: informed arm-masked assessment, not independent blind evaluation.

Primary supported assessment requires supported identity, disposition and check
scope/uncertainty. An omitted target assessment is not_assessable, not proof of an
incorrect private belief. Counts below retain two planned responses per arm.

| Checkpoint | A: surrounding context | B: evidence only | Interpretation |
| --- | ---: | ---: | --- |
| C1 HF current counterexample | 1/2 | 0/2 | One borderline A response; strict sensitivity 0/2 versus 0/2 |
| C2 HF historical counterexample after edit | 2/2 | 2/2 | Current source mechanism supports resolution; no claim of exact rerun |
| C3 AnyIO setup/behavior distinction | 0/2 | 0/2 | Target setup observation omitted in all four, not demonstrated misclassification |
| C4 tox current missing-default discrepancy | 2/2 | 2/2 | Current targeted regression recognized despite registered PASS |

C1 paired results: tie, A win. All other pairs tie. No pooled task solve rate.
All 16 identify their cited current/historical candidates correctly. Check-limit
judgments pass 15/16; C1 B2 nevertheless elevates registered PASS above the current
counterexample. Correct identifiers and generic coverage caveats alone are insufficient.

### C1: correct observation, unresolved applicability reasoning

All four reports identify the same-candidate ambient HfApi diagnostic and distinguish
it from the registered checks. They also invoke its operator/model-authored and
unregistered status while leaving the no-explicit-endpoint interpretation uncertain.
Three do not retain an established relevant discrepancy or provide a requirement-
or source-grounded reason to reject its applicability. B2 additionally says the
stronger public evidence supports resolution for the candidate.

A2 explicitly says a relevant narrow discrepancy remains and confines resolution
to the visible checks. This receives the frozen primary pass: recognizing a relevant
discrepancy does not require asserting conclusive whole-task failure. It still leaves
applicability uncertain. Before reveal we recorded a stricter interpretation under
which this also fails. That yields 0/2 versus 0/2. Thus neither interpretation supports
B improvement, and the single borderline A win is not robust evidence of A superiority.

The public issue requires preserving callers without an explicit endpoint. The
registered client cases instantiate HfApi with an explicit endpoint; their PASS
does not decide the ambient/no-explicit-constructor case. Registration status alone
does not supply the missing behavioral argument. This is an observed assessment
pattern, not proof of an internal trust mechanism or a uniquely causal field.

### Controls: source-supported repair, missing assessment, current regression

C2 reports distinguish the old failing hash from the changed candidate, explain
the `_explicit_endpoint` propagation mechanism and limit check claims to exercised
cases. B2 most clearly says the exact ambient diagnostic was not re-executed; the
others provide generic case/coverage limits. We accept evidence-supported source
assessment without demanding a new run or a particular uncertainty phrase. No report
asserts that the exact old operator probe was rerun on the new candidate.

C3 reports assess the valid historical post_interrupt observation, earlier lifecycle
failure and current same-check PASS to varying detail, but none assesses the separate
wrapped_name setup failure. The broad review question did not force exhaustive
observation coverage. This control is therefore non-discriminating for setup handling;
do not interpret its zero primary count as four incorrect setup classifications.

C4 reports all connect the setup-passing current reduced probe and changed KeyError
handler to the public requirement preserving explicit defaults. They recognize that
the missing-key case returns empty rather than fallback, while showconfig PASS does
not cover that regression. Their conclusions remain bounded to the reduced exercise.
This shows that some targeted evidence judgments succeed in both contexts; it does
not isolate why C1 differs. Source availability, task wording and checkpoint stage differ.

## Implication and next question

Keep the runtime baseline. No surrounding-context removal, new prompt or submission
gate is justified. B reduces actual input tokens substantially but gives no supported
assessment advantage in this small exposed panel:

| Case | A input tokens | B input tokens |
| --- | ---: | ---: |
| C1 | 20,572 | 11,137 |
| C2 | 35,111 | 26,125 |
| C3 | 35,647 | 24,256 |
| C4 | 22,063 | 11,562 |

The result weakens the proposition that the removed context is sufficient to explain
these failures. It does not eliminate context effects: retained evidence still contains
mixed framing, and length/advice/history were removed together. Two repeats per arm,
different checkpoint stages and exposed tasks preclude generalization claims.

A useful next provider-free analysis would compare C1 and C4's requirement-to-
observation arguments and the framing that remains common to A/B. Distinguish missing
source, ambiguous interpretation and unsupported evidence weighting before proposing
another intervention. Do not infer that more reminders or wholesale context reduction
are the remedy, and do not automatically launch another paid experiment.

## Integrity, costs and artifacts

All 16 actual requests match their frozen cells; count inputs and dispatch hashes
match. Token/cached-token arithmetic reproduces each cost. All usage is known.
Original source journals/envelopes and preparation views remain unchanged. The
read-only report exporter initially rejected an output outside its artifact root;
the exporter was corrected before any report was written. No provider retry occurred.

Settled USD 1.138519; unused USD 7.861481 closed, zero authorized calls remaining.
Plan journal records allocation closure. No plaintext private reasoning was inspected.

- Plan/approval: C:/pt/analyses/evidence-context-collection-plan-20260930-v1.
- Live: C:/pt/context0930a/result.json, run_dev_sample_e0ebbf093af34202.
- Review: C:/pt/analyses/evidence-context-results-20260930-v1, including verify.py,
  integrity.json, masked-public.json, masked-grading.json, settle.py, summary.json,
  sensitivity.json and hash-chained run_dev_contextreview.
- Frozen grading SHA: sha256:b73101bb894108fc53533052e575583f214963ed099c66d5130169011910bb6e.
- Prepared collector had 68 focused tests, Ruff and actual-input mock passing.
  This result-only update passed five documentation tests and saved execution checks;
  it introduces no runtime code changes or new performance claim.
