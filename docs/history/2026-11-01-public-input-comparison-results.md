# Public-condition comparison: saved task 8 diagnostic

Date: 2026-11-01. Status: CLOSED. Execution commit:
`0dfe7c6d590458d3eee702ba8a8745932c995d65`.
Runtime: `sha256:763e4efd4f14a7939d9ca1e01db91d770be3445da6b3642404da3ddb12e96298`.
All evidence is development-only, official=false and claim-ineligible.

## Question and fixed conditions

The [preceding diagnostic](2026-11-01-capability-aligned-verification-results.md)
stopped with material original-input uncertainty after a successful helper. Its
single case.input field did not separate the public conditions from the helper's.
The [implementation](2026-11-01-public-input-comparison.md) separates those roles
and connects the existing interpretation/plan guidance to their differences.
The question was whether the model uses that distinction accurately to choose a
discriminating observation or an evidence-supported stop. A probe is not required
when source establishes that a difference cannot affect the question.

This was one new approved fixed-patch review of dev-train 8/pydicom1413, using the
same seq38/ancestor138 public checkpoint and candidate be082f27. The checkpoint,
saved plan, source/history, capability projection and allocation match the prior
review. Only the current scope input/interpretation schema and brief-plan scope
paragraph change. The inherited plan was not reset or normalized. Later reports,
operator counterexamples, private evaluator details and raw/encrypted reasoning
from earlier runs were not supplied. This public reconstruction is not a native
resume or a fresh repair; one sample cannot isolate causality or generalization.

Model: gpt-5.4-2026-03-05/xhigh, named repository .env credential file, one run.
New cap USD1.5431895; at most four model calls, ten actions, two probes and 600
seconds; each call at most 60,000 input and 25,000 output tokens. Exact input
counting precedes dispatch, SDK retries are zero, and uncertainty stops new work.
Only read/search/public probe/report were offered; no patch changes or independent
evaluation. Four maximum-size responses would cost USD2.10, so call count is an
upper bound, not guaranteed output funding. Standard rates were verified against
the [official pricing page](https://developers.openai.com/api/docs/pricing).

## Observed execution

- Terminal: REPORT_RECORDED / no_counterexample_found.
- Two model/count calls, one read_file, one report, zero new probes.
- Elapsed 232.128 seconds. Maximum counted input 44,427 tokens.
- Recorded generation cost USD0.4385265; cache-neutral USD0.4923825.
  Generation usage is known; count endpoint billing and invoice remain UNVERIFIED.
- Candidate identity remained exact and cleanup had no uncertainty. No retry.
- Arithmetic remainder: two calls, eight actions, two probes, 367.872 seconds,
  USD1.104663. All unused allocation is closed, not reusable authority.

The first decision revised the inherited plan to read filewriter source and then
report the existing helper evidence. It selected pydicom/filewriter.py:276-620.
The next decision used the new input object for all four review rows and reported
immediately; the host accepted the scope annotation without a semantic verdict.
The rows cover the saved byte-VR family helper, its OL bytes control, a UL list
control with null public_conditions, and source inference for save_as/explicit VR.
All execution IDs refer to the previously saved candidate probe, not a new run.

The report now distinguishes direct array input from the quoted .tostring() bytes
sample and explicitly notes that the saved base helper's bytes case passed while
its direct-array case failed. It does not claim task completion or original-case
reproduction. This is narrower and more candid than treating the helper failure
as the established cause of the literal public report.

## What remains unsupported

The two main public_conditions fields still summarize the error rather than
preserving the known H-array-to-bytes and lineSeq construction. case_conditions
correctly names the I-array helper and flat Dataset/write_dataset path. The
interpretation acknowledges direct-array versus bytes substitution, but does not
fully assess the H/I, caller and setup differences. Missing indexData/lineSeq/ds
construction prevents an exact original replay; it does not establish that every
assumption-labeled observation would be irrelevant.

The writer-before-header source supports a local explicit/implicit write inference.
However, the 345-line read revisited 160 relevant lines already present in the
first actual request (276-310 and 496-620); the newly read 185 lines mostly concern
other string/date writers. No save_as/dcmwrite definition was added. The source
does not establish the entire caller's equivalence to the helper. No new original-
style or explicit/save_as observation was executed, and registered regression
checks and the added test remain NOT_RUN in this diagnostic.

The model judged a direct current-diff save_as/original-style probe unlikely to
overturn this bounded review and retained the original-input issue as a limitation.
Its plan did change, but kept the objective around validating the edited byte-VR
guard and then reporting. This is not evidence that the inherited finish criterion
was broadened to resolve the public report. Plan influence remains a hypothesis;
local source inference and the diagnostic's bounded review objective are plausible
alternative explanations. Zero probes alone does not establish an unjustified
stop, but sufficient equivalence evidence for the original conditions is still
missing. The run ended voluntarily with resources available.

## Decision and evidence

The result supports live delivery and use of the new representation, explicit
substitution disclosure, and compatible evidence reuse. It does not demonstrate
better autonomous verification selection, repair, acceptance or lower latency.
Keep the bounded comparison as an inspectable representation; do not describe it
as a proven quality intervention, increase caps on this evidence, or add a blanket
probe gate. The next unresolved question is how the model weighs public-condition
uncertainty against its self-selected patch-review finish criterion. Another run
needs a distinct evidence-based question and a fresh allocation.

Local preparation: ten public-only mock checks passed in 24.88 seconds, Ruff and
independent packet comparison passed. Existing implementation quick validation
remains 1,453 passed/one platform skip, including isolated mock evaluation.
The live run did not execute independent evaluation or modify the candidate.

External append-only evidence:

- Preparation: `C:/pt/input-comparison-review-20261101-v1/`.
  Plan `sha256:245de463ec7c74d73c7c44bb77d52d84077af5942e2de424572a3d0b3c0e65c8`;
  request `sha256:42b2b773a533ebe467dace95125b5a783a41859284daf3f9521068b51ad19640`;
  checkpoint `sha256:0c21b8823ec1edf221c9b0114baa8dea743a00905a08da5d7dd33b3ffe339fd6`.
- Execution: `C:/pt/input-comparison-review-run-20261101-v1/result.json` and
  `runs/run_dev_c4e46bb4010745ff.jsonl` under that root.
- Public audit and closure: `C:/pt/input-comparison-review-closure-20261101-v1/`.
  Selected public facts, hashes and closed allocation are retained in
  `public-audit.json`, `closure.json`, content-addressed artifacts and dev-run-v1.
  No private evaluator bodies or raw provider reasoning were read for this audit.
