# Clean-base public-observation A/B preparation

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: plan with offline implementation validation
- Origin Date: 2026-10-27
- Verification Status: PREPARED; live results NOT_RUN
- Version Label: selection-observation-pair-v1

## Question and selection reason

The [operator repair](2026-10-27-relative-root-repair.md) passed isolated acceptance.
Earlier model candidates changed downstream builder behavior while omitting the
actual child file. Does supplying unchanged-base selection/resolution/parsing
observations help the same model find an accepted repair? This tests a demonstrated
diagnostic gap without extending the failed seed or changing production policy.

## Fixed conditions

- Task: `tasks/dev-train/current-dev20/13/public.yaml`, Astroid-1333, dev-train.
- Both arms start from base `d2a5b3c7b1e203fec3c7ca73c30eb1785d3d4d0a`, empty
  diff, separate workspace and fresh conversation. No seed, old conversation,
  source anchors or 148-line builder-focused packet is imported.
- A: public issue and original clean-base call-1 F0010 observation. Its exact
  fixture contains `import os` and the original standalone control file.
- B: identical A packet plus three unchanged-base supplementary observations:
  missing-initializer directory, direct file, ordinary package. These use an
  invalid-syntax child and are explicitly distinct from the original fixture.
- Same thin request and registered reads/searches/probe/replacement/stop tools.
  A may acquire public observations using its own probe; access rights are equal.
- Same `gpt-5.4-mini-2026-03-17`, xhigh, default service tier, encrypted
  continuation, store=false, zero SDK retries. One run each, sequential A then B.
- Each arm: $1.20 cap, eight normal responses plus one protocol correction,
  twelve model tool actions, one diagnostic probe request, one accepted edit,
  40,000 ordinary / 25,000 correction output ceiling, 60,000 counted input limit,
  600 seconds including workspace/preflight and model work.
- Total cap $2.40. Each arm's cap preserves the other's allowance. Admission can
  narrow optional actions or lower normal output to retain successors/correction.
  Record this and treat budget/time cutoffs as censored evidence.
- Per produced candidate: 390 seconds for public host checks and then at most
  one isolated acceptance evaluation with its own 390-second budget.

The model snapshot, effort and rates were checked against the official
[model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini) and
[pricing page](https://developers.openai.com/api/docs/pricing) on 2026-10-27.
Registered rates per million tokens: $0.75 input, $0.075 cached input, $4.50 output.
Account availability, exact counts and local image preflight remain live checks.

## Evidence and leakage boundary

`C:/pt/selection-observation-plan-v1/packet-build/extract.py` projects the original
calibration base call and only `state=base` rows from
`C:/pt/namespace-selection-diagnostic-v1/results/result.json`. It checks receipt
and source CAS hashes, empty diff, complete capture, unchanged fixture and source
bindings. Fixture constants come from the actual public programs. Collection
checks sealed evidence hashes again.

A is 2,681 characters; B is 10,742. They contain issue/call facts, raw ordered
events, path lists and outputs. No patch, post-repair record, successful operator
result, relative-versus-absolute counterfactual, suggested fix or private material
is included. Actual `.` path entries remain observations. Removing B's sole
`additional_observations` field makes complete A/B requests identical, including
later-turn and correction construction. Operator provenance and host programs
never enter model input.

The packet was selected after the operator knew a successful solution. This is
assisted information availability, not autonomous acquisition, an unassisted fresh
solve or general accuracy. Added evidence also changes input length. Fixed order
and one sample per arm leave stochastic/time effects unresolved. Historical failed
runs are not the A control. Prior acquisition time is separate from new model costs;
the old six-probe duration includes operator rows and is not the exact cost of
acquiring only the selected base rows. No end-to-end speedup claim is possible.

## Validation and decisions

After one accepted edit, stop the model without feeding host results back. Replay
the exact original program on a fresh base and the candidate. Report call-1 input
identity, F0010 resolution, unexpected exceptions and standalone-control output.
Report call-2 input identity separately: cache files inside its observed root can
change after the preceding call. Do not silently turn that into call-1 mismatch.

Then compare five public semantic fixtures on fresh base/current code: empty
child, `import os`, invalid child, direct invalid child and ordinary-package invalid
child. Require matching inputs/caller conditions, child selection/parsing and
expected diagnostics; direct/package output must match base exactly. Run registered
base-regression on the same candidate. These added diagnostics are not benchmark
acceptance criteria.

The separate host evaluator runs once if registered regression passes, even when
an added diagnostic fails. Otherwise acceptance is NOT_RUN_PUBLIC_CHECKS under the
existing submission contract. Record acceptance, regression, scope, safety and
public diagnostics separately. The host submission is synthetic, not an agent
finish_task result. Secondary measures are changed functions, observation use,
first edit reached, actions, probe use, cost, latency and cutoffs.

- B alone succeeds: grounds for replication, not automatic policy adoption.
- Both succeed: added packet necessity is not established; compare cost/actions.
- Both fail: inspect evidence-to-action transitions and cutoffs before adding
  context, budget or machinery.
- A alone succeeds: inspect distraction and stochastic variation; one pair cannot
  establish a general negative effect.

No p-value or success-rate/generalization claim from this two-run comparison.

## Execution and provenance

Prepared root: `C:/pt/selection-observation-plan-v1`.
Future results: `C:/pt/selection-observation-live-v1`.
Credential path, unread during preparation:
`C:/Users/geonj/Documents/PatchLoop/.env`.

`run.ps1` contains the exact future command, sealed manifest hash and $2.40 cap.
`validate.ps1` is offline. This request authorizes preparation only; all previous
paid allocations remain closed. The manifest and validation receipt are external.

Code: `diagnostics/selection_observation.py`; reusable accounting loop with an
optional request builder in `exception_frame_repair.py`; bounded public helper in
`diagnostics/probes/selection_observation.py`; separate opaque subprocess in
`diagnostics/saved_candidate_acceptance.py`. Existing profiles preserve their
requests. Production runtime hash/defaults remain unchanged.

Monitor comparison/per-arm hash-chained dev-run-v1 journals, liveness and stage
deadlines. Count immediately before dispatch. Stop remaining arms on count,
transport, billing, cleanup, source/identity or evaluator uncertainty. Preserve
action_id/input_hash through the existing gateway. No uncertain-action retry,
result-root reuse, image pull/build or private-result model feedback.

## Preparation evidence

Offline only: packet re-extraction is byte-identical; 20 new-path/opaque-wrapper
tests pass in 4.43 seconds; existing diagnostic profile tests passed separately.
Quick suite: 472 passed in 102.91 seconds, including isolated mock evaluation.
Final Ruff, documentation and sealed-input checks are recorded in the external
validation receipt. No provider, token-count API, credential read, target Docker
execution or real acceptance run was performed.
