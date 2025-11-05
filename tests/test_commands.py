from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
API_KEY = "dev-secret"

def test_health():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_command_ping():
    payload = {"type": "PING", "payload": {"hello":"world"}}
    r = client.post("/api/v1/commands", headers={"X-API-Key": API_KEY}, json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["message"] == "pong"
