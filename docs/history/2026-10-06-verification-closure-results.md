# Verification closure: public replay, manual-case comparison and interface fixes

The investigation followed the [trace comparison](2026-10-06-agent-trace-comparison.md)
and the user's approval to implement its prioritized plan. All work is
`official=false`, claim-ineligible and development-exposed. The paid allocation is
closed; no retry, resume, default-policy adoption or further panel is authorized.

## Problem and decision

Earlier failures retained known public examples and available verification tools,
yet often submitted after broad public checks without testing the changed behavior.
This matters because passing those checks did not establish task correctness, while
matched-task cost had increased. Plausible explanations included an unresolved known
bug, a repaired reproduction with other semantic gaps, and failure to choose an
available verification action. A missing context item or tool was not assumed.

First replay the already-authored public programs against saved candidates. Only if
an assessable replay found an unresolved reproduction would a bounded fresh-solve
comparison test whether exposing existing saved/manual probe cases helped. This
separates the value of an available counterexample from a model choosing to use it.
The earlier completion-advice comparisons did not justify repeating that ablation.

The result preserves the ordinary-probe baseline. B did not meet the prespecified
success threshold and never exercised saved-case replay. The evidence neither
establishes benefit nor rules out benefit when that mechanism is actually used.
Another adjacent comparison needs a new evidence-based reason, not the unused cap.

## Stage 1: seven provider-free public replays

Exactly seven sequential probes ran in fresh source-only workspaces under
`C:/pt/vcr06`, each with a 30-second bound. The 1517/1733 programs were the original
agent-authored reproductions; 2419 used exact public message examples and a COALESCE
negative control. No hidden test, private spec, reference test patch or evaluator
content was used to construct or run these programs.

| SQLFluff task | Base | Saved candidate | Meaning |
| --- | --- | --- | --- |
| 1517 | Original RuntimeError reproduced | PASS | Original crash removed; broader semantics untested |
| 1733 | CTE indentation was 9 spaces rather than 8 | FAIL, same discrepancy | Known public reproduction remained unresolved |
| 2419 | Generic message failed exact examples | Earlier successful patch PASS; latest failed patch FAIL | Latest backtick quoting missed the public single-quote contract |

All seven executions were assessable, with no timeout, truncation, setup error or
cleanup uncertainty. COALESCE control passed in all three 2419 variants. The 24
classifier checks and independent replay audit passed. Wall time was 130.586 seconds;
provider and evaluator calls were both zero.

The gate passed on **1733 only**. This weakens the broad explanation that every
failure would have been caught by simply replaying its original probe: 1517's saved
candidate already passed that probe. These are operator replays of saved artifacts,
not fresh solves and not additional benchmark successes.

## Stage 2: frozen fresh-solve comparison

Frozen source was `29ff6e4f86895a89df2301f0294c6d99dae125de`, runtime
`sha256:040699254997d7461ec16fc09f6d79e369249b510c34ba6de70ad438fb3f937c`.
The packet hash was
`sha256:779af6ea6a01d68d304a83350c5bf238140695eceb4f2102f6dc28c245d14120`.
No source changes occurred before the allocation and its frozen-source audit closed.

- Tasks: exact current dev-train SQLFluff-1517/1733 packages, two repetitions per arm.
- A: ordinary `probe_policy=none`; B: existing `cases-v1` save/manual replay interface.
  Both had ordinary probes, additive/selected tests and `probe_recheck=none`.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh, 25,000 desired output tokens; repository `.env`.
- Shared policies: segmented-v1, result-or-size-v1, brief-v1, repair-recheck,
  protected-v1 and per-call-v1 admission.
- Each fresh state: USD 1.20, 40 model calls, 100 actions, four accepted mutations,
  1,800 seconds including 330 seconds reserved for registered evaluation.
- Four waves with two different tasks in parallel: 1517 A1/1733 B1,
  1517 B1/1733 A1, 1517 B2/1733 A2, 1517 A2/1733 B2.
- Total cap USD 9.60, no transfers, retries or resumes. Count/transport/billing/cleanup
  uncertainty, identity drift or registered/native disagreement stopped admission.
  Settled row-local budget exhaustion remained local.
- Native assessment was separate after each runtime, outside its 1,800-second limit.
  Public replay programs, patches and operator findings were not supplied to solvers.
- Positive result required B at least two successes ahead, no per-task count
  regression, and actual manual replay informing repair. No default adoption or
  general-performance claim followed even from a positive two-task result.

Preflight passed 22 lifecycle/schema/batch checks and 12 evaluation-reserve checks.
Fresh real-environment canaries covered public imports, ordinary operations and
selected tests for both tasks. A composed provider-free mock exercised failed
program save, durable recovery, source edit, model-chosen exact-source replay and
isolated evaluation with automatic replay off. Its 10.198-second PASS used synthetic
prepared dependencies and trusted local execution, not Docker/mini quality evidence.
The unchanged runtime reused its completed 4,277-pass/19-skip full-suite evidence,
whose interrupted main plus remainder coverage is recorded separately.

