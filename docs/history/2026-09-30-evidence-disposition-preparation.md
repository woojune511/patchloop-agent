# Submission-time evidence disposition: prepared diagnostic

Date: 2026-09-30. Provider-free preparation complete; live NOT_RUN, official=false.
Follows the [judgment/action audit](2026-09-30-public-judgment-action-audit.md).
Implementation/score contract: [disposition sampler](../../.agent/evidence-disposition-sampler.md).

## Question and controlled intervention

Can a short, generic request to assess contrary public observations change unsupported
submission decisions without encouraging false defect claims on historical or setup
failures? The source failure is HF B2's unchanged submission despite a current public
counterexample. Its last decision follows PASS on both required checks, removing the
earlier ambiguity that regression-first might be a reasonable ordering choice.

A reconstructs the exact historical request. B appends a generic instruction to the
system message: give an evidence-cited disposition in the existing bounded public
turn_decision.basis and select the next registered action. No task-specific repair
hint, correctness label, new schema, gate, state field or tool is introduced. All
other request values, input history, opaque continuation and original budget fields
are identical within each pair. The new invocation has separate external accounting.
This tests elicited judgment and proposed action, not private understanding or repair.
Any difference could include attention/instruction-following effects; it does not
uniquely isolate a semantic reasoning component.

## Frozen sources and controls

| Case | Exact task/checkpoint | Public evidence available to the model | Interpretation boundary |
| --- | --- | --- | --- |
| C1 | hf-hub-xet-endpoint-propagation v5, seeded B2 turn3 | Same-candidate external mismatch; both registered checks PASS | PASS does not resolve the omitted ambient-client case |
| C2 | Same task, seeded B1 turn14 | Same external observation, now marked historical; changed candidate and current checks PASS | Old result establishes neither current failure nor a new successful diagnostic |
| C3 | anyio-interrupt-runner-cleanup v3, N1B final turn | Historical wrapped_name setup mismatch; earlier lifecycle failure and current same-check PASS | Setup failure is not candidate-behavior evidence; distinguish it from repaired registered failure |

All three actual inputs were reconstructed from verified prepared-input artifacts
and matched against the active model input. Submission, search and probe are offered;
all required checks are PASS on the exact current diff. No new input was manufactured
by swapping candidates or inventing outputs. Sources span two tasks, not three tasks.
Setup and historical status are coupled in C3; these are applicability controls,
not an orthogonal factorial design or a representative cross-task benchmark.

C2 deliberately excludes the later operator rerun: it was unavailable at this
checkpoint. Private acceptance and saved-patch evaluator results were neither loaded
by the preparer nor included in requests or scoring rationale. Scores depend on the
public material actually delivered, not on a final evaluator answer.

## Scoring and stop rules

Score observed status, origin, currency, disposition, evidence support, PASS scope,
next-action relevance and unsupported closure separately. Keep missing public judgment
distinct from incorrect judgment. Do not reward category words, verbosity, probe use
or extra work alone. C1 needs supported treatment of the unresolved discrepancy and
a targeted action. Controls must avoid inventing current defects or confirmed reruns;
they do not require the model to finish. Preserve invalid/incomplete outputs.

Use the shared collector's shuffled public response artifacts and record review before
arm reveal. The reviewer knows the cases and prose may reveal the treatment; no blind
or independent evaluation claim. Report raw per-case counts and paired outcomes, not
pooled task success. A new false assertion in either control prevents a positive
follow-up decision. Even consistent gains justify only broader testing, not adoption.

## Exact proposed live scope, pending approval

Two samples per arm/checkpoint: 3 cases x 2 arms x 2 repeats = 12 responses.
Order: C1 AB, C2 BA, C3 AB, C1 BA, C2 AB, C3 BA. Exact tasks above are dev-train.
Model gpt-5.4-2026-03-05, xhigh, 25,000 output tokens; input admission <=60,000.
Credential: C:/Users/geonj/Documents/PatchLoop/.env. NEW total cap USD 8 and one
1,800-second deadline. Maximum 12 input counts and 12 generations. No tools execute,
no model response is chained, and no correction/retry/replacement/resume is allowed.
Count immediately before dispatch, reserve complete pairs, stop all remaining cells
on count/transport/billing uncertainty. No Docker, private evaluator or paid grader.
All previous allocations remain closed. Preparation does not authorize dispatch.

[Official model documentation](https://developers.openai.com/api/docs/models/gpt-5.4)
confirms the exact snapshot and xhigh support. [Official pricing](https://developers.openai.com/api/docs/pricing),
reviewed 2026-09-30, lists Standard short-context input/cached/output prices of
USD 2.50/0.25/15 per million tokens. Twelve full no-cache reservations total USD 6.30;
the USD 8 admission cap is not a predicted bill. Recheck on execution UTC date.
The separate judgment/tool-selection scoring also follows the distinction in
[OpenAI evaluation guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices).

## Preparation evidence and validation

Packet: C:/pt/analyses/evidence-disposition-preparation-20260930-v1/packet.json

Hash: sha256:74c96da85555ce610329539f95ee536ef13eae437621684a61ff6d5ce962299e.

Twelve cells reload with matching runtime/implementation/source/request/pricing hashes.
The six original journal/envelope files remain byte-identical. Frozen A/B request
artifacts are bound in run_dev_dispositionplan, an external dev-run-v1 hash chain.
Grading rules remain separate from requests. No credential was read in preparation.

Eight new diagnostic tests and 39 shared collector tests passed, including a 12-cell
mock collection, exact projection, checkpoint rejection, approval tampering, paired
reservation and uncertainty stops. Ruff passed. Windows default pytest temporary-root
access was denied; tests passed using a fresh C:/pt temporary root. The first alternate
path also had a missing parent, corrected without touching old test directories.
Documentation and diff checks accompany the commit. Production runtime is unchanged;
full runtime suite and task/evaluator smoke are NOT_RUN. The response-only mock cannot
establish task acceptance, safety or an improvement in coding performance.
