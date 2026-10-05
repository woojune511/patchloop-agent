# Click feedback correction preparation

Following [original review](2026-10-05-original-patch-review.md), the user requested
two corrections through existing `repair`, with exact paid approval still required.
Original requests, patches, review and execution records remain immutable.
No operator implementation or test correction was made.

Separate local sources contain only upstream
`2247b35ea1c47c727d7a06e51fa280e12a863ff6` plus each original patch:

- #2786 feedback base: `37bcf423d98460047957619ec0c49475fc4169c5`.
- #2740 feedback base: `d0d0226e005e27d78c70b495f5f61654952bd894`.

Requests include original public issues, review evidence, contracts and frozen
operator public checks, without solution patches. #2786 must retain its issue fix
and omitted callback/validation behavior. #2740 must preserve support-version
compatibility and actually test notes on Python 3.11+.

The user separately approved preparing a public Python 3.10 environment. It is
Python 3.10.22/pytest 8.4.2, image digest
`sha256:70d56b13ba853c72848ac06c9cd7c3e3defc956da88f009a4d8dc03c7d410698`.
No hidden/evaluator materials were used. Existing solver environment remains
Python 3.12.13/pytest 8.4.2. Upstream 941 tests pass on 3.10; the unchanged #2740
original patch yields 1 failed/941 passed there, versus 942 passed on 3.12.
The legacy no-note check passes on both. This new observed 3.10 test failure is
separate from the prior static review. #2786's 942 tests pass while its frozen
callback preservation check fails on the original patched base.

Prepared scope: mini `gpt-5.4-mini-2026-03-17`, xhigh, 25,000 output tokens,
one fresh correction each in #2786/#2740 order; USD 3 each/USD 6 total;
40 calls/100 actions/4 edits/1,800 seconds. No paid calls made. No old allocation
approval is reused. Stop remaining calls on count/transport/billing/identity
uncertainty; no retries, resume, replacements or budget transfers.

Preserve correction and upstream-base composed patches separately. Run existing
`repair-verify` on both bases; additionally verify #2740's identical composition
on 3.10. An existing-test decorator/body correction may be `UNSUPPORTED` against
the feedback base even if additive against upstream. Preserve every report and
do not equate those cases. If separation prevents check execution, explicitly
label frozen final-candidate checks through the existing sandbox as supplemental
public receipts, not verifier support. No runtime/driver feature is added.

Evidence and exact execution/verification steps:
`C:/pt/repair-click-feedback-20261005/`. The final manifest freezes request, source,
environment and operation hashes before paid approval. Feedback-informed results
will be recorded separately from the original use evaluation; acceptance remains
`NOT_RUN`, human approval separate. No automatic further batch is authorized.
