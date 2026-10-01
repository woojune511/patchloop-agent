# jsonschema single-run result and acceptance mismatch

One approved fresh autonomous run completed on 2026-09-30 UTC / October 1 KST.
Run `run_dev_c6b70ef10dfb4926`; runtime checkout `37e67832`, task version 1,
task hash `sha256:44d8ab5d22e9f02b8030717659bef9ca64fe966d0ae0efa1fbfde50f19793414`.
Model gpt-5.4-2026-03-05, xhigh, desired output 25,000; selected baseline
policies, repeat 1, invocation cap USD 3, repository .env credential file.
Registered rates matched the [official model pricing](https://developers.openai.com/api/docs/models/gpt-5.4)
at preflight: input/cached/output USD 2.50/0.25/15 per million tokens.

## Observed result

The agent read source, searched the regex registration, made one accepted edit,
ran both public checks and submitted. It added RecursionError to the regex
checker's registered exception tuple, preserving re.error. No operator hint,
manual edit, rescue, retry, resume or additional paid run occurred. No probe ran.

Six model calls, six input counts, six tools, one edit; active elapsed time
132,947 ms. Settled recorded cost USD 0.245791 of USD 3. Remaining allocation is
closed. Submitted patch hash:
`sha256:1cf85e65f9fead3400c77d52ddb70003174517260a82ea62910764d09ca741da`.

Both public checks pass before submission and again in the separate evaluator
workspace. Regex controls pass and eight upstream format tests pass. All four
scope/dependency/test-tampering/public-API policy checks also pass. Safety is PASS
under the recorded controls; official=false and claim_eligible=false.

The preserved terminal is nevertheless EVALUATOR_FAIL, task acceptance FAIL,
failure class PRIVATE_EVALUATION_FAILED. This is not an observed semantic failure
of the submitted patch.

## Root cause and corrected interpretation

The admitted package has no hidden checks. EvaluationEngine._aggregate returns
NOT_RUN for the empty hidden category, while evaluate requires hidden, regression
and scope categories all to be PASS. Thus the public-only package cannot satisfy
the existing acceptance contract even when every executed check passes.

The preceding admission checked commands, calibration, schema, projection and a
different mock task, but did not exercise this package through final aggregation.
That preparation omission is the operator's, not an agent repair failure. The
earlier admission record's public-only evaluation description must be read with
this follow-up; its historical bytes and the original FAIL receipts are preserved.

Evidence rules out a failing public regression or policy check as the cause in
this run: all six evaluator results are PASS, provenance says evaluation completed,
and source directly reproduces the empty-hidden NOT_RUN aggregation. It does not
establish independent hidden correctness or general repair improvement.

Next engineering question: how should the existing contract admit and report a
public-only task without pretending that hidden checks ran? Resolve this locally
with a focused aggregation/admission test before any further live work. Do not
duplicate public tests as nominal hidden evidence or silently rewrite this result.
No runtime change or corrected evaluator replay was performed in this closeout.

## Evidence

External run root: `C:\pt\runs\jsonschema-1538-20261001-v1`.
Journal: `runs/run_dev_c6b70ef10dfb4926.jsonl`.
Evaluator provenance hash:
`sha256:f75215fc22ee82687269b25467c2598fbd3942504ea69fb8b9ae5bd088de45db`.
Separate authorization/closure journal:
`C:\pt\preparations\jsonschema-1538-20261001-v2\live-authorization\runs\run_dev_jsonschema1538authorization.jsonl`.
Post-run inspection used saved receipts and local source only; no agent-context
reinjection or new provider request occurred.
