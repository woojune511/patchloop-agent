# Completion closure: eligibility, advice and evidence

Date: 2026-09-28. Provider-free public-trace audit; `official=false`.
Follow-up to [deferred cue results](2026-09-28-deferred-scope-results.md), which
links the other two closed continuations. No runtime change or paid execution.

## Question and method

Why did the agent dismiss unverified changed behavior despite available resources
and scope instructions? Read the six actual dispatched requests across unhinted,
first-input-cue and ready-cue conditions, verify their canonical public-state
delivery, and compare public decisions with completion and submission code.
This audits observable statements, not private model reasoning.

All six requests share the same system prompt: current base instructions plus
brief planning and context-projection instructions. These already say to preserve
untested assumptions, limit conclusions to actual checks, and treat plans and PASS
as insufficient to establish unrelated behavior. The initial audit assertion
incorrectly expected the base prompt alone; inspection identified the appended
instructions, and the corrected audit verifies the base prefix and full prompt
identity across all six requests. No evidence was changed.

## Observed sequence

All first requests deliver the same inherited plan to test the new branches on
small examples and then run regression. Their open question asks whether the new
implementation matches the proposed CQ formula and variant/alpha error behavior.
Thus those uncertainties were available at the post-edit boundary.

| Condition | Before regression (decision 150) | After PASS |
| --- | --- | --- |
| Unhinted | Replaces the question with regression status; plan says PASS permits submission | Decision 166 claims new variant/alpha requirements were tested, clears question |
| First-input cue | Narrows question to preserved behavior, but plan explicitly retains possible targeted uparrow probe | Decision 166 labels remaining uncertainty hidden cases and clears question |
| Ready cue | Cites completion guidance as the only required next step; plan makes regression the remaining work | Decision 167 treats remaining uncertainty as hidden fallback coverage and clears question |

The early-cue condition matters: the missing verification remained visible in its
ready-state plan, so question replacement alone does not explain closure. None
of the three performed a new read, probe or edit between checkpoint and submission;
their only actions were `run_check` and `finish_task`. The selected regression's
14 passing cases exercise default/downarrow behavior, not the new uparrow branch.
See the linked prior public audit for assertion-level coverage and patch identity.
The statements about hidden cases are model speculation, not evaluator evidence.

All six states have an empty structured verification ledger. There was no recorded
concern resolved with a misleading evidence reference: the loss occurred through
free-form question/plan revision and dismissal. Existing warnings and review
requests were delivered; they did not supply new behavioral evidence themselves.

## Contract versus plausible influence

`DevToolGateway.ready_to_submit`, its state snapshot and `_finish_task` require a
nonempty tracked patch and current-diff required-check PASS. They intentionally
do not certify semantic coverage or require optional probes. This matches the
documented submission contract; changing eligibility into a task-specific proof
requirement is not warranted by this audit.

`runner._completion_guidance` also recommends actions. Before the check it names
`run_check`; after PASS it sets `next_action={"tool":"finish_task"}` and says:

> All required visible checks pass on the current diff; submission is eligible,
> not proof of untested behavior. Use run_probe if a concrete remaining public
> uncertainty could change the edit; otherwise use finish_task to submit. No extra
> experiment is required.

All three ready inputs contain this same advice while still offering probes,
reads and edits. The ready-cue run explicitly cites completion guidance before
checking. This supports examining advice as a possible contributor, but language
overlap is not causal proof. Confidence in the inherited incorrect repair,
self-authored plan revision and the threshold for a concrete uncertainty remain
competing explanations. The three sequential samples do not isolate these factors.

## Decision

The actionable failure is unsupported closure of changed-behavior uncertainty,
not missing submission permission or evidence transport. Do not add another cue,
force probes, or make notes a submission gate on this evidence.

Next prepare an offline ablation of the completion-guidance action recommendation
from the frozen post-edit boundary, before question narrowing already occurs.
Retain factual eligibility/check status, tools, budgets, patch, system instructions
and all other context. Define the removed recommendation as one intervention,
verify the exact input difference, and keep outcome measures about new behavioral
evidence and patch correctness rather than probe counts. This is a proposed
diagnostic, not an adopted runtime change or authorization for a new paid call.

## Evidence and validation

- Audit: `C:/pt/analyses/completion-closure-20260928-v2/audit.json`.
- Hash-chained receipt: `runs/run_dev_completionclosureaudit.jsonl` under that root;
  content-addressed artifacts bind the report and audit script.
- Script: `C:/pt/audit_completion_closure_0928.py`.
- Source roots: `C:/pt/posteditlive0928a`, `C:/pt/scopecuelive0928a`,
  `C:/pt/deferredscopelive0928a`; branch `A1`, run `run_dev_33068b6e257f423a`.
- Assertions verified six delivered projections, identical full system prompts,
  initial notes/plans, ready guidance, available probes, empty concern ledgers,
  action sequences and question clearing. Source-file hashes are in the report.
- New provider calls, checks and evaluator executions: zero. No private evaluator
  internals inspected; no new efficacy result. Documentation validation is reported
  with this change; runtime tests and mock smoke are not rerun for a docs-only audit.
