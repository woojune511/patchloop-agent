# Recovery comparison after the provider-schema correction

The fresh twelve-run allocation completed with settled billing of **USD
7.70164425** under the USD 10.56 cap. A submitted four of six runs and B two of
six. All six submitted patches fail both native acceptance and the original
missing-initializer caller; all six pass the initializer-present control and
safety. Accepted repairs are **A 0/6, B 0/6** over all assigned runs.

B's earlier first-response usage failure did not recur in any of its six runs.
Automatic recovery was exercised: four B runs dispatched thirteen restored
search results. This establishes delivery, not repair benefit. No B run declared
a reproduction. B2 correctly recognized that its original-caller replay still
failed, but that did not produce a submitted repair, and the correct judgment
cannot be attributed specifically to the new recovery mechanism. B cost about
39% more than A. The prespecified follow-up criterion failed; the allocation is
closed, with no automatic further run or quality-adoption claim.

## Question, intervention and fixed boundaries

The [previous comparison](2026-10-20-recovery-http-results.md) stopped before B
could act. A [one-field diagnostic](2026-10-20-b-pattern-results.md) and subsequent
local correction removed only the provider-facing `entrypoint.pattern`; host
validation stayed unchanged. This comparison was selected to answer the original
recovery/use/repair question after removing that observed execution obstacle.
The alternative was that delivered evidence would still be applied to a different
caller or environment, or never used. Actual source delivery plus failed repairs
would weaken the hypothesis that missing source alone explains the failures.

- [Frozen specification](../../.agent/plans/recovery-schema-comparison.md), manifest
  `sha256:35e9de083dbbe2758e2c22f6559225995756a9b3795e3b7f087b2e6a1c9f7347`.
- Packet `C:/pt/evidence-comparison38/`; solver state
  `C:/pt/evidence-comparison38-live/`; preparation commit `a01ab6bb`.
- A `dc03e120ec01a1592f4818fbcba5a50677deb890`; B
  `0491642dd9ed708d4eb9223ec0ab6377e9b5025f`. The same three assigned changes
  remain bundled; this is not a component factorial comparison.
- Astroid-1333, `tasks/dev-train/current-dev20/13/public.yaml`, base
  `d2a5b3c7b1e203fec3c7ca73c30eb1785d3d4d0a`, dev-train, `official=false`.
- `gpt-5.4-mini-2026-03-17`, xhigh, desired output 25,000, project `.env`, standard
  Responses, zero SDK retries. Human approval: “새 12회·$10.56 상한으로 승인”,
  separately bound in `authorization.json` and the approval journal.
- Six fresh runs per arm, order `A1 B1 B2 A2 A3 B3 B4 A4 A5 B5 B6 A6`;
  USD 0.88/row, 5.28/arm, 10.56 overall. No replacements or transfers.
- Unchanged transition rules, two references, 24,000 retained source characters,
  60,000 input tokens, request/encrypted-item ceilings, 40 model calls, 100 actions,
  four accepted edits and 1,800 seconds including the 330-second evaluation reserve.
  Source, Pylint 2.12.2 dependencies and installed images remained pinned.

Fresh preparation passed A 161 selected checks, B 174, execution/audit controls
12, documentation 5 and Ruff. Both selections reached isolated mock evaluation.
Initial requests matched their historical arms with the exact reviewed correction
and the same six assigned A/B differences. The full suite was NOT_RUN; four old
timing failures remain unresolved. No runtime was edited during this allocation.

## Execution and independent outcomes

All twelve assigned runs were attempted and their costs settled. Public-only
annotations were sealed before opening fresh grades. Then twelve caller checks
and six native assessments evaluated exactly the six submitted patches, with zero
additional provider calls. Cleanup was confirmed and registered/native verdicts
agreed throughout. Submitted, native and source-only caller patch hashes match;
none of these submissions contained additive tests.

| Row | Terminal state | Public regression | Native / original caller | Present control / safety | USD |
| --- | --- | --- | --- | --- | ---: |
| A1 | Submitted; evaluator FAIL | PASS | FAIL / FAIL | PASS / PASS | 0.41648895 |
| A2 | Cost cap; no submission | PASS | NOT_RUN | NOT_RUN | 0.87135585 |
| A3 | Submitted; evaluator FAIL | PASS | FAIL / FAIL | PASS / PASS | 0.26741940 |
| A4 | Incomplete response; no edit | NOT_RUN | NOT_RUN | NOT_RUN | 0.87585270 |
| A5 | Submitted; evaluator FAIL | PASS | FAIL / FAIL | PASS / PASS | 0.58378470 |
| A6 | Submitted; evaluator FAIL | PASS | FAIL / FAIL | PASS / PASS | 0.20754660 |
| B1 | Submitted; evaluator FAIL | PASS | FAIL / FAIL | PASS / PASS | 0.70557360 |
| B2 | Cost cap; no submission | PASS | NOT_RUN | NOT_RUN | 0.87896235 |
| B3 | Incomplete response; no edit | NOT_RUN | NOT_RUN | NOT_RUN | 0.81957165 |
| B4 | Cost cap; no submission | NOT_RUN | NOT_RUN | NOT_RUN | 0.86544930 |
| B5 | Submitted; evaluator FAIL | PASS | FAIL / FAIL | PASS / PASS | 0.40220835 |
| B6 | Incomplete response; no edit | NOT_RUN | NOT_RUN | NOT_RUN | 0.80743080 |