| Order | Task / arm / repetition | Registered / native | Calls | Probes | Edits | USD |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 1 | 1517 A1 | FAIL / FAIL | 26 | 0 | 2 | 0.42985215 |
| 2 | 1733 B1 | FAIL / FAIL | 15 | 0 | 1 | 0.31496895 |
| 3 | 1517 B1 | FAIL / FAIL | 15 | 0 | 1 | 0.33174480 |
| 4 | 1733 A1 | NOT_RUN / NOT_RUN | 36 | 9 | 1 | 1.17127350 |
| 5 | 1517 B2 | FAIL / FAIL | 18 | 0 | 1 | 0.32642355 |
| 6 | 1733 A2 | PASS / PASS | 25 | 3 | 1 | 0.60462030 |
| 7 | 1517 A2 | FAIL / FAIL | 19 | 2 | 2 | 0.41778420 |
| 8 | 1733 B2 | FAIL / FAIL | 35 | 5 | 1 | 0.88839450 |

A: **1/4 successes**, two graded failures, one cost-limited non-submission;
USD 2.62353015. B: **0/4 successes**, four graded failures; USD 1.86153180.
All eight started; all 189 generation calls and input counts settled. Total cost
was **USD 4.48506195**, wall time **2,935.179 seconds (48m55s)** including native
assessment and wave preparation. Seven submissions had agreeing registered/native
results and safety PASS. Row 4's evaluation and safety remain NOT_RUN, not FAIL/PASS.
No global stop condition occurred, and no additional solve was started.

All B rows received the extended schema. There were **zero saved programs, zero
case-ID replays and zero selected-test actions**. The mechanism is NOT_EXERCISED.
There were 19 ordinary probes: 18 before source changes and one after a source change.
The latter was A row 7, not a saved-case replay. This exposed, small comparison does
not establish that B is generally worse or that fewer probes are better.

## Public behavior findings

1. B rows 2, 3 and 5 authored no probe despite retained verification plans and ample
   time/calls. Row 2 promised a CTE regression; rows 3/5 promised double-semicolon
   verification. They submitted after 506 or 166 ordinary checks passed. Tool access,
   missing plans and exhaustion do not explain those choices. The delivered finish
   recommendation is correlated with submission; its causal role remains unproven.
2. A row 4 reproduced and isolated behavior, but also used nonexistent APIs, a
   mismatched setup and repeated tree inspection. Its first edit followed USD
   0.97814475 of spend. The edit failed one public regression (505 passed), then a
   25,000-output-token incomplete response consumed the remaining repair budget.
   The next counted request could not fit, so it stopped without submission.
3. A row 6 efficiently compared all rules, L036 alone and L003 alone, then changed
   L003's indentation arithmetic and passed acceptance. All three probes preceded
   the edit. Its final note nevertheless cited a pre-edit failing probe as proof
   that the repaired example worked. Acceptance proves this candidate succeeded;
   it does not validate that historical-to-current evidence claim.
4. A row 7 reproduced the original crash, changed source, and ran the actual issue
   input through the linter. The crash disappeared, but `check_tuples()` raised
   SQLParseError. It copied that candidate behavior into a task-level regression
   expectation and passed 167 public checks, yet acceptance failed. This was more
   direct than row 1's synthetic grammar test, but did not independently resolve
   the public issue's uncertain expected semantics. The later edit only added a
   test, so the post-source-edit probe remains real evidence despite its earlier
   full-diff hash. No hidden failure explanation was inferred.
5. B row 8 used five pre-edit probes, explicitly declining program save each time.
   One rule-isolation attempt used an unsupported argument; a later one obtained
   the same rule contrast as successful row 6. It chose a different L003 change,
   passed 506 checks and submitted without rechecking the example; acceptance
   failed. Similar observations did not guarantee the same repair or correct result.

The remaining question is how the agent selects independently justified expectations
and uses current versus historical evidence in its repair/submission decision.
Availability and retention alone were insufficient. This is not evidence for adding
memory, mandatory probe gates, more prompts or automatic replay by default.

## Stage 3: narrow interface corrections after the frozen comparison

The original trace review found a legitimate new Astroid regression blocked solely
by `pytest.param(...)`, and repeated invented concern IDs despite rejection feedback.
These are concrete interface frictions, separate from the unproven causal explanation
for failed task repairs.

New parameter additions accept direct `pytest.param` with literal positional values
and optional literal string `id`. New marks, aliases, unpacking, other keywords and
computed values remain unsupported. Existing parameter cases (including marks/IDs),
bodies, imports, fixtures and decorators retain structural preservation. Collection
indices still identify added cases; original tests are restored for isolated grading.

