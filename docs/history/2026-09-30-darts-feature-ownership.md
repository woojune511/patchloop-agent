# Darts feature ownership: provider-free correction verification

Completed 2026-09-30 after the [failed fresh run](2026-09-30-darts-fresh-repair.md).
This is an operator-authored offline correction on separate public-source copies,
not another agent solve, an adopted runtime change or a replacement for the FAIL.

## Mechanism and correction

The submitted agent patch grouped encoder output names by the longest matching
input-column prefix. Display names do not uniquely encode feature ownership:
`c_a_x` can originate from category `a_x` of column `c`, not column `c_a`.

The first operator patch special-cases OneHotEncoder and derives each feature's
output width from fitted categories, infrequent-category grouping and dropped
category information. It slices the ordered output names by those widths without
parsing name text; generic encoders retain their previous mapping behavior.
The design uses public [OneHotEncoder attributes](https://scikit-learn.org/1.8/modules/generated/sklearn.preprocessing.OneHotEncoder.html),
not private evaluator material or private sklearn helpers.

The mapping-only patch repaired name overlap but failed a zero-output-feature case.
The inverse reconstruction loop iterated surviving transformed columns, so it could
not restore an original feature represented by no output columns. A separate second
patch also retains the fitted original column order and reconstructs decoded numeric,
categorical and passthrough values using the original masks. This separates feature
ownership from both display names and the number of surviving encoded columns.

The final patch is relative to the original upstream base, not a mutation of the
saved agent submission: one implementation file, 45 added / one deleted line.
Both operator patch versions and their observations remain preserved.

## Frozen comparison and validation

Thirteen public cases were frozen before comparison. Each checks forward/inverse
values, column count/order and index against the public sklearn encoder's own
roundtrip; pandas dtype alone is ignored. For infrequent grouping, the encoder's
lossy inverse is the expected value, not the original category spelling.

Cases cover ordinary encoding/no-drop, first-drop, overlapping names with and
without dropping, mixed binary/nonbinary if_binary, explicit category drop, dense
output, interleaved numeric columns, custom generated names, infrequent grouping
with/without dropping, an OrdinalEncoder control, and a zero-output constant feature
alongside a surviving categorical feature.

| Source | Selected public cases passed |
| --- | --- |
| Unchanged base | 8 / 13 |
| Saved agent submission | 9 / 13 |
| Operator mapping-only patch | 12 / 13 |
| Operator mapping plus original-schema reconstruction | 13 / 13 |

Both operator patches separately pass all eight unchanged registered regression
tests. The final candidate resolves the original first-drop failure, all three
name-overlap/numeric-interleave regressions, and the tested zero-output feature loss.
The same frozen program and existing check image (scikit-learn 1.8.0) were used
throughout; no dependencies, task checks or image contents were changed.

Six container receipts total 21.556 seconds, excluding source-copy/setup overhead.
All have exit 0, complete output and confirmed cleanup, with no timeout. Matrix
case failures are observations inside successful diagnostic processes, not PASS
verdicts. Receipt hashes, journal chain, final patch identity and unchanged prepared
source were verified. Provider/model calls: zero. Private acceptance and formal
safety verdict for the operator candidate: NOT_RUN.

## Artifacts and decision

Evidence root: `C:\pt\analyses\darts-feature-ownership-20260930-v1`.
Append-only journal: `run_dev_dartsownership`, binding both frozen patches,
the fixed matrix program, all receipts and the final summary.
Readable artifacts: `candidate.patch`, `candidate-v2.patch`, `roundtrip_cases.py`.
Final patch hash:
`sha256:11bf508c3f5d5687ca2677867c2de599d1f7037cbbd2770c2baec5a3d64684f7`.
The original source, failed run and private evaluation evidence remain unchanged.

The causal diagnosis is supported: name-based ownership and reconstruction from
surviving columns are separate defects. The final candidate addresses the selected
public cases, but all-features-zero output, duplicate generated output names and
other sklearn versions are not established by this matrix. No exhaustive fix,
private acceptance, generalization or agent-performance improvement is claimed.

Keep the runtime/task/prompt baseline unchanged. Retain this bounded correction as
operator evidence; do not convert it into a successful fresh agent run or silently
provide it as a hint in a later fresh solve. Any later evaluation or seeded repair
needs its own explicit scope. Documentation-only repository edits require layout/
link checks; full runtime regression and mock smoke are not repeated here.
