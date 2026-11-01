# Fixed-request model comparison: partial mini repair and incomplete full repair

## Material Passport

Date: 2026-10-27. ARS experiment result; official=false, claim-ineligible.
Status: CLOSED, all thirteen provider responses settled. The user explicitly
approved the [prepared scope](2026-10-27-model-setting-plan.md): one fresh run per
model, same seed/source/thin requests, xhigh, USD 6.60 per arm and USD 8.60 overall.
Implementation commit `d650a6f`; runtime and operator hashes matched preparation.
No additional paid run, submission or independent task acceptance occurred.

## Main result

Both models made one edit and passed the registered public regression suite.
Only mini removed the original unexpected exception. Mini still failed the
predeclared whole-case input identity requirement: the control's captured directory
changed after the first successful call. Full resolved the tokenization subproblem
but failed at the next caller stage because it omitted the stream encoding.
Neither arm satisfies the complete primary outcome; preserve both negative
verdicts without conflating their distinct reasons.

| Outcome | A: GPT-5.4 mini | B: GPT-5.4 |
| --- | --- | --- |
| Normal / correction responses | 8 / 0 | 5 / 0 |
| Model actions | 10 reads/searches, 1 actual probe, 1 edit | 10 reads/searches, 1 actual probe, 1 edit |
| Probe scope | Original-requirement call | Helper-only tokenization test |
| New patch | Empty byte stream and UTF-8 encoding | Empty byte stream only |
| Frozen original call | SystemExit 16, no F0010/unexpected exception | Outer FileNotFoundError; inner ValueError in similar.py |
| Control outcome/capture | Unchanged | Unchanged |
| Call-1 input conditions | Identical | Identical |
| Call-2 input conditions | Different root hash, 8 to 10 entries | Identical |
| Strict case_support.supported | false: whole-case identity | false: unexpected exception/incomplete case |
| Public regression | 1,231 passed, 69 skipped, 15 xfailed | Same |
| Settled USD | 0.141699450 | 0.302224000 |
| First dispatch to model terminal | 117.83 seconds | 129.05 seconds |

Total settled cost is **USD 0.443923450**. Every dispatched request retained the
same initial exception/source evidence and the full 40K output allowance. Maximum
input was 29,903 / 26,087 tokens and maximum single response output was 14,157 /
3,223; total output was 20,413 / 7,509. No input/output/cost ceiling was exhausted,
no price-induced tool narrowing occurred, and no correction or SDK retry was used.
Both exhausted twelve model actions exactly at their successful edit; mini used
its eighth response, while full used five responses through larger read batches.
Fewer responses did not yield lower observed latency or cost in this one pair.

## Repair mechanism and what was actually tested

Both patches changed `build_namespace_package_module` in `astroid/builder.py` while
retaining the seed's missing-initializer guard. They did not repeat the earlier
overbroad removal of the existing-file guard. Host public line observations
collected the new changed lines for both arms (A 292-295; B 292-294), so failure
cannot be attributed to these edits never being reached. This is launch-thread
line entry, not comprehensive branch or requirement coverage.

A sets `module.file_bytes = b""` and `module.file_encoding = "utf-8"`. The unchanged
host helper then captures normal SystemExit 16 for both original and control.
The captured diagnostic predicate and authored observation consistently say no
F0010 in either call. Public regression also matches the independently checked
seed baseline. This establishes observed behavior improvement on that original
invocation; it does not establish complete package traversal or task acceptance.

B's helper explicitly compared tokenization before and after assigning empty
bytes. It reproduced AttributeError and then returned two tokens. This was a
valid helper experiment, with `verification_scope=helper_or_unbound_diagnostic`,
not an original-call replay. Its resulting patch supplies an in-memory stream but
leaves `Module.file_encoding` at None. In the host's unchanged original call,
`pylint.checkers.similar.process_module` passes this stream and encoding into
`append_stream`. The prepared public source at lines 381-383 explicitly raises
ValueError for a binary stream with no encoding. The captured frame at line 383
matches that source hash. Crash reporting then masks the new inner exception
with the same outer FileNotFoundError. Regression PASS does not cover this defect.
Removing A's single UTF-8 assignment makes its complete `builder.py` bytes equal
to B's; the analysis journal records this source comparison. The live executions
remain one stochastic run per model, not a model-quality estimate.

