# Retained prior-decision comparison preparation

Provider-free derivative of the frozen evidence-context preparation v3. Uses its
four dev-train cases and public data only, without altering earlier artifacts.

New A equals the old reduced-context B. New B differs only by removing
data.evidence.recent_attempt_result_next_question[*].turn_decision objects. The
objects include prior public basis/plan_update, not private reasoning. Save removed
objects in an operator audit outside reviewer views; reinsert them to prove exact
structural reconstruction. Do not add omission banners, target hints or an answer key.

Keep the neutral reviewer question, all other fields, public task/check code, probes
and their questions/assertions, outputs/setup, source bodies, diff/action identities,
provenance, next_question and workflow state unchanged. Other framing deliberately
remains; neither arm is a claim of fully interpretation-free evidence.

Scan all nested containers and JSON-encoded strings for remaining turn_decision or
plan_update fields, plus whitespace-normalized copies of removed basis/plan text.
Reject preparation if copies remain; do not silently delete additional fields or
edit program/output strings. This detects these structural/exact-text duplicates,
not semantic paraphrases or every possible interpretation. Native probe questions
can encode hypotheses and are held constant as part of the observed experiment.

New files bind the source packet, source-view hashes, reconstructed receipts,
implementation and question. External immutable artifacts and a hash-chained
dev-run-v1 journal only. No credentials, API count/generation, tool execution,
evaluator, Docker, collector, live approval or runtime changes.

This preparation isolates removal of prior decision objects in these saved views.
It also reduces length and cannot separately estimate that effect. It does not
remove source-availability, task-interpretation or provenance differences across
cases. A future response comparison must hold other settings/schema fixed, use
fresh responses for both arms, and specify approval and scoring before collection.
Do not treat old B responses as newly sampled A responses. AnyIO's broad-question
setup omissions limit that case's discriminatory value; do not silently narrow
its question within this ablation or interpret omissions as incorrect beliefs.

CLI: python -m diagnostics.prior_decision_design prepare --source PATH
--source-hash SHA --root NEW_EXTERNAL_ROOT; validate --packet PATH.
