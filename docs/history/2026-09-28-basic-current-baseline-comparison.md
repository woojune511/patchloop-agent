# Basic versus current baseline comparison

Date: 2026-09-28. Closed live comparison; every run is `official=false`,
`claim_eligible=false`, and belongs to the mutable `dev-head` lane.

## Question and fixed protocol

The question was whether the chosen current coding-agent bundle produced better
task acceptance than a simpler agent under the same model, tasks, limits,
evaluator, context segmentation, cost admission, and recovery contracts.

- Model: `gpt-5.4-2026-03-05`, `xhigh`, desired output cap 25,000.
- Six checked-in `dev-train` tasks; one fresh run per task and arm.
- Basic: planning `none`, probes disabled, repair recheck disabled.
- Current: planning `brief-v1`, probes enabled with policy `none`, repair recheck
  enabled.
- Shared: segmented-v1 / result-or-size-v1, protected-v1 repair inspection,
  per-call-v1 completion cost, 40 model calls, 100 tool actions, four accepted
  mutations, and 1,800 active seconds.
- Per-run cap: $2; 12-run maximum: $24. Arm order alternated by task. There were
  no retries, replacements, resumes, or cross-run memory.

The comparison changes a three-feature bundle, so it measures the bundle only.
It cannot attribute an outcome to planning, probes, or repair recheck separately.

## Results

| Task | Basic | Current | Paired result | Basic cost | Current cost |
| --- | --- | --- | --- | ---: | ---: |
| fromager recursive orphan removal | PASS | PASS | tie | $0.293969 | $0.339510 |
| HF Hub Xet endpoint propagation | FAIL | FAIL | tie | $0.986342 | $1.122222 |
| Loguru invalid-format feedback | PASS | PASS | tie | $0.415334 | $0.426688 |
| PDM active-venv resolution | PASS | PASS | tie | $0.286192 | $0.353396 |
| pgmpy stable skeleton order | PASS | PASS | tie | $0.262716 | $0.370748 |
| pyfakefs makedirs parent traversal | FAIL | PASS | Current win | $0.532846 | $0.725626 |

Primary result: Basic 4/6, Current 5/6; paired Current wins / Basic wins / ties
= 1 / 0 / 5. All 12 runs had evaluator safety PASS. There were no `NOT_RUN`,
preflight, transport, count, billing, or cleanup-uncertainty outcomes.

| Aggregate | Basic | Current | Difference |
| --- | ---: | ---: | ---: |
| Cost | $2.777399 | $3.338190 | +$0.560791 (+20.2%) |
| Active time | 1,159.543 s | 1,431.504 s | +271.961 s (+23.5%) |
| Model calls | 49 | 51 | +2 |
| Tool actions | 64 | 66 | +2 |
| Accepted mutations | 9 | 9 | 0 |
| Registered checks | 15 | 18 | +3 |
| Input tokens | 906,455 | 1,061,720 | +155,265 |
| Output tokens | 80,529 | 102,751 | +22,222 |

Actual combined cost was $6.115589. Current executed two probes and three repair
rechecks; Basic executed neither. The append-only hash chains for all 12 `dev-run-v1`
journals verified successfully. Live state is retained at
`C:\pt\baseline-compare-20260928-v1`.

## Process evidence from the discordant pair

On pyfakefs, Basic made one mutation. Both registered public checks passed, but the
private evaluator rejected the submission. Current made two mutations. Its first
candidate passed the task contract and failed the upstream public regression check;
after a repair and recheck, both registered checks passed and the private evaluator
accepted the submission.

The public source diffs also differed in shape. Basic added special handling for
parent-directory components before delegating to the existing filesystem helper.
Current ended with a recursive `makedirs` implementation built from the module's
single-directory operation. This establishes a different repair path and final patch,
not which bundle feature caused the difference. Private evaluator details were not
fed back into either agent and are not used as a causal explanation.

## Interpretation and next question

This is evidence that the current bundle can outperform the basic configuration on
one of these six task instances, at higher observed cost and time. It is not evidence
of a general 16.7-point improvement: each arm has one stochastic sample per task,
only one pair is discordant, and three mechanisms changed together.

Keep the current bundle as a working baseline, not a proven default improvement.
If more paid evidence is warranted, start from the pyfakefs repair-path difference
and isolate one mechanism at a time under repeated paired runs. Do not rerun the full
panel merely to seek a more favorable score. This comparison's allocation is closed.
