# Evaluation protocol

Status: current effective protocol. Exact historical tuples are in `docs/09-evidence.md`; the Rapid workflow chronology
is in `docs/archive/rapid-workflow-history-20260830.md`.

## 1. Questions and dataset roles

PatchLoop separates three questions:

1. Does the agent complete the workflow and reach evaluation reliably under a fixed resource contract?
2. Conditional on a complete, fair batch, does a workflow or memory treatment improve fixed-denominator success/cost?
3. Does an independently frozen confirmatory panel support a limited external claim?

Smoke fixtures validate contracts. Public development tasks support rapid `official=false` learning and may be reused.
Qualification fixtures validate offline gates without provider/Docker/evaluator/check calls. Held-out tasks are frozen
before execution and cannot be tuned after outcomes are observed. Private specs, hidden tests and reference patches
never enter agent prompts, memory, task selection or public diagnosis.

## 2. Conditions and fair comparison

Condition A is no memory. Condition C is the fixed D-110 structured bundle. B/D remain deferred. A comparison fixes
model, prompt, tool/runtime, task/base, image, total and per-turn budgets, retry, evaluator, pricing and balanced
schedule. Workflow-successor experiments change only the declared versioned package and must state when several policy
changes are bundled, so a product-package result is not misreported as a single-policy causal effect.

Development and confirmatory work use different gates:

- **Rapid public development:** 6-12 rows, public tasks, `official=false`, one experiment plan, one validation command
  and one append-only bundle. Optimize evaluator reach, submission, success at budget, terminal class and cost.
- **Confirmatory:** fresh qualifying panel, preregistration, immutable receipts, independently frozen scoring and no
  tuning. It begins only after a public survivor is selected without consulting held-out outcomes.

## 3. Completion, metrics and interpretation

Every scheduled row has exactly one status: not started, harness/admission failure, infrastructure failure, agent
terminal, evaluator failure or scope-compliant success. Agent-rate denominators exclude only typed pre-agent admission
and infrastructure confounds; token, protocol, exploration and submission terminals remain observed zeros.

Required reporting includes:

- rows scheduled/started/settled and evaluator reach/submission/success at the fixed denominator;
- model/tool calls, input/output/reasoning tokens, total cost and terminal attribution;
- first-mutation search/read/check counts and files;
- edit attempts/acceptance, failed-check correction sequences and check order;
- `get_diff -> finish_task`, stale-evidence violations and infrastructure/confound counts.

Unequal completion censors cost. A lower mean from earlier terminals is not efficiency. Visible-check pass is not hidden
success; evaluator reach normally means submission completed and private evaluation started, not merely that public
checks passed. Selected evaluator-reached subsets cannot replace preregistered fixed denominators.

Public workflow diagnosis reads no model response/reasoning or private/hidden/reference material. It verifies event,
diff, check and result hashes, preserves sequence, and performs zero external/check/state-mutating calls. Observed facts
and hypotheses remain separate.

## 4. Rapid public development loop

Before paid work, the exact runtime/config/task/image/schedule/cost candidate is admitted in production order. R24
rehearsal assembles real public-task/model requests from a synthetic pre-action prefix and stops before the first count
SDK. It does not observe future live bytes, input counts, post-count budgets or provider acceptance. Later dynamic
requests require separate mock regressions. Two receipts must match; source changes require a zero-call successor and
fresh exact reserve/cap approval. A consumed candidate cannot replay.

Historical Rapid checkpoints remain immutable:

- R20 settled V22/V24 6/6 for `$1.62950550`, both 0/3/0, with V24 plan-feedback confounds; no retry or claim.
- Work Item 71 created Lean V25 offline; R21 then settled its three-row smoke for `$1.42525890`, reached 1/3 and
  succeeded 0/3, missing its 2/3 floor. V25 was not promoted and R21 cannot retry.