The host marks B's authored no-F0010 observation UNKNOWN/not_compared because the
target raised unexpectedly; no false success credit was granted. The limitation
is the gap between the narrow helper premise and the complete caller contract,
not failed execution of the new branch. The one-edit diagnostic cannot return
host feedback for a second repair; this remains a deliberate scope limit.

## Why A's strict identity still failed

The frozen helper, expectation and call-1 conditions are unchanged. Only call-2's
input root hash and entry count differ from the base: eight entries became ten.
The control's argument, environment, outcome and captured output remain the same.
The helper deliberately places HOME and XDG_CACHE_HOME under the root that it
snapshots as input, and executes original then control in that shared root.

Public Pylint persistent-cache creation after the first successful call is a
plausible explanation for the two added entries. However, the bounded snapshot
retains only the directory hash and count, not its individual paths, and temporary
container state was cleaned up. The actual added paths were not observed and are
not reconstructed as fact. The old frozen calibration saw a crashing first call,
so the control input could now include outputs of the improved first call.

Keep the original `same_call_conditions=false` and `supported=false`. Do not
retroactively ignore arbitrary files or mark this closed experiment as passed.
A small local follow-up should separate declared fixture inputs from cache/output
directories, record the relevant bounded path delta, and replay both seed and
saved candidates under that new explicitly versioned calibration. Check original
and control independently and verify intended directory traversal, rather than
treating absence of a fatal diagnostic alone as complete correctness.

## Decision and limits

This pair does not support replacing mini with full as a sufficient repair fix.
It also does not establish mini superiority: one stochastic run, one repeatedly
studied development candidate, fixed order, caching and service timing preclude
generalization. The new fresh mini arm is the comparison baseline; the older
annotation run had a different dollar cap and is not a matched control. Because
neither new arm approached its cap, there is no observed price-induced restriction
here, but a causal effect of the higher displayed allowance is not measured.

The decision is to retain production defaults, preserve the promising mini
candidate, and investigate the local input/output identity boundary before another
paid run. Whole-caller verification remains necessary even when a helper and the
public regression pass. No new mandatory agent gate is inferred from this result.
All eleven ARS interpretation fallacies were checked: no significance claim,
causal proof, universal capability conclusion, hidden/held-out evidence or
acceptance substitution is made. This run's known billing does not resolve the
older source-ready run's separate billing uncertainty.

## Auditable artifacts

- Approved manifest: `C:/pt/model-setting-plan-v1/manifest.json`,
  `sha256:bf640229355b720ad2c86668e776030662efbbc11dd801f0919dd782655feb28`.
- Live result: `C:/pt/model-setting-live-v1/result.json`,
  `sha256:7ab4295f620feff9291c8d088185f940d295b95899b8b091abbc8ab3a834b0ea`.
- Independent request/cost/journal audit: `C:/pt/model-setting-analysis-v1/analysis.json`,
  `sha256:00cb9207864c509e0e832c0ff4382703a07fe8b83690885ec41c421861b4dc03`.
- Public patch/exception audit: `C:/pt/model-setting-analysis-v1/repair-details.json`,
  `sha256:ce3152a9e9c7aa51e2b765a8c893fcf9925c1a226da2bfc58b05b7b2bac62085`.
- Identity-only follow-up separates completeness metadata from the compared fields:
  `C:/pt/model-setting-analysis-v1/call-identity.json`,
  `sha256:eebc92bc53e986e0ac8453e69430de5496da6cb3a7ab6ccd17429a65d9f30a80`.
- A diff: `sha256:a08485418d8117b4dd8507346f7aeed8e66ff0e1e46a0efd33dcee8449cc4bcb`;
  B diff: `sha256:2751c38506cef107831a6c9eecc28129ebca57c39cc20dea0678c64e59e60279`.

The analysis verifies all thirteen actual request artifacts, preserved evidence,
model-specific cached/uncached usage, hash-chained journals and host receipts.
The original program hash remains
`sha256:f4ac4f228032fbb827c6ac9f6b979be8cdfc0148fbad553420d768f791f19dec`.
Generated evidence remains outside the repository and prior historical records
are unchanged. Preparation's 10 new focused, 56 existing owner, docs 5, quick 472
and Ruff checks passed; this result documentation adds no runtime change.
