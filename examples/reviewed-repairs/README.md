# Original patches and feedback-informed corrections

Saved evidence from the closed three-task public-use evaluation. No new solve,
test run or acceptance decision was made for this export. Verifier JSONs are
labelled projections without host paths; patches are byte-identical originals.
[Provenance](provenance.json) and [export hashes](files.sha256.json) identify both.

| Case and original base | First artifact | Feedback-informed artifact |
| --- | --- | --- |
| [Click #2786](https://github.com/pallets/click/issues/2786), `2247b35ea1c47c727d7a06e51fa280e12a863ff6` | [original patch](click-2786-original.patch), [verification](click-2786-original-verification.json) | [correction](click-2786-correction.patch), [final whole patch](click-2786-composed.patch), [verification](click-2786-composed-verification.json) |
| [Click #2740](https://github.com/pallets/click/issues/2740), `2247b35ea1c47c727d7a06e51fa280e12a863ff6` | [original patch](click-2740-original.patch), [verification](click-2740-original-verification.json) | [correction](click-2740-correction.patch), [final whole patch](click-2740-composed.patch), [3.12 verification](click-2740-composed-verification.json), [3.10 verification](click-2740-composed-verification-python310.json) |
| [dotenv #713](https://github.com/theskumar/python-dotenv/issues/713), `0b2880591780a426b0551436f47a17e7a76d954f` | [original/final patch](dotenv-713-original.patch), [verification](dotenv-713-original-verification.json) | No correction |

Click #2786 originally fixed the reported shared-value overwrite by bypassing
processing for an omitted option. Public review reproduced skipped callback
validation. The correction preserves processing and restricts value overwrite
instead. The final candidate passed both the issue case and callback-preservation
check, plus 943 selected tests. [Correction-only verification](click-2786-correction-verification.json)
uses feedback base `37bcf423d98460047957619ec0c49475fc4169c5`.

Click #2740 originally added an unconditional `add_note()` test despite Python 3.10
support. The correction guards note-specific behavior while testing legacy output.
The [correction-only comparison](click-2740-correction-verification.json) is
**UNSUPPORTED**, since it changes an existing test body at feedback base
`d0d0226e005e27d78c70b495f5f61654952bd894`. The upstream-based final patch is safely
separable: 3.12 failed before/passed after; 3.10 passed both. Each final environment
passed 942 selected tests. Python 3.11 itself and the full suite were not run.

dotenv #713 adds flush/fsync before replacement. Public review found it within the
requested scope. Call-order tests and review do not demonstrate durability during
actual power loss. The selected 220 tests passed; other environments and the full
suite were not run.

All three original red/green comparisons passed, but code review found one scoped
candidate and two needing changes. Both corrections then became scoped candidates.
This is **not first-attempt success 3/3**, independent acceptance, or independent
model discovery of the review defects. No operator changed implementation/tests;
the operator supplied defect reproductions and contract feedback.

Human final approval and active review time remain unreported. Every public
repair's independent acceptance is **NOT_RUN**; verifier requirement fit is
**NOT_ASSESSED**. The total recorded generation/correction cost was USD 2.14702485,
and execution plus verification time approximately 33m17s, excluding preparation
and human review. See [the closed results](../../docs/history/2026-10-05-click-feedback-results.md).

Upstream excerpts: [Click license](click-LICENSE), [python-dotenv license](dotenv-LICENSE).
