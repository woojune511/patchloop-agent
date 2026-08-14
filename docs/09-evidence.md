# Evidence index

Machine artifacts under `reports/` are authoritative. Historical narrative is archived at
`docs/archive/snapshots/d121/09-evidence.full.md`.

## Held-out A/C preregistration

- Preregistration: content `sha256:3b75f049649850b7561f310229e1e5429f72ea24024e835ccf4910fb2c901f74`;
  file `sha256:f6d9d015329823f3f888aac5f15296b2ddefda9e45b5d5501b8d94587bb11d8f` (31,338 bytes). It freezes
  48 rows and `$252`/`$275` planning cost but grants no authority.
- Suite: content `sha256:1d023e8837e99889d76acf6f3a2d970261cb7aa4b3e978c84cef2ef5cf517aaa`; file
  `sha256:27157e26881cc277a9026e51d22a6f21fbf5bbb8f6c1c09eaa89aec607e52534` (13,348 bytes). Plan: content
  `sha256:b2058c48de3f2b4d13df872d7fd19a325c3a76ffb5ef24974310409100cb8885`; file
  `sha256:901f898d7f6f81b00e8840160b3efde2cc4fb7d8f4625c6188ea7235de264695` (2,466 bytes).
- Contract R1 predecessor: content `sha256:f024e04fd3a01b98f8fb469f2f0d0a11f4faf8372ed57cc7986e163bdecc5042`;
  file `sha256:1c42aecbbe4c9e3f39215658fb3ffba87930f94385b526c13287a0d09448fa22` (18,750 bytes). Current R2:
  content `sha256:0277225b0992b8e0562b21f5f8c2f8dcc4921017bea03b5087c4f6dd0e860172`; file
  `sha256:5f5406858603d918f296ca7b4a7bf2d62426c99a5915481964ed41f91c6b961c` (20,052 bytes); source
  `sha256:a61ad810d2d3de4a13c19c7dfd307dc5b64a1a8409b0de1f0858389ba866889c`.
- Binding R3/R4 preserve pre-hardening/pre-format source; R5 owns R4's exact predecessor tuple. Current R5: content
  `sha256:c1dc0d53f5df3cbd8c37cdc453fea738a803177add7a49d6e267b186192d5f59`; file
  `sha256:809981c460c9d28e0dbc17e179260e20eb48641489973cac669b6de72282094c` (4,759 bytes); source
  `sha256:caa95f52567001f68aacdcf3d2cd6bd9006ebbe9d1166c17dc076932c185b279`; plan
  `sha256:34edbad3f5a31f5d7e16ed2358905c195372a0d1f420c0ac03bd3be6a68668a8`.

Held-out gates record zero private opens, materialized/authenticated rows, calls and cost; analysis/execution remain
closed.

## R8 complete development-readiness matrix

Candidate `sha256:60c679083ad7b995918e2ba5de79843be8b03ce0511b67eb859da437f16cff9e` bound source
commit `a4f00f8565c840588b120d91e730427bb51166b5`, Moto A/C + Babel C/A, `$15.30` reserve and `$18` cap. Its one
approval produced four resolved, evaluator-v2 receipt-qualified, trace-qualified and cost-settled rows with all
hidden/regression/scope/safety verdicts PASS; no row retried or was replaced. Total cost was `$0.3664215`.

The immutable final/prepared result is `sha256:8dbcb60a...cc2878` (138,156 bytes); journal is
`sha256:f05dc041...0446a` (15 events, 21,654 bytes). The raw completion adapter accepted only
`trace-qualification-v1` and therefore misclassified four valid `trace-qualification-v2` rows as unclassified,
storing `passed=false`, `official_evaluator_runs=0` and `task_failures=-4`.

Final portable strict index
`reports/live-pilot/dev-validation-ac-fixed-bundle-readiness-20260814-r8-evidence-r4.json` has content/file
`sha256:0ef31d2b...aade83`/`sha256:5035421a...b7c62c` (19,557 bytes). It binds plan, hash-chained journal,
prepared/final result, durable results, qualifications and receipts. Offline recomputation yields 4 official v2
runs, 4 successes, 0 failures and 0 unclassified without rewriting runtime evidence or making any
provider/evaluator/Docker/agent call. Earlier correction indices remain append-only predecessors.

