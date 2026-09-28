# Boundary-pair procedure: fresh-run panel results

The generic changed/preserved-pair instruction produced A 7/12 versus B 8/12
acceptance passes across six tasks with two repetitions per arm. Paired B wins /
A wins / ties were 1 / 0 / 11. The sole discordance was PDM repetition one.
Both known failure tasks, Pydantic and HF Hub, failed all four runs each. Keep the
selected Current baseline; do not adopt this instruction as a default improvement.

## Scope and execution

See [frozen design](2026-09-28-boundary-pair-panel-design.md) and
[contract](../../.agent/boundary-pair-panel.md). A is Current; B adds the generic
procedure to brief-v1: select a changed/preserved pair, derive expected outcomes
from the requirement, trace the distinguishing condition and resolve uncertainty
with public evidence. All tools, schemas, checks and limits were identical.
No task-specific examples were supplied. This tests the instruction bundle and its
uptake with existing tools, not enforced independent counterexample execution.

All 24 fresh runs submitted and reached isolated evaluation. Safety passed 24/24;
NOT_RUN, infrastructure failure and resource-limited non-submission counts were zero.
Every run is dev-train, official=false and claim-ineligible. These are registered
PatchLoop task-package results, not an original benchmark score or held-out estimate.
The six tasks have prior execution history; repetitions are not 24 independent tasks.

Exact live configuration: gpt-5.4-2026-03-05, xhigh, 25K desired output,
C:/Users/geonj/Documents/PatchLoop/.env; 40 calls, 100 actions, four accepted edits,
1800 seconds and USD 2 per run, USD 48 invocation cap. No additional live work,
replacement or resume followed collection. Actual cost is USD 12.1553535, all settled;
USD 35.8446465 unused allowance is closed. The most expensive run was USD 1.8413465.

| Task | A acceptance | B acceptance | B wins / A wins / ties |
| --- | --- | --- | --- |
| Pydantic synthetic tool reasoning v1 | 0/2 | 0/2 | 0 / 0 / 2 |
| HF Hub endpoint propagation v5 | 0/2 | 0/2 | 0 / 0 / 2 |
| Fromager orphan removal v1 | 2/2 | 2/2 | 0 / 0 / 2 |
| Loguru invalid format v3 | 2/2 | 2/2 | 0 / 0 / 2 |
| PDM ignore active venv v2 | 1/2 | 2/2 | 1 / 0 / 1 |
| pgmpy stable skeleton v1 | 2/2 | 2/2 | 0 / 0 / 2 |

| Metric | A | B |
| --- | --- | --- |
| Settled USD | 5.3643050 | 6.7910485 |
| Summed active seconds | 2967.460 | 3701.701 |
| Model calls | 97 | 100 |
| Submitted / safety PASS | 12 / 12 | 12 / 12 |
| Selected-pair process score 2 | 10/12 | 12/12 |
| Agent run_probe calls | 0 | 0 |

B cost 26.6% more and took 24.7% more active time. Active time is the sum of terminal
active_elapsed_ms, not preparation or operator review wall time. Fromager/Loguru
successful controls showed no acceptance regression. Every final submission passed
its required public checks, including all nine evaluation failures.

## Public process review before outcome mapping

The same investigator reviewed anonymous public decisions, source observations,
checks and submitted patches, then froze grades before opening the arm mapping and
outcome file. This is arm-masked review, not independent blinding: wording can reveal
B. Rubric 2 means evidence discriminates the selected pair; it does not certify
complete applicability coverage. Concrete input classes with explicit outcomes count;
generic preservation statements do not. The two score-zero traces were GA1/GA2:
they made the correct snapshot edit and passed evaluation without stating a concrete
pair. This process measure is therefore neither necessary nor sufficient for success.
No agent used run_probe. All used registered checks; L/D/G's stdlib-only probe
limitation caused no observed probe import failure, but its effect on tool choice
cannot be inferred from absence of calls.

- **Pydantic:** all four plans/patches reduced the condition to tool calls without
  thinking plus field mode and a nonempty field name. They omitted the public
  requirement that the provider-supplied profile carry the opt-in. The selected
  pairs distinguished DeepSeek/default plain profiles, existing thinking or send
  modes; none tested an unrelated provider with field mode already enabled.
  Both checks passed for every patch. A valid easy pair did not falsify the
  overbroad applicability condition; longer pair wording did not fix this failure.
- **HF Hub:** HA1/HA2/HB1 forwarded normalized self.endpoint as explicit context.
  HB2 uniquely read the constructor normalization, retained _explicit_endpoint and
  used it in both HfApi wrappers. Its partial first patch failed the public contract;
  later propagation edits reduced failures and eventually passed all public checks.
  That is a local source-supported improvement, not proof of complete endpoint
  semantics. HB2 still failed isolated acceptance. Its frozen static boundary grade
  concerns this identified explicitness distinction only; it must not be relabeled
  a correct full repair. The residual failure cause is unresolved here; no private
  failure assertions were inspected or projected to agents.
- **PDM:** all four identified the enabled/false-like and active/other-path distinction
  and passed the same public checks. DA1 uniquely constructs PythonInfo for the
  active environment before checking ignore_active_venv; DB1/DB2 and DA2 gate that
  operation. This is a public-source candidate explanation for the sole acceptance
  discordance, not a verified failing-input diagnosis. No public check contradicted
  DA1 during its run. Frozen grades mark the selected boundary and separately note
  that DA2 uses lexical paths without resolve; its PASS does not prove alias coverage.
- **Fromager, Loguru and pgmpy:** final code preserved the reviewed pair boundaries,
  with acceptance ties throughout. More explicit pair prose in pgmpy B did not
  produce additional accepted repairs. Existing checks already exercise useful
  changed/preserved examples on these tasks.

