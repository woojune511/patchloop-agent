# First reproduction: description-only A/B preparation

Status: implemented, locally validated and sealed; paid collection NOT_RUN.
Official=false; development-exposed Astroid-1333, not a held-out comparison.

## Problem and discriminating question

The [fresh processing-evidence run](2026-10-28-processing-evidence-fresh-results.md)
completed six public read/search actions, then exhausted 40K ordinary and 25K
correction output before a usable original `run_probe` request. Inputs were below
the 60K ceiling; no target or edit executed. This makes first-request construction
a correctness/reliability bottleneck before the new host checks can be exercised.

The first-original-only tool had an 8,958-character description containing helper,
replay and post-repair guidance. Those actions were unavailable at this stage.
The leading hypothesis is that irrelevant instructions add construction burden.
Alternatives include intrinsic difficulty selecting discriminating observations,
insufficient public caller evidence, and the fixed model/reasoning configuration.
The recorded failure alone does not identify which caused output exhaustion.

## Change and fixed contracts

`patchloop/dev/first_reproduction.py` supplies a compact description only for
`original_acquisition_pending`. It preserves exact environment facts, in-process
calling APIs, fixture/output separation, distinct failure/desired observations,
same-call failure/processing rules, actual silent-target observations and handling
of incomplete captures/exceptions. It removes instructions for unavailable stages.

JSON parameter schemas, required/null fields, tool availability, host validators,
acquisition/repair/completion limits and saved invocation semantics stay unchanged.
Generic/helper and path-diagnosis descriptions remain unchanged. Surface v66 binds
the new prose; invocation v7 and diagnostic policy v2 remain unchanged. The exact
checkpoint description shrinks from 8,958 to 4,408 characters (50.8%); this is not
an input-token count. Frozen
pre-change wire hashes, with only this description excluded, verify the boundary.

## Comparison

Use `run_dev_3e21775752a54cae`, prepared-input event 65, before the failed model
dispatch. Reconstruct the same public messages and completed source/tool evidence
for both arms, excluding historical encrypted reasoning symmetrically. Fresh
continuation generated inside each new arm remains available to its ordinary
protocol correction. This is a
public checkpoint reconstruction, not literal replay of the historical request.
No post-checkpoint response, previous repair, chosen processing code, hidden test,
reference patch or evaluator result enters either model request.

| Fixed item | Selection |
| --- | --- |
| Task | dev-train/current-dev20/13, Astroid-1333 |
| Model | gpt-5.4-mini-2026-03-17, xhigh |
| Credential location | C:/Users/geonj/Documents/PatchLoop/.env; not read in preparation |
| Repeats | A once, then B once; old failure is not the new A |
| Intervention | A recorded long description; B compact first-original description |
| Context / ordinary / correction output | 60,000 / 40,000 / 25,000 tokens |
| Remaining model / tool / edit limits | 16 / 34 / 3; no edits in this diagnostic |
| Remaining solver time | 1,903 seconds; original 390-second evaluation reservation retained |
| New row / pair cost ceiling | USD 4.41415320 / USD 8.82830640; proposed, not approved |
| Policies | Original thin/segmented/acquisition/completion policies preserved |

The exact remaining cap preserves admission conditions; historical USD 0.08584680
before the checkpoint stays settled and is not billed again. Early diagnostic
stopping substantially limits the actions used; no unused allowance authorizes a
repair run. Count actual input immediately before dispatch, use zero SDK retries,
and stop the entire pair on accounting, transport, execution or cleanup uncertainty.

Each arm stops after its first settled original probe receipt, explicit stop or
terminal failure. Existing bounded protocol correction may precede that receipt.
Even a preflight rejection ends the diagnostic arm and is reported as request
failure, never target execution. No candidate edit, finish, regression or isolated
evaluation is scheduled. The schema and host still enforce original obligations.

## Outcomes and decision rule

Record valid tool-call completion, host admission, actual target entry, complete
capture, declared baseline-failure match and desired-value mismatch separately.
Audit intended-input processing and code selection against public evidence. JSON
generation or a model-declared match alone is not sufficient reproduction evidence.

A meaningful B advantage is reaching actual, interpretable original reproduction
where A cannot, under the same conditions and without a schema/host relaxation.
B producing a valid request that fails host validation diagnoses a later bottleneck.
Both failing weakens this description intervention on this checkpoint; both passing
leaves a single-pair causal effect unresolved. One pair cannot establish reliability,
repair gains, clean-start success or generalization. A model-setting comparison is
subsequent work only if these observations provide a reason.

## Local validation and artifacts

- Focused final owner/diagnostic/documentation selection: **22 PASS in 14.04s**.
  Covers schema-only change, preserved stages, offline/single-use preparation,
  count/dispatch identity, first-probe endpoint, fresh correction continuation,
  whole-pair uncertainty stops and cleanup uncertainty.
- Quick: **568 PASS in 62.16s**, including isolated mock evaluation. Two final
  wording clarifications followed it and passed the focused selection; the full
  quick suite was not repeated for those text changes. The description owner file
  is now included in quick. Ruff over runtime/tests/diagnostics PASS.
- Seven surface-identity owner checks passed in 2.82s. Frozen historical branches
  remain unchanged. Two stale generic schema fixture hashes were refreshed only
  after independently proving HEAD and current generic schema equality.
- Both actual-checkpoint preparation arms passed ordinary-runner scripted-stop
  rehearsal. Simulated counts/cost in those receipts are not actual API usage.
  They do not assert reproduction. Separate synthetic probe tests verify stopping.
- Source baseline: commit `5ea221da`; source runtime
  `sha256:1efe175d82fa407d1d91c144dfb9082f82e9052e3199bf0c224f563eaaeafca5`.
- Sealed plan: `C:/pt/first-reproduction-description-plan-v1/manifest.json`.
  Hash: `sha256:caeabc911f787aea417a704d024e21afc1f893e1460766b1d18afea7138fca25`.
  Runtime and all diagnostic Python contents are bound by the manifest. Ordinary
  host files have separate hashes; plan validation rechecks the pair and source.
- Public input hash: `sha256:a384af401ccee200e50bf6e27f710672c74de7c8d7fd94254ca17ffd2206d726`.
  Shared parameter hash: `sha256:6d5fd9137f0cb9fc4689ad590c450492f90234b520f85af637b85f2ebc3be0df`.
- Future collection entry: `C:/pt/first-reproduction-description-plan-v1/run.ps1`.
  Read-only validation entry: same directory's `validate.ps1`, executed PASS.
  Proposed fresh result root: `C:/pt/first-reproduction-description-run-v1`.
  The result root does not exist; no collection was started.

Provider calls, real input counts, credential reads and target benchmark execution
are zero during this preparation. Local mock execution is mechanism evidence only;
model uptake, task acceptance and repair efficacy remain NOT_RUN/not established.
The current decision is to test the description intervention while preserving the
stronger verification requirements. There is no result-based adoption claim yet.
