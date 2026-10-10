# FAQ

**The evaluation fails in CI with "no recording for request".**
Something in the request changed: prompt text, schema, an input case or the model name. Run
`uv run python evals/run.py --mode record` with an API key and commit the new files in `evals/recordings/`.
Delete recordings that no case uses any more.

**Why record responses instead of calling the model in CI?**
Three reasons: CI needs no secret, the result is the same on every run, and a pull request shows exactly which
answers changed. The cost is that recordings must be refreshed when the request changes; the gate enforces it.

**My scores move between runs in record mode.**
Model output is not deterministic. Look at which cases changed; if they sit on a boundary (urgency normal vs
high), the label or the instruction is ambiguous. Fix the instruction or the label, not the threshold.

**Can I put a business rule in the prompt?**
Put it in the prompt so the model knows about it, and also in code if it must always hold. In the triage
example, fraud always goes to a person whatever the model answers.

**What may I log?**
Token counts, cost, latency, prompt version and the request key. Not the input, the prompt or the output.
Redaction protects the model call; it is not a reason to log the redacted text.

**How do I choose a model?**
Record the evaluation with two or three models and compare quality, cost per case and latency in the reports.
Pick the cheapest one that passes every gate.
