# Saved public repair: python-dotenv #715

Open [index.html](index.html) locally for the short walkthrough. This is a **saved
result**, not live inference, a new solve, or a new verification run. No network
service is needed to view it. [Provenance](provenance.json) identifies original
file hashes and transformations; [file hashes](files.sha256.json) bind this export.
Check the export without running any project tests: `python verify_export.py`.

## Request and original artifact

- [Original public issue](https://github.com/theskumar/python-dotenv/issues/715)
  and [saved issue text](issue.json).
- Base: `0b2880591780a426b0551436f47a17e7a76d954f`.
- [Public task](public.yaml), [portable request example](request.example.json),
  [unmodified returned patch](returned.patch), [model tests only](model-tests-only.patch).
- [Solve summary](result.public.json), [sanitized repair-verify result](verification.public.json).
- Recorded public receipts: [before](base-model-tests.json),
  [after](patched-model-tests.json), [original issue example](patched-public-issue.json).

The model wrote a new parameter case in an existing test, observed its failure,
changed the implementation, and observed a pass. Independent execution of the
unchanged model test confirmed 1 failed / 218 passed before and 219 passed after.
The later common `repair-verify` replay confirms the same artifact; do not count
it as another autonomous repair. Recorded solve cost was USD 0.12695715, CLI wall
time 98.967 seconds, excluding preparation and external review/verification.

## Reproduce verification without a model

Obtain python-dotenv at the exact base above in a separate local checkout. Prepare
a compatible Python 3.12.13 / pytest 8.4.2 / Click 8.3.1 sandbox independently.
The historical local image identity is retained in the example; it may not exist
on your machine or be publicly downloadable. No image acquisition is automatic.

Copy this directory outside PatchLoop, edit **only the example request's local
source/state paths and prepared sandbox identity**, and record those differences.
The source must contain the original base commit, not the returned patch. Set
`state_root` outside both repositories. Then run the existing command:

```powershell
patchloop repair-verify --request ./request.example.json --patch ./returned.patch --state-root ../verify-state
```

This verifies a saved patch with no model call or credential loading. The example
is **not approval to run paid `repair`**. The original generation entry point is
`patchloop repair --request request.json`, after exact live-scope approval.
For a self-contained provider-free plumbing example, use the
[mock repair example](../repair/README.md).

## Interpretation

The added test covers an **empty environment variable**. The original issue's
empty value inside a file was checked separately; the model did not add that
case to the repository. The unchanged selected tests passed, but the full project
suite and other environments were not run. Independent acceptance is `NOT_RUN`;
the verifier's requirement fit is `NOT_ASSESSED`. Human approval is unreported.

JSON projections remove host artifact/workspace paths, credentials and provider
internals. Content hashes identify originals but do not make projections original
bytes. Public command/output excerpts are allowlisted; raw journals are not shipped.
No operator implementation or test correction is included.

python-dotenv source/test excerpts are covered by the included
[upstream BSD-3-Clause license](UPSTREAM-LICENSE).