| Task | A tokens/cost | C tokens/cost | C minus A |
| --- | ---: | ---: | ---: |
| Moto | 121,601 / `$0.1086345` | 83,604 / `$0.07001175` | -37,997 / `-$0.03862275` |
| Babel | 108,534 / `$0.115158` | 72,493 / `$0.07261725` | -36,041 / `-$0.04254075` |

Both conditions resolved both tasks. These two one-repetition development pairs authorize descriptive analysis only;
memory-effect, retrieval, held-out, core and B/D authority are false. R8 is consumed.

## R10 source qualification and R9 predecessor

R10/v11/R8 preserved R7 schedule, treatment, budget and cost while adding strict scalar, duplicate-key, paid
import-closure and evidence checks. Artifact
`reports/live-pilot/artifacts/evaluator-v2-ac-successor-offline-source-qualification-r10.json` has content/file
`sha256:66bd54bc...a88b25`/`sha256:09b0d966...6d18b` (20,843 bytes), evaluator source
`sha256:6c6594b4...12bcb1` and successor/base suite `sha256:0c42c3a5...7d71f2`/`sha256:924e21e5...d52e77`.
It qualified the executed bytes; post-run correction source needs a new identity before future execution.

R9 content/file `sha256:aeb41b81...f366`/`sha256:6d59aaae...eb22` and R7 candidate
`sha256:8b962b80...bf6c` recorded zero provider/evaluator/Docker/agent calls. R7 is superseded unexecuted.

## Sealed R6, R5 and R4 attempts

- R6 candidate `sha256:c800f36b...e5d61`: Moto A `run_7c835a6aa5c2411f` resolved and passed evaluator v2,
  but runtime evidence wrote `model-tool-observability-only-v1` instead of required
  `model-tool-bounded-enforcement-v1`; Babel and Moto C did not start. Usage was 144,240 input + 13,648 output,
  14 model/15 tool calls and `$0.169596`. Index content/file is
  `sha256:241f4218...12a6`/`sha256:b84a2783...59d7` (7,218 bytes).
- R5 candidate `sha256:b8d156c6...a1627`: Moto A `run_2007cde54b464938` resolved and passed evaluator v2,
  but qualification required legacy null-call/aggregate-only limits; remaining rows did not start. Usage was
  173,193 input + 14,031 output, 16 model/21 tool calls and `$0.19303425`. Index content/file is
  `sha256:01775e68...655`/`sha256:fa49986e...832c` (6,605 bytes).
- R4 candidate `sha256:be4ea2e4...8d7124`: paid-plan revalidation selected the legacy budget, so Moto A
  terminated before provider dispatch at `$0` and three rows did not start. Its index is
  `reports/live-pilot/dev-validation-ac-fixed-bundle-readiness-20260814-r4-evidence.json`.

All are sealed `inconclusive`; none may retry, resume, repair or transfer approval.

## R3 readiness predecessor

Index `reports/live-pilot/dev-validation-ac-fixed-bundle-readiness-20260813-r3-evidence.json` binds execution
`sha256:c6506a33...374a2a`, journal `sha256:cff6c0e7...4f69` and result `sha256:d94b0a29...edecf`. Moto A resolved
with typed v2 safety and cost `$0.10254975`; Moto C ended before evaluator at 2,963,919/3,000,000 tokens and
`$3.374763`; Babel C/A did not start. Total settled cost was `$3.47731275`. The matrix is `inconclusive`, with no
retry/replacement, held-out A/C or B/D activity.

## Compact historical index

- V23 passed Docker and both typed frames, then ended `ERROR(child_checker_error/diagnostic_result_invalid)`;
  V24 is an offline order-loss fixture and V25 an unused superseded gate.
- D-142 gate `d142_9515aeb4c7289fa26987ec605917c395e54b27d076cd226c266acd2a3cb82914` is source-qualified,
  unactivated and deferred after 170/170 mocked tests. D-129-D-141 are consumed.
- Evaluator-v2 commit `04ee027171d9d4891c4f481d2ccfb277e7a4a9e6` is a predecessor. Exact historical tuples
  remain in `reports/`, Git and the D-121 archive and cannot be backfilled.
