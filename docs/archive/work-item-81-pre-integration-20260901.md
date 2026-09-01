# Work Item 81 pre-integration record — 2026-09-01

Historical audit only. These excerpts describe the frozen V27 review before Work Item 82.
They grant no authority. Old current-source builders are not runnable over later source integrations.

## Earlier active evidence excerpt


R16 candidate `sha256:24044c1ed525458446f1c97d94f52331082d74051f5c6d680da995ea9aa48813` settled 48/48 for `$27.24465825`; A/C were 8/24 and 7/24, so C-minus-A is `-1/24` with no causal/general authority. R8's four receipt-qualified Moto/Babel rows passed for `$0.3664215` and support no memory or held-out claim. Exact source-chain tuples remain in the named held-out archives; all are immutable and grant no retry or authority.

## Consumed Rapid R1-R8

Full tuples are in `docs/archive/rapid-r1-r5-evidence-20260818-20260823.md` and the Rapid R7/R8 archives.
R1-R8 are consumed `official=false`; their descriptive completion/cost signals and zero-call qualifications support no quality, memory or external-authority claim.

## Consumed Rapid R9-R18

Exact tuples remain in the named Rapid archives. R9-R18 are immutable `official=false` and non-retryable; R18 settled 6/6 for `$1.52799750`, with V18 3/3/1 and V20 0/0/0, selecting plan-gate liveness only.

## Lean V21/V22 and consumed R19

V21 qualification/review were 5,617/5,559 bytes at file/content `sha256:e45a36b...467bb`/
`sha256:dc1c5be7...71867` and `sha256:aabe212a...a69d`/`sha256:86a58009...18f9`; candidate preparation remained
blocked. V22 qualification/review were 5,281/6,574 bytes at file/content `sha256:abeed728...cf0dc`/
`sha256:57f3b3e5...0d30e` and `sha256:897204b8...270d2`/`sha256:d1194a9c...1a18d`. These are byte-stable public-mock
JSON bytes, not provider-token, cost or quality evidence.

R19 candidate execution `sha256:ed5c3197...066cd` settled 6/6 once for 3,068,239,500 nanos. Its 44,890-byte
append-only bundle is file/final-event `sha256:8647dfdf...a939c`/`sha256:5ace0ddf...446d`: V18
reach/submit/success was 0/0/0, V22 1/1/0, and one V18 row was infrastructure. Diagnosis file/content
`sha256:eae5b243...d764`/`sha256:402943ef...3696` records that V22 rows 3/6 exhausted correction investigation after
one read and two searches, while row 2 submitted then failed hidden evaluation. Full identities and limits are in
`docs/archive/rapid-r18-r22-reproduction-20260829.md`; R19 is consumed and supports no efficiency or quality claim.

## Lean V23/V24 and consumed R20

Full source, qualification, rehearsal and result tuples are preserved verbatim in
`docs/archive/rapid-r20-preparation-evidence-20260831.md`. R20 remains consumed: 6/6 settled for
`$1.62950550`, both arms 0/3/0, with two V24 compatibility-confounded terminals. No retry or quality claim follows.

## Status before integration

# Current status - 2026-09-01

## Current checkpoint

PatchLoop remains a single bounded coding loop. Consumed Rapid/development/held-out evidence is immutable.
Held-out R16's C-minus-A was `-1/24`, with no causal/general memory claim. Exact identities are in `docs/09-evidence.md`.

Work Item 81 reviewed the frozen, offline-qualified Lean V27 (`v28/phase-evidence-v37`) package. Its disposition is
`eligible-not-adopted` for a separate candidate-integration decision, **not live-ready**. Final strict-schema gates,
count accounting/recovery and equal-resource limits passed offline review. Qualified runtime/source and R23 artifacts
remain unchanged. The review adds no candidate, rehearsal, provider/Docker/evaluator call or cost.

Two integration gaps remain: V27 admits only public-calibration mock manifests, and the existing rehearsal checks
row/image/provider capabilities without constructing the final request or entering the pre-count gate. A future
candidate needs both connections and fresh exact approval; local validation does not establish provider acceptance.

