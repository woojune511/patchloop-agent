# System review and external research

Date: 2026-10-07. Reviewed HEAD: `f8e28e0622950b469d274cd49242fd993a706ff9`.
Research and public-record analysis only; no runtime change, provider dispatch,
task execution, evaluator execution, or paid allocation. The existing AGENTS.md
working-tree edit was preserved. External source versions are identified below;
unversioned web pages and main-branch code were read on this date.

## Question and decision

Repeated failures after more context, funding, optional tools, and delivered
counterexamples make the next feature choice consequential. The question is which
mechanism can improve actual repairs, rather than increase activity or explain an
unchanged patch more convincingly.

The strongest observed quality bottleneck is premature acceptance of an inadequate
candidate after regression PASS. This is not a universal inability to repair from
feedback: positive contrasts exist. Model capability, model-facing controller
complexity, usable behavioral evidence, and candidate diversity remain distinct
possible causes. The latest reliability fixes do not isolate them.

Keep the selected baseline. Recommend preparing a substantially simpler policy
reference over the existing execution substrate and a public candidate/test
discrimination audit before adding another default mechanism. This is a proposed
research direction, not an approved live comparison or a claim of improvement.

## System map and observations

| Layer | Existing implementation / evidence | Assessment |
| --- | --- | --- |
| Task and environment | Public dev-train packages, prepared dependencies, registered checks, optional tests/probes, private evaluation boundary | Broad regression checks do not necessarily test the reported defect. Environment faults must be separated from assertion failures. |
| Model and policy | Structured per-turn decisions, planning fields, completion guidance, action horizons; full model as general baseline, mini used in bounded panels | Substantial policy surface exists. Its net effect relative to a genuinely thin controller has not been measured. More prose is not a new repair mechanism. |
| Retrieval and context | Read/search, retained source, native observations, segmented handoff, notes and verification concerns | Source loss was observed, but 24k to 48k tied at 2/4. The 24k setting is a retained-source character pool, not the model's entire token window. |
| Mutation | One exact replacement in an observed existing file per action; additive tests; four accepted edits | Restrictive for larger repairs, but no reviewed run exhausted four edits. Blanket relaxation does not explain voluntary early submission. |
| Verification and finish | Required checks on current diff qualify submission; optional observations remain available | Eligibility is correctly distinguished from semantic correctness in the contract. The agent still sometimes treats regression PASS as sufficient. |
| Execution and recovery | Journal, action/input idempotency, bounded dispatch accounting, sandbox cleanup, isolated evaluation | Preserve these foundations while changing model policy. Reliability improvements and repair-quality improvements need separate measurements. |
| Evaluation | Closed fresh panels, continuations, seeded repairs and response-only diagnostics | These measure different abilities and must not be pooled. Repeated exposed tasks are development evidence, not generalization evidence. |

Source owners: [model policy](../../patchloop/dev/model.py),
[runner and availability](../../patchloop/dev/runner.py),
[tools and mutation admission](../../patchloop/dev/tools.py),
[context retention](../../patchloop/dev/context.py),
[segment transitions](../../patchloop/dev/segments.py),
[verification concerns](../../patchloop/dev/verification_concerns.py),
[repair verification](../../patchloop/repair_verification.py),
[execution feedback](../../patchloop/sandbox/execution_feedback.py).

### Strongest local evidence

- [Latest counterexample comparison](2026-10-07-counterexample-results.md): both
  SQLFluff-1733 rows ran the broad check and submitted the unchanged wrong seed.
  B received the actual current-candidate failure in both inputs, with 39 calls and
  three edits still available. Delivery loss, a spent edit budget, and absent probe
  tools do not explain this particular result. It does not distinguish capability
  from interpretation or policy influence.
- [Development review](2026-09-30-development-review.md): 24 earlier full-model
  fresh episodes included nine acceptance failures despite public PASS. However,
  eleven registered failures across eight trajectories later received same-check
  PASS. Optional counterexamples also prompted repairs in some cases. All failure
  observations must not be treated as equally valid bug evidence.
- [Verification follow-up](2026-10-06-verification-closure-results.md): even a
  successful patch could lack post-edit reproduction; another trace copied observed
  candidate output into a test expectation. Probe count and self-authored PASS are
  insufficient success measures.
- [Context comparison](2026-10-06-source-retention-results.md) tied at 2/4;
  [funded continuations](2026-10-06-cost-cap-continuation-results.md) submitted but
  still failed. These local results argue against blindly increasing those limits.
- [Basic/current comparison](2026-09-28-basic-current-baseline-comparison.md)
  shared the core context, reserve and gating machinery; only planning, probes and
  recheck differed as a bundle. It was not a minimal-harness control.
  [Mini/full](2026-10-04-mini-full-results.md) was six tasks with two repetitions:
  6/12 versus 4/12, with the difference concentrated in Astroid-1196. It did not
  include SQLFluff-1733 and does not establish a general model ranking.
- Completion advice was already removed in a
  [real seeded comparison](2026-09-26-completion-status-comparison.md) with 0/2
  versus 0/2 and a [response comparison](2026-09-29-completion-recommendation-ablation-results.md)
  with 1/3 versus 1/3. Another isolated wording removal is not the recommended next step.

