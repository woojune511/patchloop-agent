# Expectation reconciliation: conditional probe-construction design

Status: PREPARED_NOT_EXECUTED. official=false. No new paid calls or Docker runs.

## Problem and hypothesis

The construction audit found contrary numeric observations in the actual final
input, yet a later probe reused the contradicted CQ expectation. Storage loss was
not established. A generic instruction to reconcile expectations with observations
may improve oracle selection. Exact floating-point setup equality is a separate
failure; this experiment does not add numerical-tolerance advice.

## Fixed comparison

Use original-toqito-1538 dev-train, source C:/pt/probefollowup0928a/B2,
run_dev_33068b6e257f423a turn 544, the final of five actual dispatches.
Both arms force run_probe using named tool_choice; all source inputs and tools
otherwise remain unchanged. A preserves the original system message. B appends
only the sampler RECONCILE text. Existing optional-experiment advice stays intact.
No operator witness, hidden evaluator material or rubric enters model context.
This measures construction conditional on requesting a probe, not natural action
selection or repair quality. The source patch is already fixed and submitted.

Schedule A1/B1/B2/A2, two independent responses each; gpt-5.4-2026-03-05 xhigh,
25,000 output ceiling and 60,000 counted-input limit. Exact credential file:
C:/Users/geonj/Documents/PatchLoop/.env. Proposed new cap $4 invocation/$1 response,
30 minutes total. No retries, continuation or feedback. Stop on count, transport,
billing or identity uncertainty. Prior authorizations and unused funds are closed.
Official model documentation checked: $2.50 input/$0.25 cached/$15 output per
million; full reservation <=$0.525 per response, <=$2.10 for four under these limits.
Sources: https://developers.openai.com/api/docs/models/gpt-5.4 and
https://developers.openai.com/api/docs/guides/function-calling (named tool choice).

## Preregistered assessment

Before displaying samples, strip metadata down to anonymous ID and public response
content. No timestamps, sample order, arm or cost. The same investigating agent
reviews the content, so this is arm-masked assessment, not independent blind judging.
Record semantic judgments before execution or arm reveal:

- Expectation: supported, contradicted, unsupported, or unassessable; record public
  mathematical evidence and applicability, independently of the program exit code.
- Reuse of the previously contradicted formula: yes/no/not applicable, distinguishing
  a justified commuting restriction from an unsupported general CQ claim.
- Existing contrary observations: explicitly reconciled, merely mentioned, unused,
  or not relevant to the selected case. A trivial valid case is not broad coverage.
- Program setup and behavioral relevance, including whether it exercises the changed
  path. Absence of a CQ formula alone is not a successful repair.

Execute every syntactically valid returned run_probe once unchanged on an isolated
copy of the same frozen patch with existing prepared Docker dependencies. No model
feedback, corrections, retries, source mutation or new image build/pull. Syntax,
setup, infrastructure and actual API outcomes remain separate. Unreached behavior
is NOT_RUN. Stop operator execution on unexpected external-state uncertainty.
Report all four responses; do not select a favorable sample. Benchmark acceptance
and safety remain NOT_RUN in this diagnostic; prior patch results are separate.

## Implementation and validation

The sampler accepts an explicit reconciliation intervention while preserving its
legacy deletion default. It binds original delivery, exact projections and hashes;
shared count-before-dispatch and funding controls remain unchanged. Frozen old
packets are not rewritten. Prepared pair/plan:
C:/pt/analyses/expectation-reconcile-pair-20260928-v1 and
C:/pt/analyses/expectation-reconcile-plan-20260928-v1.
Plan hash: sha256:0463ee3778dea446be8fc8776c88f451afd490e0a6cff286b9b42dd7aad89722.

Focused sampler, continuation and documentation tests: 25 passed in under 10s,
including four fake dispatches with named tool choice and zero tool executions.
Default Windows pytest temp access initially failed; a fresh external test root
resolved that infrastructure issue. Current status size was trimmed to its bound.
Ruff and final packet validation are required before collection. No runtime change;
no full suite or fresh benchmark/mock evaluator run was needed for this collector-only
projection. Live acceptance of the named choice remains untested until approval.
