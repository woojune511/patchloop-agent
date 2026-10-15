# isort I4: requirement scope and derived-oracle validity

Date: 2026-10-16, Asia/Seoul. Read-only follow-up to the
[I4 result](2026-10-16-isort-finish-advice-result.md). No new model, count,
metadata, target diagnostic, registered check, evaluator or mypy execution.
No private assertion or reference-patch inspection. Historical run, diagnostic,
manifest, rubric and grade bytes remain unchanged.

## Conclusion and correction of interpretation

I4's distinction between the explicit issue example and the derived `type_item`
expectation is legitimate. The issue does not expressly require that crossed
input to remain unchanged. Preserving it is a supported regression hypothesis,
but the reviewed evidence does not independently establish it as the uniquely
correct task behavior. The expected value is not proved wrong either.

The model's complete dismissal is also underjustified: the supplied system
instruction requires preserving behavior outside the requested change, the
base preserved `type_item`, and ordinary item-comment regression tests support
association preservation. None is automatically irrelevant merely because the
exact input is absent from a registered test. Conversely, these facts do not
settle whether this particular linter comment is a legitimate special case.

The experiment cleanly exposed the observation and distinguished keyword-based
relocation from original-position preservation. It did **not** independently
settle which policy is correct for the crossed type-ignore input. Treating its
U FAIL as proof that the model rejected an unquestionably valid bug counterexample
would overstate the evidence. The narrower result is an unchanged submission
after disagreement about an inferred requirement. Keep the runtime baseline;
do not launch another prompt experiment on the premise that oracle validity
has already been resolved.

## What the public requirement actually establishes

The immutable public task is
[`original-isort-2491/public.yaml`](../../tasks/dev-train/original-isort-2491/public.yaml),
base `ae91dadf34951e316d5a81ffe7ac086952f1da65`.
Its title is "Comments moving bug when using import aliases". The description
mentions a comment after a long aliased `from` import, with a mypy comment as an
example. The supplied input places `# type: ignore[attr-defined]` after the
opening parenthesis. Its explicit expectation is no change because that is the
line where mypy reports the error. Its observed bad output moves the comment
to the imported alias line.

The audit compared the exact code blocks with the diagnostic cases. After only
CRLF/LF and surrounding-blank-line normalization:

- `type_opening` is exactly the issue's input.
- `type_item` is exactly the issue's **observed, unwanted output**.

The second equality does not prove that an independently authored item-comment
input must be hoisted. A formatter may need to preserve author association even
when identical bytes could result from an earlier bug. It does show why the
issue's example alone cannot establish the opposite no-change expectation for
that input. The source does not demonstrate mypy behavior for either new input;
the diagnostic uses placeholder import names and never runs a type checker.

The issue's generic comment wording supports investigating ordinary comments;
it does not itself specify a complete position policy for every comment kind,
original location and formatting configuration.

## Provenance and strength of the four-case expectations

The [public control](2026-10-15-isort-control.md) froze all expectations before
execution. Its manifest and the delivered packet explicitly call the three
crossed cases derived controls, not pre-existing regression expectations or
independent private oracles. That disclosure was accurate and reached I4.

| Evidence | What it establishes | What it does not establish |
| --- | --- | --- |
| Exact issue example | Keep the opening-line type-ignore comment on the opening line. | A no-change rule for an original item-line type-ignore. |
| Public regression `issue_1219`, lines 398-411 | A wrapped aliased import with an ordinary item comment is accepted unchanged under Black. | The same policy for every linter directive. |
| Public regression `issue_1431`, lines 655-666 | Ordinary `NOT DRY`/`DRY` comments stay on their items, including an alias, under Black. | The precise `type_item` combination or a checker-specific policy. |
| Public regression `issue_1381`, lines 530-542 | The text `# type: ignore` survives `combine_as_imports=True`. | Its line or item ownership; the assertion checks substring presence only. |
| Bound base/current diagnostic receipts | Under the same Black configuration, `type_item` goes from base item to current opening; parser categories distinguish original placements. | Whether the new placement is semantically wrong for this directive. |
| Supplied system preservation instruction | Changes outside the requested behavior need justification. | That every baseline behavior is correct or that this case necessarily lies outside the requested repair. |

The exact source is the already prepared public `tests/unit/test_regressions.py`,
hash `sha256:9c3cb8a23e15cf7389b584e26ba868b825509f946192b07da169448986f38ea6`.
The first two test bodies and the type-ignore search excerpt are present in I4's
actual native input, with source text and line ranges verified byte-for-byte.

There is also public precedent for comment-kind-specific treatment: base
`wrap.py:85` treats `noqa` specially, and regression `issue_1594:1589-1608`
expects it on the opening line after wrapping. This is auditor-read public
evidence against a universal rule that all comment kinds have identical
placement behavior. It does not establish an analogous rule for `type: ignore`,
nor is it presented as an exact excerpt necessarily delivered to I4.

