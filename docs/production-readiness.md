# Production readiness checklist

A service built from this template is ready for production use when every item below is checked and the
evidence is linked. Items marked (gate) are enforced in CI.

## Quality

- [ ] Evaluation set of at least 50 cases drawn from real inputs, labelled or reviewed by the business owner.
- [ ] Thresholds agreed with the business owner and recorded in `evals/thresholds.json`.
- [ ] Unacceptable errors identified and gated at 1.0 (gate).
- [ ] Evaluation runs on every pull request (gate).
- [ ] A sample of live traffic is reviewed by a person every week and added to the evaluation set when it
      fails.

## Safety and data

- [ ] Personal identifiers are redacted before any model call; redaction tests cover the identifier types in
      your inputs (gate).
- [ ] Data classification of inputs and outputs agreed with information security.
- [ ] Rules that must always hold are implemented in code, not only in the prompt, and have unit tests.
- [ ] Every automated outcome that affects a customer has a human route.
- [ ] No prompts, inputs or outputs are written to logs; traces carry token counts, cost and prompt version
      only.

## Operations

- [ ] Traces reach the shared collector; a dashboard shows latency, error rate and cost per request.
- [ ] Alert on error rate and on daily cost above the budget.
- [ ] Timeouts, retries and the fallback model are configured and tested.
- [ ] Runbook: what to do when the model API is down, slow, or returns refusals.
- [ ] Owner and on-call named in the asset registry entry.

## Change management

- [ ] Prompt version recorded in every response and trace.
- [ ] A prompt or model change goes through the same review and evaluation as a code change (gate).
- [ ] Rollback is a revert of the prompt file and recordings.
