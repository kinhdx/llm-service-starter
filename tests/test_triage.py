from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from service.llm import MissingRecording, ReplayClient, Request, TracedClient, Usage
from service.triage import load_prompt, triage

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evals.run import gate, score  # noqa: E402

EXPORTER = InMemorySpanExporter()
_provider = TracerProvider()
_provider.add_span_processor(SimpleSpanProcessor(EXPORTER))
trace.set_tracer_provider(_provider)


class FixedClient:
    def __init__(self, output: dict):
        self.output, self.requests = output, []

    def complete(self, request: Request):
        self.requests.append(request)
        return self.output, Usage(request.model, 120, 40, 0.0001, 0.2)


def answer(category="card", urgency="normal", legal=False):
    return {"category": category, "urgency": urgency, "summary": "Khách hàng báo lỗi.", "mentions_legal_action": legal}


def test_model_never_sees_raw_identifiers():
    client = FixedClient(answer())
    result = triage("Gọi tôi theo số 0912345678, CCCD 001190012345", client, load_prompt())
    sent = client.requests[0].user
    assert "0912345678" not in sent and "001190012345" not in sent
    assert result.redactions == {"PHONE": 1, "ID_NUMBER": 1}


def test_fraud_is_always_high_urgency_and_routed_to_a_person():
    result = triage("Giao dịch lạ", FixedClient(answer("fraud", "low")), load_prompt())
    assert (result.urgency, result.route) == ("high", "human")


def test_legal_threat_goes_to_a_person_whatever_the_category():
    result = triage("Tôi sẽ kiện", FixedClient(answer("other", "normal", legal=True)), load_prompt())
    assert result.route == "human"


def test_replay_returns_recording_and_fails_on_changed_request(tmp_path):
    inner = FixedClient(answer())
    request = Request("claude-haiku-5-5", "system", "user text", {"type": "object"})
    ReplayClient(tmp_path, "record", inner).complete(request)
    replay = ReplayClient(tmp_path, "replay")
    assert replay.complete(request)[0] == answer()
    with pytest.raises(MissingRecording):
        replay.complete(Request("claude-haiku-5-5", "system v2", "user text", {"type": "object"}))


def test_traced_client_records_genai_attributes():
    EXPORTER.clear()
    TracedClient(FixedClient(answer()), "v1").complete(Request("claude-haiku-5-5", "s", "u", {}))
    span = EXPORTER.get_finished_spans()[-1]
    assert span.attributes["gen_ai.request.model"] == "claude-haiku-5-5"
    assert span.attributes["gen_ai.usage.input_tokens"] == 120
    assert span.attributes["app.prompt_version"] == "v1"


def test_gate_fails_on_a_single_missed_fraud_case():
    rows = [{"category": "fraud", "urgency": "high", "route": "human", "want_category": "fraud",
             "want_urgency": "high", "want_legal": False, "cost_usd": 0.0001} for _ in range(19)]
    rows.append({"category": "card", "urgency": "high", "route": "queue", "want_category": "fraud",
                 "want_urgency": "high", "want_legal": False, "cost_usd": 0.0001})
    thresholds = json.loads((Path(__file__).resolve().parents[1] / "evals" / "thresholds.json").read_text())
    failures = gate(score(rows), thresholds)
    assert any(f.startswith("fraud_recall") for f in failures)
    assert not any(f.startswith("category_accuracy") for f in failures)  # 95% passes the average
