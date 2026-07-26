# Task audit: hf-hub-xet-endpoint-propagation

- Dataset role: proposed `memory-development`
- Source: SWE-rebench V2 instance `huggingface__huggingface_hub-3180`, split `train`
- Benchmark revision: `475dd5e8703bb5fb22dd3c60b5d038b019eba1e0`
- Benchmark row: 266
- Upstream issue: <https://github.com/huggingface/huggingface_hub/issues/3168>
- Upstream resolution: <https://github.com/huggingface/huggingface_hub/pull/3180>
- Base commit: `6f9b87ecda5025259c69a1eb0ae6f8ee80d05d33`
- Resolution commit: `eebd13d365b925340dcf452c22d8cc7df56b149d`
- License: Apache-2.0
- Retrieved: `2026-07-26T17:46:42Z`
- Benchmark gold patch SHA-256:
  `sha256:9f1deb6f07d5f25935194d0e225ee89958d5b093da2e28774e7f5b9d035b5c82`
- Benchmark test patch SHA-256:
  `sha256:607a98df948020098cbb39f7070b100f34e49d3ca071bf162c09f8b2c834f18d`
- Evaluator image:
  `docker.io/swerebenchv2/huggingface-huggingface-hub@sha256:c698facf4c9a9e636b8dc114aa9bda6a17ee5f89fe3efd43f39a6543540e891f`
- Workflow: real-repository issue fix
- Failure pattern: request-scoped endpoint context is lost across abstraction boundaries
- Expected source changes:
  `src/huggingface_hub/file_download.py`,
  `src/huggingface_hub/hf_api.py`, and
  `src/huggingface_hub/utils/_xet.py`
- Public regression: all 15 benchmark P2P nodes in `tests/test_xet_utils.py`
- Private acceptance: header/link parsing, relative and foreign route preservation,
  default and explicit endpoint handling, low-level metadata, internal download, HfApi
  propagation, submitted-source binding, and exact public-signature delta
- Leakage control: benchmark interface, gold patch, test patch, reference patch, and
  hidden assertions remain evaluator-only and are excluded from agent context and
  memory source text
- Contamination risk: high. The task, benchmark training row, issue, PR, and code review
  are public.

The V2 image has working directory `/huggingface_hub`, while PatchLoop mounts the submitted
checkout at `/workspace`. Every check therefore pins `PYTHONPATH=/workspace/src` and writable
cache roots under `/tmp`. The private oracle additionally verifies that imported production
code comes from the submitted checkout.

The intended fix adds optional parameters to two public functions. The current task contract
can only allow or reject public API changes as a whole, so this task declares them allowed.
To prevent that boolean from widening the real acceptance boundary, the private oracle compares
the base and submitted AST signature maps and accepts changes to exactly those two symbols only.

Difficulty audit:

| Dimension | Score | Reason |
| --- | ---: | --- |
| Localization | 1 | The issue names metadata retrieval, but the dropped context spans three modules. |
| Reasoning depth | 1 | Default-origin routes must change while relative and foreign routes remain stable. |
| Implementation breadth | 2 | Parser, internal download path, and public HfApi wrapper must be connected. |
| Verification breadth | 2 | Header/link forms and three caller layers require separate checks. |
| Total | 6 | Hard under `dataset-manifest-v1`. |

Admission requires an official network-disabled Docker gate showing:

1. the unmodified base passes 15 public P2P tests and fails private acceptance;
2. the reviewed production-only reference passes hidden, regression, scope, and safety
   verdicts three times;
3. every declared known-bad patch applies cleanly and fails at its intended boundary;
4. source commit, image, specs, patch, manifest, result, and provenance are content-addressed.

The hidden tests are independently authored from the reported behavior. They do not copy the
benchmark F2P test or inspect implementation helper names.
