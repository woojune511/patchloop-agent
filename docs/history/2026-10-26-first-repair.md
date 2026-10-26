# First-repair original observation and small requests

Date: 2026-10-26. Implementation and local controls, official=false, claim-ineligible.
Base: `7d0966ef53e6530802094e4f8852ac8947407ac1`. No provider-backed execution.

## Problem and decision

The closed [first-mutation investigation](2026-10-26-first-mutation-analysis.md)
found unresolved candidate-path evidence after broad source exploration. A helper
fixture failed for both inputs; two later responses exhausted output without tools.
The post-edit diagnosis could not help before the first mutation. Action construction
also carried general decision/plan/memory fields. These are distinct possible
bottlenecks; local mechanics do not establish their causal contribution to the stall.

Implement an optional frozen original observation before the first edit and simplify
ordinary edit/correction construction. Keep direct supported editing and existing
original-replay/check completion requirements. Increasing output or global cost is
not part of this change. Both mechanisms must later be measured separately if a
causal effectiveness claim is needed.

## Change and boundaries

- `observe_original` accepts a hypothesis and 1-2 candidate functions with event
  predictions. The host supplies original identity, source hashes, parameters and
  executable lines. The entire frozen caller program, including its clean control,
  runs unchanged. The trace covers the selected failing call's begin/end window.
- Complete no-hit can contradict a path premise; unknown/truncated/source-changed
  observations cannot. Matched predictions concern trace events, not semantic proof.
  A caught exception or unwinding return is not classified as an escaping exception
  or normal return. Both-setup-failure and nondiscriminating controls get no credit.
- Hypothesis, prediction and result retain root/call/diff/source/request/execution
  identities. The following mutation links the observation action/status. It then
  becomes historical; fresh original replay and visible checks remain necessary.
- Fresh edits have six fields; fresh stops have two. Exact anchors, scope checks,
  rollback and legacy explicit annotation recovery remain. Absent annotations stay
  absent through parsing, transcript, gateway, attempt cards and recovery.
- Ordinary repair uses a compact public context. No-action correction gets a fresh
  segment with public evidence and the same remaining budget. Field/anchor failures
  stay typed. General note/plan review is absent from the repair request.
- Exploration preserves one optional observation using the maximum of the existing
  protected route and the minimum observe/edit/replay/check/finish route, not their
  sum. Model calls and physical actions remain separate. Direct edits can skip it.
  Existing run-global protocol correction funding is not replenished.
- An accepted pending observation reserves the one execution. Rejections permit
  one field correction. Durable rejected requests stay rejected; completed results
  reuse their receipts; uncertain dispatch never auto-retries.

## Local evidence

External append-only journal: `C:/pt/first-repair-local-v1`,
`run_dev_firstrepairlocalv1`. Final validation results and identities are recorded
there. Focused controls and the quick suite use public authored fixtures, with no
network/provider or evaluator image pull/build. Full suite and live model: NOT_RUN.

Initial local runtime content identity:
`sha256:455ef01742658f163efa881ae39f6b580ce58a719133f1c651501e2c502024ef`.
Final runtime after the reservation boundary fix:
`sha256:9c46be3bc3adcc184d3c50a997bbef3aec2687661e00f266ad49649315bf8833`.

| Phase | Result | pytest time |
| --- | --- | --- |
| `@tests/first-repair.txt` | 132 PASS | 19.16 s |
| `@tests/quick.txt` | 363 PASS, 11 FAIL | 85.14 s |
| Failed quick nodes after expectation/doc fixes | 11 PASS | 0.81 s |
| Final first-repair controls plus completion-resource owner | 154 PASS | 18.68 s |
| Ruff / diff whitespace | PASS | bounded local checks |

The 11 quick failures were old schema/prompt assertions and the current-guide byte
limit. Updated current expectations explicitly assert six/two fields and unchanged
memory-body content; frozen historical hashes stay intact. Condensed current
guidance within its existing 16,000-byte limit. No runtime changed between quick
and its 11-node targeted rerun. All 374 quick nodes have a passing result across
those phases; this is not a second whole-suite run. Focused/quick counts overlap.

A final source audit then found a real reservation gap after a rejected first
edit consumed mutation retry protection: when protected equalled minimum, helper
probes/tests could use the last physical observation slot, and diagnostic checks
could use its monetary slot. Applied the same exploration set to physical and
cost admission. Two-child tests share the same reserve at schema and batch admission;
mandatory correction stages take precedence. Added five exact model/action/money/
comparison-boundary controls. The final 154 PASS reruns all first-repair controls
plus the completion-resource owner after this runtime fix; quick was not repeated.
Quick's scripted smoke reached isolated mock acceptance; mock safety is NOT_RUN.
The fake-provider correction control reaches submission but intentionally gets
EVALUATOR_ERROR from its synthetic backend identity; that is not acceptance.

With brief-v1, compact schema characters are replace_text 1,397 (previous 7,063),
stop_task 610 (previous 5,814), and observe_original 1,200. These are serialized
character counts, not token/cost savings or measured model effectiveness.

Log hashes: focused `f11ffa5fd0a43894cf107f644cbf9ed129a947ca278984fb0751a594e170bc14`;
quick `ebcc90349a2b90d7d59b9535885e16d57a6b39c617e18181f77b9fec55dca9dd`;
delta `cd0e06f5bf1e8988df77ce16f4181418c6c9fa2ed4478e2c1cce4633ba23b4ac`.
No provider call, Docker startup/image build/pull, historical artifact change or
private evidence projection occurred. Pre-existing AGENTS.md and the untracked
pytest temporary directory were preserved. Full-suite and Linux CI remain NOT_RUN.

## Next question

Does the model use the preserved original observation to choose a useful first
edit within unchanged limits? The implementation and scripted local repair path
answer only whether the mechanism operates and recovers. They do not establish
model uptake, Astroid F0010 repair, independent benchmark acceptance or safety.
