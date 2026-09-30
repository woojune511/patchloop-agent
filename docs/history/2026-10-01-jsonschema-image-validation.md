# Approved jsonschema image build and validation

The user explicitly approved the prepared local image build. No model run or
paid allocation was authorized. Built `patchloop-jsonschema-1538:py312-v1` from
the existing pinned Python image and the hash-verified site-packages bundle.

Build arguments: `--pull=false --network=none`. The base layer was cached and
there was no package installation or image-layer download. However, BuildKit
performed registry authentication and metadata resolution. Thus this was not a
fully network-isolated build: the network option does not disable registry
resolution. Preserve this limitation rather than claiming zero network traffic.

Immutable local image reference:
`patchloop-jsonschema-1538@sha256:901f8eebd991b12da7dfb43a74c4c6ee51d7fcd9d37cead1f8af7dc292017ccd`.
Reported image size: 210,095,354 bytes. It contains dependencies, not task source,
credentials or prior run records; source is mounted separately. Container user is
10001:10001. No image was pushed to a registry.

## Validation

Used the normal DockerSandbox registered-check execution path, read-only root and
workspace with network=none. Unchanged prepared source at
`51cd75e399c760e5aa3adce600dcce1385756ab0` was verified before and after execution.

- Valid regex: zero validation errors.
- Ordinary invalid regex: one validation error, no escaped exception.
- Public issue's 500-opening-parentheses input: escaped RecursionError reproduced.
- Upstream jsonschema.tests.test_format: eight tests passed, none skipped.
- Both container executions and cleanup completed successfully.

The reproduction wrapper catches the exception to record it; its exit zero is
execution evidence, not a repaired bug. This is neither isolated task acceptance
nor an independent quality evaluation. No candidate patch was generated.

An initial preflight used a bare sha256 reference, which the sandbox identity
resolver does not support. No container was dispatched from that assertion failure.
Using the inspected repository@digest reference passed the existing identity check;
no resolver relaxation or runtime change was made.

## Evidence and remaining work

Build context and dependency/source identities are retained under
`C:\pt\preparations\jsonschema-1538-20261001-v2`.
Build/validation journal:
`image-build\runs\run_dev_aca56d9ead3d40a0.jsonl` (ten events verified).
It records approval, recipe/dependency hashes, complete build output, image
identity, the registry-contact limitation and both execution receipts.

Image readiness is established. A checked-in dev-train task and explicit
acceptance/check semantics still need admission before any exact paid proposal.
Provider calls: zero. Historical preparation records remain unchanged.
