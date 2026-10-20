# isort I2: observed revision, repair censored by timeout

Date: 2026-10-15. Status: `UNCERTAIN`; runtime terminal
`PROVIDER_TIMEOUT_OR_UNKNOWN`. Official=false, claim-ineligible.
The one authorized I2 invocation closed without a new edit or submission.
Unlike I1, the model explicitly revised its keyword-only placement hypothesis
and investigated the contrary case. A fourth generation timed out at the solver
deadline with unknown usage. The uncertainty stop prevented U review and both
terminal assessments. This is neither a completed repair nor U FAIL.

## Question, authorization and unchanged conditions

The [frozen design](2026-10-15-isort-table-design.md) tested whether a four-case
comparison table could support revision and a correct final repair while I1's
initial plan and completion guidance stayed fixed. The
[provider-free bridge](2026-10-15-isort-table-bridge.md) had passed its prepared
checks. The comparison is with the existing
[I1 result](2026-10-15-isort-uptake-result.md); I1 was not rerun.

The current human request approved exactly one I2 under
`C:/pt/isorttableready01/manifest.json`,
`sha256:7c712c96495464f228dfd368c83b98efc95144e1c042dbd537ed26952e4f84d7`.
Execution used commit `2c594f0eeef10b8a9fea3a005730aea1bbc9d987`, the bound
`original-isort-2491` dev-train task, `gpt-5.4-2026-03-05`, xhigh/default,
25,000 output tokens, the repository `.env`, and USD 3.50. The manifest's
preparation-time `paid_authorized=false` remains immutable; new authorization
is recorded in the launch and invocation journals.

The frozen ceilings remained six generations/six input counts, 60,000 input
tokens per request, eighteen tool actions, two new accepted source edits,
four parallel reads, 281 solver seconds including preparation and inherited
time, and 720 seconds overall. The one terminal public oracle/30 s and one
isolated evaluation/330 s remained conditional on an actual submission and
prior U seal. Retries, correction calls, resume, replacement samples, paid
compactions/judges and operator seed-diagnostic reruns remained zero.

