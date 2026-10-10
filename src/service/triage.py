"""Example task: triage a customer complaint into category, urgency and handling route.

The model classifies. Two business rules are applied in code afterwards, because they must hold regardless of
what the model returns:
- fraud and complaints that mention legal action always go to a person;
- fraud is always high urgency.

Replace this module with your own task; keep the shape: redact, call the model through `ModelClient`,
apply rules in code, return a typed result.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from service.llm import ModelClient, Request, Usage
from service.redact import redact

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "triage.md"
CATEGORIES = ["card", "transfer", "loan", "account", "fraud", "fee", "other"]
URGENCY = ["high", "normal", "low"]
DEFAULT_MODEL = "claude-haiku-5-5"


@dataclass(frozen=True)
class Prompt:
    version: str
    text: str


def load_prompt(path: Path = PROMPT_PATH) -> Prompt:
    raw = path.read_text(encoding="utf-8")
    _, header, body = raw.split("---", 2)
    meta = dict(line.split(":", 1) for line in header.strip().splitlines())
    return Prompt(meta["version"].strip(), body.strip())


SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": CATEGORIES},
        "urgency": {"type": "string", "enum": URGENCY},
        "summary": {"type": "string"},
        "mentions_legal_action": {"type": "boolean"},
    },
    "required": ["category", "urgency", "summary", "mentions_legal_action"],
    "additionalProperties": False,
}


@dataclass
class Triage:
    category: str
    urgency: str
    route: str  # "human" or "queue"
    summary: str
    mentions_legal_action: bool
    redactions: dict[str, int]
    prompt_version: str
    usage: Usage


def triage(text: str, client: ModelClient, prompt: Prompt, model: str = DEFAULT_MODEL) -> Triage:
    cleaned = redact(text)
    output, usage = client.complete(Request(model=model, system=prompt.text, user=cleaned.text, schema=SCHEMA))
    category, urgency = output["category"], output["urgency"]
    legal = bool(output["mentions_legal_action"])
    if category == "fraud":
        urgency = "high"
    route = "human" if category == "fraud" or legal else "queue"
    return Triage(category, urgency, route, output["summary"].strip(), legal, dict(cleaned.counts),
                  prompt.version, usage)
