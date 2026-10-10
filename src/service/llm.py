"""Model access in three layers that compose:

    TracedClient(ReplayClient(AnthropicClient()))

- AnthropicClient makes the structured-output call and reports token usage and cost.
- ReplayClient stores each response under a hash of the request, so evaluations can run in CI without an API
  key and give the same answer every time. If the prompt, schema, input or model changes, the hash changes and
  the replay fails loudly until the case is re-recorded.
- TracedClient wraps any client in an OpenTelemetry span with the GenAI semantic-convention attributes.

Application code depends only on the `ModelClient` protocol.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from opentelemetry import trace

PRICES = {  # USD per million tokens: input, output
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}
FALLBACK_MODELS = {"claude-opus-5-5", "claude-sonnet-5-5"}

tracer = trace.get_tracer("service.llm")


@dataclass
class Usage:
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    seconds: float = 0.0


@dataclass
class Request:
    model: str
    system: str
    user: str
    schema: dict
    effort: str = "low"

    def key(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


class ModelError(Exception):
    pass


class MissingRecording(ModelError):
    pass


class ModelClient(Protocol):
    def complete(self, request: Request) -> tuple[dict, Usage]: ...


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    price_in, price_out = PRICES.get(model, PRICES["claude-opus-5-5"])
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000


class AnthropicClient:
    def __init__(self, timeout: float = 60.0, max_retries: int = 3):
        import anthropic

        self._client = anthropic.Anthropic(timeout=timeout, max_retries=max_retries)

    def complete(self, request: Request) -> tuple[dict, Usage]:
        params = dict(model=request.model, max_tokens=2000, system=request.system,
                      output_config={"effort": request.effort,
                                     "format": {"type": "json_schema", "schema": request.schema}},
                      messages=[{"role": "user", "content": request.user}])
        if request.model in FALLBACK_MODELS:
            params.update(betas=["server-side-fallback-2026-07-01"], fallbacks="default")
        started = time.monotonic()
        response = self._client.beta.messages.create(**params)
        usage = Usage(response.model, response.usage.input_tokens, response.usage.output_tokens,
                      cost_usd(response.model, response.usage.input_tokens, response.usage.output_tokens),
                      round(time.monotonic() - started, 3))
        if response.stop_reason in ("refusal", "max_tokens"):
            raise ModelError(f"no usable answer: stop_reason={response.stop_reason}")
        text = next((b.text for b in response.content if b.type == "text"), None)
        if text is None:
            raise ModelError("no structured answer was returned")
        return json.loads(text), usage


class ReplayClient:
    """mode = "replay" (recordings only), "record" (call and save), or "live" (call, never save)."""

    def __init__(self, folder: Path, mode: str = "replay", inner: ModelClient | None = None):
        if mode not in ("replay", "record", "live"):
            raise ValueError(mode)
        self.folder, self.mode, self.inner = folder, mode, inner

    def complete(self, request: Request) -> tuple[dict, Usage]:
        path = self.folder / request.model / f"{request.key()}.json"
        if self.mode == "replay":
            if not path.exists():
                raise MissingRecording(f"no recording for request {request.key()} ({request.model}); "
                                       "re-run the evaluation with --mode record")
            saved = json.loads(path.read_text(encoding="utf-8"))
            return saved["output"], Usage(**saved["usage"])
        output, usage = self.inner.complete(request)
        if self.mode == "record":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"output": output, "usage": asdict(usage)}, ensure_ascii=False, indent=1),
                            encoding="utf-8")
        return output, usage


class TracedClient:
    def __init__(self, inner: ModelClient, prompt_version: str = ""):
        self.inner, self.prompt_version = inner, prompt_version

    def complete(self, request: Request) -> tuple[dict, Usage]:
        with tracer.start_as_current_span(f"chat {request.model}") as span:
            span.set_attribute("gen_ai.operation.name", "chat")
            span.set_attribute("gen_ai.system", "anthropic")
            span.set_attribute("gen_ai.request.model", request.model)
            span.set_attribute("app.prompt_version", self.prompt_version)
            span.set_attribute("app.request_key", request.key())
            try:
                output, usage = self.inner.complete(request)
            except ModelError as e:
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise
            span.set_attribute("gen_ai.response.model", usage.model)
            span.set_attribute("gen_ai.usage.input_tokens", usage.input_tokens)
            span.set_attribute("gen_ai.usage.output_tokens", usage.output_tokens)
            span.set_attribute("app.cost_usd", usage.cost_usd)
            return output, usage
