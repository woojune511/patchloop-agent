# PatchLoop on the mini-SWE dev20 roster

Date: 2026-10-16. Allocation CLOSED; official=false and claim-ineligible.
All 20 tasks were attempted once with the frozen PatchLoop runtime. Eighteen
submitted: 8 PASS / 10 FAIL, with agreeing registered/native grades and safety PASS.
Two reached their per-task cost limit before submission and remain NOT_RUN.
Fresh usage cost was USD 7.01172285; including the preceding mini experiments,
the conversation total was USD 13.27841505 of the authorized USD 24.

## Question, scope and conditions

The user requested our agent on the same problems and selected the full dev20
roster. The purpose was to establish a current bounded reference against
[mini's original panel](2026-10-16-mini-swe-dev20-results.md) and its
[separate completion work](2026-10-16-mini-swe-completion-results.md).
This is a comparison of complete agent configurations on an exposed development
panel, not an isolated test of planning, memory or shell access.

The [frozen contract](../../.agent/patchloop-mini-dev20.md) selected:

- Core runtime `fcfa496dfb57f7e0d79616e5389fac034cfbc6b2`; operator-only commit
  `22d8217fba31b2d85dec086e6f634d8d02c94774` preserves those runtime bytes.
  Execution checkout: `C:/Users/geonj/.codex/worktrees/patchloop-dev20/PatchLoop`.
  Subsequent primary-checkout changes were not evaluated by this panel.
- `gpt-5.4-mini-2026-03-17`, xhigh, desired output 25,000, default service tier/global endpoint,
  exact primary-repository `.env` file; one fresh trajectory per task, two workers.
- Same 20 public task hashes, base commits and local evaluation-image identities
  as mini. Native harness `02e7a74ffd0b707aab73d203fe87bdc7c76afc8e` remained pinned.
- Segmented-v1, result-or-size-v1, brief-v1, 24,000 retained source characters,
  ordinary probes, probe-policy/recheck none, repair-recheck, protected-v1 and
  per-call-v1. PatchLoop exposed its registered tools; mini's bash exception did
  not change PatchLoop's tool interface.
- Per task: 40 model calls, 100 actions, four accepted edits and 1,800 seconds
  including a 330-second registered-evaluation reserve. Native grading had a
  separate 600-second host allowance and 300-second test timeout.
- Prior mini spend USD 6.2666922; reserve USD 0.88 per task / USD 17.60 in total.
  Maximum cumulative liability was USD 23.8666922. Row allocations were fixed
  without transfers. Count immediately before dispatch, zero SDK retries, and
  stop on counting, transport, billing or cleanup uncertainty.

The cost cap was lower than mini's original USD 1.19987985 per task and actually
constrained two tasks. Thus this is not a fully matched resource comparison.
Solver environments, prompts, tools, edit limits, verification and concurrency
also differ. Original mini SQLFluff environments lacked public package metadata;
their frozen results retain that limitation. All five PatchLoop SQL environments
passed ordinary default-config, single-core-plugin and parse/lint canaries through
both public probe and registered-check execution before dispatch.

## Outcomes and accounting

| Axis | Fresh PatchLoop result |
| --- | --- |
| Planned / attempted / submitted | 20 / 20 / 18 |
| Registered and native acceptance, each | 8 PASS / 10 FAIL / 2 NOT_RUN |
| Registered/native agreement | 18/18 graded submissions; incomplete over the full 20 |
| Registered safety | 18 PASS / 2 NOT_RUN |
| Last recorded base regression | PASS on all 18 submissions; row 17 PASS, row 18 FAIL |
| Native cleanup | Confirmed on all 18 graded submissions; not run for two unsubmitted tasks |
| Generations / input-count requests / tool actions | 285 / 294 / 399 |
| Input / cached input / output tokens | 8,619,953 / 4,601,088 / 811,665 |
| Reasoning output tokens, included in output | 720,623 |
| Fresh usage cost | USD 7.01172285 |
| Prior mini cost / conversation total | USD 6.2666922 / USD 13.27841505 |
| Panel wall time | 4,456.635 seconds, about 74m17s with two workers |
| Billing and counting | Known for all 20; every one of 285 dispatches settled exactly once |

Wall time excludes preparation, the initial zero-call launch, audit and public
diagnosis. Mini's original run used one worker and took 57m33s, so these wall times
are operational observations rather than a controlled speed comparison.
Public regression PASS is not task correctness: ten submitted patches passed
their last base regression but failed both final graders.

Costs were reconstructed from provider usage at USD 0.75 uncached input,
USD 0.075 cached input and USD 4.50 output per million tokens, verified against the
[official model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini).
Uncached input, cached input and output contributed USD 3.01414875,
USD 0.3450816 and USD 3.6524925 respectively. These are usage-ledger amounts,
not invoice reconciliation. All responses reported the selected model snapshot.

Rows 17 and 18 stopped with COST_CAP_REACHED because the minimum next provider
request could not fit their remaining allocation. Neither was submitted or graded;
neither is a native FAIL. They used 28 calls / USD 0.87572205 and
24 calls / USD 0.8742096 respectively. Each had two calls below the desired
25,000-token output ceiling, reaching minima of 7,756 and 1,643 tokens.
No other row had a reduced output ceiling. Unused conversation budget does not
change these frozen outcomes; no continuation or replacement solve was launched.

## Task-by-task comparison

The completion column covers only mini's five separately extended tasks. A dash
means not included. Its larger limits and row-18 metadata correction prevent
pooling it into a uniform mini accuracy result. The original mini result remains
10 PASS / 5 FAIL / 5 NOT_RUN; its mixed final coverage remains 12 PASS / 8 FAIL.

| # | Task | PatchLoop | Mini original | Mini completion | PL calls | PL USD |
| ---: | --- | --- | --- | --- | ---: | ---: |
| 1 | marshmallow-1343 | PASS | PASS | - | 10 | 0.235068 |
| 2 | pvlib-1072 | PASS | PASS | - | 8 | 0.136638 |
| 3 | pvlib-1154 | PASS | PASS | - | 9 | 0.169124 |
| 4 | pvlib-1606 | PASS | PASS | - | 10 | 0.323633 |
| 5 | pvlib-1707 | FAIL | FAIL | - | 9 | 0.220628 |
| 6 | pvlib-1854 | PASS | PASS | - | 7 | 0.137037 |
| 7 | pydicom-1139 | FAIL | FAIL | - | 8 | 0.167835 |
| 8 | pydicom-1413 | FAIL | NOT_RUN | PASS | 16 | 0.416437 |
| 9 | pydicom-1694 | PASS | PASS | - | 12 | 0.298863 |
| 10 | pydicom-901 | FAIL | FAIL | - | 14 | 0.379982 |
| 11 | astroid-1196 | FAIL | PASS | - | 14 | 0.401764 |
| 12 | astroid-1268 | FAIL | FAIL | - | 14 | 0.279086 |
| 13 | astroid-1333 | FAIL | NOT_RUN | FAIL | 36 | 0.589732 |
| 14 | astroid-1866 | FAIL | PASS | - | 10 | 0.128512 |
| 15 | pyvista-4315 | PASS | PASS | - | 10 | 0.278851 |
| 16 | sqlfluff-1517 | FAIL | NOT_RUN | FAIL | 14 | 0.347425 |
| 17 | sqlfluff-1625 | NOT_RUN | NOT_RUN | FAIL | 28 | 0.875722 |
| 18 | sqlfluff-1733 | NOT_RUN | NOT_RUN | PASS | 24 | 0.874210 |
| 19 | sqlfluff-1763 | FAIL | FAIL | - | 11 | 0.375519 |
| 20 | sqlfluff-2419 | PASS | PASS | - | 21 | 0.375659 |

On the 15 tasks graded in both original panels, eight passed both, five failed
both, and mini alone passed rows 11 and 14. PatchLoop alone passed none.
That is a useful observed difference within these runs, not evidence of a general
ranking. Mini used 524 generations and USD 3.2146974 for its original fresh panel;
PatchLoop used fewer generations but more cost per generation overall.
The comparison does not isolate the cause of that difference.

For historical context, the earlier full PatchLoop remeasurement was
[9 PASS / 11 FAIL](2026-10-06-portfolio-dev20-results.md), and the later
[corrected panel](2026-10-06-corrected-dev20-results.md) was
11 PASS / 7 FAIL / 2 NOT_RUN, followed by a separate two-task failing supplement.
Their original grades remain unchanged; none are pooled into this fresh result.

## Public diagnosis of the two original-mini wins

After every solver had closed, six provider-free probes compared base source,
the submitted PatchLoop source patch and mini's submitted patch on rows 11 and 14.
The programs used only public issue text, source and generated patches. They did
not execute private evaluators, access hidden test details or supply feedback to
any solver. Successful probe exit means the observation completed, not that the
observed library behavior was correct.

- **Astroid-1196:** both patches fix lookup through a constant dictionary
  reference. For an uninferable reference (`{**MISSING}`), PatchLoop leaks
  NameInferenceError, whereas mini yields the usual AstroidIndexError requested
  by the public issue. PatchLoop iterates `value.infer(context)` outside its
  exception handler; mini uses `helpers.safe_infer` before dictionary lookup.
- **Astroid-1866:** both patches handle the reported TypeError from formatting
  None with `:s`. Public examples involving a missing attribute and an invalid
  format specifier still raise AttributeError and ValueError under PatchLoop;
  mini returns Uninferable for both. PatchLoop added only TypeError to the
  handler, while mini also covered AttributeError and ValueError.

These controls demonstrate concrete public gaps in the submitted PatchLoop
patches. They do not establish the exact private assertion responsible for either
grade or explain all ten failures. The cost cap did not bind either of these rows.
The resulting question is how the agent selects verification beyond the reported
example; this measurement does not identify a particular runtime intervention.

## Startup failure, validation and evidence

The first launch at `C:/pt/plmini20prep01` / `C:/pt/plmini20live01` closed before
any input count or model generation. Row 1's image lookup returned no identity,
and row 2 stopped through the shared admission barrier. Cost was zero. The runtime
did not retain the underlying lookup diagnostic, so timeout or a missing image
must not be asserted as the cause. All 20 images were subsequently verified as
local, and a two-process check of the exact preflight passed. No image was pulled
or built. A separately bound observer then recorded Docker image-inspection
results without changing retries, timeouts, return values or exceptions.
The actual panel's 40 observed image lookups all succeeded, at most 0.5761s each.

The zero-call attempt was preserved. The second launch used fresh state and the
same frozen runtime, limits and already verified preparation evidence; no model
trajectory was repeated. Preparation artifacts were copied byte-for-byte with an
explicit reuse receipt, not represented as newly executed tests.

- Frozen checkout validation: 30 focused tests PASS in 16.79s; full suite
  5,152 PASS / 19 SKIP; Ruff PASS. Selected-policy mock reached EVALUATOR_PASS
  with zero actual provider calls/cost; mock safety remained NOT_RUN.
- Primary integration and closeout: 13 focused operator/documentation tests and
  Ruff PASS. History-index labels were shortened to retain its existing byte
  budget; historical report contents were unchanged.
- All 20 public import, ordinary-operation and selected-test canaries passed.
  All five SQLFluff public probe and registered-check environments passed the
  added metadata/config/plugin/parse/lint checks. An initial diagnostic API call
  was incompatible with the older native Python; that original failure and the
  compatible diagnostic were retained separately. No agent runtime change resulted.
- Post-run audit revalidated the launch files, manifest, runtime, public task
  and dependency bindings, native identity and prior mini closeout hash. Journal
  chains, dispatch/settlement identities and per-generation price arithmetic
  matched. No billing or counting uncertainty remained.
- Runtime hash: `sha256:83ea374981b5f0c65935b13e0fd1c3270d0e85a0830fe47c863a6f5e2553d144`.
  Packet: `sha256:928ea46ebe0686bdeebcf92dc30d207860afa100b77555e75e3975b713f81595`.
- Preparation/results: `C:/pt/plmini20prep02`; live state:
  `C:/pt/plmini20live02`; audit: `C:/pt/plmini20audit01`.
  Key records: `comparison.json`, `final-boundaries.json`, and
  `public-contrast01/result.json`. The comparison retains full instance IDs,
  costs, caps, grades, safety, cleanup and original evidence hashes.

The decision is to retain this as an 8/20 bounded development-panel reference,
with two cost-limited non-submissions, and preserve the observed public patch gaps.
It supports no quality-gain claim or automatic policy adoption. No further paid
run, held-out evaluation, ungraded-task continuation or runtime tuning was executed.
