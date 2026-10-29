# Integrated follow-up after shared repair guidance

Date: 2026-10-30 KST. Status: CLOSED; official=false, development-exposed tasks.
The user explicitly approved this new allocation after implementation and local
validation. No prior unused allowance is reused.

## Question and fixed conditions

The [guidance change](2026-10-30-repair-contract-guidance.md) asks the agent to derive
small checks from affected public contracts, related paths and boundaries, and
observe preserved results/state. Its local delivery and regression tests cannot
establish live repair quality. This fresh integrated run assesses actual public
verification choices and independent acceptance, alongside regression, cost and time.

The descriptive baseline is the [previous 3/9/16 run](2026-10-30-integrated-3916-results.md):
pvlib and pydicom acceptance PASS; SQLFluff acceptance FAIL. Same tasks, model,
limits, selected policies and prepared source/dependency identities are retained.
The runtime intervention is shared prompt guidance plus condensed surrounding
prose; no task-specific hints or runtime execution rules changed. This is one
fresh attempt per task, not randomized replication or held-out generalization.
Outcome differences alone do not establish causal benefit from the prompt.

Success of interest is correct submission without regression, supported by relevant
public checks of the changed behavior and preserved contracts. A larger number of
tests/probes, intent prose, submission, or mock PASS alone is not improvement evidence.
Use concrete regressions or repeated coverage gaps to choose the next change;
the guidance is not declared effective solely because it was delivered.

## Authorized scope and provenance

- dev-train 3 (pvlib1154), 9 (pydicom1694), 16 (SQLFluff1517), fresh once each.
- Model `gpt-5.4-2026-03-05`, xhigh, desired output 25,000 tokens.
- Credential file `C:/Users/geonj/Documents/PatchLoop/.env`; values are never logged.
- Maximum two workers. USD4 per task, USD12 total, fixed non-transferable caps.
- Current/brief-v1, segmented-v1/result-or-size-v1, public-checks-v1, ordinary probes,
  repair recheck, protected inspection, per-call cost admission.
- 40 model calls, 100 actions, 12 accepted edits, 1,800 seconds per task, including
  330 seconds reserved for evaluation.
- Count immediately before dispatch; zero SDK retries. Count, transport, billing,
  continuation or cleanup uncertainty stops new admissions while in-flight calls settle.
- No saved patch, operator diagnosis, previous notes or private feedback is seeded.
  No image pull/build, replacement attempt, automatic resume or extra evaluation.

Implementation and execution commit: `05b1bd7be6340038b5cfca52a1221edd0277c158`.
Runtime: `sha256:4fe33c20ca40c4ed53ce58d5efb508bba6825ff1872d3eeed59da918ee2bf374`.
Preparation: `C:/pt/contract3916-20261030-v2`.
Execution: `C:/pt/contract3916-run-20261030-v2`.
Manifest: `sha256:37534eb07292cdf990d058d1484c71d4feb7cd3e9b73c97a322b9ec23d1dcd41`.

All task/source/runtime/image/credential-shape preflights passed with zero provider
calls. The user then answered "이 범위로 실행" to the exact new scope. The first
approval receipt serialization failed on a datetime before writing content; the
empty file was preserved and `approval-v2.json` plus journal events record the
correction. Direct human approval preceded execution; corrected receipt persistence
followed the first dispatch. This did not start a replacement, retry or resume.

