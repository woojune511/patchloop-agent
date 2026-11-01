# Canonical diagnostic clean-start pilot

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: bounded execution preparation
- Origin Date: 2026-10-27
- Verification Status: PREPARED / PREFLIGHT_PASS; live NOT_RUN
- Implementation commit: `c9efc5c4`; official=false, claim-ineligible

## Question and decision

Can the ordinary agent use the host's canonical diagnostic judgment, receive a
remaining failure even when its wording changes, revise if needed, and finish from
clean source? The [previous clean-start trial](2026-10-27-normal-recovery-fresh-results.md)
stopped after one edit because helper and host predicates diverged on F0010. Calls,
time and money remained. The [implemented change](2026-10-27-canonical-diagnostic-feedback.md)
removes that duplicate computation for fresh diagnostic-code observations.

This follow-up holds the previous task, model and limits fixed. The request differs
only in its fresh state root; runtime intervention is wire v64 / invocation v6 /
captured-diagnostic-v2. The model chooses its own calls and diagnostic rules from
the public task. No old patch, source excerpt, helper evidence or prior history is
injected. Private specifications, tests, reference patches and evaluator internals
remain outside model context. The prior collection is an operator-only comparator.

This is one within-task transfer pilot, not a randomized comparison or held-out
quality result. A different model trajectory may avoid the exact changed-wording
case. If no eligible failed edit occurs, feedback-driven revision and that mechanism
are NOT_EXERCISED; do not manufacture failure or repeat merely to exercise them.

## Exact proposed allocation

- Astroid-1333: `tasks/dev-train/current-dev20/13/public.yaml`.
- `gpt-5.4-mini-2026-03-17`, xhigh; one run, invocation cap USD 4.50.
- Credential file: `C:/Users/geonj/Documents/PatchLoop/.env` (existence only checked).
- 20 total model calls including at most one protocol correction; 40 tool actions;
  at most three accepted edits. Zero SDK retries, no automatic retry or resume.
- 60K input; 40K normal / 25K correction output. Segmented context,
  result-or-size handoff, 24K retained source characters, thin agent, planning none.
- Probes enabled, bounded reproduction acquisition, probe policy none,
  repair-recheck, protected inspection and completion-recovery-v1.
- 2,400 seconds total including 390 reserved for isolated evaluation; initial
  solver budget 2,010 seconds. No increase from the previous clean-start trial.

Prepared clean source and pinned public dependencies are environment inputs only.
Acquired originals replay after edits. Public check scheduling remains model-selected;
known failures recheck after edits, and normal finish requires current-diff registered
checks PASS. Helper inspection can read caller source; the diagnostic loop's
`dependency:pylint` read/search scope is not added to the ordinary runner.

At the registered mini rates, twenty maximal 60K-input/40K-output calls cost USD
4.50; nineteen such calls plus one 25K correction cost USD 4.4325. This is a token
envelope, not a guarantee of useful output, enough time, or correctness.

## Sealed artifacts and validation

- Plan root: `C:/pt/canonical-diagnostic-fresh-plan-v1`.
- Result root: `C:/pt/canonical-diagnostic-fresh-run-v1` (absent at preflight).
- Manifest hash: `sha256:346cfa8cfc2a4100634bdd908c6237a2a79fc614b2296479427453774b256225`.
- Runtime hash: `sha256:9130765db5c64f08c7d95799d0cd3cc10566e4a4a82e449169b295b8fd100162`.
- Command: `& 'C:/pt/canonical-diagnostic-fresh-plan-v1/run.ps1'`.

The manifest binds request/entry bytes, full task identity, prepared source and
dependency descriptors, probe profile and local image identities. The unchanged
one-shot entry also verifies the clean source, dependency inventory and tracked
runtime/task state. It holds the execution lock and records a started receipt before
dispatch; a consumed allocation cannot be retried. Only preflight was executed.

`preflight.json` records PASS with zero provider calls, input counts, credential
reads and target executions. Images were inspected, not pulled, built or started.
No approval file or result root exists. Preparation uses the new runtime hash and
does not reuse the previous allocation or its initial-admission receipt.

Implementation evidence remains `C:/pt/canonical-diagnostic-local-v1/summary.json`:
25 new core cases, including two ordinary-loop integration cases in 20.36 seconds.
Quick covered 526 cases in 82.779 seconds including isolated mock: 514 initially
passed, and all 12 stale schema-hash/document nodes passed targeted reruns after
correction. Ruff passed. These are local scripted-provider results; they establish
neither real-model uptake nor Astroid repair. Broad tests were not repeated for
this documentation/preparation-only change.

## Outcomes and stop rules

Record model-authored acquisition, selected diagnostic codes, raw complete captures
and host verdicts, first edit, current-diff original outcome, actual next-request
feedback, any revision, registered checks, normal finish, isolated acceptance and
safety separately. Inspect raw public captures before interpreting a verdict.

Mechanism support requires an eligible changed-wording failure to remain failed
and reach an actual subsequent request when resources permit. Task success requires
normal finish with a supported original, public checks PASS and separate isolated
acceptance PASS. Submission alone is insufficient. One trajectory cannot establish
a repair-rate gain; an unrelated model failure would leave that question unresolved.

Stop on count, transport, billing or execution/cleanup uncertainty, identity drift
or configured limits. No operator repair or synthetic submission is included.
Previous allocations remain closed. This new invocation is prepared, not approved
or executed; AGENTS.md hard gate 5 requires its exact fresh authorization.