Unsubmitted A2/B2/B4 workspace changes remain preserved but were not evaluated as
submissions or replaced with new runs. `outcomes_complete=true` means all assigned
bounded outcomes and required assessments are known, not that all agents submitted.
`favorable_local_signal=false`, `official=false`, `claim_eligible=false`.

The old zero-usage failure is distinct from the eight later incomplete responses
across A2/A4/B2/B3/B6. All eight have accounted positive usage, HTTP/SDK selected
fields agree, and the reason is `max_output_tokens`. Their entire reported output
is reasoning tokens and they emit no tool call. Five exhaust the full 25,000-token
output ceiling; three exhaust already reduced ceilings (645, 1,767 and 20,463).
This is a completion/output-budget failure, not a recurrence of unknown billing.
No reasoning text was decoded or interpreted.

## Acquisition, delivery and judgment

All runs acquired some relevant public source and the original issue. That is
partial acquisition, not complete caller knowledge. Direct Pylint source bodies
were not inspected. The important distinction is whether the agent actually ran
the reported caller with the reported conditions and used its result correctly.

| Observation | A | B |
| --- | ---: | ---: |
| Automatic source recovery | 0 | 13 actions in 4/6 runs |
| Eligible lost-body search opportunities | 7 actions in 2/6 | 13 actions in 4/6 |
| Ordinary rereads restoring complete earlier ranges | 4 actions in 2/6 | 8 actions in 4/6 |
| Explicit history-search calls | 0 | 0 |
| Faithful original-caller failure execution | 0 | B2 only |
| Altered-environment Pylint execution | 0 | B4 only |
| Declared reproductions | Not offered | 0 |
| Strict pre-baseline expectation plus fixed before/after comparison | 0 | 0 |
| Unbound identical original-caller program replay | 0 | B2 only |
| Supported mechanism use together with accepted repair | 0 | 0 |

Every automatically recovered range matches its previous version/range and is
fully present in a subsequent dispatch. The 1,987 previously absent line
occurrences include repeated restorations; they are not 1,987 distinct useful
caller lines. A also restored some source by ordinary rereading, so the comparison
must not equate absence of automatic recovery with absence of all recovery.

**B1: delivered source, unsupported causal claim.** Inputs 337 and 410 restore
modutils/test bodies. Probe 459 aborts at a file modpath ImportError before its
later file-info/manager calls execute. It does not run Pylint. Edit 474 guesses
directory package validation is the cause; finish 506 admits that the exact repro
was not run while asserting the changed branch is the root cause. The later
independent original-caller FAIL confirms that this claim was unsupported.

**B2: original failure acquired and correctly rejected after the edit.** Probe
290 runs Pylint 2.12.2 on `src/project` from the fixture root, without adding `src`
to `sys.path`, and observes F0010. Input 299 delivers that result. A later helper
shows an empty normal directory listing, and edit 491 changes `get_module_files`.
The original F0010 result is present in input 484 immediately before that edit.
Its wrong causal hypothesis therefore cannot be explained solely by missing
evidence. Replay 523 executes the identical original program after the edit and
still reports F0010. Plans 537/553 explicitly reject the general suite PASS as
repair proof. This is a positive instance of diagnostic judgment, without a
successful repair or submission. It uses an existing replay capability; the
caller program preceded the first recovery, so specific attribution to the new
mechanism remains UNKNOWN. No expected result was explicitly bound before the
baseline; credit for the unbound replay is separate from the strict endpoint.
The final notes also mix an older enumeration observation with current-diff
language, so this is not a claim that every B2 inference was sound.

**B4: caller name matched, environment changed.** Probe 245 calls Pylint but first
inserts `src` into `sys.path`. The unmodified code then reports ordinary lint
messages rather than F0010. This does not establish reproduction under the
original conditions. Later edits and an unexecuted added test target direct
`ast_from_file(directory)` instead. There is no post-edit caller execution. The
environment difference is observed; its individual effect was not isolated by a
new experiment in this allocation.

**B5: helper success promoted to original-task success.** After editing the spec
type, probe 282 verifies namespace/ordinary-package helpers, adds `src` to
`sys.path`, and tests an initializer-present sibling. Those assertions pass, but
neither the original Pylint caller nor a pre-edit baseline is run. Finish 297
claims the missing-initializer case is addressed; independent caller/native FAIL
contradicts that scope. A1/A3/A5/A6 similarly submit after broad regression PASS
without a faithful original-caller verification. A4/B3/B6 end without a patch;
an unfinished investigation is kept separate from a false success claim.

