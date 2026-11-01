# Source-ready seeded repair: preparation

Date: 2026-10-27. Status: PREPARED AND USER-AUTHORIZED; official=false.

## Material Passport and question

ARS experiment preparation using the same public Astroid-1333 first failed candidate
and current-profile observations. Can the model produce a supported revision when
the current exception and relevant public source are available at its first turn?

The [preceding comparison](2026-10-27-exception-frame-repair-live.md) stopped both
arms at four responses without an edit. B retained the complete exception chain
but spent those responses inspecting builder/manager code. It did not exhaust
context, output or cost. This justifies testing a feasible repair opportunity from
the saved state before another fresh solve.

This is a single feasibility run, not another A/B effect estimate. It jointly
changes source availability, current-failure presentation and the response horizon.
A positive result cannot isolate which change helped. A negative result with no
edit remains different from an executed candidate that fails the original call.

## Fixed inputs and intervention

- Task: public dev-train `current-dev20/13`, Astroid-1333.
- Seed: the first failed candidate, diff `9914a973...`; no later model repair or
  private evaluator/reference material enters the request.
- Calibration: `C:/pt/exception-frame-calibration-v2/calibration.json`, hash
  `sha256:82529d87a5cc86e00d5c1ca670fc54a37ab0a4969a406b90766996109b2027fc`.
- Runtime remains `5753dbef...`: this preparation changes diagnostic code only.
- Initial evidence: existing complete exception chain and bounded raw public source.
  The operator observes workspace ranges through registered reads, preserving edit
  anchors. Dependency excerpts are read-only and bound to the prepared public
  dependency inventory and original file hashes. No proposed repair is supplied.
- Model/settings: `gpt-5.4-mini-2026-03-17`, xhigh, normal/correction output ceilings
  40K/25K and input ceiling 60K, unchanged from the previous model comparison.
- One run, eight ordinary responses plus at most one protocol correction, twelve
  model-requested tool actions, one diagnostic probe and one accepted source edit.
  Initial host source reads are recorded separately from model-requested actions.
- New invocation and single-run cap: USD 1.20. Exact repository `.env` credential
  path; 600 seconds for preparation/model actions, then 390 seconds for host checks.

Eight responses provide twice the previous inspection horizon, while the source
packet removes the already-observed locating/reading work from the model's initial
burden. This is a bounded engineering choice, not a guarantee of a candidate.

## Outcomes and stop conditions

Record whether a candidate is produced, which source is changed, whether its stated
hypothesis connects to the observed exception, and the actual original-call outcome.
After one accepted edit, stop model generation and run the frozen original/control
program plus registered public regression on that candidate. Require identical
original program/input/environment, no unexpected target exception, unchanged
control and public regression PASS before reporting support for this public case.
Disappearance of F0010 alone is insufficient. Submission and independent task
acceptance are outside this diagnostic; no general repair-rate claim is possible.

Stop on the first accepted edit, model stop, admitted count/action/time/cost limit,
or exhausted correction. Count/transport/billing uncertainty and unresolved external
execution or cleanup stop the invocation without automatic retry. Prepared manifests
bind the profile, source packet and implementation. No image pulls/builds occur.

## Readiness

Existing probe and public-regression image identities were checked locally and
matched. The exact credential path exists; its contents were not read. The source
packet at `C:/pt/source-ready-packet-v1/packet.json` contains eight excerpts, 148 lines
and 5,140 source characters. Six workspace reads registered current edit anchors;
two dependency excerpts remain read-only. Its hash is
`sha256:3997b006bea64990518c288c3bc2e1fa48a80d2d1e0f1d93929dbe76ce83d69b`.

Prepared manifest: `C:/pt/source-ready-repair-plan-v1/manifest.json`, hash
`sha256:49f8be0b833c33c511bb83031cba1c8a6909b6d3ef55cc83c7e4faf23a726968`.
The actual first request is 60,871 UTF-8 bytes, with `current_failure` and
`source_packet` in its first user message. This is a byte count, not a token estimate.
Preparation and validation used no credential read, token-count request, model call
or target execution. Exact-runtime calibration was reused without replaying it.

Focused operator/source/docs checks passed in 13.46 seconds. They include source
drift rejection, registered-anchor edits, an edit after the fourth response,
profile caps and helper-hash binding. Existing default A/B first requests were
reconstructed and matched the saved request bytes. Quick472 passed in 40.05 seconds,
including isolated mock evaluation; Ruff passed. Receipts are in
`C:/pt/source-ready-local-v1/summary.json`. Execution remains NOT_RUN at preparation.
The user approved the exact manifest and USD 1.20 single invocation; that answer
is recorded in the preparation root's authorization journal. Results will be a
separate record, with no reuse of historical unused funds.

Exact command after authorization:

```powershell
uv run --locked --offline python -X utf8 -m diagnostics.exception_frame_repair collect --manifest C:/pt/source-ready-repair-plan-v1/manifest.json --approved-manifest-hash sha256:49f8be0b833c33c511bb83031cba1c8a6909b6d3ef55cc83c7e4faf23a726968 --approved-cap-usd 1.20
```

Output root: `C:/pt/source-ready-repair-live-v1`. No resume or automatic repeat.
