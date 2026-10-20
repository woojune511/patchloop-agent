# Size-only boundary replay: retention, input size and cost

2026-10-19. Offline diagnostic; official=false; no new model requests, provider
token counts, tool executions, evaluator runs, credential reads or spend.
Runtime/default policies are unchanged. This does not reopen the closed
[caller-evidence experiment](2026-10-19-caller-evidence-results.md).

## Question and decision

The caller experiment lost its full supplied public caller observation at the
first subsequent handoff in every B continuation: five result-driven boundaries
and one token boundary. Would the existing `size-only-v1` policy retain it longer
under the same limits, and what would that cost?

Reconstructing the saved trajectory supports a retention benefit in five of six
B rows, but not a repair benefit. The central estimate retains the exact caller
packet for 32 request opportunities instead of 25, increases total input tokens
by 10.83%, and increases the fixed-trajectory cost by 9.42% if the same absolute
number of input tokens is cached. Three rows cannot reproduce their entire saved
response sequence within their original row allocations. Keep the runtime
baseline: delivery and affordable opportunities to use that delivery must both
be measured in any later, separately approved comparison.

## Scope and reconstruction

- Source: the last Astroid-1333 A/B experiment, six continuations per arm,
  `gpt-5.4-mini-2026-03-17`, xhigh. All 123 dispatched requests after checkpoint
  sequence 341 are included. No row is selected using its repair grade.
- Start with each row's exact common fresh-segment input at request 350. Change
  subsequent boundaries only. This does not estimate running size-only from the
  beginning of the original 40-call task or recover pre-checkpoint discarded text.
- First reconstruct the original policy. All 123 input projections match the
  saved input and canonical request hashes; all original cost admissions and
  settled usage reconcile to USD 3.97121625.
- Reuse public context artifacts, actual native continuations and completed tool
  results in order. No new model response or tool outcome is invented. The
  runtime's source deduplication, historical snapshot preservation, optional
  evidence selection and public projection helpers build each input. Derived
  plan handoff-review signals follow the new boundaries. Model-authored plans,
  notes, receipts, decisions and all resource observations otherwise stay fixed.
- No new source reads enter the inputs. Selected current source remains at most
  24,000 characters; current-question references remain at most two. The latest
  completed tool batch is separate from those optional references. Earlier native
  history may contain more records, exactly as in the existing segmented policy.
- Opaque reasoning is copied and hashed, never decrypted or printed. The
  reconstructed requests are diagnostic artifacts, not resumable run envelopes.
  Provider acceptance of recombined opaque items is NOT_RUN.

Unchanged limits: 60,000 input tokens, 1,048,576 serialized request bytes,
262,144 bytes per encrypted item, 40 model calls, 100 actions, four accepted edits,
1,800 seconds including the 330-second evaluation reserve. No extra calls,
actions or time are allocated. Changed inference latency is unknown; a saved
trajectory's wall time is not a forecast of its counterfactual runtime.

## Exact bytes versus estimated tokens

HTTPX serializes the entire reconstructed request locally. Reported bytes are
before the output-ceiling cost adjustment; that adjustment can only shorten the
25,000 ceiling used here. Both byte limits are checked before accepting a
candidate. A size boundary rebuilds the normal public seed, with the existing
optional-evidence fallback; it does not clip native content or expand the limits.

Counterfactual token counts are estimates. A locally installed `tiktoken 0.12.0`
and cached `o200k_base` tokenize visible content only. Retained opaque items use
their one-to-one saved reasoning-output usage. Protocol overhead is approximated
by 30 tokens per native call/output pair and seven per developer message. Each
estimate is anchored to that same request's actual count with identical tools.
An empirical sensitivity margin of at least +/-128 tokens covers observed
within-schema residual variation across six schema groups. This is neither a
provider count nor a statistical confidence interval or guaranteed upper bound.
The CLI blocks socket connections, including tokenizer downloads.

Central, lower and upper estimates all produce 13 subsequent transitions rather
than 36. Only B5's precise transition position changes in the sensitivity replay:
its untrimmed request 421 is estimated at 60,068 tokens, so the lower scenario
keeps it and transitions at 435. The central and upper scenarios transition at
421. This ambiguity must be resolved by an actual count before any live dispatch;
the 60,000 limit has not been relaxed.

