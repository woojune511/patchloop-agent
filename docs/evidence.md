# Evidence and limitations

Evidence guides problem selection and tests whether a change helps the agent solve
tasks. There is no predetermined memory-effect or other method claim to establish.
This page describes interpretation rules and evidence locations; run narratives
belong in [history](history/README.md). The latest decision-relevant result belongs
in [current status](current-status.md).

## What each observation establishes

| Evidence | Supports | Does not establish by itself |
| --- | --- | --- |
| Local deterministic tests | Implemented contracts and reproduced defects | Live model decisions or provider acceptance |
| Mock end-to-end | Tool, recovery, submission, and isolated evaluation wiring | Autonomous task solving or Docker safety |
| Actual model input and receipt | What was delivered, with identity and currency | Effective use or correct interpretation |
| Registered public checks | Their actual assertions on the checked diff | Complete requirement or regression coverage |
| Isolated acceptance result | Acceptance of that submitted artifact under that task contract | Generalization or a method's causal benefit |
| Controlled comparison | A bounded estimate under its fixed tasks/settings/resources | A general success rate from a small familiar panel |

Local reproduction and regression checks can settle deterministic defects. Use a
bounded comparison when uncertainty about model behavior requires one. Count task
correctness, regressions, completion, cost, and time separately. Notes, probes,
valid declarations, and delivered context are diagnostic observations, not success
criteria. Report observed behavior separately from inferred causes.

## Result boundaries

- Distinguish planned, started, submitted, evaluated, and accepted work. NOT_RUN,
  infrastructure/preflight failure, and executed task failure are different results.
- Keep task acceptance and safety verdicts separate. Mock safety NOT_RUN is not PASS.
- Keep implemented, locally tested, live-executed, and claim-producing evidence separate.
  Every current run is `official=false`; the claim-producing lane is disabled.
- A supplied repair, operator-selected verification case, or reused familiar task
  does not demonstrate autonomous discovery or generalization.
- A passing check or correctly linked source does not validate a model-authored
  expectation. A durable audit journal does not establish cross-run learning.
- Input counting and generation are separate operations. Record uncertainty as
  uncertainty; never infer settled billing or transport success from a missing receipt.
- Byte/line reduction in documentation is not a measured token, latency, or agent
  performance improvement. That requires observing actual use.

## Preparing public regression checks

A required base regression must not demand behavior that the public issue explicitly
asks to change. Establish the conflict from the public issue and original public
source alone; reference success or private test membership is not a selection rule.
For a mixed test, retain its unaffected assertions rather than excluding the whole
test or module. A task-specific operator projection may isolate only the conflicting
expectation in the temporary check copy. Preserve original workspace/test bytes and
record the exact projection and its public rationale in a separate package/evidence
record. Bind the original test-file hash and unique edit anchor; input drift is an
infrastructure error, not permission to skip a check.

Keep original private tests, reference patches and scoring unchanged. Validate base
and reference controls, and show that a deliberate regression in the retained behavior
still fails. Removing an obsolete regression expectation does not add a public oracle
for the new behavior: record that coverage boundary explicitly. This is reviewed task
preparation, not a solver tool or automatic rule for disregarding failing tests.

## Where evidence lives

### Recorded public uses

| Case | Original artifact | Later work, kept separate |
| --- | --- | --- |
| Click #3362 | Usage wrapping repair; test writing was outside the request | Human-written tests are not autonomous test-writing evidence |
| dotenv #715 | Implementation plus useful model regression case; external red/green confirmation | Common verifier replay of the same patch, not another solve |
| Click #2786 | Issue test passed, but omitted callback/validation was bypassed | Model corrected the regression after public review feedback |
| Click #2740 | Notes test passed on 3.12, but unguarded add_note was incompatible with 3.10 | Model corrected test compatibility; 3.10 and 3.12 checked |
| dotenv #713 | Requested file synchronization sequence and selected tests checked | Scoped code-review candidate; power-loss durability not demonstrated |

Sources: [three uses](history/2026-10-05-three-public-repair-uses.md),
[original review](history/2026-10-05-original-patch-review.md),
[feedback corrections](history/2026-10-05-click-feedback-results.md), and the
[portable saved dotenv evidence](../examples/saved-repair/README.md).
The [public review packet](../examples/reviewed-repairs/README.md) contains original,
correction and final patches with sanitized verifier JSONs.
The three-use original code review yielded one candidate and two modifications;
the two corrections do not retroactively make the first attempt 3/3 successful.
Human final approval and active review time remain unreported. The user reported
that reading the diff alone was insufficient to judge correctness; this is a
qualitative review burden, not measured time savings.

For Click #2740 the correction-only verifier returned `UNSUPPORTED` because it
changed an existing test body. The upstream-based composed patch was supported:
3.12 failed before/passed after; 3.10 passed both. Python 3.11 itself was not run.
These are different comparisons, not a replacement of UNSUPPORTED with PASS.
Full project suites and unlisted environments remain unverified; independent
acceptance for these public repairs remains `NOT_RUN`.

### Benchmark measurements

The [dev20 rerun](history/2026-10-06-portfolio-dev20-results.md) resolved **9/20** at
USD 3.46111455 versus [historical](history/2026-10-02-lite-dev20-results.md) 10/20
at USD 5.01124395. Same mini, roster and USD 1.20/task cap; current runtime.
All twenty submitted; evaluations agreed and cleanup was confirmed.
Transitions: nine PASS->PASS, one PASS->FAIL, ten FAIL->FAIL; no evaluation errors.
[Public JSON](../examples/portfolio-dev20/results.json) records costs, times and
receipt/patch hashes. Eight environment corrections and two public-check projections
remain limitations. This exposed dev panel is not a Lite test or causal comparison.
Below 11/20: test300 NOT_RUN. Allocation closed; no retries or case diagnoses.

- [Current status](current-status.md): current implications, unresolved questions,
  and links to the latest relevant validation and experiment records.
- [Documentation history](history/README.md): retained investigations and byte-exact
  pre-split narratives. Search the index and matching sections on demand.
- External run/validation/analysis roots: append-only journals, artifacts, exact
  inputs, cost records, and detailed local validation reports; follow the recorded path.
- `reports/`, `experiments/`, and `docs/archive/`: immutable historical material,
  never current operational authority. Existing bytes must not be rewritten.
- Task- and fixture-local audit files: evidence for that package, not universal guidance.

Record a significant investigation once: problem, public evidence, hypothesis,
change, executed checks/results, limitations, and unresolved question. Preserve
original failures and negative results. Link exact external evidence without
copying private evaluator details into development-agent context. Update the
current snapshot with the consequence, not a second copy of the narrative.
