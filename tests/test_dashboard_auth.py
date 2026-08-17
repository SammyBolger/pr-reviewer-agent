from fastapi.testclient import TestClient


def _client(monkeypatch, token: str = ""):
    from app import main as main_mod
    monkeypatch.setattr(main_mod.settings, "dashboard_token", token)
    return TestClient(main_mod.app)


def test_dashboard_returns_404_when_no_token_configured(monkeypatch):
    with _client(monkeypatch, token="") as c:
        r = c.get("/dashboard")
    assert r.status_code == 404


def test_dashboard_returns_401_when_no_header(monkeypatch):
    with _client(monkeypatch, token="secret-value") as c:
        r = c.get("/dashboard")
    assert r.status_code == 401


def test_dashboard_returns_401_with_wrong_token(monkeypatch):
    with _client(monkeypatch, token="secret-value") as c:
        r = c.get("/dashboard", headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 401


def test_dashboard_ok_with_correct_token(monkeypatch):
    with _client(monkeypatch, token="secret-value") as c:
        r = c.get("/dashboard", headers={"Authorization": "Bearer secret-value"})
    assert r.status_code == 200
    assert "totals" in r.json()
