# Onboarding: from template to a running service

Target: a squad engineer who has not built an LLM service before has their own task running locally, with an
evaluation that gates pull requests, by the end of the first day.

## Before you start

- Python 3.12 and uv installed.
- An API key for local experiments, from the platform team. CI does not need one.
- A list of 30 to 50 real inputs for your task, with the answer a domain expert expects. Ask the business
  owner for these on day one; everything else depends on them.

## Steps

1. Create a repository from this template and run it as is:
   `uv sync`, `uv run pytest -q`, `uv run python evals/run.py`. All three should pass without a key.
2. Write your task in `prompts/<task>.md`. Keep the front matter: `version` changes on every edit, and is
   attached to every trace and evaluation report.
3. Copy `src/service/triage.py` to your task module. Keep its shape: redact the input, call the model through
   `ModelClient`, apply the rules that must always hold in code, return a typed result.
4. Put your expected answers in `evals/cases.jsonl` and set the thresholds in `evals/thresholds.json` with the
   business owner. Decide which errors are unacceptable (for triage: a missed fraud case) and gate those at 1.0.
5. Record once with a key: `uv run python evals/run.py --mode record`. Commit the recordings with the change.
6. Run the API: `uv run uvicorn service.api:app`. Traces print to the console; set
   `OTEL_EXPORTER_OTLP_ENDPOINT` to send them to the shared collector instead.

## What CI checks

- Lint and unit tests.
- The evaluation in replay mode. It fails if a score drops below a threshold, and it fails if a prompt,
  schema, input or model changed without re-recording, so an untested prompt change cannot merge.

## Getting help

Office hours are open twice a week (see `docs/templates/office-hours-log.md` for what gets recorded).
Questions asked more than once go into `docs/faq.md`.
