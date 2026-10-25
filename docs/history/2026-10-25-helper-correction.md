# Helper API preflight and bounded same-question correction

Date: 2026-10-25. Follow-up to the
[helper failure audit](2026-10-25-helper-stop-analysis.md).

## Material Passport

- Origin: academic-research-suite / experiment-agent, authorized implementation
  and local code validation.
- Version: `helper-correction-local-v1`.
- Verification: locally tested mechanics; live behavior remains unmeasured.
- `official=false`, `claim_eligible=false`; no paid solve or real Docker run.

## Problem and selected intervention

The previous live helper called an original-only injected API and failed before
its intended diagnostic. The error was retained, but four source inspections spent
the remaining probe opportunities. Post-mutation diagnosis could not help before
the first repair. This is a completion bottleneck, not evidence that larger output
budgets or a new memory mechanism would fix the task.

The requested change was clearer helper APIs and one bounded corrected diagnostic.
Existing setup/changed-line receipts cannot establish that an arbitrary runtime
exception preceded every target call. Instead of inferring that boundary or adding
a general tracer, this implementation catches provable source errors before dispatch.
It is not a general runtime setup-error recovery implementation.

## Implemented behavior

`helper_program.py` compiles fresh helper source and checks lexical bindings for
`reproduction_workspace`, `observed_target`, and `record_observation`. Unbound uses
are rejected with the source hash, invalid field and location; ordinary imports,
locals and closures remain valid. Dynamic namespaces are inconclusive. The tool
description separates these original-only APIs from common `check_setup` and shows
a `TemporaryDirectory` fixture. No input-schema fields or output/cost caps change.

`helper_recovery.py` derives the first pre-mutation correction ticket from durable
host rejection receipts. It binds action/input/source/diff identities and the exact
question. Only changed source for that question or explicit stop is admitted next;
unrelated reads, a different question or a speculative project edit cannot replace it.
One correction request is allowed across restart. Rejection does not earn another.

The correction adds one real model/tool action to minimum completion. Admission
preserves the minimum repair, acquired original replay, fresh checks and finish;
future failure recovery is not guaranteed when speculative reservations are spent.
The independent protocol-output reservation remains separate. An unfunded or
unresolved correction returns `VERIFICATION_INCOMPLETE`, preserving an underlying
output/physical stop cause. Count/transport/billing uncertainty keeps its own stop.

A settled corrected execution ends program correction, including an intentional
target assertion failure. Its exit status remains visible; behavior is not assessed
by this mechanism. This avoids classifying every target exception as another setup
failure. Original reproduction, required checks and independent acceptance remain
separate. Completed receipts replay without execution; unknown dispatch never retries.

## Local evidence and review findings

- The actual saved call-25 helper source is rejected at line 8 for unbound
  `reproduction_workspace`, without executing imports or target code. The source
  is bound to the immutable analysis hash and run `run_dev_b727d95fec6b4f93`.
- Focused controls cover lexical correctness, same-question admission, source changes,
  restored rejections, completed and uncertain dispatch recovery, first-mutation
  scope, no renewed ticket, and exact model/tool/money boundaries.
- Initial integration exposed the missing compact-model-state field. It was added
  and tested through the actual model context as well as policy projection.
- A separate native worker found that saved `case_id` programs could otherwise
  create a correction with a null/missing question. Preflight now applies only to
  newly authored helpers; saved/replayed programs and legacy pending admissions
  retain their contracts. A regression exercises omitted raw source/question fields.
- Rejected correction admission stores its error so a lost action result cannot
  turn a rejected question into a dispatch during recovery.
- The first documentation run exceeded the existing guide byte limit; its entry
  was reduced to a contract link without raising the limit.
- A scripted corrected-helper path continues through the first mutation, checks,
  finish and isolated mock acceptance, without acquiring original-failure evidence
  from the helper. This demonstrates continuation wiring, not model repair skill.
- Final focused: 64 PASS, 21.76 seconds pytest / 23.548 seconds command wall time.
  Quick: 346 PASS, 65.21 / 66.949 seconds, including isolated mock evaluation.
  Ruff PASS; runtime hashes stayed stable. Exact receipts and commit are recorded
  in the external closeout. Full regression and live model execution were not run.

Evidence root: `C:/pt/helper-correction-local-v1`, with an append-only hash-chained
`dev-run-v1` journal and immutable initial failures/final receipts. Native workers
shared project context; their source review is not a blinded model experiment.
Historical live artifacts and unrelated user changes are preserved.

## Decision and remaining question

The source error can now be corrected before target dispatch and cannot silently
lose its one opportunity to source exploration. This is a local mechanism result.
It does not show that the live model will write a useful diagnostic, observe the
original call path, make a first repair or resolve F0010. Runtime-only/dynamic
helper failures remain outside this narrow preflight classifier. A returned helper
result still requires interpretation and linkage to the original failing call.
