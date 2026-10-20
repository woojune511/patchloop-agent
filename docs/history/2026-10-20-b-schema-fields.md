# B reproduction schema: provider-free field diagnosis

The entrypoint regex is the next specific candidate, not a confirmed cause of the
provider failure. Local checks found no malformed schema or unsatisfiable required
object. The [live pair](2026-10-20-b-schema-results.md) remains the causal evidence
for the reproduction-schema family; this audit does not replace it with a claim
about the provider's undocumented compiler.

The audit was selected to narrow the schema-family result before any additional
spending. It compared the frozen successful OFF request with the failing ON
request and the current owner `patchloop/dev/reproduction.py`, then used the
installed OpenAI strict-schema helper, Pydantic and native Node regex engine.
No provider/count call, credential read, package install or runtime change occurred.

## What was narrowed

- The saved reproduction schema exactly matches the current owner. Removing
  titles is the only authored projection; there is no double-escaped regex.
- The SDK's strict-schema normalizer changes no constraints. Required-key order
  was ignored only for this semantic comparison; actual request bytes were not
  normalized or changed. Both a null branch and an `x.y` object satisfy the host
  type. Object fields are required and additional properties are forbidden.
- Nullable object unions, length bounds and patterns already occur in the
  successful OFF request. It contains 21 pattern occurrences of two simple
  forms, `^n[1-9][0-9]*$` and `^v[1-9][0-9]*$`, with 30-character bounds.
  It also contains larger 3,000- and 8,000-character string bounds. Thus those
  keyword categories alone do not distinguish the failure.
- The new `entrypoint` constraint combines length 3-200 with
  `^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+$`. Its word-class escapes, noncapturing group
  and repeated dotted-name grammar are absent from the successful schema.
  This is a useful variable to isolate, not proof that any construct is unsupported.

The [OpenAI supported-schema guide](https://developers.openai.com/api/docs/guides/structured-outputs#supported-schemas)
supports nested `anyOf` and `pattern`; the extra string-keyword exclusions there
apply to fine-tuned models. It does not document an exact regex engine or establish
that this particular expression causes an all-zero response. The
[strict-mode rules](https://developers.openai.com/api/docs/guides/function-calling#strict-mode)
require closed objects and required fields, which this added schema satisfies.

## A real portability difference, with a limited implication

The exact expression compiles locally in both Pydantic's validator and Node's
ECMAScript regex engine. Thirteen representative values exercise ordinary dotted
names, invalid separators, length boundaries, newline and Unicode. The tested
ordinary ASCII cases agree. Three Unicode suffixes, including `a.bé`, are accepted
by Pydantic and rejected by ECMAScript. The final-newline witness agrees; an initial
audit caption saying otherwise is explicitly corrected in a separate record.

[JSON Schema's regex guidance](https://json-schema.org/understanding-json-schema/reference/regular_expressions)
uses ECMAScript and recommends a portable subset because implementations differ.
The cross-engine witnesses show why host regex validation alone cannot certify
provider compatibility. They do not show what engine OpenAI used, nor that a
Unicode output was attempted in any failed request. The failed initial request
contains a schema, not a concrete reproduction declaration.

No provider grammar compiler is available locally. The preserved HTTP evidence
contains selected metadata/usage, not an internal error trace. Claims that `\w`
caused grammar state explosion, that the noncapturing group is rejected, or that
the length bound is the culprit remain untested. Repeating local validation would
not settle them.

## Next discriminating check

A [one-request diagnostic](../../.agent/plans/b-pattern-check.md) is prepared to
remove only the `entrypoint.pattern` keyword from the failing B request. It retains
the reproduction object and every other constraint/prompt/control, with the host
validator unchanged. The new paid scope, if authorized, is one generation and one
count with USD 0.1575 cap; no response has been requested. Use the saved ON failure
as the comparison and acknowledge the historical-control limitation.

The diagnosis changes the next test from removing the whole feature to isolating
one constraint. It does not adopt a runtime workaround or resolve the UNKNOWN
bills. If this request also fails, stop and report that pattern removal was
insufficient rather than assuming another field or automatically spending again.

Evidence: `C:/pt/b-schema-fields35/result.json`, `label-correction.json`,
`inspect_schema.py`, `regex_check.cjs` and hash-chained `run_dev_bschemafields35`.
The immutable original report/result remain available alongside the correction.
Prepared request/collector: `C:/pt/b-pattern36/`. Runtime, transitions, reference
count, accounting validation and all closed artifacts remain unchanged.
