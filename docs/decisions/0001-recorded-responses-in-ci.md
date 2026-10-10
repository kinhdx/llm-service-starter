# 0001: The evaluation gate replays recorded responses

## Context

Prompt changes are code changes: a reworded instruction can move accuracy by several points. The evaluation
has to run on every pull request. Calling the model from CI needs a secret in every repository, costs money on
each push, and gives slightly different answers on each run, which makes a failing gate hard to trust.

## Decision

`ReplayClient` stores each model response under a hash of the full request (model, system prompt, input,
schema, effort). CI runs the evaluation in replay mode. The author of a change that alters any part of a
request re-records with a key and commits the recordings with the change.

## Consequences

- CI needs no API key and the gate is deterministic.
- An unrecorded change fails the gate with the case ID, so an untested prompt cannot merge.
- The diff of `evals/recordings/` shows which answers changed in review.
- Recordings reflect the model at the time they were made. A scheduled job should re-record against the live
  model (weekly, or when the provider announces a model update) to catch drift.
