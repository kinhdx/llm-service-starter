import os

os.environ.setdefault("OTEL_CONSOLE", "0")

from fastapi.testclient import TestClient  # noqa: E402
from test_triage import FixedClient, answer  # noqa: E402

from service import api  # noqa: E402


def test_triage_endpoint_returns_route_and_redaction_counts():
    api.app.dependency_overrides[api.get_client] = lambda: FixedClient(answer("fraud", "normal"))
    response = TestClient(api.app).post("/triage", json={"text": "Có người dùng thẻ 4111 1111 1111 1111 của tôi"})
    api.app.dependency_overrides.clear()
    body = response.json()
    assert response.status_code == 200
    assert body["route"] == "human" and body["urgency"] == "high"
    assert body["redactions"] == {"CARD": 1}


def test_healthz_reports_prompt_version():
    body = TestClient(api.app).get("/healthz").json()
    assert body["status"] == "ok" and body["prompt_version"]