Thus `type_item` is a reasonable regression guard with an unresolved applicability
question. A base-to-current change and AST/text preservation establish behavior,
not complete directive semantics. The plain-opening control has its own inferred
scope; its failure cannot independently validate the type-item expectation.

## Actual I4 input and public decision

The dispatched request at row events **350/351** matches the prepared request
at **344**, hash
`sha256:4d58699283f282a70950f1cc9a4ef12f02d6d6ddfa2b912587aad391e4293ad5`.
The supplied `operator_public_observation` is exactly the frozen feedback file:
`sha256:da7d65fe849d424c425ea9121fd0d4746f257ef7fde448d06ce1acd8fdca1fcd`.
It includes both execution receipts, the four-case table, configuration, source
and diff identities, parser observations and expectation provenance. The notice
says execution status is not a repair verdict and the packet is not a registered
check. No extra instruction orders the model to accept every derived expectation.

The system explicitly says to preserve behavior outside the requested change and
also allows a diagnostic itself to be wrong. It requires conclusions to follow
actual inputs/results. The inherited plan calls `type: ignore` a statement-level
linter comment and proposes narrowing the existing change by text. Its cited
public type-ignore test proves text survival, not the stronger placement rule.
The plan is labelled model-authored and unverified in the input.

At **354**, I4 acknowledges that the derived item-line type-ignore is hoisted,
then says the task and visible checks do not establish its placement as required.
It calls the case a "derived, untested control". At **356**, the plan says no
further publicly supported repair remains. **358/362** finish and submit the
unchanged seed. The other failing table row, `plain_opening`, is not discussed.

Three judgments must stay distinct:

1. **Not an explicit exact-case requirement:** supported by the public issue,
   tests and delivered provenance. This is not evidence of missing diagnostic
   delivery or simple failure to notice `type_item`.
2. **Untested:** if this means not executed, the receipts contradict it. If it
   means no independently established regression expectation, that limitation
   is real. The public wording does not establish which meaning was intended;
   the earlier result's categorical execution-error reading should be narrowed.
3. **Therefore exclude it and declare no supported work:** insufficiently
   justified. I4 neither addresses the preservation obligation and analogous
   tests nor supplies public evidence that this type-ignore should be normalized
   to the opening line. This is a gap in the observable decision, not proof that
   the experiment's alternative expectation is definitely correct.

## Frozen grades, causal limits and minimum change

The original U FAIL faithfully applies the frozen clause: unchanged seed
submitted as sufficient. P also fails the frozen new-edit/fresh-regression/four-
case conjunction. Those records are not regraded. The original isolated FAIL
and safety PASS also remain; a private aggregate FAIL is not used to justify
the expected position of a particular public control.

However, the U/P rubric embeds the position-preservation hypothesis: success
requires rejecting or qualifying keyword-only placement and acting on it in a
new edit. It has no separate successful path for a well-supported rejection of
the operator's expectation. Pre-registering that rule prevents result-based
scoring changes; it does not validate the rule's premise. This makes I4 an
uptake/repair experiment conditional on an inferred public contract, not an
independent test that the model can distinguish valid from invalid counterexamples.

The minimum correction now is interpretive and documentary. Separate explicit
issue requirements, directly tested public regressions, observed behavior and
inferred semantic expectations. Preserve the existing grades and immutable
records, while withdrawing the stronger conclusion that refusal to adopt this
particular expectation proves a clear hypothesis-update error. Neither a
mandatory-edit rule nor another completion prompt follows from these data.

Before any future study uses this crossed type-ignore case as correctness
authority, its applicability would need an independent public justification
that distinguishes association preservation from deliberate linter-comment
normalization. That is an unresolved question, not an approved experiment or
a request to run one. No target behavior, expectation, rubric or prompt was
changed in this audit.

## Evidence and static verification

External root: `C:/pt/isortrequirementaudit01`; hash-chained journal
`runs/run_dev_isortrequirementaudit.jsonl`. The read-only extractor does not
import target isort code or inspect private assertions.

- `audit.json`: file hash
  `sha256:deb1411561fe8cf302591c22247122095e3ee94c8ae7643dc133ca7d2157bfac`;
  canonical artifact
  `sha256:f09fb7a6e17e1e5532528a7326b5d2a1b07668afb25ad790130c4bd376554996`.
- `public-evidence.json`: exact public excerpts and case observations; canonical
  artifact `sha256:ca98b3dd551d52639e8bd46b29d0a570f497c0b3c1032eac7d1bbdf47f982e0d`.
- Thirteen source/artifact bindings, full row-journal chain, count/dispatch input
  identity, original/observed code-block equalities and native source excerpts
  were verified from saved bytes. Historical grade and result hashes are bound.

Only this follow-up, current status and the history index change. Static size,
link, whitespace and preserved-file checks apply; no target/test/evaluation
suite is rerun. The user's unrelated `AGENTS.md` modification remains intact.
