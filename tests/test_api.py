from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)


def test_health():
    assert c.get("/api/health").json()["ok"] is True


def test_analyze_ok():
    r = c.post("/api/analyze", json={"text": "hello"})
    assert r.status_code == 200 and r.json()["bot"] is None


def test_analyze_rejects_bad_input():
    assert c.post("/api/analyze", json={}).status_code == 422
    assert c.post("/api/analyze", json={"text": ""}).status_code == 422
    assert c.post("/api/analyze", json={"text": "x" * 5001}).status_code == 422
    assert c.post("/api/analyze", json={"text": "a", "url": "b"}).status_code == 422
