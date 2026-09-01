# Project specification

## Product

PatchLoop is one coding agent that repairs a public software task, validates the
current diff through registered checks, submits it, and receives a private
evaluator summary. The evaluator, journal, workspace manager, and model adapter
exist to make that agent safe, recoverable, and easy to improve.

## Development objective

Maximize completion and submission reliability through short `official=false`
loops. Optimize for an answerable next question and a durable terminal, not for
historical runtime comparability.

## In scope

- public task and source inspection
- constrained mutation and visible check execution
- one embedded mutation hypothesis and exact anchor
- bounded failure cards and recovery
- pre-dispatch cost enforcement
- separate private evaluation after submission
- append-only external run state

## Out of scope

- memory retrieval or memory experiments
- development tuning on validation or held-out splits
- candidate, qualification, activation, or adoption workflows
- claim-producing evaluation
- automatic provider retries, Docker startup, image pull/build, or dependency install
- compatibility with historical Rapid runners
