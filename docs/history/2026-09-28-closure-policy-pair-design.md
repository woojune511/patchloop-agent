# Closure-policy next-decision comparison design

Date: 2026-09-28. `official=false`. Offline pair frozen; live collection NOT_RUN.
Follows the [closure audit](2026-09-28-verification-closure-process.md).

## Question and intervention

Does the residual conditional-submit wording affect the next action when a public
verification question survives but required checks already pass? This tests local
decision sensitivity, not general repair quality or the cause of a private failure.

A retains the exact dispatched time-extension request before the returned finish
decision. B removes only these consecutive sentences from its system message:

> Use an affordable experiment if it could change the decision, otherwise submit.
> No extra review call, annotation or experiment is required.

No replacement instruction, task hint, new concern, tool, gate or budget change is
introduced. Existing cautions about coverage remain. Prior exposure to this policy
remains shared; this is a current-input ablation, not a policy-naive fresh solve.
The source plan had already weakened before this checkpoint, so a null result
cannot exclude an earlier policy effect.

## Frozen evidence and validation

Packet: `C:/pt/analyses/closure-policy-pair-20260928-v1/packet.json`.
Script: `C:/pt/prepare_closure_policy_0928.py`.
Append-only journal `run_dev_closurepolicypair` binds script, packet and request CAS.
Source: `C:/pt/timeextension0928a`, group `run_dev_timeextension`, branch
`A1/run_dev_33068b6e257f423a`, turn sequence 460. The source's historical unknown
charge remains unresolved and is not reused as funding.

- A request: `sha256:78baab55a3b9007d5edeb0c9fa20d15dad823d88a6f1a0cf6e70bdb66cb4a77e`.
- B request: `sha256:98673c002fe2440f38ca28a9c9dc742f33ec4c41abb6ed99480e840680c60d53`.

Offline assertions verified source request identity, native public-state delivery,
one exact deletion, equality of all other request fields, and equality of tool
schemas and subsequent input messages. Source journal hashes are frozen. No key
contents, provider endpoint, Docker or evaluator were accessed. Production unchanged.

## Proposed collection and scoring

Collect only one response per independent sample, A1/B1/B2/A2 (two per arm), without
executing returned tools or feeding outputs between samples. Use the exact public
dev-train task `original-toqito-1538`, `gpt-5.4-2026-03-05`, xhigh, 25,000 maximum
output tokens, and `C:/Users/geonj/Documents/PatchLoop/.env`. Proposed new cap is
$4 total with $1 admission cap per response, no transfer, immediate pre-dispatch
count and zero SDK retries. Count, transport or billing uncertainty stops the
whole group. Admission failure or missing response remains NOT_RUN, not a finish
choice. Record invalid/incomplete responses separately; no repair retry.

Primary outcome is the first returned registered action: finish, probe, inspect,
mutate or stop. Secondary review examines the selected public behavior, justification
for expected values, cited current-diff evidence, and reason for keeping or closing
the existing question. Record cost and elapsed time separately. Review shuffled
response labels before revealing arms; two samples per arm are exploratory, not
a reliable effect-size estimate.

No tool runs means probe plans cannot count as verified behavior, discovered bugs,
repairs, benchmark success or safety results. Operator-discovered boundary cases,
the historical finish response and this scoring rubric are excluded from model
inputs. A later continuation would need its own matched execution design and
actual check/repair outcomes; do not promote this response-only comparison to one.

## Readiness and next step

Design and exact request pair are complete. This pair has no admitted live collector
or execution manifest yet; existing collectors do not directly admit this schema.
Implement and locally validate a response-only collector that enforces these
identities and caps before requesting paid approval. This record and packet are
not approval, and all earlier funding remains closed. No default policy is adopted.
