# Clean-start ordinary completion pilot

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: execution preparation after local implementation
- Origin Date: 2026-10-27
- Verification Status: PREPARED / PREFLIGHT_PASS; live NOT_RUN
- Implementation commit: `dc3c2b2c`; official=false, claim-ineligible

## Question and scope

Can the normal agent acquire the original Astroid-1333 failure, repair it, use
current-diff public verification and complete through `finish_task` from clean base?
The [saved-evidence result](2026-10-27-public-regression-cycle-results.md) exercised
revision but used a diagnostic loop and synthetic submission. The
[transfer implementation](2026-10-27-normal-recovery-transfer.md) established normal
feedback delivery locally and repaired useful-output/time reservation gaps.

This is one within-task transfer pilot. It is not an A/B comparison, a fresh task,
or held-out generalization evidence. The model starts from the public task and clean
base source; no saved patch, source excerpt, helper result or past-run history is
injected. Private evaluation remains outside model context.

## Sealed request

- Task: `tasks/dev-train/current-dev20/13/public.yaml`, Astroid-1333.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh; one run, cap USD 4.50.
- Credentials: repository `.env` at
  `C:/Users/geonj/Documents/PatchLoop/.env`; existence checked, contents not read.
- 20 total model calls including correction, one funded protocol correction,
  40 tool actions and at most three accepted mutations.
- 60K input; 40K normal / 25K correction output. Segmented context, result-or-size
  handoff, 24K retained source characters, thin agent, planning none.
- Probes enabled, bounded reproduction acquisition, probe policy none,
  repair-recheck and protected inspection; completion-recovery-v1.
- 2,400 seconds total, including 390 seconds reserved for isolated evaluation.
  Solver budget starts at 2,010 seconds; this is not an additional evaluator timer.
- Prepared clean source and public pinned caller dependencies reused only as
  environment inputs. Local images were inspected; none were pulled/built/started.

Normal regression scheduling is model-selected. A known failing check replays after
an edit, and finish requires all current-diff registered checks PASS. This does not
copy the diagnostic's unconditional all-checks-after-each-edit behavior. Caller
source is available through the existing helper's inspection API; the diagnostic
`dependency:pylint` read/search scope is absent from the ordinary runner.

At registered mini rates, 20 maximal 60K-input/40K-output calls cost USD 4.50;
19 such calls and one 25K correction cost USD 4.4325. These are token envelopes,
not promises of useful responses, enough wall time, or task success.

## Artifacts and preflight

- Plan root: `C:/pt/normal-recovery-fresh-plan-v1`.
- Result root: `C:/pt/normal-recovery-fresh-run-v1` (absent at preflight).
- Manifest: `manifest.json`.
- Manifest hash: `sha256:be198c8809a84191b558292147743c90ca036d09515b61de6bac86b1a8493d92`.
- Runtime hash: `sha256:bdb0bdfd7ee044429bb24a38616061890473a25850ac93c80afe17ed1fda9450`.
- Command: `& 'C:/pt/normal-recovery-fresh-plan-v1/run.ps1'`.

The manifest binds request/entry bytes, full task identity, clean source, dependency
inventory, probe profile and local image identities. The entry verifies these before
run_dev, holds the existing execution lock, records an irreversible started receipt,
and refuses a second invocation. Exact human approval is still required.

`preflight.json` records PASS with zero provider calls, input counts, credential reads
and target executions. `initial-admission.json` confirms read/search/probe availability
on the actual public task, with seven successor slots, USD 1.01682 future/correction
reservation and 960 seconds reserved within the solver budget. This is host policy
calculation only. Local validation: 500 quick PASS/61.887s including isolated mock,
five documentation checks, Ruff and diff checks PASS. Initial preparation failed to
serialize a datetime before any manifest was written; ISO formatting corrected it.
No paid attempt or target execution occurred.

## Interpretation and stops

Record acquisition identity, first edit, actual failure/success delivery, revision
when needed, normal finish, isolated acceptance/scope/safety, and resource usage
separately. If the first repair passes, revision is NOT_EXERCISED. Success requires
normal finish with supported original, all current-diff public checks PASS and
isolated acceptance PASS; submission alone is insufficient.

Stop on count, transport, billing, execution/cleanup uncertainty, identity drift or
configured limits. No automatic retry or operator patch is authorized. Earlier paid
allocations remain closed; this new USD 4.50 invocation has not been approved or run.
