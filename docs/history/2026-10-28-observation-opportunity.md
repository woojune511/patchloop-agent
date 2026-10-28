# Original-call observation opportunity and pre-target request evidence

## Material Passport

- Date: 2026-10-28; implemented on dev-head from `8c54d993`.
- User authorized proceeding with the preceding analysis's structural fixes.
- Scope: implementation and short offline verification, official=false.
- No paid model, benchmark-target or Docker/evaluator-image execution. Synthetic
  local fixtures and pure replay are separate from live repair evidence.
- Actual F0010 repair efficacy and model use of the new choice remain NOT_RUN.

## Problem, evidence and decision

The [clean-start analysis](2026-10-28-autonomous-fresh-analysis.md) found a concrete
decision bottleneck. After acquiring the original failure, the model could inspect
source but could not observe execution. The first-observation selector required
diagnostic rules, while the saved case used null rules. General probes were rejected
under protected failure-recovery cost even though a successful minimum path fit;
reads could release that speculative reserve. The subsequent two downstream edits
failed to establish real fixture processing before tool capacity ran out.

The same run's helper settings failure happened before a call row existed and
remained an UNKNOWN obligation. Deleting arbitrary unknown cases would weaken
verification; treating proved request construction failures separately is narrower.

The intervention restores model choice with consistent resource accounting. It
does not prescribe a source fix, require tracing after every read, increase any
cap, or make observation satisfy original-failure verification. Larger context
alone was not selected: the relevant caller file and first negative feedback had
already reached the model. Better opportunity is not evidence of better repair.

## Implemented behavior

### Select a captured original call without diagnostic rules

`first_observation.py` accepts a healthy unchanged-base acquired original with null
rules. The small schema adds a required `call_id` enum drawn from up to four
complete captured calls. The connection between that selected call and the failure
is labeled model-selected/unverified. Existing rule-based automatic selection and
its original wire shape remain available.

The host replays the frozen original program and controls; source-derived parameters
and bounded trace events stay attached to the selected call. Binding, observed
failure JSON, call identity, conditions and paired captures must remain equal.
An admitted selection fixes the call identity for execution and recovery. Missing
or invalid selections share the existing two-rejection allowance; one actual
execution is not renewed by a new action name, changed selection or restart.
The next edit can reference the observation; it still needs fresh verification.

`tools.py` binds the selected call into the admission receipt, and `runner.py`
passes current first-observation state into the actual provider tool schema.
This last connection is tested through a normal scripted request, not only a
direct schema-unit invocation.

### Let observation use a funded minimum completion path

For known original failure without pending correction or required diagnosis,
completion-recovery admission prefers a protected later-failure route. If that
does not fit, it can use an explicitly reported successful minimum route for
source inspection, general probe and the first original observation.

General probes conservatively retain one prospective new original case: the
current probe, repair, each existing/new original replay, required checks and
finish all consume their real resources. A missing source anchor also remains.
`observe_original` reuses a registered case and does not invent a new one. Source
inspection and general probes preserve an available first observation's response,
action and timeout. Model calls, tool actions, role-based output costs, execution
time and the unused protocol correction must all fit simultaneously.

The current response cannot spend the reserved successor path. Protected recovery
is retained when feasible and its release stays explicit. No next repair is promised
to succeed, and another unsuccessful repair can still exhaust the finite budget.
Other completion-cost policies and specialized correction paths are unchanged.

### Distinguish settings rejection from unknown target execution

Fresh invocation channel v10 adds host `request_phase` metadata:
`settings_rejected` and `target_entries`. The latter must agree with the validated
call rows. Settings rejection before the first row can therefore be recognized
without inferring absence of execution from an empty trace or matching an error
message. Exact action/input/binding and settled complete host execution/cleanup
receipts remain prerequisites.

Only cases whose related actions all prove pre-target failure become
`request_attempts`. An entered call, pending action, missing/malformed stage marker,
truncation, timeout or cleanup uncertainty keeps the case obligation. Attempts
still consume action, acquisition and monetary limits and grant no reproduction
credit. Corrected requests need their own healthy baseline and candidate evidence.

