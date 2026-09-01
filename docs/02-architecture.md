# Architecture

```text
public.yaml
    |
    v
dev-head runner -----> public context builder
    |                        |
    |                        v
    |                  model adapter
    |                        |
    v                        v
external journal <---- constrained tool gateway
    |                 read/search | mutation | visible check | finish
    |                                      |
    v                                      v
artifact store                     isolated workspace
                                             |
                                             v
                                  separate private evaluator
                                             |
                                             v
                               public PASS/FAIL failure class
```

## Composition

- `patchloop/dev/runner.py` owns one mutable loop and its four states.
- `patchloop/dev/tools.py` owns the small tool grammar, source-span evidence,
  exact-anchor mutation admission, visible checks, and finish admission.
- `patchloop/dev/state.py` owns append-only hash-chained JSONL and action replay.
- `patchloop/dev/cost.py` owns model pricing and pre-dispatch reservation.
- `patchloop/agent/model.py` owns stateless OpenAI Responses calls with zero retries.
- `patchloop/repository.py` owns allowlisted, isolated workspaces and full diffs.
- `patchloop/sandbox/runner.py` executes registered checks locally for mock or in a
  digest-pinned, no-network Docker container for live development.
- `patchloop/verifier/core.py` creates a separate evaluator workspace, adds private
  files only there, and produces an unofficial result.

There is no runtime-version switch. A normal improvement edits `dev-head` directly.
