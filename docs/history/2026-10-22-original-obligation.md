## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run
- Origin Date: 2026-10-22
- Verification Status: UNVERIFIED
- Version Label: exp_result_v1
- Scope: local engineering controls; no research-quality or live-model conclusion.

# Original obligation, bounded acquisition and explicit delivery

## Problem and selected question

The [fresh Astroid pilot](2026-10-22-original-case-live-results.md) acquired zero
original cases and submitted after regression PASS. The original public caller and
independent acceptance failed; the normal input passed. Acquired-case replay alone
could not affect a run with no acquired case. This repeated caller/helper gap affects
correctness and made submission success an inadequate account of verification.

The selected requirement was to retain missing original evidence from the public
task, offer a bounded acquisition opportunity, and return an unverified patch honestly.
The [pre-execution protocol](../../.agent/plans/original-obligation.md) compares
acquisition off/on with the same delivery policy. The baseline is c1019854fa7bf6dd683366dd736cfebce9e91dc6.
Model capability, issue interpretation and acquisition opportunity cost remain
alternative explanations for the live failure. These controls do not resolve them.

## Implementation

- A public-task hash binds the unmet obligation independently of plans, notes and
  helper results. `bounded-v1` records an immutable root in the ordinary journal.
  Acquisition statuses distinguish no attempt, incomplete setup, no reproduced
  failure, and an acquired unchanged-base mismatch. Normal-only PASS gives no
  failure credit. Mapping and expected values remain model-authored/unverified.
- Opt-in `--enable-probes --reproduction-acquisition bounded-v1` offers at most two
  original attempts or six read/search/probe actions before edits. Direct gateway
  calls enforce the stage. Duplicate replay and rejected edits do not spend its
  investigation allowance. Global model/action/time/cost limits still apply.
- The stage releases without success credit when its bound is reached, probes are
  unavailable or another investigation would spend protected completion resources.
  Admission includes the extra future replay/recovery cost of acquiring one case.
  Real-loop budget releases are durable; forecast previews do not write state.
- Fresh invocation v2 captures actual `sys.argv` as well as the existing caller,
  arguments, cwd and selected fixture/environment identities. Different argv is
  incomparable. The v1 observer and complete wrapper retain their exact bytes.
- Finish returns `cases_verified_delivery` only after an unchanged-base failure and
  current support for all selected cases. Missing/incomplete evidence returns
  `unverified_delivery`; a current comparable refutation still rejects finish.
  Required-check PASS, delivery and independent acceptance remain separate.
  Terminal/repair recovery derives delivery from the same durable successful finish
  and patch hash; even evaluator PASS cannot upgrade missing original evidence.

The acquisition flag defaults to `none`; no new live policy was selected or funded.
Public repair currently has no probes and therefore returns `unverified_delivery`
with acceptance `NOT_RUN`. This change adds no semantic judge or unrestricted tool.

## Local experiment

Command (exit 0):

```powershell
uv run --locked python -m diagnostics.original_obligation_experiment --output C:/pt/original-obligation22-local/confirmed
```

Four fixed public CSV conditions, each with acquisition `none` and `bounded-v1`;
truthful delivery is enabled in both. Candidate implementations and probe programs
are scripted. Each pair has the same final patch hash. The trusted local subprocess
backend simulates probe-container receipt identities; this is not Docker evidence.
Each operation has a 10-second bound and the invocation a 180-second bound.

| Condition | Acquisition off | Bounded acquisition |
| --- | --- | --- |
| Helper only | Early edit accepted; unverified delivery | Early edit rejected; six investigations release; unverified delivery |
| Original failure and correct repair | Selected cases verified | Selected cases verified |
| Original failure and wrong repair | Current refutation rejects finish | Current refutation rejects finish |
| Two normal baseline matches | Unverified delivery | Two-attempt release; unverified delivery |

All eight controls passed in 95.255 seconds, with zero model/provider calls and
USD 0. Correct repairs replayed both original and normal cases. Every repeated finish
executed zero additional probes. Independent acceptance is `NOT_RUN` for these rows.
Counts are protocol assertions, not eight independent repairs or an accuracy rate.

The earlier `final/` run also passed 8/8 in 67.150 seconds. Subsequent review found
two untested boundaries: a malformed purpose could poison projection/recovery, and
acquiring a new case could consume protected replay resources. Both were fixed and
covered by focused tests before the explicit `confirmed/` follow-up. Keep both runs;
do not pool them or interpret their timings as a speed comparison.