The concern-ID schema explains that null creates and returned IDs update. Guidance
was moved to that field with duplicate wording removed; the complete memory-update
schema stays within its existing 3,200-byte bound (3,198 bytes). Unknown-ID
feedback supplies a complete explicit-null example while preserving the original
statement on retry. It neither creates an ID implicitly nor changes recovery state.
These fixes do not alter the completed comparison or establish a quality gain.

Implementation commit: `5323a033`. Runtime:
`sha256:52bd5ca036bc876556b29e6f949fbfc67b7222445b3228015d0bb54b806a3c0e`.
No live run of these interface fixes is included.

Local validation:

- Focused additive-case, protection, concern and repair-comparison checks:
  **94 passed in 17.34 seconds**. The named case failed against base source and
  passed against repaired source with its index and original-test restoration intact.
- Final description/schema/order/size and documentation checks: **61 passed in
  0.94 seconds**. Three full-wire hashes were intentionally updated; description-free
  shapes, prompt, tool descriptor and run schema were preserved. Full Ruff passed.
- Complete four-worker suite: **4,306 passed, 1 failed, 19 skipped in 2,871.66
  seconds**. The sole failure still looked for creation guidance in the array
  description after that guidance moved to `concern_id`. Only that assertion was
  updated to check the new field and returned-ID guidance; **all 69 related tests
  passed in 0.26 seconds**. Runtime and all other source/test bytes stayed fixed.
  Final coverage is **4,307 passed and 19 skipped over the same 4,326 nodes**, using
  the completed full run plus this targeted follow-up, not an uninterrupted green
  full-suite run. Original failed output is preserved.
- Fresh mock smoke `C:/pt/vc06mock`, run `run_dev_580b29bdd6b948ab`, reached isolated
  **EVALUATOR_PASS**. Mock safety is NOT_RUN, spend zero; no live quality claim follows.
- Early local documentation-size and duplicated-schema-description checks failed.
  Current summaries were shortened and duplicate concern guidance removed without
  increasing existing byte limits. Those failed reports remain alongside final checks.

The final `closeout.json` verifies unchanged runtime bytes, maps full-run and
follow-up test identities, binds exact commits and report hashes, and records final
documentation checks. New dev20/test300 runs, Linux CI and remote publication are
NOT_RUN. No automatic follow-up is queued.

## Audit and evidence

Root: `C:/pt/analyses/verification-closure-20261006-v1`; preparation `C:/pt/vcp06`;
live states `C:/pt/vcl06/01` through `08`. All run journals are append-only/hash-chained;
historical roots and original NOT_RUN records were preserved.

- `replay/packet.json`, `result.json`, `audit.json`, `report.md`, `closeout.json`:
  seven saved-public replays. Packet file hash
  `sha256:f85437090ca0e82b22c31b7f0015bdc8bcb87417b57b425c62cc48a02f4fb2e1`;
  result file hash
  `sha256:4a99db51e625881c994b04313b42c85867d7712a99508c2a2f67e8f783aab0a2`.
- `diagnostic-gate.json`: binds the 1733-only gate; no provider/evaluator execution.
- `preflight-tests.xml`, `reserve-tests.xml`, `preflight-mock/closeout.json`:
  local preparation. Early preparation wiring/import failures were retained and
  corrected before any affected probe/provider dispatch; they were not live retries.
- `C:/pt/vcp06/manifest.json`, `authorization.json`, `result.json`, wave results,
  registered completion receipts and native assessments: exact scope, cost and grades.
- `comparison-audit.json`: original audit preserved with one overly strict
  no-error-code assertion. Row 4's fully billed output-limit response was legitimate
  under the existing bounded incomplete-response contract, not transport uncertainty.
- `comparison-audit-v2.json`: **1,064 checks, no issues**. Its narrow exception
  requires matched complete usage, exact admitted output ceiling, valid continuation,
  no tool calls and `incomplete_response/max_output_tokens`; other accounting gates
  remain unchanged. Fourteen predicate boundary tests passed. File hash
  `sha256:89d30b953d5226462b40ac3bf3a513484802e62fe8e9b96608e2153e28b3ed37`.
- `behavior-rows01-03/evidence.json`, `behavior-row04` through `behavior-row07`:
  public action/request analysis. Raw reasoning and hidden evaluation contents were
  neither read for behavior analysis nor passed into solver context.
- `behavior-final/evidence.json` and `report.md`: row 8 and synthesis with source
  journal and partial-analysis hashes. Evidence hash
  `sha256:070d7869bda5843bf5a824f3bc4c3673f95d9eba9156ff767767c8bd43274b09`.

The audit verified schema delivery, request hashes, model/prices, counting and
settlement, caps/order/concurrency, fresh state, recovery receipts, source-only native
projection, cleanup and grading agreement. Operator replay, mock execution, fresh
solves, local implementation tests and hidden acceptance remain distinct evidence.
