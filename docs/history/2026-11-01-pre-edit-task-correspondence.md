# Pre-edit task correspondence using existing repair intent

2026-11-01. Implementation and local validation; live effect NOT_RUN.
Development-only, official=false, claim-ineligible.

## Observed problem and chosen intervention

The [task8 comparison](2026-11-01-task8-diagnosis-comparison.md) found an earlier
normal solve repairing a direct-array helper while the public bytes input remained
unexplained. Its ordinary bytes sample passed, and the solver correctly retained
both that result and the report. It adopted the different helper failure as the
repair target without investigating the earlier transformation. The latest
successful solve instead searched for that missing transformation and repaired it
on its first edit, before post-mutation review became active.

The problem matters because a successful helper repair and passing regression
suite can leave the reported behavior unresolved. More probes, larger budgets or
another post-edit reminder do not directly address this decision point. The same
model succeeded in the latest sample, so this is not evidence of a universal
reasoning deficit. Early tool/schema effects and trajectory variation remain
unisolated explanations for that result.

The user authorized proceeding with the proposed improvement. The smallest chosen
intervention replaces the compact repair prompt's existing generic instruction
to explain the revised mechanism using original-call observations. It does not
add a separate review phase or restore retired requirement-reference fields.

## Implementation and contract

The ordinary pre-edit repair prompt now asks for a concise causal explanation
under the known public caller/input/setup, preserving input representation and
labeling inferred or missing conditions. A helper that changes conditions remains
separate evidence until source or comparable execution connects it to the report.
A passing sample supports its exercised conditions. When the proposed cause cannot
explain a reported transformation, use a relevant producing-step read or a
discriminating observation before adopting that helper as the repair target.
Source evidence may support the connection without exact reproduction.

Two short descriptions in repair_guidance.py are attached to the existing
hypothesis and expected_behavior fields of TextReplacementIntent and FileEditIntent.
Both fresh edit schemas inherit them through their existing projections. The
hypothesis is a proposed cause, not an observed fact; expected_behavior names
the required observable under public conditions and distinguishes helper outcomes.
This includes ordinary edits, batches, creation and receipt undo.

No field, enum, state, tool, semantic validator, budget, mandatory probe or extra
model call is added. Existing 1-1,500 character limits, required-field ordering,
mutation admission, test preservation and finish policy are unchanged. The shared
general verification guidance and post-edit scope review are not expanded.
No task8-specific bytes, VR, delimiter or expected-answer hint appears in runtime
guidance. Missing setup does not prohibit a source-supported repair.

Descriptions change fresh provider-schema fingerprints; the tool-surface contract
hash stays unchanged. The modified source changes runtime identity. Existing
argument serialization, absent/null handling and
action_id + input_hash recovery remain unchanged. Closed requests and historical
approvals are not rewritten or made executable under the new runtime.

## Validation and interpretation

Focused tests exercise actual pre-edit runner requests across current/thin and
append/segmented policies, including an unchanged public task, an ordinary original-
representation control and a failing helper with substituted input. They verify
that guidance reaches the repair request before behavior_change exists while
public observations, resources and offered tools stay intact. Schema checks cover
both mutation tools and existing legacy serialization tests remain applicable.

The focused owner/contract selection passes 133 tests in 12.489 seconds. It also
exposed a pre-existing expectation that omitted edit_files from the exact optional-
annotation tool set and prompt wording. That test now reflects the existing runtime;
no action policy changed. The first failure and corrected result are retained.
The new delivery fixture initially compared the unprojected source_spans key with
the model view; it now compares exact file hashes, ranges and contents after the
existing current_sources normalization. Those fixture failures are also retained.

An isolated HEAD/current comparison of ten generated schema variants found only
the intended mutation-field descriptions changed. Ordered structure without
descriptions and six absent/null/legacy/batch/undo serializations match. Seven current
description fingerprints were updated across four test files, preserving historical
arms, argument identities and the tool-surface hash. The affected fingerprint and
wire checks pass eight cases in 1.001 seconds plus the feedback schema check in
0.893 seconds. Their earlier failures reflect the intentionally changed descriptions,
not altered argument contracts. The general prompt remains byte-identical and
within its existing 8,007-character ceiling (7,994); only the repair prompt changed.

The complete quick traversal took 777.718 seconds: 1,451 PASS, six description-
fingerprint failures and one host symlink-permission skip. It had collected the old
expectations before they were updated. All six failures passed the exact targeted
recheck in 0.929 seconds on the same unchanged runtime. The combined result is
1,457 PASS, one skip and zero unresolved failures, not a claim that the first
command passed. Both included isolated mock evaluation tests passed; they were
not repeated. Ruff passed. Focused validation remains below two minutes.

These are delivery and contract tests, not a model making a better diagnosis. The
expected live effect is that an unexplained public input remains an active question
instead of being replaced by the easier helper failure. A later diagnosis that
still narrows the task despite receiving this guidance would weaken the intervention.
Source-supported equivalence or a genuinely irrelevant difference should still
allow direct repair; a model spending redundant probes on those cases would also
count against it. No paid run is performed or authorized by this change.

Focused, Ruff, fast-suite and included isolated mock evidence is recorded outside
the repository at `C:/pt/pre-edit-correspondence-local-20261101-v1/`.
Runtime/contract behavior and live repair gain remain separate claims.
