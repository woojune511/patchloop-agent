# Mini SQLFluff-1733: public metadata correction

Closed: the [corrected attempt](../docs/history/2026-10-16-mini-swe-completion-results.md)
submitted after 52 calls and passed native grading at USD 0.4397661. Across both
row-18 attempts: 150 calls/USD 1.54609845. All five target tasks now have grades;
cumulative experiment spend is USD 6.2666922. No paid follow-up is queued.

The requested five-task completion run submitted all five patches. Rows 8/13/16/17
received native PASS/FAIL/FAIL/FAIL. Row 18 submitted after 98 calls, but native
collection failed before tests. Preserve that run, its NOT_RUN/ERROR evidence and
all original verdicts in `C:/pt/mini5extlive01` and `C:/pt/mini5extaudit01`.

A provider-free public-source 2x2 control found a concrete setup defect: masking
the image's original checkout removed editable package metadata. Import succeeded
but SQLFluff's default configuration/plugins were unavailable. Public `setup.py
egg_info` restored them without changing tracked code. The candidate compensated
with unconditional core-plugin registration, then failed with duplicate registration
in the correctly installed native environment. Hidden tests were unnecessary to
reproduce this cause. The old public import-only canary was insufficient.

Restore public metadata before importing the package, including when plain import
would succeed. This changes no task hint, solving policy, native grader or submitted
patch. The existing 40-call and five-task evidence remains immutable. Historical
SQLFluff comparisons carry this environment mismatch limitation.

The user's request to complete the ungraded cases and existing USD 24/bash consent
cover this necessary corrective continuation. Only the still-ungraded row 18 receives
one fresh attempt with the same model, xhigh, prompts, public issue/source and local
image. No old patch, trajectory, grade, failure diagnosis or hidden information is
supplied to it. Other already-graded tasks are not repeated.

Keep the original five-task per-row resource allocation across both row-18 attempts:
98 of 250 generations and 138 of 1,000 actions were used; USD 1.10633235 of USD 3
was spent. Thus this correction has at most 152 generations, 862 actions and
USD 1.89366765, with no transfer. Give it 2,400 solver seconds and the same 330-second
native allowance. Previous cumulative cost USD 5.8269261 plus its full remaining
allocation is at most USD 7.72059375, below the original USD 24 limit.

Use a fresh frozen checkout and external preparation/live/audit roots. Bind the
operator script, exact source/dependencies, original audit/inputs, public 2x2 control,
configuration, credential path and current authorization basis into the packet.
Run provider-free metadata/config canaries and an isolated native negative mock
before dispatch. Count immediately before dispatch; zero retries and all established
uncertainty/cleanup stops remain. No automatic follow-up after this correction.

Report raw first-follow-up ERROR separately from the corrected attempt and mixed
task coverage. Do not rewrite it as native FAIL or claim a uniform 20-task score.
This repairs an observed public-environment defect; it establishes no PatchLoop
quality gain and does not justify broad reruns of completed tasks.