- V26 was source-qualified with an unexecuted runner-continuity proposal. Work Item 76 scheduled
  V25 control and V26 treatment, three rows each; the runner-continuity check stays excluded. R22 stopped before rows because 13 planned
  image inspections exceeded approval for one.
- R23 is now the latest consumed live batch before R24: one shared image inspect, two settled rows, four unstarted and
  `$0.16285425`. V25 failed hidden evaluation after submission; V26's invalid strict-read schema failed during count.
  The confounded halt cannot compare/promote V26 or retry/resume; zero generation events do not prove zero transport.
- Work Item 82 bound V25/V27 three rows each with the same pre-count gate and unchanged resources. Empty-object
  validation changed no wire bytes; rehearsal/qualification granted no execution or provider-acceptance claim.

Rapid promotion requires zero harness/admission/infrastructure/contract loops, valid plan and first mutation, reach at
least 2/3 and no lower reach/submission/success than control; settled-row cost must stay within 1.25x. Every mutation
retains plan, ordered-check, fresh-correction-read and fresh submission check/diff evidence. Passing selects only a
public-development default; failure preserves the candidate without retry and supports no quality/generalization claim.

R24 consumed that authority once and halted after 3/6 settled rows for `$0.927549`; 3 rows are unstarted. Reached,
submitted and successful rows are all zero. V25 exhausted exploration before a plan. V27 produced one accepted initial
plan and mutation, but the targeted check failed; three later V27 plan requests across two rows violated the owner/state/
transition component relation. The second V27 row then timed out during recovery generation. Unstarted rows are not
agent failures, and the partial schedule cannot apply promotion floors or compare cost/performance. No retry/resume is
permitted. A public halted audit may diagnose only agent-visible metadata/tool inputs and visible-check output.

Work Item 84 qualifies Lean V28 offline against the public R24 mismatch shapes. V28 changes only the declared
lifecycle plan/feedback package: one component registry, integer transition references, exact structural mismatch and
the existing one-use recovery boundary. Public mock runners cover accepted plans, one-retry recovery, repeated
rejection before a third dispatch and restart. This qualification performs no Docker/provider/evaluator/visible-check
call and creates no candidate. Work Item 85 performed the required activation review; no comparison schedule,
promotion floor or paid authority was created.

Work Item 85 reviewed the frozen package at zero calls/cost. It verified V29 routing, local strict-schema admission,
mock-only manifest admission and the public qualification boundaries, then recorded `eligible-not-adopted`. This was
not provider acceptance or activation; it left V27/V28 treatment selection to Work Item 86 and selected no schedule,
cost or execution authority.

Work Item 86 selects that V27-control/V28-treatment package only for later Rapid preparation. Three rows per arm are
recommended, but exact schedule/cost remain unselected. Existing completion/promotion gates apply; contract-friction
removal is not task-quality evidence. The decision creates no candidate, rehearsal, call, cost or paid authority.

## 5. Preregistered held-out A/C

The consumed held-out design froze 12 tasks by A/C by two repetitions, complete-panel SCRR and assumption-limited
stability/sign-flip diagnostics. Eligible evaluator FAIL and typed agent terminals score zero; infrastructure confounds
are inconclusive. R7/R11/R14/R15 remain immutable incomplete predecessors.

R16 settled 48/48 for `$27.24465825`: A 8/24, C 7/24, difference `-1/24`, stability `[-1/4, 1/6]`, sign-flip `p=1`,
same/cross 0/`-1/12`, benefit/negative flips 3/24 and 4/24. This unblinded consumed panel cannot tune caps, tasks,
memory, workflow or thresholds. It establishes neither memory benefit nor harm/generalization.

## 6. Confirmatory successor contract

A future confirmatory successor requires: an independently source-qualified fresh panel; raw-source completeness;
public/private separation; a frozen task/evaluator/runtime/cost schedule; no held-out tuning; deterministic typed
evaluator-v2 evidence; complete execution; append-only artifacts; and prespecified estimands/uncertainty. Selection must
use only public development evidence. No current artifact authorizes that work.
