# Latest SQLFluff patch: public rejection and preservation comparison

Date: 2026-10-30 KST. CLOSED. Operator diagnosis, no model or independent evaluation.

## Why and what was compared

The [latest fresh run](2026-10-30-retained-source-sqlfluff-results.md) delivered the
relevant source and directly tested token reconstruction, but did not verify the
changed success meaning against rejection conditions. Earlier counterexamples
belong to a different two-branch patch. The user requested confirming the remaining
defects in the latest one-branch patch before another agent-system intervention.

Candidate: `sha256:cd24a748b205fed40320032d91f0927ab68f219d909958884e61052128a146f7`,
from `run_dev_bd9bf1f93aeb41aa`. It changes the zero-length-element return in
`src/sqlfluff/core/parser/grammar/delimited.py` and adds a grammar test. No operator
repair was applied. The baseline uses the pristine implementation with the identical
agent-added test file, isolating the implementation change. Both receive the same
eight-case program and public test fixture. Expectations were frozen before execution
from public Delimited guards/options, MatchResult and existing grammar tests.

The two adjacent-delimiter cases target the changed branch. Two cases exercise
unchanged failure branches; four provide normal/option controls. Matching success
and raw input preservation are measured separately. A diagnostic process exiting
zero only means observations were collected, not that these contracts passed.

Fresh root: `C:/pt/retention16-public-comparison-20261030-v1`.
One execution per condition using the already-installed, digest-pinned task image
and registered public-copy wrapper, with its command pointed at the public program.
Python 3.9.20, no network or image acquisition, overall 120-second deadline,
70-second condition ceilings and 40,000-byte output limits. This is a public
operator run in the task image, not execution of private evaluation. The preceding
model helper used the separate Python 3.12 probe environment; the paired conditions
here share one environment and do not measure that helper's environment effects.

## Observed result

| Input and condition | Expected match | Original match / preservation | Latest match / preservation |
| --- | --- | --- | --- |
| `bar..`, trailing forbidden | False | False / lost | **True / preserved** |
| `bar..`, minimum 3, trailing allowed | False | False / lost | **True / preserved** |
| `bar.bar`, minimum 2 | False | False / lost | False / lost |
| `bar.foo.`, trailing forbidden | False | False / lost | False / lost |
| `bar.bar`, minimum 1 | True | True / preserved | True / preserved |
| `bar.bar.bar`, minimum 2 | True | True / preserved | True / preserved |
| `bar.`, trailing allowed | True | True / preserved | True / preserved |
| `bar.`, trailing forbidden | False | False / preserved | False / preserved |

The first two rows reproduce new success-condition regressions in the exact latest
patch. It returns matched `bar.` plus unmatched `.`, so reconstruction succeeds,
but the nonempty matched prefix makes the result truthy despite the rejection
condition. Preservation and match eligibility are distinct obligations.

The next two rows retain earlier input-loss defects in unmodified branches: the
minimum failure returns only `bar`, and the invalid-element failure returns only
`foo.`. These are not new regressions introduced by this patch. The four controls
remain unchanged. No aggregate success-rate or coverage claim is derived from the
hand-selected eight cases.

Both conditions completed without timeout, truncation or cleanup failure. The
loaded grammar hashes match the exact baseline/candidate bytes. Elapsed time:
42.551 seconds; model calls: 0; independent evaluation: NOT_RUN. No retry occurred.

## Decision and limits

The concern is now an observed public defect in this latest patch, not merely an
untested option. Keep the host source-retention and finish-description fixes; this
comparison does not modify the runtime or repair the submitted task patch.

The prior agent's positive preservation test did not settle whether a failure path
may become success. The next general improvement question is how the repair review
selects checks for that semantic change using already-delivered public conditions.
Existing guidance already asks for this distinction; these results alone do not
justify another generic warning, check quota, automatic reviewer or paid repeat.

This is operator-designed evidence. The agent did not discover or execute these
cases, and they must not be injected into a fresh solve as if discovered there.
The exact private failing assertion and the model's capability ceiling remain
unknown. No hidden tests, reference patch or private evaluator content was opened.

## Evidence

Operator commit: `656f6ae17532fe51422b1ef645d77687628638c7`.
Runtime, unchanged:
`sha256:c70488eef7bf533d471d47396d213edec62783d754016c4fadc1115de2a7b728`.
Program:
`sha256:b4a1726bc78b437610be8a0e99569f25dacd4273b83495d918a79e4c70dc873a`.
Summary:
`sha256:06b844aace874988c43974c525825228cb61b14b23011bfa311ccf811052d3e7`.
Comparison-completion journal event:
`sha256:618dc526052219ee4085371c248715a7905f939108458ea0f9f1880d24d0acd4`.
Baseline grammar:
`sha256:027a5eb2b20d20511fc13298594516b1c76159af25d902aea7e317a5fd222173`.
Candidate grammar:
`sha256:788c2d6ce790d69d87e5f92cdacea09aa43f2e1103c2e396deb9ee97be2a2a18`.
Common agent-added grammar test file:
`sha256:d03222949d9d481bb6ddb7c983c1569ee5e2ed038ac810f80f9990508cdc7194`.
