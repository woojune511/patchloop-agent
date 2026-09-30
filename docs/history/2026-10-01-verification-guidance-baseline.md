# Restore the previous verification guidance

Decision: do not adopt the assumption-directed prompt change as the baseline.
This is a follow-up to the immutable
[comparison result](2026-10-01-verification-selection-comparison.md), whose
close-out statement that the guidance remained implemented describes that earlier
state. The user approved this subsequent restoration.

The single fresh Darts pair showed direct probes only in B, but both submitted
patches retained the same frozen failures. B cost more and took longer in that
pair. These observations do not prove general ineffectiveness, but do not justify
changing the working baseline. Restore the exact pre-experiment system prompt,
the corresponding prompt hashes/assertions, and the implementation guide wording.
No tool, task package, evaluator, recorded patch, frozen public case or completed
history record is changed. The final PR contains evidence and current decisions;
its runtime and test files match the pre-experiment baseline.

Do not continue tuning against the exposed Darts cases or add another mandatory
verification rule. Future work should begin with an observed failure in another
real repair task and determine whether the same narrow verification pattern
recurs. This is a direction, not a selected task or permission for paid execution.
The previous USD 6 allocation remains closed at USD 1.125171 recorded usage.

Local validation passed 17 focused prompt/schema/documentation checks, Ruff and
git diff --check. Mock smoke reached EVALUATOR_PASS with safety NOT_RUN; receipt:
`C:\pt\runs\verification-baseline-restored-20261001-v1\runs\run_dev_c9f4badd85214be4.jsonl`.
Require the final PR head's complete Linux/Windows CI before merge. These
engineering checks do not establish model-quality improvement.