OpenAI Docs confirmed the exact [snapshot and xhigh support](https://developers.openai.com/api/docs/models/gpt-5.4)
and [standard short-context pricing](https://developers.openai.com/api/docs/pricing):
USD2.50 input, USD0.25 cached input and USD15 output per million tokens. These match
the frozen preparation rates. The default global endpoint and 60K input bound
avoid the documented regional/long-context premiums. Runtime remains frozen.

## Results

| Task | Independent acceptance | Safety | Accepted edits / model calls | Task seconds | Settled USD |
| --- | --- | --- | --- | --- | --- |
| 3: pvlib1154 | PASS | PASS | 1 / 10 | 345.332 | 0.578208 |
| 9: pydicom1694 | PASS | PASS | 1 / 13 | 410.307 | 0.8839905 |
| 16: SQLFluff1517 | FAIL | PASS | 2 / 17 | 535.207 | 1.1981815 |

Total USD2.66038 against USD12; two-worker wall time **882.901 s (14 min 43 s)**.
All three fresh attempts submitted once. All 40 provider calls and 40 input counts
settled and linked. No retry, replacement, resume, pending action, orphan receipt,
validation rejection or undo was recorded. Caps were respected and the allocation
is CLOSED. All deliveries were `unverified_delivery`: independent acceptance is a
separate result and does not retroactively supply original/candidate case evidence.

The previous same-roster result was also PASS/PASS/FAIL, with USD1.899919, 33 calls
and 632.445 s wall time. This run cost **40.0% more** and took **39.6% longer**.
These are descriptive differences from one attempt per condition, not an estimate
of the prompt's causal effect. No acceptance gain was observed on this panel.

## Public verification choices

### pvlib: scalar/control observations and the existing-file test path

One transaction changed the implementation and added `test_reindl_zero_ghi` inside
the existing `pvlib/tests/test_irradiance.py`. The original NaN test expectation was
retained. The registered wrapper selected that file and ran **99 PASS** on the
submitted diff; this exercised the recently fixed projection path with admitted
test additions. The earlier run created and explicitly selected a separate file.

The candidate probe asserted zero-GHI scalar output, the nonzero scalar result
27.941169871809286, and four Series values including zero and normal controls.
It did not run the original implementation or assert Series index/type preservation.
The previous run covered ndarray and Series cases in a new file, so this is not
uniformly broader coverage. Acceptance remained PASS; neither the guidance's
causal contribution nor the edit-cap effect is established.

### pydicom: an appropriate added test, then a corrected probe condition

One transaction moved element access under the existing exception handler and
added a test with strict validation, an unsuppressed exception expectation, and an
exact suppressed result containing the valid LO element. The required public file
ran **27 PASS**. The preceding run needed one implementation edit and two test
corrections; this attempt's test was configured correctly at its first edit.

The initial and replayed probe used WARN mode, so the invalid value returned both
before and after the edit. Those observations do not distinguish the repair. A
third probe selected and checked RAISE mode: the default call raised ValueError,
suppression returned the expected valid-only dictionary, and the valid value
remained `0017`. It did not compare RAISE mode on the original implementation.
The unsuppressed and suppressed calls shared a dataset, so this does not establish
simultaneous fresh raw conversion of both elements. Acceptance remained PASS.

### SQLFluff: more observations, the same narrow repair mechanism

The implementation changed only the empty pre-content return in `Delimited.match`:
it returns accumulated matched segments plus `seg_buff`. The earlier candidate
returned accumulated matched segments plus `mutated_segments`. These are different
patches; do not treat the earlier dynamic replay as a replay of this candidate.

The added grammar test uses adjacent `bar..`, `allow_gaps=True`, and
`allow_trailing=True`, asserting the matched prefix's raw text/types and remainder.
Its first execution failed because the expected delimiter used CodeSegment while
the matcher produced SymbolSegment: **1 FAIL / 166 PASS**, one deselected. A test-only
correction fixed that expectation; the automatic public recheck ran **167 PASS**,
one deselected. Explicit selection of the added node then ran **1 PASS**. This was
not a missing-test-execution failure or a second implementation repair.

All five candidate probes concerned the same adjacent `;;` input and a normal
single-semicolon control:

| Public action sequence | Observation | What it establishes |
| --- | --- | --- |
| 186 | Caught SQLParseError from `check_tuples`; normal case returned raw text with L009 | A zero exit is not proof of the question's no-exception premise |
| 219 | AttributeError: FileSegment has no `raw_segments` | Probe API error before completing its cases |
| 235 | Normal case had L009; doubled case raised from `check_tuples` | The planned zero-violation assertions were not reached |
| 252 | Assertions passed for raw preservation, one statement, normal parse and a doubled-case unparsable section | Useful normal/adjacent-case behavior evidence |
| 286 | Both raw texts matched; PRS/L009 versus L009 printed | Repeats the same input pair; no new separator or option boundary |

The issue permits reporting a parse violation rather than ignoring the extra
semicolon. Therefore accepting the PRS observation is not itself weakening a known
requirement. The actual gap is selection: no probe covers whitespace, newline or
comment-separated delimiters, `allow_trailing=False`, or an unmet minimum count.
The source still has the other failure returns that omit consumed input, and the
new partial-success branch still has no trailing/minimum guard. This static review
shows that the mechanisms identified by the [prior public diagnosis](2026-10-30-sqlfluff1517-public-contract-diagnosis.md)
remain unaddressed; the exact earlier counterexamples were not rerun here.
Independent acceptance again FAILs, but its exact failing assertion remains unknown.

## Time and decision

| Task | Provider seconds | Public action seconds | Input-count seconds | Manifest to evaluator receipt seconds |
| --- | --- | --- | --- | --- |
| 3 | 264.182 | 31.483 | 9.445 | 17.905 |
| 9 | 325.356 | 40.450 | 12.097 | 12.153 |
| 16 | 354.107 | 93.009 | 16.233 | 33.512 |

These are interval unions within each task, not sums across concurrent tasks or
pure network/evaluator-compute measurements. Provider dispatch occupied 66-79% of
task time. Unclassified setup/host intervals were 22.318, 20.251 and 38.346 seconds.
SQLFluff increased from 12 to 17 calls and from one to five probes; API correction
and repeated input pairs consumed work without testing the omitted contracts.
The five probe execution receipts total 45.994 seconds, within the action interval.
There is no end-to-end speed improvement in this run.

The shared guidance is implemented and exercised, but this run does not establish
repair gain. Keep its status as an unproven instruction, not a quality milestone.
Do not increase probe quotas, introduce a blanket completion gate, or repeat this
paid panel merely to seek a better outcome. The next engineering question is how
existing verification chooses a case that reaches a different affected return or
option boundary, and how it reuses an adequate observation instead of repeating
the same pair. First inspect that selection/feedback path; another generic prompt
expansion or new tool is not justified by probe count alone. No further change,
public replay, paid solve or independent re-evaluation is performed in this record.

The result preserves the distinction between a public verification gap, task
acceptance and generalization. It does not show that probes are useless, that more
edits would have solved SQLFluff, or that the hidden failure is one of the public
examples. Public action/source analysis read no model inputs, reasoning, private
specifications, hidden tests, reference patches or evaluator internals.

## Evidence and validation

- Final result: `C:/pt/contract3916-run-20261030-v2/result.json`,
  `sha256:a3f23f1c40f62d8dc5865e1366832834c9f8c132c576be7d28225dce7be7aeb8`.
- Settled summary: `summary.json` in the same root; batch completion event
  `sha256:0b921016ac650efaf1a57c053c045a504c1b54d57df18f976db3433ba19ea2cd`.
- Public action audit: `analysis/public-audit.json` points to
  `sha256:2b1b4e9085bbd468146f245bbc2ff31b61ecbcedf059049cdf1d049e24e0276e`.
- Timing/count audit: `analysis/timing-audit.json` points to
  `sha256:bf0b53d281f987ade6c1a19db557cde9f76b184a597fd7e5f0d5a5be6b250a65`.
- Public-only packets: `analysis/public-task-{3,9,16}.json`; task 16 packet
  `sha256:1af1d6894888c84797f5b14b67dd3b49503c9127ff0ef8770b77a7a3f15c37b8`.
- Submitted SQLFluff patch:
  `sha256:6931dbb1c3761b473d5abb81cb11d96ee0e3ca1e05a04fe063810168ee75ee29`.

The source journals are hash-chain verified and remained byte-identical during
public audit. Generated evidence remains outside the repository. Runtime identity
is unchanged from the approved manifest. Prior closed reports are preserved;
this record and current status supply the follow-up interpretation.

Final documentation validation: 6 PASS in 0.11 seconds; HTML has 51 unique IDs and
66 checked links, with JavaScript unchanged; `git diff --check` passed. No runtime
source changed during execution or result recording, so the earlier focused,
Ruff, 1,236-PASS quick suite and isolated mock validation remain the code validation
record; a full suite or new runtime test run is not claimed here.
