# Observation retention comparison: frozen scoring and live contract

Question: does retaining a structured unsuccessful-execution catalog improve the
connection between observed failure, interpretation and action? Default behavior
and submission gates are fixed. This is a checkpoint diagnostic, not fresh solves.

## Panel and intervention

Use N1 (AnyIO) and P1/P2 (pyfakefs) from the frozen optional-probe shortlist, one
A/B pair per checkpoint. Fixed order: N1A, N1B, P1B, P1A, P2A, P2B. A hides only
working_notes.verification.observations on every turn; B preserves it. Both retain
original public outcomes, task, candidate, tool schema, notes, history and remaining
model/action/edit/time allowances. Each branch receives the same fresh USD cap;
unused historical funds and unused row funds cannot be transferred. Keep the
selected GPT-5.4 snapshot, xhigh and desired 25,000 output tokens. Actual output
admission remains cost-bounded. No task-specific hints or probe corrections are added.
N1 originated on GPT-5.4/xhigh; P1/P2 originated on GPT-5.4-mini/medium. Both arms
continue under the selected GPT-5.4/xhigh baseline. Parent model/settings are explicit
manifest provenance, not a claim of same-model resume. Inherited continuation state
is identical within each pair; cross-model provider compatibility remains untested
until actual execution and any continuation failure stops the comparison.

## Scoring fixed before execution

Primary window: first three newly completed tool batches, including a stop/finish
decision if earlier. Report full-trajectory behavior separately. Only actually
delivered public inputs, declared decisions, source/actions/checks and notes are
scoring evidence. Do not inspect encrypted reasoning or infer internal attention.

For each row preserve event/action/input/diff identifiers and quoted public evidence:

| Dimension | Values and evidence rule |
| --- | --- |
| Retention | 0 no observable reference; 1 explicitly mentions the discrepancy; 2 carries it into a targeted action or still-open question. Absence of evidence is not proof of forgetting. |
| Interpretation | supported / unsupported / unresolved / absent. Distinguish product behavior, invalid probe assumption/API, and environment failure using public source or executed evidence. Error type alone is insufficient. |
| Action | 0 none/unrelated; 1 relevant investigation; 2 distinguishes competing causes with an executed check or directly inspected, cited public source, or verifies a supported correction. A planned probe alone is not execution. |
| Closure | supported / premature / no closure / unknown. Unrelated PASS, registering a concern, or changing its status does not resolve the original discrepancy. |
| Unnecessary change | supported / unsupported / unknown. Mark unsupported only with a public requirement conflict or reproduced regression, not simply because a file changed. |

Primary endpoint: a publicly supported discriminating action (Action=2,
Interpretation=supported), without premature closure or a demonstrated unsupported
change in the primary window. Preserve each dimension even when the endpoint fails.
An explicit evidence-backed rejection of an invalid probe can succeed; blind repair
after any failure cannot. A provider/preflight failure before a delivered decision
is NOT_RUN, not an incorrect agent answer. Resource-censored trajectories are marked
incomplete, with their observed prefix retained; no imputed later outcome.

Score an arm-masked public review sheet first; reveal treatment after recording the
judgments. The operator already knows the historical cases, so this is imperfect
blinding. Resolve ambiguous expectations as unknown, not using hidden tests or
reference patches. Report pair wins/losses/ties and raw evidence; three checkpoints
on two already examined tasks cannot establish significance or generalization.
Each manifest row fixes the particular failed-probe action ID being judged. Other
catalog entries cannot substitute for it. The selected panel contains probe setup/API/
introspection failures; it cannot estimate performance on confirmed product defects.
Record cost, time, mutations, public checks, final submission and isolated acceptance/
safety separately. Hidden evaluation is terminal-only, never agent feedback or a
criterion for grading the public interpretation. No model-as-judge calls are added.

## Preparation, execution and stop boundary

`diagnostics.observation_comparison prepare` binds source hashes/cuts, rubric,
implementation/runtime, credential path, row/group caps and normalized first inputs.
Preparation uses synthetic stop responses and read-only environment admission;
it reads no credential contents, counts no real tokens and starts no containers.
Only elapsed active-wall seconds are normalized for first-input parity. The manifest
is not paid authorization. `collect` needs the explicitly approved manifest hash
and exact positive invocation cap. A fresh result root is single-use, including
failed/interrupted attempts. No retries, automatic resume, budget/time extensions
or replacement rows. Sequential execution preserves scoped per-turn exposure.

The ordinary adapter counts immediately before dispatch with zero SDK retries.
See [official OpenAI token counting](https://developers.openai.com/api/docs/guides/token-counting).
The [GPT-5.4 model page](https://developers.openai.com/api/docs/models/gpt-5.4)
was checked on 2026-09-29: per-million input/cached-input/output USD 2.50/0.25/15.00,
matching the existing standard-tier ledger below its enforced 60K input bound.
The shared continuation ledger admits both row and group costs and records only new
usage against the group. Count, transport, usage, continuation or cleanup uncertainty
stops all remaining rows. Unknown billing is not reported as zero. Readiness is
rechecked before each row; Docker is never started and images never pulled/built.
Original prefixes remain byte-bound; a separate executing Git identity overrides
the inherited Git label for new submission provenance. Ordinary resume guards remain.