## Preserved and displaced evidence

Thirteen recovery actions enter twelve distinct subsequent inputs. Nine of those
input transitions lose no source lines or probe bodies. The other three are:

| Row and input transition | Restoration | Newly absent evidence |
| --- | --- | --- |
| B2 299 -> 318, result handoff | Builder body, 229 formerly absent lines | Original F0010 probe body; one modutils docstring line |
| B2 397 -> 415, size handoff | 110 test lines | 655 current-version source lines and the namespace-helper probe body |
| B4 194 -> 211, result handoff | 260 builder lines | Helper body containing a keyword TypeError and successful namespace load; no source loss |

The 655 lines comprise builder 187, import spec 240, import util 3, modutils 133,
scoped nodes 61 and scoped-node tests 31. These include relevant resolver and
loading context. Later searches restore builder/spec/scoped-node ranges. B2's
original F0010 body reappears by input 415 and remains available at the edit in
484; its loss is temporary, not permanent lack of acquisition. B4's altered-setup
Pylint body separately leaves at result handoff 267 before the later edit.

These are observed adjacent-input changes. They do not isolate which losses were
caused by adding recovered source rather than the unchanged handoff/selection
rules. All handoffs and versioned source ranges are retained in
`public-review-summary.json`; `delivery-review/` records probe disappearance and
reappearance. Source-version replacement is not automatically missing current
counterevidence. The sealed description originally called modutils line 241 blank;
`postseal-descriptive-correction.json` records that it is `:return: the loaded module`.
No label, count or sealed annotation was changed after grades were opened.

## Cost, context and completion overhead

| Settled cost component, USD | A | B |
| --- | ---: | ---: |
| Uncached input | 1.43077500 | 2.00344575 |
| Cached input | 0.29589120 | 0.38906880 |
| Reasoning output | 1.32568650 | 1.82295450 |
| Other output | 0.17009550 | 0.26372700 |
| Total | **3.22244820** | **4.47919605** |

| Resource | A | B |
| --- | ---: | ---: |
| Generation / input-count calls | 156 / 165 | 202 / 215 |
| Input tokens, including cached | 5,852,916 | 7,858,845 |
| Cached input tokens | 3,945,216 | 5,187,584 |
| Output tokens, including reasoning | 332,396 | 463,707 |
| Reasoning output tokens | 294,597 | 405,101 |
| Largest dispatched input | 58,935 | 58,912 |
| Size handoffs: input / encrypted item | 8 / 1 | 11 / 2 |
| Result handoffs | 11 | 15 |
| Output-ceiling reductions | 3 | 5 |
| Sum of last active-time receipts, seconds | 2,528.628 | 3,154.709 |

B uses more model calls, input and output under the same limits. Its cost is
USD 1.25674785 higher, approximately 39.0%. This bundle comparison does not isolate
automatic recovery's individual cost from changed trajectory, prompt/schema and
verification behavior. Separate local assessments took 217.180 seconds in total.
Previous settled charges and UNKNOWN bills remain separate and unresolved by this
allocation. Official standard/global pricing was reviewed before dispatch.

## Decision, limits and evidence

The evidence supports a narrow schema-operability correction and successful
source delivery. It contradicts a repair-gain claim for this six-per-arm exposed
task. It also distinguishes a real diagnostic success in B2 from unsupported
helper-to-task conclusions elsewhere. The declared-reproduction comparison was
not exercised, so its potential benefit is unresolved, not disproved by six uses.

The next unresolved issue is how the agent selects and preserves the original
caller/input/environment and uses contradictory observations when choosing a
repair. B2/B4 offer existing contrasting traces for diagnosis. Another prompt,
memory rule or paid repetition is not automatically justified. The current runtime
is not changed by this report; no further experiment or rollout is authorized here.

Primary packet evidence: `manifest.json`, `authorization.json`, `collection.json`,
`audit-public/`, sealed `annotations.json`, `review/`, `delivery-review/`,
`result.json`, `assessments/`, `usage.json`, `execution-review.json`, `analysis.json`
and `closeout-verification.json`. Journals are append-only/hash-chained. Final
verification rechecked runtime/environment identities, all 358 generation receipts,
380 count receipts, exact submitted-patch identities, twelve caller checks and six
native evaluations. The only allowed post-count request change was a reduction
of `max_output_tokens`; exact request reconstruction checked all other fields.
An initial closeout equality check incorrectly rejected these eight already
authorized reductions; its script is preserved and the corrected exact-field
check passed without changing a run, limit or historical artifact. Manifest-bound
guidance was copied before current documentation was updated.
