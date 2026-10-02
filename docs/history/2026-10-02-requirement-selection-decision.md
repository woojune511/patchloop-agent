# Requirement-based investigation: reuse evidence before adding instructions

## Question and decision

The user asked to proceed after the [B scope diagnosis](2026-10-02-review-scope-diagnosis.md).
The proposed direction was to select investigations from public requirements.
Before changing behavior, this review compared existing authority, agent prompts,
diagnostic implementations and matching saved evidence. Source HEAD: 29dec643.

Do not add another planning tool, mandatory requirement list or adjacent prompt
variant now. A task-first mechanism and a more explicit selection variant already
exist, with completed observations that did not establish discovery improvement.
This does not prove they would fail on OpenSandbox; it rules out treating the
proposed approach as an unimplemented, evidence-free next step.

## Existing guidance and mechanisms

| Layer | Existing support | What it does not establish |
| --- | --- | --- |
| AGENTS.md | Important public questions, competing explanations, smallest distinguishing diagnostic | Whether a model selects the right question |
| dev model system prompt | Identify the owner of each preserved behavior; connect observations to next actions; bound conclusions | That all named requirements become executable tests |
| Current reviewer | Review public issue, choose one possible defect, separate observations and assumptions | Comprehensive task coverage within four calls |
| task-first-v1 | Freeze up to four cases from the public task before revealing candidate/source | Correct applicability, constructed inputs or independent expectations |
| task-first-factors-v1 | Separate applicability from activation while keeping other factors fixed | Actual factor control in the executed probe |

The case-design mechanisms are implemented in diagnostics/discovery_case_plan.py
and documented in .agent/task-first-discovery.md. Cases are intentionally unverified
proposals, not an oracle or submission gate. They belong to a fixed-candidate
discovery diagnostic, not the review/repair loop. Porting them into B would be a
new intervention with call/context overhead, not restoring a missing contract.
The ordinary repair prompt's ownership rule is not part of the custom reviewer
system prompt; copying the whole repair prompt would also add unsupported state
and mutation instructions. No such copying was performed.

## Relevant saved observations

| Observation | Requirement signal present | Gap in actual verification |
| --- | --- | --- |
| OpenSandbox B, latest completed run | Original backend/PVC requirement and conditional caller span delivered | Helper-only probe; no backend/PVC body inspection or distinguishing check; patch unchanged |
| Pydantic task-first, 2026-09-19 | Four cases recorded before candidate exposure | Ordinary-profile preservation did not construct the same activation conditions; copied/renamed profile missing |
| Pydantic factorized variant, 2026-09-19 | Scope/activation instruction and separate preservation proposal | Executed default plain profile without controlling field mode; acknowledged gaps, then reported without further probing |

The two older samples returned no supported counterexample. Their reports supported
only the narrow observations; candidate correctness/repair acceptance was not
assessed. The factorized sample did not stop on resource or infrastructure limits.
They used a different task, medium rather than xhigh reasoning, and a discovery
procedure rather than repair. Do not pool their outcomes into a repair success
rate or infer that the same latent cause explains every case.

The recurring observable gap is between a named requirement and an executed check
that can discriminate a relevant wrong behavior. More requirement prose or a plan
does not by itself close that gap. Candidate anchoring remains plausible for B,
but missing contrasts before candidate disclosure in the older sample show that
candidate exposure is not necessary for this broader selection/construction failure.

## Minimum next-design boundary

The decision is narrower than abandoning review: keep the current coding-agent
baseline and stop automatic context/time/planning variants. No live run is queued.
If a later intervention is justified, specify the missing transition concretely:
public clause -> behavior-owning source -> input/conditions -> independently
expected observation -> executed result -> next action. Use this as operator
analysis, not a new mandatory runtime schema or an automatic coverage verdict.

Success must mean a useful new discrimination followed by correct repair and
preserved behavior, not more cases written, fields populated, probes, or reports.
Any future comparison must keep resources explicit and avoid transferring these
operator-known examples into agent context. The known examples can test tooling
offline, but would not earn autonomous-discovery or generalization credit.

## Validation and evidence

Compared the existing source and authority with saved public-review.json,
public-trace-audit.json and result.md under:

- C:/pt/analyses/counterexample-discovery-task-first-20260919-v1
- C:/pt/analyses/counterexample-discovery-factors-20260919-v1
- C:/pt/analyses/review-scope-audit-20261002-v1/summary.json

New evidence inventory and append-only journal:
C:/pt/analyses/requirement-selection-review-20261002-v1.
Seven source evidence files were hashed and verified unchanged. No private specs,
provider calls, credentials, candidate executions or Docker operations were used.
No runtime/prompt/tool behavior changed. Documentation tests and diff hygiene
passed; runtime tests were not repeated. The user's AGENTS.md edit is preserved.
