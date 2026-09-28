# Plan-to-condition public trace audit

Follow-up to the [pre-edit experiment](2026-09-28-pre-edit-issue-focus-results.md).
Question: was the incorrect applicability condition already present in the inherited
plan, or introduced only while editing? This is an offline audit, not another paid
comparison. No runtime change, model call, sampled tool execution or evaluator run.

## Evidence boundary

Audited Pydantic PA1 calls 1-5, HF Hub HA1 calls 1-9 and Fromager FA1 calls 1-2,
the same public dev-train sources as the experiment. All sixteen actual saved inputs
passed native/segmented projection verification. For each turn, the input plan text
matched the previous recorded plan; the recorded output plan exactly matched the
model's first non-null public plan_update, or retained the previous text when null.
There was no observed semantic rewrite or loss of plan text in this trace segment.
Original issue text was present in the reconstructed public inputs.

The current working_plan implementation agrees with that contract: record stores
the first non-null whole-text update, while project copies the latest plan and adds
currency/review metadata. Plans are labeled model_authored_unverified. Current code
alone is not evidence about old execution; the saved-input checks above establish
the observed historical delivery. Encrypted continuation remained opaque.

## Findings

| Case | Earliest relevant public statement | State at selected mutation | Interpretation |
| --- | --- | --- | --- |
| Pydantic | Call 1 plan proposes empty-field insertion for field mode, preserving non-field modes/providers | Revision 1 unchanged through call 5; no working-note findings | Provider-profile applicability was already broadened in the first plan |
| HF Hub | Call 1 correctly retains calls without an explicit endpoint; call 4 question shifts to whether wrappers forward self.endpoint | Call 9 input has plan revision 4 plus note n2 about omitted forwarding | Preservation wording survives, but its implementation condition is not resolved |
| Fromager | Call 1 plan distinguishes newly parentless descendants from surviving-parent references and unrelated orphans | Same plan feeds call 2; code queues newly parentless children | Successful control preserves the distinction from requirement to plan to code |

Pydantic's issue requires a provider-carried behavior that survives profile reuse
and copying, while other profiles retain existing behavior. The first plan instead
says to patch the serializer so field mode inserts the empty field, preserving
non-field modes/providers. It does mention inspecting the DeepSeek profile, and
call 2 explicitly considers profile reuse rather than provider-class checks; the
missing distinction is between the opted-in provider profile and other field-mode
profiles. Calls 2-5 use null plan_update. The first edit follows that broad condition.
Thus the hypothesis was already incomplete before the observed source inspections;
the audit cannot establish that persisting the plan caused the later edit.

HF's preservation clause was never simply dropped from the inspected plan revisions.
The open question at call 4 asks whether HfApi.hf_hub_download passes self.endpoint
while the metadata wrapper does not. At call 5 the model writes note n2, stating
that the download wrapper forwards self.endpoint whereas metadata omits explicit
endpoint context. Its citations show delegation, not the provenance of the value.
The first parser edit correctly accepts an optional endpoint. Later plan revisions
and public-check feedback focus on remaining missing forwarders. Call 9 input is
revision 4; revision 5 and the unconditional self.endpoint edit are produced together
at call 9, so revision 5 must not be treated as an earlier causal input.

The public HfApi constructor resolves omitted endpoint to constants.ENDPOINT at
line 1708. That line is outside the hf_api inline ranges in the selected checkpoint;
the delivered snippets focus on wrappers and delegation. This bounded coverage
observation is not a claim that no earlier/native input could contain related facts.
The observed gap is checking whether the value retains explicit-input provenance,
not remembering the sentence about preserving omitted-endpoint callers.

## Implication

These traces narrow the engineering target to the semantic use of public evidence:
Pydantic broadens a condition while drafting a plan; HF retains the requirement but
treats forwarding a resolved value as satisfying it. Plan storage/projection did
not alter the inspected plan texts. This rules out that particular delivery failure
for these turns, not all harness faults or a general model-only explanation.

The previous response experiment fits this distinction: one Pydantic B response
recovered the profile opt-in distinction despite the inherited plan; HF's A/B
responses remained focused on forwarding. That does not measure how much the plan,
notes, native continuation or feedback contributed separately.

Do not adopt plan deletion or add a new mandatory gate from this audit. A causal
test of plan influence would need to control its repeated public occurrences in
prior function arguments/results as well as working_plan, and explicitly retain or
vary native continuation. Removing only the latest projected field tests that field's
incremental exposure, not whether the agent can escape its prior hypothesis. Choose
and label that estimand before another paid run; keep successful controls.

## Artifacts and verification

External evidence: C:/pt/analyses/plan-condition-audit-20260928-v1/
public-timeline.json and verification.json, bound by the append-only, hash-chained
run_dev_planconditionaudit journal. Sixteen input and plan-transition checks passed;
source journals were hash-checked unchanged after analysis. New provider cost $0.
This is documentation/evidence work; runtime tests, Ruff and evaluator smoke were
not rerun because no executable repository code changed. Task acceptance remains
NOT_RUN for this audit. Historical records and frozen experiment inputs are unchanged.