Work Item 70 consumed R20 exactly once; both arms reached/submitted/succeeded 0/3/0 and two V24 rows were confounded.
Work Item 71 is complete offline. R21 then settled 3/3 for `$1.42525890`, reach/submission/success 1/1/0.
V25 failed its 2/3 evaluator-reach floor and is not promoted. V26's bundled review stays frozen;
the separate runner-continuity check remains unexecuted and excluded.

Work Item 77 closed R22 candidate-v30
`sha256:3930c68bdca28e28de1233a374e52f091d03d1dde95414d681c5be4c27c7f62b`
before any row: its full path would inspect the image 13 times against approval for one. All six rows are unstarted;
model cost/provider/evaluator/check calls are zero, outer Docker count unknown. The plan and stop audit stay unchanged.
No R22 result or promotion exists; retry authority is closed.

R23's pre-execution status is in `docs/archive/r23-preparation-and-pre-execution-status-20260831.md`.

## Consumed R23 - Work Item 79

Candidate-v32 execution `sha256:d9d3818c9d2b80eb8238746c510fd071d808fb734bdc7f3d74837548c967d309`
was approved and invoked once for six V25/V26 rows at `$7.20` reserve/`$7.50` cap. One local image inspection passed.
The driver halted after two started/terminal/settled rows for `$0.16285425`; four rows are not started.

- V25 row 1: all three visible checks passed, then diff review/submission and hidden failure. Its cause is not public.
- V26 row 2: HTTP 400 `invalid_function_parameters` for `read_file`: `strict=true` with an empty `required` array.
  Recorded outcome: infrastructure_error during pre-generation token counting. The rejected request is absent from
  usage counters: zero model calls does not mean zero provider requests.

Original bundle, image receipt and halted audit remain append-only. Exact tuples and accounting limits are in
`docs/09-evidence.md`. This partial, infrastructure-confounded batch cannot compare or promote V26. R23 cannot retry or resume.

## Evaluator correctness gap

Evaluator-v1 still assigns literal safety PASS. Rapid remains `official=false`; public checks do not prove hidden
success or generalization.

## Evidence, retry and authority

No paid, held-out or B/D execution is currently authorized. R11-R21 approvals are consumed; R22 and R23 are closed.
D-142 remains **source-qualified only, unactivated**; its planning disposition is now **deferred**.
PDM is retired; Harbor remains 0/12 local images and pull authority is closed.

## Next work

Work Item 82: separately decide whether to adopt V25 control/V27 treatment as one public-development package.
If adopted, integrate versioned live admission and exact-request no-call rehearsal before candidate freeze, retaining
AnyIO-v5, equal resources and one batch image inspection. Candidate creation/execution is not part of Work Item 81.


## Historical Work Items 80/81 runbook


```powershell
uv run --offline --frozen pytest -o 'addopts=' -q -p no:cacheprovider `
  tests/test_provider_schema_admission.py tests/test_provider_count_accounting.py `
  tests/test_provider_schema_runner.py tests/test_provider_schema_qualification.py `
  tests/test_provider_schema_activation_review.py `
  tests/test_rapid_r23_halted_audit.py tests/test_rapid_r22_prestart_stop.py --basetemp .p81g1
uv run --offline --frozen python scripts/build_lean_harness_provider_schema_qualification.py --check-only
uv run --offline --frozen python scripts/build_lean_harness_provider_schema_activation_review.py --check-only
```

Both builders compare two in-memory builds and perform zero external/check calls. The review also verifies frozen V27
qualification/source and its stored review bytes. Materialization is exclusive/idempotent; differing bytes require a
successor, never overwrite. Static call order is not a full control-flow proof; separately executed tests use fake
count/create methods, synthetic checks and mock submission, guarded against real provider/Docker/evaluation.
Synthetic row-receipt tests do not issue live authority. The legacy rehearsal remains capability-only, not an actual
request-construction/pre-count rehearsal. Review disposition is `eligible-not-adopted`, not live-ready.

Work Item 81: 113 focused/regression/audit tests passed with `.p81g1`. Work Item 80's 312-test gate and hash-blocked
historical candidate fixtures are archived in `docs/archive/work-item-80-validation-20260901.md`; do not rebuild them.
Documentation: 10/10 with `.p81d1`; scoped Ruff, three new Python files' formatting and `git diff --check` passed.
Repeated check-only review builds match stored v2 bytes; the V27 qualification still matches its frozen source hashes.


## R23 preparation detail (unchanged historical identities)


