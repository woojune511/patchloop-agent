# New public issue intake

Status: NOT_READY. Provider calls: zero. No paid run or cost allocation authorized.

## Selected candidate

[jsonschema #1538](https://github.com/python-jsonschema/jsonschema/issues/1538)
reports that a deeply nested regex escapes validation as RecursionError instead
of a validation error. The public issue supplies a small reproducer using
Draft202012Validator and FormatChecker, and identifies Python 3.13/jsonschema
4.26.0. Observed open on 2026-10-01 KST. Upstream main was resolved to
`51cd75e399c760e5aa3adce600dcce1385756ab0`; no repair/reference patch was retrieved.

No jsonschema repository match was found in existing task public manifests. This
does not establish model-training novelty. The issue's own explanation remains
public issue content, not an operator-created repair hint.

## Checks performed and blockers

1. The normal prepare_source path rejected the repository URL because it is not
   in ALLOWED_REMOTE_REPOSITORIES. No source manifest was published. No alternate
   clone path or temporary bypass was used.
2. The existing digest-pinned patchloop-sandbox image runs Python 3.12.13 but lacks
   jsonschema, attrs, referencing, rpds and pytest. This was a read-only, no-network
   dependency inventory with confirmed container cleanup, not issue reproduction.
3. No checked-in dev-train package, public regression execution or isolated
   acceptance environment has been prepared. No completion/quality verdict exists.

Existing image:
`patchloop-sandbox@sha256:1144b4be9927ac5882401185c326003383630eac9db84102ee3d71c06e261cac`.
Evidence journal:
`C:\pt\preparations\jsonschema-1538-20261001-v1\audit\runs\run_dev_277dfa912daa4ab9.jsonl`.
The failed preparation directory is retained, not reused.

## Candidate disposition

- SQLGlot #8443 has a short MySQL comment reproducer and an existing local image.
  Rejected after public-manifest inventory found an existing cross-repo-heldout
  task in the same repository. Its new public source was prepared but never
  executed; no held-out private material was read. Preserve repository separation.
- SQLGlot #8390 has the same repository overlap.
- Click #3840 is intermittent and Windows GUI dependent, making it unsuitable
  for the current Linux sandbox. Click #3802 is already closed.
- jsonschema #1511 additionally depends on duration-format support. Prefer the
  smaller regex reproducer for initial intake; no comparative execution occurred.

SQLGlot rejected-source journal:
`C:\pt\preparations\sqlglot-8443-20261001-v1\audit\runs\run_dev_87a95e82a2de4955.jsonl`.

## Next preparation work

Review and register only the exact selected repository in the normal allowlist;
keep arbitrary remote repositories rejected. Prepare a new immutable source at
the pinned commit and verify the issue is still present before writing a solver
task. Prepare reviewed dependencies and a runnable pinned environment, with no
automatic image acquisition. Verify the public reproduction and upstream format
regressions; record Python-version differences and stop if they change the issue.

Then define the exact dev-train package, meaningful completion checks, mutation
scope and evaluation boundaries. Do not label public-only checks as hidden or
independent quality evidence. Only after readiness should a one-run proposal name
the model, credential file, repeat and positive cost cap. No cost estimate from
the earlier PDM run is evidence for this task's actual cost.

During an eventual autonomous run, supply only the frozen public task and normal
tools. No operator hint, manual repair or mid-run rescue. Preserve failures and
analyze them after termination; operational approval is separate from solving.