## Exact caller observation retention

Presence requires the identical complete public observation object, including
both original programs, setup checks, missing/present inputs, caller arguments,
environment and results. Matching a summary or keyword is insufficient. The
object's observation-record hash is
`sha256:74ad9e0aaec01f003f7eb38b070e00e64970f512cf919c65a49389be771c44b9`.

| Row | Original request opportunities | Size-only central | Additional | Last original -> size-only request sequence |
| --- | ---: | ---: | ---: | --- |
| B1 | 3 | 6 | 3 | 378 -> 426 |
| B2 | 4 | 5 | 1 | 394 -> 410, end of saved trajectory |
| B3 | 3 | 4 | 1 | 377 -> 393 |
| B4 | 6 | 7 | 1 | 421 -> 437, end of saved trajectory |
| B5 | 4 | 5 | 1 | 390 -> 405; lower scenario retains through 421 |
| B6 | 5 | 5 | 0 | 406 -> 406; both encounter the size boundary at 425 |
| Total | 25 | 32 | 7 | Lower sensitivity: 33 opportunities |

All these additional early opportunities also fit the unchanged row budgets
under the saved-cache-count scenario. The same observation remains historical
after edits; presence does not mean it describes the current candidate. B3/B5
had already changed the tested caller conditions while the original packet was
present in the actual logs. Longer retention does not establish corrected judgment.

## Other retained and displaced information

Across the full fixed 123-request trajectory, size-only adds 9,071 source-line
exposures and loses 1,643 relative to the original inputs; it adds 108 tool-result
exposures and loses 24. An exposure is a record/line in one request: these are
not counts of unique lines, relevant facts, or correct interpretations. File hash
and line ranges identify every source difference in `result.json`.

Losses are concentrated in B1 (1,008 line exposures), B3 (150), and A5 (485).
They include manager, modutils, builder, import-spec and test source. Twenty-three
lost tool-result exposures are reads/searches: later size boundaries can discard
records that a more recent original segment still retained. Thus the two policies'
inputs are not a simple subset/superset relationship.

The remaining lost result is B5's earlier probe at sequence 325, which the
original handoff reintroduces at request 405 via a question reference. Size-only
has not transitioned then and therefore does not reselect that older result.
It shows namespace success for `src.project`; it is useful comparison evidence,
but uses a different module name from the actual failing `project` caller.
At that request size-only instead still has the exact supplied caller packet.
This illustrates a real tradeoff between retaining old history and reselecting
older evidence at a handoff, without increasing the two-reference allowance.

Complete program-plus-stdout delivery lasts longer for five newer probes:
B1/447 (+2 requests), B1/508 (+2), B3/370 (+1), A5/399 (+1), B5/383 (+1).
These include helper successes as well as failures; they are not uniformly
evidence for a correct repair. One of B1/508's added exposures occurs at 544,
which does not fit the saved-cache-count budget projection.

B1's actual Pylint failure at action 537 is present in request 544 in both
reconstructions. The size-only projection cannot fund that next saved response.
Retaining counterevidence in a constructed input is not the same as funding a
model opportunity to act on it.

## Input and cost comparison

The table holds all 123 output sequences fixed, before applying early cost stops.

| Metric | Original observed | Size-only central reconstruction |
| --- | ---: | ---: |
| Subsequent segment transitions | 36: 31 result, 4 token, 1 encrypted-item | 13: 12 token estimate, 1 encrypted-item plus token estimate |
| Total input tokens | 4,601,601 | 5,099,810 (+10.83%) |
| Median input tokens | 35,813 | 40,858 |
| Maximum admitted candidate input tokens | 56,270 | 59,657 estimated |
| Total serialized request bytes | 24,940,211 | 29,328,873 (+17.60%) |
| Median serialized bytes | 180,890 | 227,705 |
| Maximum serialized bytes | 422,798 | 475,118 |
| Maximum retained encrypted-item bytes | within 262,144 | 177,316 |
| Cost, original absolute cached-token counts | USD 3.97121625 actual | USD 4.345124775 estimated (+9.42%) |
| Cost, no cached tokens | USD 5.44131225 repriced | USD 5.814969 estimated |

