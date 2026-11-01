# Observation-value contract and bounded comparison feedback

Date: 2026-10-25. Local implementation and validation; official=false,
claim_eligible=false. No provider or Docker execution in this change.

## Problem and decision

The [native-call pilot](2026-10-24-invoke-live.md) captured the public F0010
diagnostic on stdout, but its authored predicate checked stderr. It declared
failure/desired objects with four/three fields, then recorded six fields mixing
diagnostic tails, execution outcome and exit code with the behavior predicate.
`outcome="returned"` and `exit_code=null` were actual call metadata; they were not
the declared semantic fail/pass or exit codes 32/0. Both exact comparisons
mismatched, and no normal-input control was constructed. This was selected because
original-failure acquisition failed even though native arguments and capture worked.

The comparator correctly refused credit. Its opaque mismatch did not identify
which fields disagreed. Better guidance and field feedback may help the model
construct an interpretable case, but that uptake is a hypothesis. A task-specific
misunderstanding of the API or selected channel could still defeat the intervention.
The subsequent 27 inspections without an edit are a separate unresolved problem.

## Change

Tool contract v53 keeps invocation v3 and all observer/program bytes. Guidance
uses small behavior values, with one extractor for failure/control before and
after repair, and leaves raw logs and call metadata in their existing separate
receipt. It distinguishes returned execution from task success and null SystemExit
code from zero, and instructs inspection of both streams before choosing a channel.

Healthy v3 comparisons include `comparison_feedback.desired` and, when declared,
`comparison_feedback.declared_failure`. These report missing/extra/type/value
differences at JSON Pointer paths. Each declaration is bounded to eight rows,
160 characters per path and 2,048 UTF-8 bytes, with explicit truncation/omission.
Values stay in the original binding and observation rather than being duplicated.
Type distinctions and signed-zero differences follow exact canonical JSON equality.

Feedback cannot change frozen declarations, grant failure acquisition, or certify
a channel/control. Unavailable comparisons receive no field feedback. A malformed,
duplicate, missing, truncated or unexpected observation stays unverified. Legitimate
failure/fix outputs may have different shapes, so no shape admission gate was added.
Legacy v1/v2 receipts, replay identities, history bytes, exploration and budgets
remain unchanged. Existing stored receipts are never recomputed.

## Local validation

Base commit: `a66ac6d6377736b608778bf22a93fe1730dc58e8` plus this change.
Validated runtime hash:
`sha256:6dd1cad5aeb16063857c28bb5df099cf52c75debb471d1ba1c57ba42ce5aaef1`.
External evidence: `C:/pt/observation25-local-v1/`, with `plan.json`,
`validation-summary.json`, JUnit XML, CAS artifacts and an append-only hash-chained
`runs/run_dev_observation25localv1.jsonl`. The journal binds the source snapshots,
public receipt identity, saved-JSON explanation and local test results. Summary CAS:
`sha256:59c52c9c2300b519c48632a010a350c0dc3e17e5ca86e2a445b29fa22071e39f`.

The initial focused run passed 32 cases in 6.55 seconds. After three additional
missing/invalid/duplicate-observation controls, all 35 observation cases passed
inside the final quick/owner selection. That selection ran 271 tests in 45.65 seconds:
270 passed and one assertion still looked for the previous guidance wording. The
test was changed to check that the complete non-replay guidance survives projection;
that single test then passed in 1.07 seconds. This is 271 distinct selected passes
in split validation, not one clean full-suite run. Runtime code stayed unchanged
during that repair. Ruff passed; quick included isolated mock evaluation. The six
extra owner selections checked current contract identities and exact gateway replay.

Trusted tiny callable fixtures cover the pilot's structural error, correct
bug/control extraction, repaired output, a control regression and a wrong-channel
false desired match. The latter still fails declared-failure matching. Existing
capture-health controls cover exceptions, truncation and incomplete calls.

Separately applying the feedback function to the saved public pilot JSON reported
seven declared-failure differences and five desired-result differences, with no
omissions. The original mismatched verdicts were retained. This was a read-only
diagnostic explanation of saved data, not a rerun or a new assessment of that task.

Reproduce the focused controls with `uv run --locked pytest
tests/test_probe_comparison.py tests/test_probe_observation.py --basetemp
C:/pt/tmp/<unique-short-id>`. The quick selection is `uv run --locked pytest
@tests/quick.txt --basetemp C:/pt/tmp/<another-unique-short-id>`.

These checks test mechanical feedback and existing evidence boundaries, not live
model uptake, reproduction of the real Astroid call, repair success or generalization.
The intervention changes the local interface decision; a fresh paid comparison would
need a separately specified and authorized allocation. None was executed here.

Material Passport: public pilot receipt and current source ANALYZED; trusted local
fixtures EXECUTED; live effectiveness NOT_RUN. Historical pilot results are preserved.
