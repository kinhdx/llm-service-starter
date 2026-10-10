# llm-service-starter

A starting point for a small LLM-backed service, with the parts that are easy to leave out of a prototype and
expensive to add later: input redaction, tracing with token and cost attributes, rules that hold regardless
of what the model says, and an evaluation that gates every pull request without an API key.

The example task triages Vietnamese customer complaints for a retail bank into category, urgency and route
(a person or the queue). Replace it with your own task and keep the structure.

## What is in the box

| Concern | Where | What it does |
|---|---|---|
| Redaction | `src/service/redact.py` | Masks card numbers (Luhn-checked), citizen and old ID numbers, phone numbers, e-mail and account numbers before the model call |
| Model access | `src/service/llm.py` | `AnthropicClient` (structured output, retries, timeout, fallback model), `ReplayClient` (record / replay), `TracedClient` (OpenTelemetry span) |
| Tracing | `src/service/telemetry.py` | One trace per request: HTTP span plus a model span with `gen_ai.*` attributes, token counts, cost and prompt version. Console by default, OTLP when `OTEL_EXPORTER_OTLP_ENDPOINT` is set |
| Prompt | `prompts/triage.md` | Versioned prompt file; the version is returned in every response and trace |
| Business rules | `src/service/triage.py` | Fraud and complaints that mention legal action always go to a person; fraud is always high urgency |
| Evaluation gate | `evals/` | 40 labelled cases, thresholds, recorded responses, report; CI fails below threshold or on an unrecorded change |
| Delivery docs | `docs/` | Onboarding, production readiness checklist, embed report and handover templates, office hours log, FAQ |

## Run it

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run pytest -q                                   # unit tests
uv run python evals/run.py                         # evaluation gate from recorded responses, no key needed
MODEL_MODE=replay uv run uvicorn service.api:app   # API serving recorded answers for the evaluation cases
```

With an API key in `.env`:

```bash
uv run uvicorn service.api:app                     # live model
uv run python evals/run.py --mode record           # refresh recordings after changing the prompt or cases
```

```bash
curl -s localhost:8000/triage -H 'content-type: application/json' \
  -d '{"text": "Sáng nay tài khoản bị trừ 4.990.000đ, tôi không thực hiện giao dịch này"}'
```

## Evaluation

Current recordings, `claude-haiku-5-5`, prompt version `2026-10-10.1` (from `evals/report.md`):

| Metric | Value | Gate |
|---|---|---|
| Category accuracy | 95.0% | ≥ 85% |
| Urgency accuracy | 75.0% | ≥ 70% |
| Fraud recall | 100% | = 100% |
| Cases routed to a person when they must be | 100% | = 100% |
| Highest cost per case | $0.00025 | ≤ $0.002 |

The ten urgency misses go both ways: six cases labelled normal came back high (three delayed transfers, a
late replacement card, and two cases the model classed as fraud, which the rule then forces to high), and four
labelled low came back normal. The two category misses were both read as fraud: a disputed automatic debit
(labelled card) and a lost phone with the banking app (labelled account). Those are the cases to discuss with
the business owner before changing the prompt; the labels were written by one person.

The cases are synthetic, written to resemble real complaints. Before a service built from this template goes
live, replace them with labelled real inputs (see `docs/production-readiness.md`).

## How the gate works

```
pull request ──► unit tests ──► evals/run.py --mode replay ──► report.md
                                   │
                                   ├─ request hash not recorded   → fail: re-record with a key
                                   └─ score below thresholds.json → fail
```

A weekly workflow re-runs the cases against the live model to catch drift in the provider's model. Rationale:
[docs/decisions/0001](docs/decisions/0001-recorded-responses-in-ci.md).

## Starting a new service

Follow [docs/onboarding.md](docs/onboarding.md). In short: create a repository from this template, write your
prompt, copy the task module, collect labelled cases with the business owner, agree thresholds, record, and
open a pull request.
