# isort comment-position public control

Date: 2026-10-15. Follow-up to the existing-record
[three-task probe audit](2026-10-15-probe-audit.md). Two operator-authored public
diagnostic executions, no model, input-count, registered-check or evaluator
calls. Every record is `official=false`; provider cost USD 0.

## Decision and reason for selection

The frozen diagnostic distinguished keyword-based relocation from preservation
of original comment position on `original-isort-2491`:
`KEYWORD_SHORTCUT_DISTINGUISHED`. The historical submitted patch fixes the exact
public issue example, but its output position follows comment text in the
crossed controls. The parser still distinguishes the two original positions.

The prior audit found an explicit hypothesis revision in this run, followed by
an unsupported discriminator. The model had varied text and position together,
then restricted its broad comment-hoisting patch to `type: ignore`. This case
therefore permits a small control for the unresolved decision without another
model sample. The question is whether identical text/configuration at different
original positions produces a position-preserving repair or a keyword shortcut.

Keep PatchLoop's runtime, prompts, memory/context limits and tool gates.
This establishes the usefulness of one operator diagnostic and narrows the
isort failure mechanism; it does not demonstrate a current tool contract defect
or a measured repair improvement. No paid follow-up is queued.

## Frozen design and expectation provenance

Before importing the target source, the manifest bound the four inputs,
expectations, competing predictions, program/driver hashes, source states,
environment, execution order, resource limits and stopping rules.

The input is the public issue's long aliased `from` import, with one comment
either after the opening parenthesis or after the imported alias. Text is
either `type: ignore[attr-defined]` or `ownership marker`. Each text is held
constant while position changes. Both parser inspection and formatting receive
the same `Config(profile="black")` object. The four import ASTs are identical.

The opening-line type-ignore expectation comes directly from the public issue:
the comment should remain on that line. The other three exact inputs are
**derived controls**, not pre-existing exact regression expectations or private
acceptance oracles. Preserving their original association is the declared
public-contract inference. Public `test_regressions.py` cases `issue_1219` and
`issue_1431` support preserving genuine item comments under the black profile.
No mypy execution or private-test inspection was performed.

Bounds were two public `run_probe` calls total, one per source state, four cases
per call, 30 seconds per probe and a 120-second invocation deadline. Model,
input-count, registered-check and evaluator calls were capped at zero; no retry,
extra case or repeat was permitted. Base runs first and must reproduce the
opening-type movement while preserving the ordinary item control. Setup/source
mismatch, incomplete output, timeout, truncation or cleanup failure stops the
remaining call. Other valid behavioral outcomes are reported without retuning.

The predeclared alternatives were: submitted output follows the keyword table;
submitted output preserves all four original positions, weakening the shortcut
explanation; or mixed behavior. These rules and inputs were not changed after
execution.

## Observed outputs

Here, opening means the line containing `from ... import (`; item means the
line containing the imported alias. The expected position is the input's
original position, with the provenance limits above.

| Comment text | Original / expected position | Base output | Submitted output |
| --- | --- | --- | --- |
| `type: ignore[attr-defined]` | opening | item | opening |
| `type: ignore[attr-defined]` | item | item | **opening** |
| `ownership marker` | opening | item | **item** |
| `ownership marker` | item | item | item |

All eight outputs preserve the exact comment text/count and import AST. Those
invariants rule out deletion or import changes in this matrix; AST equality
does not establish comment semantics or correct placement. These deliberately
selected controls are not an accuracy or generalization sample.

Both receipts have exit 0 and execution status `passed`, with no timeout,
truncation, deadline exhaustion or cleanup failure. All ten setup comparisons
match: four black-profile values and the public source import path per call.
The emitted environment also confirms `multi_line_output=3` and the expected
`wrap.py` hash. Five observed settings are `line_length=88`, parentheses on,
trailing-comma splitting on, trailing comma inclusion on, and wrap mode 3.
Returned output was 4,323/4,329 bytes; receipt durations were 7,262/2,646 ms.
Execution PASS is not repair acceptance; timing is not a performance comparison.

## Parser ownership narrows the failure mechanism

