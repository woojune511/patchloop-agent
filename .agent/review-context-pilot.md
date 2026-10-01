# Review context pilot: bounded execution protocol

Status: IMPLEMENTED / PROVIDER-FREE REHEARSED / NOT AUTHORIZED FOR LIVE CALLS.
This file specifies a proposed experiment, not new baseline behavior or a work queue.

Offline progress: `diagnostics/review_context_offline.py` materializes candidates
and builds A/B review inputs. `diagnostics/review_context_rehearsal.py` connects a
finite scripted reviewer to the native repair loop with one replenished allowance.
See the [integration record](../docs/history/2026-10-01-review-loop-rehearsal.md)
and [probe admission](../docs/history/2026-10-01-review-probe-admission.md).
The manifest-bound `diagnostics/review_pilot_collector.py` provides the paid entry
point; preparation never reads credential contents. Scripted reviewers can enable
real registered probes with verified existing images/dependencies. The separate
review_integrated_execution adapter exercises real repair probes and isolated Docker
evaluation using finite model responses; the older local adapter stays unchanged.
An explicit current-runtime fork now writes a new branch envelope and retains the
source envelope as an artifact; ordinary resume remains strict. See the
[fork and accounting record](../docs/history/2026-10-01-review-fork-accounting.md).

## Decision and hypothesis

Question: does separating a review from the repair trajectory help discover a
valid public counterexample and produce a better final patch, compared with the
same review retaining that trajectory and ordinary continuation?
Mechanism hypothesis: commitment to the existing repair narrows subsequent test
selection. Removing prior rationale may improve selection. Competing explanations
are extra review instruction/computation, lost useful history, inability to repair
even an observed defect, and insufficient remaining resources. This pilot cannot
identify an internal psychological cause; it compares observable procedures.

## Source checkpoints and selection

Use all four inspected final-candidate, pre-finish boundaries, not each run's first
public PASS. They are outcome-selected, exposed development cases, not a sample
for estimating success rates. Do not replace a case after pilot outcomes.

| Public task | Version | Source run | Prepared sequence | Role |
| --- | --- | --- | ---: | --- |
| original-opensandbox-816 | 1 | run_dev_75ec90f0be654c84 | 131 | Publicly demonstrated incomplete repair |
| original-isort-2491 | 1 | run_dev_49397fa9568d4b80 | 339 | Publicly demonstrated ownership error |
| original-pyinfra-1679 | 1 public / 2 evaluation | run_dev_710588e1c1a94d4f | 142 | Preservation control under calibrated v2 |
| original-conan-19735 | 1 | run_dev_ffee311ba7aa4a11 | 140 | Preservation control under original evaluation |

Exact source-journal, prepared-request and candidate hashes live in
C:/pt/analyses/review-checkpoint-feasibility-20261001-v1/inventory.json.
Positive control means passing the recorded checks, not proven complete correctness.
Private verdicts, role labels and post-run diagnostic programs never enter model
inputs. Pyinfra v1 FAIL is preserved and reported separately from v2 evaluation.

## Arms and resource accounting

Three arms are necessary to distinguish role effects from history effects:

- C: ordinary continuation from the restored repair context, no review stage.
- A: a bounded reviewer receives the repair trajectory context; report returns to
  a repair continuation restored from the same prefix.
- B: the same review instruction/tools/report schema, but a fresh reviewer receives
  public issue, candidate diff and factual current-diff check/probe receipts without
  prior rationale, plans, notes or encrypted reasoning. Report returns to the same
  original repair context as A. Do not replace the repair agent's context.

Both reviewers may use registered reads/searches and public probes, never edits,
unrestricted shell or private material. Capture executed probe receipts separately
from report claims. Limit reports to a concrete suspected behavior, public evidence,
executed observation if any, candidate hash and limitations; no mandatory bug claim.
Forward reports as untrusted data. Old-candidate reports cannot certify later edits.
The generic instruction, bounded report validator and factual packet builder are
implemented offline. Scripted report delivery reaches the native repair loop;
real provider acceptance remains unvalidated. Reviewer probe execution now uses
the original registered gateway and admitted Docker backend, with a shared deadline.

Proposed model for every role: gpt-5.4-2026-03-05, xhigh, 25,000 output tokens.
Credential file for future explicit approval: C:/Users/geonj/Documents/PatchLoop/.env.
Repeat=1 per arm/checkpoint: twelve episodes, USD 2 each, USD 24 maximum aggregate.
These are proposed new allocations; historical unused balances remain closed.

