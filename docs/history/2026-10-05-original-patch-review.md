# Original patch acceptability review

Follow-up to [three uses](2026-10-05-three-public-repair-uses.md): finish the
remaining original-patch review without another paid run or runtime change.
The prior execution record and all original patches/tests remain unchanged.
These are Codex recommendations, not human approval or independent acceptance.

| Original | Recommendation | Evidence |
| --- | --- | --- |
| Click #2786 | Modification required | Omitted callback/validation bypass reproduced |
| Click #2740 | Modification required | New test incompatible with supported Python 3.10 |
| dotenv #713 | Acceptable within requested scope | Correct destination, synchronization order and error path in source; existing public execution evidence |

For #2786, an operator-authored check used the same prepared sandbox on the
unchanged base and original patched verifier workspaces. Two options shared a
destination; only the second was supplied. The first option's callback recorded
its value, and a second invocation made that callback reject with `BadParameter`.
Base called it and rejected with exit 2. The patched version skipped it and
returned exit 0. The operator check passed on base and failed on patched code.
This violates Click's documented
[missing-parameter callback behavior](https://click.palletsprojects.com/en/stable/click-concepts/#callback-evaluation-order).
The patch skips all `handle_parse_result` work, not only overwriting the value.
This closes the specific scope concern as a reproduced regression. The new check
is separate review evidence, not model-authored coverage or a verifier replacement.

For #2740, base `pyproject.toml` declares Python >=3.10, while the added test
unconditionally calls `add_note`,
[introduced in Python 3.11](https://docs.python.org/3.11/library/exceptions.html#BaseException.add_note).
The implementation uses `getattr` and preserves no-note output paths; no
implementation incompatibility was established. Python 3.10 was not executed.
A version condition on the new notes-specific test would be reasonable, but no
test or implementation correction was made. Earlier zero skips were observations,
not a universal acceptance criterion.

For #713, source confirms `dest.flush()` then `os.fsync(dest.fileno())` while the
temporary destination is open, before replacement. An error prevents replacement
and flows to existing cleanup/re-raise. Original tests cover both public APIs and
fsync-before-replace. The mock does not validate the descriptor or flush ordering;
source review covers those points. No power-loss experiment or new error injection
was run. Lack of empirical crash durability is a limit, not a blocking defect in
the requested scope. Directory fsync was outside the frozen requirement.

Evidence: `C:/pt/repair-usage3-20261005/acceptability-review/` contains `review.json`,
`REVIEW.txt`, the operator program, base/patched receipts and a six-event verified
hash-chain journal. Review snapshot:
`sha256:b201081543aec7aba65ec349b56f9a96f175f154fbdb478f6aa870d1ea7a6792`.
Additional sandbox execution: 6.672 seconds; new model calls/cost: zero.
Active operator/assistant and human review time was not measured. The user's
conditional assessment explicitly did not inspect the original diff, so actual
human original-patch approval remains unreported.

Decision: recommend one original for scoped acceptance and two for modification.
Do not report 3/3 autonomous success from the automated before/after checks.
Keep the existing workflow subject to source review; no new batch, runtime policy,
generic reviewer, correction or further diagnosis is queued. Actual human approval
and any separately authorized supplementation remain distinct from these originals.
