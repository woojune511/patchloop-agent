# Pydicom saved candidate: public logging repair and changed opt-in output

## Material Passport

- Workflow: academic-research-suite experiment-agent, authorized local execution.
- Status: four public comparisons COMPLETED; official=false, claim-ineligible.
- Question: does the saved candidate preserve user logging configuration, and
  how does its existing `debug()` behavior differ from the original?
- Inputs: the unchanged base and submitted task-10 candidate from the
  [five-task panel](2026-10-29-repair-five-results.md).
- Evidence: `C:/pt/pydicom-public-logging-v1/plan.json`, `summary.json`, four raw
  receipts and the hash-chained `run_dev_pydicompubliclogging` journal.
- Provider calls, credential reads, new repairs and private evaluations: zero.
  These operator results were not injected into a repair model.

## Why this question

Pydicom-901 was the panel's only acceptance failure despite public-check PASS.
The saved patch directly removed the import-time handler/formatter attachment and
default-level override requested by the public issue. That leaves two plausible
explanations to distinguish: it may still fail the public symptom, or it may fix
that symptom while changing existing behavior or missing additional acceptance
expectations. A larger model budget would not distinguish those explanations.

The public description asks clients to control logging configuration. Existing
`config.debug(debug_on=True)` documents debug on/off through the pydicom logger.
The inspected public material does not specify a new debug argument or signature.
Therefore, default console emission is measured as a compatibility observation,
not asserted as a newly invented requirement. Previously observed private
acceptance details remain separate external evidence.

## Frozen comparison

Base commit: `3746878d8edf1cbda6fbcf35eec69f9ba79301ca`.
Candidate patch: `sha256:fa293020945696d0e7a604cf14b9f11d7846543afefe80cb3431932ee847e4bb`.
Both sources were mounted read-only, with no existing package bytecode. Their
commit, patch, config bytes and untracked state were checked before and after.
Actual imported module paths and config hashes were checked inside each process.

Four fresh processes used the same program and existing pinned task image,
Python 3.6.13, no network, no image pull/build, 15 seconds per process and a
95-second overall execution deadline. The same two scenarios ran on base then
candidate. Total diagnostic time was **12.471 seconds**, without timeout,
truncation, cleanup failure or retry. No original/candidate source was changed.

1. **Configured:** before import, attach a user StreamHandler/StringIO formatter
   to the pydicom logger and set DEBUG. Record logger/root state before and after
   import, then emit a unique WARNING marker. WARNING is intentional: the base's
   level override would suppress a DEBUG marker and hide duplication.
2. **Unconfigured:** begin with no root or pydicom handlers, import, call the
   existing one-argument `debug(True/False)` and emit separate DEBUG markers.
   Record levels, flags, handlers and actual output.

Stderr capture starts before import, so a StreamHandler's captured stream is not
missed. Import messages are recorded separately from markers. A public-only
reviewer checked the design and results without private evaluator logs. The
parent had seen earlier private failure details; this is an operator diagnostic,
not a blinded or independent performance sample.

## Observed results

| Observation | Original | Saved candidate |
|---|---|---|
| Configured logger after import | DEBUG changed to WARNING | DEBUG preserved |
| Configured handler count | User handler plus new library handler: 2 | Same user handler only: 1 |
| Configured WARNING marker emissions | 2 | 1 |
| Recorded user formatter/root/propagation state | User formatter/root/propagation preserved; logger changed | Recorded state preserved |
| Unconfigured `debug(True)` marker emissions | 1 | 0 |
| `debug(True)` level / flag | DEBUG / True | DEBUG / True |
| `debug(False)` level / flag | WARNING / False | WARNING / False |
| DEBUG marker after `debug(False)` | 0 | 0 |

The configured candidate satisfies all five measured public checks: recorded
logger and root state preservation, exact user handler preservation, one user
marker and no extra stderr marker. The original fails the logger/handler/extra
output checks. Thus this public scenario demonstrates a real repair of import
configuration interference and duplicate emission.

The unconfigured candidate retains level/flag switching but emits no default
DEBUG output because the previous library-attached output handler is gone.
This confirms the suspected change in existing opt-in usage. It does not prove
that a default output handler is required by the public issue, or that every
logging environment is correct. Root-handler-only configurations, repeated
imports/reloads, concurrency and other sink arrangements were not exercised.

## Interpretation and decision

Keep the original benchmark **FAIL**. These local observations neither rerun nor
override it. They distinguish three statements:

- The candidate repairs the measured public import symptom.
- An existing no-configuration debug-output behavior changes, while the existing
  on/off level and flag behavior remains intact.
- The previously retained original-oracle failure includes further expectations;
  the public diagnosis alone cannot establish or reconstruct all of them.

This weakens a blanket explanation that the agent failed to understand or repair
the reported symptom. The model still submitted without executing either public
logging scenario; this operator comparison does not retroactively become solver
verification. It also does not prove that mandatory reproduction would have made
the candidate pass every benchmark expectation.

Keep model, budget and submission rules unchanged. No new tool, hard gate or
hidden-derived API hint is justified by this comparison. If a future intervention
is considered, its public question should concern checking the reported behavior
and affected existing usage together; whether that improves acceptance needs a
separate controlled test. This turn makes no agent/runtime change or new paid run.

## Validation

The two external diagnostic scripts passed scoped Ruff (E501 excluded) and syntax
checks. Four actual isolated public executions and a read-only receipt review
validate the observation. Result docs receive the five documentation tests and
`git diff --check`. The unchanged runtime's prior focused/quick/mock evidence is
reused; no broad runtime suite or hidden evaluation was repeated.