[Official pricing](https://developers.openai.com/api/docs/pricing) was fetched
before dispatch and matched the frozen standard short-context rates: USD
2.50/0.25/15.00 per million input/cached-input/output tokens. Existing environment
readiness passed, and one metadata request confirmed the exact model. No Docker
start, image pull or build was performed.

## Actual input and public actions

All sequence numbers refer to the I2 journal, after inherited event 338.
The first prepared request at 344 counted **53,279 tokens** at 346 and dispatched
at 349/350. Its hash is
`sha256:1234c958e6aabee2fb48ac61eb5a7b64cbfedb03f16db8232e8f1e9fcce984b1`.
Normalizing only displayed remaining active time recovers the frozen request
hash `sha256:fd14c6ea17b4491b55597d6b66b380f9c46239cf8fb4bfe33e598de907331099`.
The actual display was 269 s versus I1's 270 s; the original deadline was not
extended. The original packet, native continuation, initial plan, completion
guidance, tool definitions and other fields matched. The sole display addition
was the faithful four-case table. Input length increased by 135 tokens over I1.

| Public events | Observed action and implication |
| --- | --- |
| 352, 354-355 | The first response explicitly says the diagnostic contradicts the safety of a `type: ignore` text special case: it fixes the opening-line example but hoists an item-line comment. The model revises its plan and open question toward preserving original comment association. |
| 356-359 | Two searches inspect output/comment helpers. Searching `def with_comments` in `isort/output.py` returns no match; `def add_to_line` in `isort/comments.py` returns its declaration. Neither action changes source. |
| 369, 372-374 | The second response selects a model-authored probe of opening-line and item-line `type: ignore` inputs. It describes the item case as still untested, despite the earlier delivered observation. |
| 374 | All four declared configuration checks match. The probe reports the issue input unchanged and the item input moved, then raises `AssertionError: per-item type: ignore moved`. Execution takes 2.870 s, with confirmed cleanup and no truncation or timeout. |
| 383, 385-390 | The third response again rejects text-based placement and reads `isort/output.py` lines 1-80 and `isort/comments.py` lines 1-60 to locate a structural distinction. The plan remains unfinished. |
| 394-400 | The fourth request counts 29,468 tokens and dispatches with the full fixed output allowance. No response is recorded; `APITimeoutError` terminates the row at the solver boundary. |

The probe is the model's new registered tool action, within the authorized
continuation; it is not a replay of the frozen operator program or the terminal
four-case oracle. Saved-source AST inspection confirms its two input strings
contain actual newlines and the declared distinct comment positions. The audit
did not execute either input again. Its observed failure addresses the two
selected type-comment cases, not all four terminal cases.

The initial hypothesis revision is directly visible; it is not inferred from
later evaluation. No `replace_text`, registered recheck or `finish_task` occurred.
All five successful tools retained the seed diff
`sha256:6edb32a68f8fea1002de9fa6836b1e583de021a53c176b94653dc894567e2940`.

## Context and limits on the explanation

Two ordinary segment transitions occurred at 362 and 393. As designed, the
operator packet was injected into the first current-state message only.
The second actual request still contains the revised plan stating that the
item-line counterexample contradicts the text-based rule, plus the new open
question. Later input plans have revisions 17 and 18, and the model-authored
probe failure remains in the public observation catalog. No paid compaction
occurred.

Thus the repeated probe cannot be explained simply by the revised conclusion
being absent from the second input. The visible response nevertheless recasts
that case as an untested assumption. These saved inputs establish a local
repetition and time cost, not its internal cause or a proven pruning defect.
The experiment did not vary retention, planning, reasoning effort or deadlines.

The unchanged completion guidance and initial plan were compatible with an
explicit revision in I2. They did not force immediate unchanged submission in
every continuation. The table's causal contribution remains unresolved: I1
and I2 are single, non-randomized observations, with extra display data and
sampling variation. No performance effect or general repair gain is established.

## U ordering, independent axes and I1 comparison

The fixed connector stops on unknown provider usage. It invokes public U review
only after a sufficiently certain solver outcome; on actual submission that
review must seal before either assessment. This row stopped before that stage.
There is no public-review-ready file, U-grade file, U-seal event, submission,
terminal-oracle event or isolated-evaluation event. No late grade or fabricated
submission was substituted.

| Axis | I1, existing record | I2, this invocation |
| --- | --- | --- |
| First-input exposure | Bound raw packet delivered; D PASS | Bound packet/table and parity verified; raw D remains UNKNOWN because the collector also requires known billing |
| Public hypothesis behavior | Confirming evidence used to justify completion | Item-position contradiction explicitly recognized; plan revised and investigated |
| Formal U | FAIL: unchanged seed submitted as sufficient | NOT_RUN: uncertainty stop before review; no accepted edit to satisfy U PASS |
| New accepted edit / submission | 0 / yes, unchanged seed | 0 / no |
| P: final public repair | FAIL | NOT_RUN |
| I: isolated acceptance | FAIL | NOT_RUN |
| Isolated safety | PASS | NOT_RUN |
| Generation / input count | 1 / 1 | 4 dispatched / 4; three responses completed |
| Tool actions | 1 finish | 2 searches, 1 probe, 2 reads |

The raw D value is preserved rather than silently changed. Independently,
complete first-input delivery is directly verified by the counted/dispatched
request and its matched hash. This distinguishes observed exposure from the
collector's conservative aggregate field.

U requires evidence-to-revision-to-accepted-edit linkage. Recognition and a
revised plan alone do not meet that criterion. Conversely, the timeout and
unchanged working diff do not satisfy I1's U FAIL clause: I2 did not submit that
diff as sufficient or explicitly preserve the contradicted premise. Formal
U remains NOT_RUN, and final repair correctness is untested. This follow-up
does not replace the frozen rubric with a looser recognition score.

## Cost, timing and integrity

| Generation | Counted input | Cached input | Output | Usage-based cost | Maximum reserved cost |
| --- | --- | --- | --- | --- | --- |
| 1 | 53,279 | 0 | 5,114 | USD 0.2099075 | USD 0.5081975 |
| 2 | 27,335 | 3,456 | 6,891 | USD 0.1639265 | USD 0.4433375 |
| 3 | 36,882 | 9,600 | 4,330 | USD 0.1355550 | USD 0.4672050 |
| 4 | 29,468 | UNKNOWN | UNKNOWN | UNKNOWN | USD 0.4486700 |

The known usage subtotal is **USD 0.509389**. The fourth request's usage and
total provider bill remain **UNKNOWN**; the subtotal is not the total cost and
the unresolved call is not zero-priced. Known usage plus that call's full
uncached-input/output reservation is **USD 0.958059**, below USD 3.50. This is
the admitted exposure under the reviewed rates, not a provider invoice.
No account/billing API or recovery call was made to resolve it.

Each dispatch used its own immediately preceding successful count and matched
request hash. All four were below the input ceiling and reserved the full
25,000-token output allowance. New generations/counts were 4/4, tools 5/18,
accepted edits 0/2, maximum parallel reads two/four, metadata reads one/one,
and terminal assessments zero. No post-terminal model or tool admission occurred.

Accounted new active solver time was **280.919 s** against 281 s. The journal
span from invocation approval to final closure was **281.104 s**, including
terminal bookkeeping, against the 720 s overall ceiling. The fourth provider
call had approximately 53 seconds left and timed out at that boundary. The
connector closed instead of extending time to use the remaining two calls.
This is a time-censored repair chain with unresolved provider usage, not an
ordinary behavioral rejection by the final oracle or evaluator.

The saved-evidence audit validated the original and nested design bindings,
manifest/runtime/implementation identities, four journal chains, 116 artifact
references, full first-input parity, exact count/dispatch linkage, cost arithmetic,
unchanged seed, absent assessments and stop ordering. File/provenance checks
passed; that does not turn unknown billing or unrun safety into PASS.

## Evidence and decision

- Launch approval and pricing evidence: `C:/pt/isorttablelaunch01`, journal
  `runs/run_dev_isorttablelaunch.jsonl`.
- Live result: `C:/pt/isorttablelive01/result.json`; invocation journal
  `runs/run_dev_isorttablecollection.jsonl`; row journal
  `I2/runs/run_dev_49397fa9568d4b80.jsonl`.
- Full row artifact:
  `sha256:658728cbe0d3841c2c2f9a1279e389e11e29a4944b5549eaf37fca355a9cc92a`.
- Read-only audit: `C:/pt/isorttableaudit01/audit.json`, journal
  `runs/run_dev_isorttableaudit.jsonl`, artifact
  `sha256:daf8887b4ac1e534e0342869d327ca3b906c745f461e5641ed83ec2ff31040c9`.

The audit added no model, target diagnostic or evaluation execution. Historical
artifacts, frozen instructions and the user's AGENTS.md changes remain intact.
Only this result record, the history index and current status are updated.
Five documentation-layout/link checks passed in 0.10 s, and `git diff --check`
passed. Runtime tests and mock smoke were not repeated for this documentation-only
closeout; the unchanged connector's prior validation remains bound by the manifest.

**Close this allocation and preserve the baseline.** The table condition was
followed by observable hypothesis revision and investigation, unlike I1's
immediate unchanged submission. It did not produce an accepted edit, verified
submission or measured repair gain within the fixed resources. The unresolved
question is whether recognized contradictory evidence can be converted into a
correct edit and final verification within those resources. No wording change,
additional sample, deadline extension, resume or new experiment is authorized
by this result or by the unused budget.
