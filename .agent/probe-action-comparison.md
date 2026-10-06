# Ordinary action replay: bounded checkpoint comparison

Status: preparation authorized; paid execution NOT_RUN. Every row is official=false.

## Question and selected state

Does removing the need to reconstruct a past probe program lead the agent to verify
its current patch against the public requirement, reject a wrong repair, and repair
it? This is an interface comparison, with no new task-specific verification advice.
Existing unit/mock tests establish program reuse, not autonomous verification.

The read-only audit of the two funded SQLFluff continuations selects B2's prepared
boundary 526, immediately after base-regression PASS and before its finish decision.
Source: `C:/pt/sretcl01/2`, run `run_dev_984d4340fa4e43d3`.
The public probe `call_YcnJuf5oV8ffOwrmGNBweCbB` at events 253/254 calls the full
public fix API and asserts the issue's WITH indentation plus the plain SELECT case.
Its program left the recent-probe window, but its ID remains in the current
verification observation catalog. Current replay resolves the exact recorded code.
The target ID/program are operator audit metadata; do not add them to model input.

Earlier B2 boundaries 493/507/511 do not offer probes. At 526 they reopen, with five
model calls, 50 tool actions, three edits, 162 solver seconds and 330 evaluation
seconds remaining. Preserve these limits. B1's boundary 509 has four calls and 427
solver seconds, but its visible full-pipeline probe prints observations without
asserting the required indentation. Keep B1 as audit evidence, not another paid row.

## Fixed comparison

- Exact task: `tasks/dev-train/current-dev20/18/public.yaml` (dev-train).
- Model: `gpt-5.4-mini-2026-03-17`, xhigh, 25,000 desired output tokens.
- Context: inherited segmented-v1, brief-v1, 48,000 retained source characters;
  preserve the parent's notes, plans, encrypted continuation and public evidence.
  This does not change the selected general 24k baseline.
- A: ordinary inline probes; omit replay_action_id and its description, require
  question/source strings. Reject a non-null replay selector even if unoffered.
- B: current ordinary action-ID replay. All later turns retain their assigned arm.
- Order: A once, then B once; two continuations of one exposed task, not two tasks.
- Proposed fresh allowance: USD 1.20 per row, USD 2.40 invocation-wide. Historical
  funds stay closed. Cap is a ceiling, not an estimate or a promise of completion.
- Credential path: repository `.env`; preparation checks path/existence only.
- Fresh roots: preparation `C:/pt/parpairprep01`, collection `C:/pt/parpairlive01`.
  Root reuse is forbidden, including after interruption. Run serially because the
  diagnostic installs process-local hooks. No retries or automatic continuation.

`diagnostics/probe_action_comparison.py` reuses current-runtime restoration,
count-before-dispatch admission and the ordinary action loop. Both arms retain all
observation catalogs. Offline scripted stops capture actual first requests, assert
that the only A/B difference is the run_probe schema, and bind those requests in a
manifest. Elapsed-time fields are normalized for the comparison; actual deadlines
still spend time. No historical probe executes during restoration.

Prepare and inspect before authorizing collect. Bind the exact source prefix,
candidate, public program, runtime/collector, model, credential path, first request
hashes, repeats and new cap. Read-only preflight checks only existing local images;
never start Docker or pull/build images. A manifest is not paid authorization.

## Judgement and stopping

Report separately: schema admission; autonomous replay/other public verification;
whether the returned full-path result contradicts the current patch hypothesis;
whether the agent changes that hypothesis/patch; regression checks; submission;
isolated acceptance and safety; calls, time and newly billed cost.

Replay count or regression PASS alone is no improvement. If B uses the exact probe
and discovers the wrong patch but cannot repair it, that supports verification use
only. If neither arm checks the requirement, the feature's behavioral benefit is
unestablished. If both repair, this pair supplies no incremental repair benefit.
Only B's verified repair with A's failure is a local positive signal warranting a
separately designed fresh-task measurement, not a general success-rate claim.

The short inherited time/call allowance may censor repair; report budget stops and
unrun evaluation separately rather than treating them as wrong answers. No allowance
extension or additional arm follows automatically. Stop the whole pair on count,
transport, billing, continuation or cleanup uncertainty. Keep evaluator data and
the later operator diagnosis out of model inputs. One pair cannot separate model
sampling variability or execution order from the intervention with confidence.
