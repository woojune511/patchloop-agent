# Delivered counterexamples that remain unresolved: eligibility audit

Date: 2026-09-30. Read-only, provider-free follow-up to the
[N1 evaluation](2026-09-30-observation-n1-saved-patch-evaluation.md).
Question: which saved trajectories actually show a delivered public counterexample
remaining in the submitted patch, and where does the evidence-to-action link break?

## Scope and stricter eligibility

Rechecked the [45-run inventory](2026-09-29-cross-task-evidence-action-audit.md) and
the [56 deduplicated unsuccessful optional probes](2026-09-29-optional-probe-survey.md).
Verified hash chains and frozen source hashes for 95 distinct journal files in their
union. Copies, inherited prefixes and shared trajectories are not independent runs.
This is a bounded saved-evidence inventory, not a census of all failures.

A positive failure case needs all four:

1. A public requirement and applicable observation establish a candidate mismatch.
2. That observation reached the agent while it described the current candidate.
3. A meaningful opportunity to investigate or repair followed delivery.
4. The same behavior is still wrong on the final candidate, established by public
   evidence, not just a private evaluator FAIL or lack of a later probe.

This rule distinguishes unresolved product behavior from unfinished experiments,
post-run discoveries, resource-censored prefixes and successful repairs. Failure to
qualify does not prove the candidate correct or that the observation was irrelevant.

## Cases and counterexamples to a broad diagnosis

| Case | Evidence after delivery | Eligibility / implication |
| --- | --- | --- |
| HF seeded B2 | Exact contrary feedback in all three inputs; no edits; final unchanged patch fails the same frozen public probe | Confirmed unresolved delivered counterexample |
| HF seeded B1 | Same initial feedback; targeted inspection and three edits; final frozen probe PASS | Positive repair contrast; its residual private FAIL is a separate unknown |
| tox T2 | Publicly applicable missing-default regression; next decision explains the cause and next edit narrows the handler | Responded and repaired; not an ignored-counterexample example |
| AnyIO N1 A/B | Selected probe setup mismatch not handled; competing lifecycle defect repaired; saved patches pass task v3 | Target non-response is not demonstrated task failure |
| pyfakefs registered failure | Broken-symlink regression leads to narrower exception handling and same-check PASS | Positive registered-check recovery |
| toqito final probe | Syntax error acknowledged; no candidate behavior executed; later operator discoveries were not delivered | Unfinished verification, not proof of a delivered defect remaining |
| Pydantic / earlier HF / PDM operator replays | Public discriminating cases executed after the original episodes | Useful coverage evidence, not ignored in-episode observations |

HF A1/A2 received the program and expectations but not the executed counterexample's
stdout; they do not satisfy the same delivered-observation criterion. Response-only
ablation choices likewise cannot prove eventual abandonment without executed follow-up.

### Broader optional-probe screen

The 56 outcomes include 31 import/setup/syntax/API/inspection/sandbox failures,
two numerical expectation disagreements, two candidate-execution TypeErrors, one
tox fallback mismatch, and 20 lifecycle/execution outcomes with unresolved public-path
applicability. These categories describe evidence, not 56 product defects.

For the 20 lifecycle/execution outcomes (14 source journals), 16 had later valid
decisions and accepted edits. Four had no later valid action: three cost-cap stops
and one incomplete response. None is an unchanged submitted candidate supported by
a same-behavior final replay in this audit. Later editing does not prove resolution.
One apparent AnyIO failure actually runs only asyncio/ContextVar code to investigate
cross-task generator behavior; it never imports the candidate. Its exception can
inform a design decision without establishing a candidate bug (screen index 48).

All 11 registered-check failures from the earlier inventory still link to later
same-check PASS: HF six, AnyIO four, pyfakefs one. Blocking submission rules and
selection of completed trajectories confound channel comparisons; this does not
justify making every optional experiment mandatory.

### Newly traced tox continuation

The real tox CLI applicability check was already saved in the
[restoration record](2026-09-29-optional-probe-restoration.md). This audit follows the
original seeded trajectory beyond that checkpoint:
`C:/pt/change-review0925a/TA/runs/run_dev_a70238e212334718.jsonl`.

