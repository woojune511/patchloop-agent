# Helper-path information at the saved Astroid failure

Date: 2026-10-22. Origin: ARS experiment-agent / run, code_plan_v1.
Status: preparation; no new diagnostic or paid outcome yet.
The user explicitly requested execution of the preceding two-stage design.
This authorizes the four public diagnostics and, only after their information and
compatibility gates pass, the six specified continuations. Prior allocations remain closed.

## Question and reason

The prior caller-evidence comparison supplied the original input, environment,
call trace and missing/present controls, but repair was 0/6 in both arms. Related
initial investigation occurred in all six supplied-observation continuations;
scope drift also began while the original tuple remained visible. Thus more
detail is justified only if it resolves a concrete missing execution fact.

The old observer did not collect `file_info_from_modpath` or `_spec_from_modpath`.
Distinguish a helper reached with different inputs/branches from a helper bypassed
by the original caller. A repeated `source=True -> file_build` observation is
insufficient. No reference patch, hidden assertion or evaluator internals may be
used to select observations or judge this information gate.

## Stage 0: four public probes

Driver: `uv run --locked python -m diagnostics.helper_path_probe --output C:/pt/helperpath22-g0`.
Freeze order: missing-off, missing-on, present-off, present-on. Reuse the exact
base source and public Pylint 2.12.2 dependencies from the original observation.
The old caller profiler remains common; ON adds bounded line/return observation
of the two helpers, selecting modpath components `src` or `project` and counting
all calls to those helpers. Record caller location, inputs, executed source lines,
whitelisted state changes, exception types and returns. No arbitrary repr/locals.
Zero recorded calls is interpretable only within this explicit coverage and with
no observer overflow. It does not establish global unreachability.

Keep normal public probe isolation and limits (30s, 512MiB, 8,000 source characters,
12,000 output bytes); do not pull/build images or start Docker automatically.
Compare the complete common caller observation after normalizing the independent
temporary root. Require unchanged outcome, arguments, configuration, environment,
call sequence and child analysis. Missing must retain F0010/exit1 and no child
get_ast; present must retain exit0 and child get_ast. Bind source/dependency/image
identities; report any historical wrapper/profile difference explicitly.

Stop on altered behavior, incomplete collection, truncation, timeout, unconfirmed
cleanup, unchanged information, or no distinction between the proposed explanations.
No retry/replacement or expansion after examining outcomes. The information gate
requires a cited public review, not a program flag claiming semantic novelty.

## Conditional paid comparison

Task: tasks/dev-train/current-dev20/13/public.yaml (Astroid-1333, dev-train).
Prefix: run_dev_f1a28479931d443f through event341, hash
`eaf6e01ef57a1df862d728dbd5367dc76736d6b695ba7811f93a4969fe304596`.
Base: d2a5b3c7b1e203fec3c7ca73c30eb1785d3d4d0a; empty diff.
A receives the original caller packet; B additionally receives only qualified new
helper observations. First input only, ordinary later retention. Same task/source,
tools, prompt, inherited state and limits in both arms. No reviewer, forced probe,
automatic recheck, pinning or finish rule is added. Packet length/attention/cost
are part of the intervention; do not claim an isolated semantic-information effect.

Model gpt-5.4-mini-2026-03-17, xhigh, desired output25000, standard/global,
store=false, zero SDK retries. Credential path C:/Users/geonj/Documents/PatchLoop/.env.
Order A1 B1 B2 A2 A3 B3. Three continuations/arm, no matched-seed claim.
Each retains 16 model calls, 76 actions, four edits and 1,530,158ms including 330s
evaluation reserve. Historical cost0.37263270 is bookkeeping, not billed again.
New cap0.50736730/row, 3.04420380/group; no transfer, top-up, replacement or resume.
Count immediately before dispatch, using freshly reviewed prices. Uncertain
count/transport/billing/cleanup stops every remaining row.

The past runtime hash differs from current dev-head. Do not bypass strict resume
or alter the historical packet. Qualify an explicit diagnostic fork at one final
current commit, including restored budgets and common-input equality. If this
cannot preserve the specified comparison, stop rather than silently substitute a
fresh solve, other checkpoint, different model or historical runtime.

## Measurement and decisions

Freeze public action/claim annotations before opening new acceptance grades.
Primary: successful repairs among all three assigned rows per arm. A successful
repair requires registered/native acceptance plus both original public caller
conditions on the same submission; child file analysis must actually occur.
Keep NOT_RUN and evaluated FAIL separate. Secondary: first supported action change;
helper/scope/source-currency overstatements; cost/time/calls and actual input
evidence displacement. Report unsupported claims alongside NO_CLAIM/noncompletion.

Exploratory advancement requires B>=2/3 repairs, B>A, two evidence-linked behavior
changes and no normal-control regression. This permits consideration of a separate
multi-task study, not product adoption or statistical/general-quality claims.
Accurate uptake without repair gain stops further trace expansion. Non-use does
not support information shortage. Fewer claims through noncompletion is not gain.
Everything is official=false and claim_eligible=false. Persist generated evidence
outside the repository with immutable CAS and append-only dev-run-v1 journals.
