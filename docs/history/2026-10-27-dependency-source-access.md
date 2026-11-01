# Registered dependency source access and single-trial preparation

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: implementation, local validation and bounded experiment preparation
- Origin Date: 2026-10-27
- Verification Status: IMPLEMENTED / LOCALLY TESTED; live NOT_RUN
- Baseline: `05323cc5`, following the [caller-access audit](2026-10-27-caller-access-analysis.md)

## Problem and selected intervention

The preceding R1 trial made three Pylint searches over zero repository files and
stopped without an edit. Caller source was present in the prepared public
dependency bundle, and the helper description already explained how to read it.
The observed problem was failure to switch acquisition methods. Interface burden
is a plausible explanation, not an established account of the model's reasoning.

Make registered caller sources selectable through the existing read/search tools.
This removes Python-program authoring and helper-quota use from simple source
acquisition. Keep execution diagnostics optional: frozen original failure evidence
was already supplied, so forcing another unchanged replay would not retrieve the
missing caller body. No new diagnosis gate or resource increase is introduced.

## Contract

- Registration is explicit and backed by the prepared public descriptor. This
  experiment registers only `pylint==2.12.2`, root `pylint`, as `dependency:pylint`.
- Enabled read/search schemas require `source_scope`: `repository` or a registered
  dependency. Paths within dependency scopes remain site-packages-relative, such
  as `pylint/lint/expand_modules.py`. Existing calls without the field keep the
  repository default; deployments without registration keep their existing schema.
- Read only indexed Python source under that registered root. Verify file bytes
  against the pinned descriptor and return package, version and file provenance.
  Do not import packages, run target code, enumerate arbitrary host directories or
  turn public dependency files into editable workspace anchors.
- Keep existing page/range/search limits. A dependency inspection uses a normal
  tool action; it consumes neither a helper request nor an original-call selection.
- Zero-file repository searches disclose their scope and the registered alternative.
  A zero-file result does not prove that the caller source is absent.
- Keep previously observed dependency spans separate from mutable repository
  spans, including on hydration and context handoff. Revalidate pinned bytes before
  treating retained observations as current. Preserve action/input identities.

The diagnostic profile is `feedback-source-pair-v4`. Its scope records the
registration policy and roots. Preparation binds runtime bytes, diagnostic
modules, immutable public inputs and exact first-request bytes. No operator repair
hint, reference patch, private evaluator detail or hidden test is added to input.

## Smallest live trial

One R1 continuation on the same Astroid-1333 saved candidate,
`dev-train/current-dev20/13`, official=false. Supply the same public feedback and
676-line Astroid source; newly available caller source is selected by the model.
Use `gpt-5.4-mini-2026-03-17` xhigh, repository `.env`, one run with a $1.20
invocation cap. Keep 16 ordinary responses, one correction, 24 model tool actions,
two helpers, one optional original selection and three additional edits. Input
60K, outputs 40K/25K, shared model/intermediate-check deadline 600 seconds; final
public and isolated evaluation each 390 seconds. Count immediately before every
dispatch, SDK retries zero, stop all work on execution/transport/count/billing
uncertainty. A started row cannot be repeated; unused money does not authorize it.

After every accepted edit, return current-diff original-call feedback before the
next model response. Final public controls/regression and isolated evaluation
remain separate outcomes. All old allocations are closed. Fresh exact execution
approval follows concrete preparation and read-only preflight.

## Interpretation and decision criteria

Record whether the model selects the dependency scope, obtains the relevant caller
source, uses an execution observation when needed, makes a first edit, and revises
from failed original-call feedback. Report repair of the original behavior, public
regression and isolated acceptance separately, with cost/time and invalid requests.
Source delivery alone is mechanism uptake, not repair success.

The historical run is context, not a concurrent randomized control. This single
trial cannot isolate schema routing, search feedback and acquisition cost or
establish a general improvement. If direct source access is offered but unused,
the acquisition-interface explanation weakens. If source is acquired but no
justified edit follows, investigate the remaining diagnosis/decision bottleneck.
If an edit leaves F0010, inspect public execution evidence and the actual changed
path before proposing more budget. If the trial repairs the task, retain the
capability for broader controlled evaluation without claiming general adoption.

## Validation and preparation receipts

Focused validation: 79 PASS, 3 SKIP in 48.85 seconds; Ruff and whitespace checks
PASS. The skips are Windows actual-symlink fixture creation without link privilege.
The equivalent file/ancestor/root reparse-metadata rejection tests pass. Tests
cover dependency source acquisition, bounded pages/search, provenance, scope
feedback, edit isolation, same-action replay, changed-file rejection, hydration,
context handoff and the existing post-edit feedback loop. Receipt:
`C:/pt/tmp/depscopefocus27.xml`.

The public Pylint bundle has 125 registered Python-source files. A source-only read
of `pylint/lint/expand_modules.py` returns 5,329 bytes with its pinned hash. This
checks availability without importing or executing that package. Dependency search
skips files between 1 MB and 2 MB after verification; a file above the 2 MB backend
read ceiling fails the request. The fixed Pylint bundle does not reach this limit.

Fast suite: 472 PASS in 106.52 seconds, including isolated mock evaluation.
Receipt: `C:/pt/tmp/depscopequick27.xml`. Ruff and whitespace checks PASS.
The focused check stays below two minutes. These results support local mechanism
and compatibility claims, not actual model uptake or task repair.

Fresh offline preparation and exact paid-execution approval follow this
implementation commit. No provider call or target execution was made during
implementation and local validation.