Frozen study prices are USD 0.75/M input, 0.075/M cached input, 4.50/M output.
The cache scenarios are assumptions, not bounds or a claim of unchanged cache
behavior. Longer prefixes may alter cache hits, and actual outputs may differ.
Lower/upper token sensitivity yields full-trace costs of USD 4.3451-4.3507 using
saved cache counts, and USD 5.8150-5.8206 uncached. The lower token scenario can
cost more than the central scenario because it delays B5's rollover.

Each row still has a USD 0.88 logical cap, of which USD 0.37263270 is inherited
debit: only USD 0.50736730 remains. Group new-spend cap stays USD 6.08840760, with
no transfer between rows. The production cost ledger admits uncached input plus
an affordable output ceiling even under the cached billing scenario.

| Counterfactual cache assumption | Saved responses reproducible within caps | Estimated cost of those compatible prefixes | First incompatible saved responses |
| --- | ---: | ---: | --- |
| Same absolute cached-token counts | 120/123 | USD 4.201550625 | B1/544, A3/520, A5/558 |
| Uncached | 109/123 | USD 5.04175350 | A1/506, B1/502, A3/485, B3/483, A4/508, A5/516 |

For A3/520 the central affordable ceiling is 7,403 versus 11,029 saved output
tokens; for A5/558 it is 170 versus 3,259. B1/544 cannot admit the minimum output
under its row cap. These are incompatibilities with the saved trajectory, not
predictions that the live model would necessarily fail or produce those outputs.
Original B1/A3 were already unsubmitted cost stops; the diagnostic does not count
them as two newly observed repair failures. Having group budget left does not
permit borrowing across row caps.

## Evidence, implementation and validation

Reusable diagnostic: [size_only_replay.py](../../diagnostics/size_only_replay.py).
Regression tests: [test_size_only_replay.py](../../tests/test_size_only_replay.py).
No runtime code, transition defaults, prompt, source selector or limits changed.

Final evidence root: `C:/pt/sizeonly19replay-v3/`:

- `result.json`: all three token scenarios, per-request hashes, exact byte sizes,
  source ranges, program/stdout delivery and cost admissions. SHA-256:
  `f3742de5b9a21ebf457086b550b02af3752f3ec6be958b4da06e3d228ca730ac`.
- `summary.json`, `analyze.py`, `analysis-console.log`: descriptive aggregation.
- `artifacts/`: exact central reconstructed inputs and all scenario receipts.
- `runs/run_dev_sizeonlyreplay.jsonl`: hash-chained specification, baseline
  parity, token calibration, per-row receipts and completion records.
- 592 source files verified unchanged. Original experiment data and the user's
  existing `AGENTS.md` edit are preserved. Initial development runs remain at
  `C:/pt/sizeonly19replay/` and `C:/pt/sizeonly19replay-v2/`.

The first new focused test run had one invalid minimal fixture without a required
state `content` field; the fixture was corrected without relaxing validation.
A subsequent broad command named a nonexistent cost-test file and collected zero
tests; that receipt is preserved separately. Final validation receipts record
13 focused/documentation tests passing in 7.67 seconds (`focused-docs.xml`),
including a mock solve reaching isolated evaluation, and 99 related tests passing
in 389.73 seconds (`C:/pt/sizeonly19replay-v2/validation-final.xml`). The related
group overlaps the focused group; these are not 112 distinct tests. Ruff over
runtime/tests/the new diagnostic and `git diff --check` pass.
Full repository tests and live model uptake/repair evaluation are NOT_RUN here.

Reproduce offline with the frozen local tokenizer package/cache and a fresh
external output directory:

```powershell
.venv/Scripts/python.exe -m diagnostics.size_only_replay --manifest C:/pt/ce19ready/packet/manifest.json --output C:/pt/sizeonly19-new --after-sequence 341 --tokenizer-package C:/pt/sizeonly19-tools --tokenizer-cache C:/pt/sizeonly19-tools/tokenizer-cache
```

The supported conclusion is narrowly mechanical: size-only generally buys more
early raw-evidence opportunities in these saved continuations, at larger input
and reduced affordable continuation length. Whether the model uses those
opportunities to preserve the original caller conditions and repair the task is
still unanswered. No paid follow-up is authorized by this record.