Only HB2 encountered semantic public-check failures, while its repair was incomplete;
it then completed propagation. No trace demonstrates a wrong applicability guard
being overturned by an agent-created falsifying example. Source reads, valid pair
selection, test PASS and complete task correctness remain separate observations.

## Interpretation and next decision

The numerical follow-up screen (more B wins than losses, no safety regression) is
met, but the mechanism evidence is weak: the one acceptance win has no discriminating
public observation, and the clearest local condition improvement still failed the task.
This is insufficient for adoption or a general quality claim. Two repetitions on six
selected tasks cannot separate a reliable effect from sampling variation. No component
of the procedure bundle has isolated causal credit.

The observed bottleneck is choosing evidence capable of exposing an incorrect repair
condition. The instruction increased explicit case descriptions but did not reliably
make agents challenge the condition they had already chosen. Before another paid
panel, use the saved public traces/patches to check whether selected examples would
actually distinguish the proposed broad guard from the public requirement, and whether
an excluded input still reaches fallible work (as in DA1). Separate a missing capability
from an existing check that simply does not cover that boundary. Do not add more plan
fields, compulsory prose, hidden-derived examples, or change defaults on this evidence.
No follow-up live invocation is authorized by the closed allocation.

## Integrity, validation and artifacts

Implementation commit b9823b2 froze the diagnostic, tests and design; production
runtime source was unchanged. Four diagnostic tests and 42 related planning/input
tests passed before execution; both mock arms reached isolated evaluation. Six real
source/image/dependency preflights passed. The initial packet boundarypair0928a
closed before paid calls on an old source hash mismatch; historical source bytes
were preserved and all six sources were freshly prepared for the successor.

Post-run audit verified all 24 journal chains/settled ledgers, every one of 197 saved
model inputs, correct A/B instruction delivery and fresh empty initial plan/notes/diff.
Runtime, diagnostic, task packages and prepared descriptors revalidated after grading.
No private evaluator feedback entered subsequent agent decisions. Only final acceptance
and safety summaries were opened after public grading; no private test content was
needed for this report. The original masked grades and run records remain immutable.

External evidence root: C:/pt/boundarypair0928b.

- packet.json: sha256:aacd4f607271712803d4a823d2ad407494fe798dbe67b394ea7b42c45095bce8
- preflight.json and delivery-audit.json: preparation and actual-input receipts.
- public-review/index.json and its 24 artifacts: anonymous public evidence.
- pre-mapping-grades.json: sha256:2bba2a9c858bd7338efff878c267a550519d653a246e591dda188e70c4ff911d
- review-mapping.json, result.json, mapped-analysis.json: mapping, closure and metrics.
- runs/run_dev_boundarypanel.jsonl: hash-chained collection/audit/grading/mapping order.
- state/<label>/runs/<run_id>.jsonl: per-run immutable journal and artifact references.

Per-run ledger below allows every planned slot to be accounted for. All safety PASS.

| Label | Anonymous review ID | Acceptance | Process score | USD | Active seconds |
| --- | --- | --- | --- | --- | --- |
| DA1 | cd12d7ee9841f4b2 | FAIL | 2 | 0.3175130 | 218.031 |
| DA2 | fba58c19a43fad9d | PASS | 2 | 0.2994790 | 204.007 |
| DB1 | 7bf3bae116e30f5f | PASS | 2 | 0.2949735 | 222.101 |
| DB2 | b1b5d604430f30a4 | PASS | 2 | 0.3067050 | 219.486 |
| FA1 | b55efd6220baeca7 | PASS | 2 | 0.3317730 | 159.679 |
| FA2 | d5a97d3ab48c4433 | PASS | 2 | 0.2957830 | 177.186 |
| FB1 | 1478bd39a47f777f | PASS | 2 | 0.2934565 | 148.256 |
| FB2 | ead4011a74775e9f | PASS | 2 | 0.2838565 | 160.754 |
| GA1 | ad04f0d84435d900 | PASS | 0 | 0.2641085 | 145.846 |
| GA2 | f969459990906f0b | PASS | 0 | 0.2661470 | 137.610 |
| GB1 | 9a5372481f782cb4 | PASS | 2 | 0.3224760 | 184.209 |
| GB2 | e071065351964421 | PASS | 2 | 0.2568365 | 145.073 |
| HA1 | 1b4384acb30eb80f | FAIL | 2 | 0.9624645 | 556.693 |
| HA2 | 13df2b538df1a42b | FAIL | 2 | 0.8294680 | 436.088 |
| HB1 | d92d0b642ad79e7e | FAIL | 2 | 1.3268985 | 676.749 |
| HB2 | c2391bbec62e4080 | FAIL | 2 | 1.8413465 | 919.362 |
| LA1 | 14b1654f1a0197dc | PASS | 2 | 0.3936540 | 199.922 |
| LA2 | 0377e7d07d6e18f6 | PASS | 2 | 0.4514220 | 200.668 |
| LB1 | 4fd8b5398fb4d686 | PASS | 2 | 0.4811395 | 213.826 |
| LB2 | e86f1411f425671a | PASS | 2 | 0.4461735 | 230.068 |
| PA1 | 74d81f60e7840fc1 | FAIL | 2 | 0.5026490 | 253.654 |
| PA2 | 22102e353ed26648 | FAIL | 2 | 0.4498440 | 278.076 |
| PB1 | 3c86483b9e1860f6 | FAIL | 2 | 0.4830980 | 314.575 |
| PB2 | f1ff20287fc980ab | FAIL | 2 | 0.4540885 | 267.242 |