Evidence root: `C:/pt/original-obligation22-local/confirmed`.

- `protocol.json` semantic hash: `sha256:b6ce4457275efdb7284c26d4039aae74cf5f9b03791783acecf9e241872629f1`.
- Protocol file hash: `sha256:0415f44e52a931edba656671cb36a7a2376cf853f58431981e97d850a2181317`.
- `result.json` file hash: `sha256:2ae7226a4269ee8876731930ef9101c0c8ac3956eac2c2336f90c1ce9706add2`.
- Runtime identity: `sha256:07c5217f67a3ac8e447b4af568c3967ba0e2e291334f99cb047924677a05a498`.
- The protocol retains 97 source hashes, including its public fixture, runtime and
  selected test-backend files. Per-row journals are append-only/hash-chained;
  result receipts and exact programs/diffs remain external.

## Validation and remaining question

Final focused acquisition tests: 11 PASS in 38.62 seconds. Additional malformed-input,
successor model/tool/cost budget and phase-admission tests: 13 PASS; with the existing
budget-release integration, 14 PASS in 8.06 seconds. Delivery metadata tests include
metadata-only evaluator resume and independent PASS with unverified delivery.
The v2 invocation tests cover changed argv, caught SystemExit and legacy bytes.

CLI mock smoke `run_dev_28b3255b6a4c4015` at
`C:/pt/original-obligation22-local/smoke` reached isolated evaluation: acceptance PASS,
safety NOT_RUN, `unverified_delivery`, cost USD 0. It used four scripted model turns,
five tool actions and no provider requests. This is separate from the eight-row test.

The final Windows regression coverage contains 5,697 collected nodes: 5,677 PASS,
20 declared SKIP, zero missing nodes and zero unresolved failures. This is composed
coverage from the full invocation and matching-file rechecks, not one passing full
invocation. Runtime and diagnostic source bytes remained unchanged across phases.

| Phase | PASS | FAIL | SKIP | Seconds |
| --- | ---: | ---: | ---: | ---: |
| Initial full suite, four workers | 5,649 | 28 | 20 | 4,137.198 |
| Quick selection | 312 | 0 | 0 | 1,025.795 |
| Final feedback wording file | 15 | 0 | 0 | 31.686 |
| Five current-identity files | 133 | 0 | 0 | 380.864 |
| Short-path recheck | 1 | 0 | 0 | 2.818 |
| Five wording/fixture files | 53 | 0 | 0 | 66.548 |

The initial failures comprised 15 old current-head hash/prose expectations, 11
source-rebinding tests whose abbreviated `SimpleNamespace` was not a `PublicTask`,
one 260-character Windows temporary-file path, and one interrupted Git execution
whose descendant cleanup was unknown. Current assertions were updated without
changing frozen-arm identities, and the source fixture now uses the actual public
task contract. The path failure passed with a short base directory. The interrupted
Git case passed in the 133-test recheck; the runtime's fail-closed stop was retained.
The feedback test file changed after full-suite collection, so its final 15-test
run supplies coverage instead of the old collected assertions. No runtime limit or
verification requirement was weakened to obtain these results.

Skipped tests require host symlink support, a supported planning/context combination,
or explicit real-execution/dependency prerequisites. The quick suite ran concurrently
with the full suite; these timings are not a performance comparison.

Validation evidence: `C:/pt/original-obligation22-local/validation`. Its hash-chained
journal retains source inventories and result references. `full-coverage.json` maps
every collected node to a result with matching final test-file bytes; the JUnit files
retain the original failures and skips.

- Coverage hash: `sha256:6e8d382cefabce519520d8b3229addf57245058ed53bef293e1011a6d3f058f3`.
- Final source-inventory hash: `sha256:ffe84c25649814b15bf0cabec759c767d039065c20b451e17b73328168da3804`.
- Ruff, documentation layout/link checks and `git diff --check` passed after the
  final test/document edits.

Decision: retain the locally tested mechanism, without claiming an LLM repair gain.
The bounds 2/6 are provisional. A model may still spend the phase on helpers or choose
an unfaithful case. The remaining question is whether the bounded phase improves
faithful acquisition and repair under the same live budget, including its opportunity
cost. No paid run, Linux CI or generalization claim was executed or authorized.