A fresh read-only extraction from the 24 journals bound by the
[fix-impact audit](2026-10-07-fix-impact.md) found at most three new accepted
replace_text actions per run, no four-edit exhaustion, and three mutation rejections.
These were an Astroid literal pytest.param case (now supported), a SQLFluff existing
fixture rewrite (not additive test creation), and a stale/absent exact anchor.
Seed patches are not counted as new mutations; the seeded rows added zero edits.
This does not prove the interface is optimal, only that raising this cap has no
observed trigger in these traces.

Extraction artifact: `C:/pt/analyses/system-review-20261007-v1/mutation-audit.json`.
Its input hashes and extraction rule are retained, with a hash-bound
`dev-run-v1` event in `runs/run_dev_systemreview.jsonl` under that root.

## External evidence and transfer limits

These sources provide mechanisms and comparison designs, not measured PatchLoop
gains. Paper experiments, vendor engineering observations, and social anecdotes
have different evidential weight.

| Source | What is useful here | Limit on transfer |
| --- | --- | --- |
| [CodeMonkeys, v2, 2025-02-03](https://arxiv.org/html/2501.14723v2) | Separates candidate generation from selection. More serial iterations cannot rescue a trajectory that prematurely approves. Its selector executes discriminating tests on the original and candidates. | Ten candidates and multiple internal iterations do not fit our limits by default; selection cannot invent a missing correct candidate. |
| [Agentless, v2, 2024-10-29](https://arxiv.org/html/2407.01489v2) | Separates localization, repair and validation, including regression versus reproduction tests. It analyzes tests that fail on the original but also reject a correct repair. | Base failure alone does not validate a generated expected result. Large sample counts and removing model-selected regressions are not adopted. |
| [SWE-agent, v3, 2024-11-11](https://arxiv.org/html/2405.15793v3) | Interface ablations show file-view scope, search summaries and feedback affect results. | Its older-model line-window results do not determine our retained-character budget. Use decision-time evidence, not a universal context size. |
| [mini-SWE-agent implementation](https://raw.githubusercontent.com/SWE-agent/mini-swe-agent/main/src/minisweagent/agents/default.py) | A small query/execute/observation loop supplies a reference for policy complexity. | Its bash and full-history assumptions differ. Preserve registered tools, bounded context, recovery and cost contracts. |
| [OpenHands, v3, 2025-04-18](https://arxiv.org/html/2407.16741v3) | Separates agent policy, event stream and runtime execution. | Supports replacing policy independently, not a framework migration or automatic multi-agent adoption. |
| [Cursor, 2026-04-30](https://cursor.com/blog/continually-improving-agent-harness) | Reports model-specific tool/prompt adaptation, dynamic context and evaluation of harness changes; call/error metrics are diagnostic rather than quality outcomes. | Vendor observations motivate comparison, not a causal estimate for PatchLoop. |
| [Cursor cloud-agent lessons, 2026-06-02](https://cursor.com/blog/cloud-agent-lessons) | Describes moving behavior from rigid orchestration into agent-controlled tools as models improve. | Product workload and capability differ; deleting all restrictions is not justified. |
| [Anthropic long-running harnesses, 2025-11-26](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) | Incomplete work can be declared finished; actual end-to-end verification matters. | Long-running web-app work is not bounded library bug repair; copying initializer/progress systems is unnecessary here. |
| [Anthropic evaluations, 2026-01-09](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) and [infrastructure noise, 2026-02-05](https://www.anthropic.com/engineering/infrastructure-noise) | Distinguish task outcomes, repeated trials and trace diagnoses; resource enforcement can change coding-eval results. | Match resources and account for censoring. Do not transplant another benchmark's noise magnitude. |
| [OpenAI trace grading](https://developers.openai.com/api/docs/guides/trace-grading) | Use trace-level failures to locate causes and task-level evaluations to test changes. | Here traces mean public actions/observations and explicit decisions, not private reasoning. A trace rubric does not replace patch correctness. |
| [OpenAI apply_patch](https://developers.openai.com/api/docs/guides/tools-apply-patch) | A concrete alternative edit interface with structured operations and execution receipts. | This documents capability, not a string-replacement quality comparison on our selected model. Defer until measured edit friction warrants it. |

Actual source checks corroborate the paper mechanisms:
[CodeMonkeys selection](https://raw.githubusercontent.com/ScalingIntelligence/codemonkeys/main/codemonkeys/stages/selection_state_machine.py)
runs tests on the original and candidates;
[Agentless reranking](https://raw.githubusercontent.com/OpenAutoCoder/Agentless/main/agentless/repair/rerank.py)
can fall back to regression-only filtering if reproduction filtering leaves no
candidate. Neither supports treating all generated assertions as authoritative.

For social media, Boris Cherny's January 2, 2026
[X post](https://x.com/bcherny/status/2007179861115511237) recommends robust
domain-specific verification. Direct X fetching returned 403; its text was read in
the [Thread Reader reproduction](https://threadreaderapp.com/thread/2007179832300581177.html).
This is a practitioner's report, not a controlled PatchLoop result. Its claimed
quality multiplier is not used as an expected gain or budget justification.

## Recommended sequence

### 1. Measure the controller's net effect before growing it

Prepare a thin policy reference using the same registered execution methods,
sandbox, mutation scope, source binding, current-diff required checks, journal,
accounting and hard stops. Keep the same source information and available tools;
remove the requirement for the model to maintain controller commentary and the
redundant model-facing policy narration. Log exactly which fields and instructions
change. This is a meaningful policy/interface bundle, not a pure wording test.

First verify action/observation fidelity and hard-gate parity without a provider.
A later explicitly funded comparison should start fresh from original code, use
the same model/resources, include both known failures and successful controls,
repeat each task, and balance run order. A small development panel is directional;
it is not a new general-accuracy estimate. Preserve tool availability across arms
so removing model advice does not silently relax execution rules.

Decision: if repairs improve without losing controls, simplify that layer. If both
policies fail in the same way, do not cycle through adjacent prompt variants; a
matched model-capability comparison becomes the relevant next question. A single
strong-model seeded success would establish feasibility only. Model and harness
effects ultimately require crossed conditions to distinguish interaction.

### 2. Make public behavioral verification useful before making it mandatory

Build a small public-only table from existing distinct candidate patches and
execution receipts: public requirement, expected behavior, actual execution path,
base result, candidate result, and preserved behavior. Separate valid defect
assertions from setup errors, wrong expectations and non-discriminating tests.
An author must derive expectations from public requirements, not candidate output.
Where receipts cannot answer the question, mark it unmeasured rather than inventing
a verdict. Freeze cases before any later evaluation; do not tune them from private
failures or reference patches.

There is a concrete implementation gap to evaluate here. The existing operator
`repair-verify` already compares base, base-with-added-tests and patched trees, but
`_pytest_args` recognizes direct `python -m pytest` only. All twenty current-dev20
registered launchers instead use `python -B -c ...` with copied source and pytest
children. Changed-line feedback has the same topology problem: 37 of 38 retained
file observations were unsupported, not evidence that changed code was unexecuted.

If this comparison is selected for implementation, reuse prepared environments and
registered execution through an explicit launcher adapter. Validate real child
execution, source/candidate identity, test collection and outcome, unsupported
states and cleanup with a small local fixture. Do not merely remove the `-B`
rejection or infer behavior coverage from executed lines. Extending operator
verification and exposing a native agent observation are separate scope choices.

The latest external feedback lives outside the native verification catalog by
contract. Native integration is plausible but unproven. Preserve real execution
provenance, invalidate currency after edits, and give no registered-check credit
to arbitrary imported assertions. A new observation field alone repeats the
unsuccessful information-delivery approach. Adoption needs actual repair changes,
not more mentions of failure or more probes.

### 3. Consider two independent candidates only if public selection is feasible

Use the table above to ask whether distinct useful candidates and discriminating
public tests exist. If all available candidates make the same mistake, work on
generation; a selector cannot fix missing alternatives. If tests cannot separate
the candidates, work on the behavioral check rather than an LLM judge.

Only with both prerequisites should a bounded two-trajectory design be prepared.
The two solves plus all checks and selection must share one total cost/call/time
allocation, with isolated working directories. Compare against one trajectory with
that same total allocation. Candidate coverage and final selected correctness are
different metrics. This is candidate search inside one coding-agent product, not a
default planner/coder/reviewer organization. Task-level parallelism only speeds up
independent measurements; it does not itself improve solve probability.

### 4. Fix interface friction where it is observed

Classify failed actions, wasted search time, truncated/missing relevant source and
unsupported checks using existing public logs. This need not add model calls or
a new autonomous monitoring service. Search-once was a demonstrated useful repair;
its faster runs still failed correctness, correctly limiting the claim.

Atomic multi-replacement edits or a model-adapted patch format could reduce
source+test editing overhead. They need existing-file/scope preservation,
all-or-nothing application and idempotent recovery. Keep them below the behavioral
and policy questions until traces show representation failures or exhausted edit
capacity. Do not expand context, remove test preservation or add cross-run memory
as substitutes for that evidence.

## Immediate deliverable and limits

The next preparation should produce two reviewable artifacts: a thin-policy parity
specification and a public candidate/test discrimination matrix using saved
evidence. They answer different questions and can be prepared in parallel. Only
then choose one intervention and freeze tasks, model, credential path, repetitions,
caps, outcome criteria and stops for any live work. No experiment is queued here.

Success measures are actual submitted patch correctness, regressions, completion,
cost and elapsed time, reported separately from safety and infrastructure. Source
reads, plans, probe counts and explanation scores only locate failure mechanisms.
The baseline remains selected; no new runtime behavior or performance gain is
claimed by this review.

Validation: documentation layout/link suite 5 PASS in 0.24 seconds; this report's
local links and `git diff --check` also passed. XML:
`C:/pt/validation/system-review-20261007.xml`. Runtime suites and mock smoke were
not rerun for this documentation-only change. No live or quality comparison ran.
