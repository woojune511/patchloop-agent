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

## Where evidence lives

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