Give each episode a new, equal continuation allowance of 900 active seconds,
16 model calls, 48 tool actions and at most two new accepted edits. A/B review
uses at most four of those calls, twelve actions and 180 seconds; its actual usage
is deducted from the shared episode ledger, with unused allowance returned to the
repair phase. All review/count/repair charges must pass one invocation-wide cap;
separate role caps must not accidentally authorize double spending. C can use its
whole allowance for normal work. Admission is counted immediately before dispatch,
zero SDK retries, and any count/transport/billing/cleanup uncertainty stops the panel.
No automatic retry, resume, replacement, image acquisition or allocation extension.
After submission, operator-only scoring has a separate 300-second deadline per row
and makes no model calls. This includes frozen public matrices or isolated pyinfra
v2 evaluation; original native evaluation remains separately recorded. Scoring is
never returned to a model and scoring failure stops the remaining panel.

This is a replenished diagnostic continuation, not exact original-budget resume:
isort had only 281.669 seconds remaining. Preserve historical usage separately.
Recompute tool admission consistently for every arm; do not fabricate check credits.
The scripted integration replenishes native-loop counters and uses the ordinary
accepted-mutation counter for two additional accepted edits. Reviewer cost is
included when the repair ledger restores historical usage; it is not refunded.
The earlier standalone edit-attempt guard is not used for repair-loop admission.
Equal caps do not imply equal tokens spent; report actual resources and censoring.

Fixed interleaved order: OpenSandbox C/A/B; isort A/B/C; pyinfra B/C/A;
Conan C/B/A. Use one frozen runtime revision in all arms; original source runtime
differences are provenance, not treatment differences. No tuning after observations.

## Outcomes and stopping rules

Before dispatch freeze the existing public diagnostic programs and scoring map,
regression commands and private evaluator versions/hashes. Operator-only analysis
must distinguish a valid contract failure from a test expectation/setup failure.
Do not author new scoring cases after seeing arm outcomes. Public diagnostic
matrices are incomplete; a pass is scoped evidence, not full task correctness.

Primary: final submitted patch corrects a predeclared public defect without losing
checked behavior. Run exact final-diff regressions and isolated evaluation. Also
record preservation-control damage, valid counterexample discovery, whether it
led to repair, cost/time, submission and resource censoring. Criticism, prose,
probe count and submission alone are not success. No submission means NOT_RUN
acceptance, not a fabricated correctness failure or success.

The pilot is promising only if B discovers and executes a valid distinguishing
test and repairs at least one flawed candidate that both A and C leave flawed,
without losing another frozen behavior or damaging either preservation control,
within caps. If A and B improve similarly, that supports review generally, not
fresh context. If B identifies but cannot repair a defect, it supports discovery
only. If no such difference appears, close this candidate; do not auto-tune wording.
Uncertain or censored outcomes remain inconclusive. One repeat is feasibility
evidence only; even a promising result does not authorize baseline adoption or
another run. Generalization/held-out/claim execution remain disabled.

## Execution admission

1. Require explicit approval of the exact manifest hash and USD 24 cap. Bind the
   tasks, model, credential path, repetitions, programs, runtime and helper code.
2. Rebuild and compare the entire manifest, require clean tracked implementation,
   and readmit all four source/evaluation environments before reading credentials.
3. Use a fresh external result root. Record dispatch/count/settlement and stop on
   uncertainty. An interrupted or completed root cannot be silently reused.
4. Preserve source records and private boundaries. Report actual correctness,
   regressions and resources separately; do not automatically declare improvement.

Candidate materialization, recursive CAS verification and current-runtime scripted
continuation succeeded for all four cases, including Conan, in all twelve arms.
The exact source/target runtime mapping remains explicit; this is a new diagnostic
fork, not permission to resume an old envelope. Reviewer count/dispatch/settlement
records are durable and its settled cost reduces the repair allowance.
The operator-only manifest builder binds the twelve rows, public diagnostic programs,
package hashes, scoring implementation and caps. The execution schema reports
collector_ready=true but paid_execution_authorized=false. Provider-free injected
transport traversed all twelve collector rows; saved submissions exercised scoring
for all four tasks. These checks establish routing, not model repair performance.
Reviewer response parsing uses the shared adapter
and preserves encrypted continuation and call ordering. See the
[integration follow-up](../docs/history/2026-10-01-review-integrated-execution.md).
Paid admission must
recheck the complete frozen manifest and current environment; no paid run is queued.
See the [collector readiness record](../docs/history/2026-10-01-review-pilot-ready.md).
The final approval manifest is stored outside the repository at
C:/pt/analyses/review-pilot-ready-20261001-v1/manifest.json. Older preparation
manifests bind older implementations and grant no execution authority.
