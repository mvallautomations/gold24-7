"""Characterize the current status endpoint's paper/live labeling bug."""

from fastapi.testclient import TestClient

from dashboard import server


def test_api_status_currently_reports_live_account(monkeypatch):
    monkeypatch.setattr(server.mt5_syncer, "get_account_stats", lambda: {})

    response = TestClient(server.app).get("/api/status")

    assert response.status_code == 200
    assert response.json()["environment"] == "LIVE_ACCOUNT"
    assert response.json()["is_simulation_only"] is False
