"""HTTP API. Configuration comes from the environment:

    MODEL_MODE   live (default) | replay | record   -- replay serves recorded answers, for demos without a key
    MODEL_NAME   model used for triage (default claude-haiku-5-5)
    OTEL_EXPORTER_OTLP_ENDPOINT   send traces to a collector instead of stdout
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel, Field

from service import telemetry
from service.llm import AnthropicClient, ModelClient, ModelError, ReplayClient, TracedClient
from service.triage import DEFAULT_MODEL, load_prompt, triage

RECORDINGS = Path(__file__).resolve().parents[2] / "evals" / "recordings"

load_dotenv(find_dotenv(usecwd=True))
telemetry.setup("llm-service-starter")
app = FastAPI(title="Complaint triage")
FastAPIInstrumentor.instrument_app(app, excluded_urls="healthz")


@lru_cache
def get_prompt():
    return load_prompt()


@lru_cache
def get_client() -> ModelClient:
    mode = os.getenv("MODEL_MODE", "live")
    inner = None if mode == "replay" else AnthropicClient()
    return TracedClient(ReplayClient(RECORDINGS, mode, inner), get_prompt().version)


class ComplaintIn(BaseModel):
    text: str = Field(min_length=5, max_length=5000)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "prompt_version": get_prompt().version}


@app.post("/triage")
def triage_complaint(body: ComplaintIn, client: ModelClient = Depends(get_client)) -> dict:
    try:
        result = triage(body.text, client, get_prompt(), os.getenv("MODEL_NAME", DEFAULT_MODEL))
    except ModelError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return {"category": result.category, "urgency": result.urgency, "route": result.route,
            "summary": result.summary, "mentions_legal_action": result.mentions_legal_action,
            "redactions": result.redactions, "prompt_version": result.prompt_version}