At 64 the probe returns empty for `[source]missing:fallback`. At 74 the agent explicitly
attributes this to catching SectionProxy lookup KeyError together with factor-filter
KeyError. The edit succeeds at 79, moving missing-key lookup outside that handler.
Registered regression passes at 94 and submission completes at 109. No later replay
of the exact discriminating probe appears, so this is a supported interpretation and
targeted repair, not proof of agent-performed verification of that exact case.

## HF B2: localization and remaining alternatives

Reconstructed all 17 B1/B2 inputs under the current reader and matched their exact
input and feedback hashes to the saved decision audit. B2's turns at sequences
12/26/41 all contain current-candidate feedback, including actual/expected ambient
client routes. Its final patch hash remains the seed hash, and the saved final frozen
probe fails the same ambient-client distinction. No new probe was executed here.

B2's observable sequence is contract check -> regression check -> submission.
After the first PASS, it carries check success into notes and retains only the
remaining regression question; it never records a verification concern or explains
why the contrary observation can be dismissed. The finish decision says no concrete
public uncertainty remains. This is not simply a one-step ordering choice: the episode
ends with the same public mismatch. Before finish it has 38 calls, 98 actions,
three edits, 846 seconds and USD 1.935501 left; reads/search/probe are available.

| Explanation | Evidence / status |
| --- | --- |
| Observation dropped from input | Ruled out for B2 by three exact input reconstructions |
| Hard resource or tool closure forced finish | Ruled out for this episode; editing first needed a source anchor obtainable by a read |
| Could not produce any repair from such observations | Too broad: B1 and tox provide contrary examples |
| Overextended registered-check PASS to the untested case | Compatible with plans and final closure; public statements do not prove the internal interpretation |
| Operator evidence received lower authority / insufficient attention | Plausible; the source label is explicit, but this is not a demonstrated causal effect |
| Completion recommendation caused abandonment | Still possible in a broader sense; prior latest-recommendation ablation showed 1/3 versus 1/3, not a supported fix |

The narrow supported failure is **failure to reconcile a current contrary observation
with the submission decision**. The records cannot uniquely separate semantic
interpretation, evidence weighting and action priority. Recognizing the abstract
explicit-endpoint requirement in a plan does not demonstrate applying it to the
observed ambient-client case.

The system represents these channels differently: operator_public_feedback is
current and present, while current_public_failure is null and verification concerns
are empty. The current gateway derives active failure from registered checks and
ready_to_submit from diff/check eligibility; the diagnostic feedback overlay is
separate. This is a concrete representation asymmetry, not a missing-payload bug
or proof that a new blocking gate will improve task solving.

## Decision and next discriminating question

Only HF B2 satisfies the full unresolved-delivered-counterexample criterion in the
reviewed evidence. This is one seeded episode on one task, not a cross-task failure
rate. The wider screen adds positive response cases and exclusions, not evidence
for a universal failure to remember or react to unsuccessful tools.

Keep the baseline. Before choosing a correction, distinguish whether an agent can
correctly judge that the supplied observation and registered PASS cover different
cases, and whether that judgment changes its next action/submission assessment.
Correct judgment with unchanged premature closure points toward action priority;
incorrect judgment points toward applicability/coverage interpretation. This is a
future diagnostic question, not an implemented gate or an authorized paid experiment.
Do not repeat the latest-recommendation ablation or expand a memory mechanism merely
because it is available. Any future comparison must preserve source provenance and
must not relabel operator feedback as an agent-executed registered check.

## Evidence and validation

New packet: `C:/pt/analyses/retained-counterexample-audit-20260930-v1`.
`audit.py` and `audit.json` bind all source hashes, all 56 screen entries and their
later public decisions/actions, the 11 recovery links, and 17 exact HF inputs.
A dev-run-v1 hash chain binds the audit artifact. Source files were checked unchanged
after extraction. No model credentials, private test definitions or reasoning content
were read. No model, task tool, Docker, private evaluator or new performance run was
executed; provider cost is zero. Runtime and closed historical records are unchanged.
`verify_hf.py` and `hf-final-verification.json` independently bind the final public
probe results to the old audit journal, verify the identical probe program, compare
actual/expected routes, and confirm B2's feedback/current/submission diff continuity.
Documentation layout/link tests and diff checks validate this documentation-only
follow-up; the runtime suite and mock smoke were not repeated.