For both texts and both source states, opening comments appear in
`categorized_comments['straight']`, keyed by the fully qualified imported name.
Item comments appear in `categorized_comments['nested']`, keyed by the module
and aliased item. `from` and `above` are empty in these cases; alias maps agree.

The historical probe printed only `from` and `nested`, then the model inferred
that the opening comment was not stored in parser maps. The new observation
directly contradicts that inference for these inputs. The old result was
delivered and retained according to the prior audit; there is no new evidence
of context loss or a memory failure.

Public source `isort/output.py:402-449` reads `straight`, appends any `nested`
comment to the same list and supplies rendered comment text to `wrap.line`.
The submitted change touches only `isort/wrap.py` and uses
`"type: ignore" in comment` to select the opening line. The parser distinction
is thus available before this formatting boundary, while the final patch uses
a text discriminator that does not recover original ownership.

A repair investigation should inspect how to preserve that distinction through
the caller/formatter boundary, using the crossed controls. No such repair was
implemented or evaluated here, and this does not identify a particular private
failing assertion. Whether a model selects or uses the observation and then
produces a correct final repair remains untested in this follow-up.

## Source and environment identity

PatchLoop head: `b2416f58e1cf64f95730891085884650cca9cf0d`.
Historical run: `run_dev_49397fa9568d4b80` under
`C:/pt/runs/fixed-batch-20261001-v1/original-isort-2491`.
Public task base: `ae91dadf34951e316d5a81ffe7ac086952f1da65`.
Two isolated workspaces were copied from the verified prepared public source.
The submitted workspace replays only historical edits 106 and 331, checking
pre/postimage hashes and matching the complete historical submitted diff.

- Submitted diff: `sha256:6edb32a68f8fea1002de9fa6836b1e583de021a53c176b94653dc894567e2940`.
- Base `wrap.py`: `sha256:5bb59481af79e29f606a8e097b6960ae41c02d3c8a7a4d671a5c7845189ac275`.
- Submitted `wrap.py`: `sha256:c1693209c9d4d61c7ddf9591074360a7898f8389015c2248f763fff687ce8b38`.
- Shared current profile: `sha256:2996cf070a61589ad80c8d9c68bdfab52ad832804273fc1c59576fc080df129b`.
- Historical profile: `sha256:b8d627b9ed80a71f17034b9b9e7f83c15ac1d0d73742473ea366218952ae9e18`.

The existing public Python 3.12 image, dependencies, wrapper and setup helper
match the historical profile. Only the line-trace helper hash differs; both
arms use the same current profile, and no line-coverage claim is made. Docker
was already running; no image was pulled or built. The public sandbox uses
network none, read-only source/root, user 10001, one CPU, 512 MiB, eight PIDs and
12,000 output bytes. Source bindings were rechecked unchanged after execution.

## Evidence and closeout

All generated state is outside the repository in `C:/pt/isortposition01`:
`manifest.json`, `probe.py`, `driver.py`, both receipts, `result.json`,
content-addressed objects and hash-chained `runs/run_dev_isortposition.jsonl`.

- Frozen manifest file: `sha256:0f504b4dc6a60f224e67265f673bb2eaacbd3e06afb531fb7d1fc4746abca730`.
- Manifest artifact: `sha256:88ddc2c42aebf13d0afc1177af2dd7d55e9420be006eb08c4fa1504967c602e0`.
- Shared program: `sha256:61283548574cf5c2b6757d292be0780033215a56fddc0369bf641c08612bcd67`.
- Result artifact: `sha256:c8c75df918ee88ee9859da9336d8a20537e43fc4449157093c4a50c153cac2e2`.

Historical artifacts and the earlier audit are unchanged. This record advances
one proposed discriminator from unexecuted to publicly observed. Model test
selection, diagnostic uptake, final repair acceptance, regressions and quality
gain remain unmeasured here. The separate
[SQLFluff uptake result](2026-10-15-uptake-grade.md) is unchanged.

Documentation validation: five layout/link tests pass; `git diff --check`
passes. No runtime files changed, so runtime suites and mock evaluation were
not run. The external closeout receipt records artifact/source integrity,
the two-call count, document hashes and the unchanged user-edited `AGENTS.md`;
the commit is linked by a subsequent journal event.