Stored v1-v9 observer programs remain byte-identical; old empty v9 traces are not
retroactively erased. The v10 host program fits the existing8K cap, including the
longest entrypoint and optional trace hooks. Existing v9/v10 signature-bound
argument correction uses the receipt's actual channel and keeps its old limits.

## Verification and meaningful failure found during integration

The first pure audit of saved public state114 showed a remaining integration
failure: general `run_probe` opened, but activating the new ruleless selector made
`observe_original` and reading fail protected cost admission. The failed result
is preserved under `C:/pt/observation-opportunity-local-v1/`; it is not rewritten
as success. The final correction applies the same observation-preserving minimum
path to reading and the already-bound first observation as well.

Local controls cover positive selection and negative identity/capture cases,
request rejection and completed-result recovery, each resource boundary, real
synthetic settings errors, legacy bytes and original argument correction.
The normal scripted request test sees the dynamic enum, selects a call, observes,
edits and submits. Its synthetic provider/image fixture deliberately ends in an
evaluator identity error; the separate quick-suite isolated mock smoke is the
evaluation-path check. Neither is a live-model repair result.

The targeted rerun selection is `tests/observation-opportunity.txt`. Quick includes
the inexpensive selection and admission controls plus existing pre-target and
isolated mock checks. A stale v1 diagnostic-overlay test discovered during owner
regression was updated to the current v2 frozen required-check registration contract;
it no longer assumes the removed policy override. No historical result was changed.

Final verification on the frozen runtime:

| Check | Result |
| --- | --- |
| `uv run --locked --offline pytest @tests/observation-opportunity.txt -n 4 --dist loadfile --max-worker-restart 0` | 79 passed in32.73s; `C:/pt/tmp/obs-focus28-v1.xml`. |
| `uv run --locked --offline pytest @tests/quick.txt -n 4 --dist loadfile --max-worker-restart 0` | 792 passed in88.09s, including isolated mock evaluation; `C:/pt/tmp/obs-quick28-v1.xml`. |
| `uv run --locked --offline ruff check patchloop tests` and `git diff --check` | PASS. |
| Saved-state policy audit v2 | PASS in about2.12s, pure calculation only. |

All test basetemps were short, unique directories outside the repository. The
focused and quick selections each stayed below two minutes. Additional owner
checks covered frozen invocation bytes and v9/v10 argument recovery; their counts
overlap and are not added into a larger total. No full regression or live pilot
was performed.

The corrected audit under `C:/pt/observation-opportunity-local-v2/` reuses the exact
public context, counters, remaining USD3.861695,13 response slots,31 action slots
and original cap/limits at sequence114. It preserves the old v9 UNKNOWN obligation.
With recorded first-observation state, the new policy opens the general probe.
With the current ruleless selection projection, it offers read/search,
`observe_original` and `run_probe` together. It verifies unchanged historical
journal/envelope bytes and binds the current runtime source hashes.

- Preserved v1 failing audit:
  `sha256:42e7c1f8225f7d30f0b71598fc99743ad606101adbc8ede17c8032efd796829b`.
- Final `audit.py`:
  `sha256:bbac1cfde25298e9fbd6d1cb60f8f355e46cf2aab25f072d48b84f8fc7edd590`.
- Final `audit.json`:
  `sha256:fd89673f99a3260a80c3d85a42e642413b74e7e949c77452de1e524e15a2f3b1`.

This is a source-bound mechanism comparison, not a live counterfactual repair.
The saved historical run and its failed outcome remain unchanged.

## Evidence boundary and next question

The implementation addresses observed action availability and evidence accounting.
It does not establish that the model will select informative caller functions,
interpret returned file lists correctly, revise its hypothesis, or solve Astroid.
The model still needs to check actual fixture processing, not only error absence;
no task-specific answer or prior successful patch is added to its context.

Only after these local controls pass would a newly authorized same-budget live
trial measure actual uptake, repair, original behavior, public regression and
delivery separately. Earlier allocations remain CLOSED; no provider run is
prepared or funded by this implementation request.