Runtime/config-file/config-semantic are `sha256:eb3bd798157dd027c7743bee1b1ab56b5cc04c651cb46d48208313c729505641`/
`sha256:c133fa1d83b356d92896d4ad73b76d572d983e7dfc09485362dcf19b7175c2e1`/
`sha256:1e0260be494c2bde0206e5ea8cbdffe17cec047e11b5155028fafca5a193598c`; schedule/cost hashes equal R22 above.
Plan/verifier-entry: `sha256:c46930b2d0d5414dcbd94bc62add2033b5cc92623fd68fa8cf6455a05b7e8000`/
`sha256:3cf6cd90604aed1f508b36d478163c74b637fe85117b0749684149715a3273ed`.

Each rehearsal/qualification was built twice byte-identically. Six real row starts use one mocked inspect command
and zero per-row inspections; synthetic terminals and explicitly closed mock SQLite handles measure no agent quality.
Preparation had zero provider/Docker/evaluator/visible-check/network calls and cost; it did not observe a real image.
V25/V26, AnyIO-v5 and `$7.20`/`$7.50` stayed fixed. The subsequently approved execution is closed below.

Candidate-v31's candidate/rehearsals remain unchanged. Its 1,987-byte `candidate-v31-zero-call-superseded-v1.json`
audit is file/content `sha256:3c028ab49aaac4f539acc597256bc9044416e8448128bbcd1285d5d57f966fb1`/
`sha256:de17592ea1c06a3e51adde2d9b3fbabeb2a8435d802877b4745fb2ac73d2daa5`: zero-call superseded after mock
SQLite cleanup failed, never approved/executed and not retryable.


## Frozen V27 evidence detail


`experiments/lean-harness-provider-schema-public-qualification-20260831-v1.json` is 18,124 bytes, file/content
`sha256:cb80ed051f37fa50a601462510fdc866b3bf40d18c0df6fb027bdb75e286bcc2`/
`sha256:acc5a10184db11e9611b91d68d28b94907dd89d7c0a11e363b137abaab77e276`.
Two builds are byte-identical. Opt-in V27/v28/phase-evidence-v37 binds strict nullable reads, final dynamic-schema
admission and durable count-attempt accounting. Synthetic count/schema scenarios and separate guarded runner tests
are offline evidence, not observed provider acceptance, task performance or billing.

`experiments/lean-v27-r23-predecessor-source-delta-20260831-v1.json` is 35,794 bytes, file/content
`sha256:0dd0fee1ab6af06f167b7c0364ff96eb3aa67d0a98ea3f439b87ca145b6aff72`/
`sha256:ac5f81180ae92b34e707b36eb1025913185c71e295d85b7a7ad1f09d5a49bc4a`.
It recovers exact R23-era bytes for five extended shared files in memory. Standalone V26 source/qualification/review,
legacy adapter and consumed R23 artifacts remain unchanged. No historical candidate is rebuilt or rebound.
Qualification records `offline-qualified`, `candidate_created=false`, `rehearsal_created=false`, zero provider,
Docker/evaluator/visible-check/network calls and cost. The separate review below grants no paid execution.

## Lean V27 activation review - Work Item 81

`experiments/lean-harness-provider-schema-activation-review-20260901-v2.json` is 19,527 bytes, file/content
`sha256:f10914748b0d91f7c060d3063e3115df6e96705e8996683f99f0dc2738f47340`/
`sha256:7a9cb2d9517bf5cae1246c16b1d45bcf572f54d6de4a53bb1ccb47723e1abd1d`.
Two builds match; 113 focused/regression/audit tests pass. Frozen V27 and R23 bytes remain unchanged. Disposition:
`eligible-not-adopted`, not live-ready. Mock-only manifest admission and capability-only rehearsal leave two integration
gates; no candidate, rehearsal, actual provider/Docker/evaluator/check call, cost or provider acceptance is added.
The same-prefix v1 is 19,093 bytes, file/content
`sha256:aa938a4291436b91a1dde78bb21bf448aefd2c4ec1f86a0abb1c511474d22ffd`/
`sha256:0e438f47d4dbcaef5bf82cab1e34f8de1bf2f8dffd0dfbff62c68a1dcd880b24`.
It is zero-call superseded for review-only formatting/check-only verification; it is retained, never overwritten.
