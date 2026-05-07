from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from src.dashboard.api import app
from src.exchanges.common.adapter import ValidationResult
from src.exchanges.common.models import ExecutionReport, MarketSnapshot, PaperFill, SelectionSnapshot, StrategySignal
from src.trading.journal import JournalStore


def _snapshot() -> MarketSnapshot:
    now = datetime.now(timezone.utc)
    selection = SelectionSnapshot(
        exchange="betfair",
        market_id="1.200",
        selection_id="101",
        market_title="Match Odds",
        selection_name="Liverpool",
        category="sports",
        subcategory="soccer",
        event_start=now + timedelta(hours=18),
        best_back=2.2,
        best_lay=2.28,
        last_traded=2.24,
        status="open",
        event_name="Liverpool v Spurs",
        competition_name="Premier League",
        captured_at=now,
    )
    return MarketSnapshot(
        exchange="betfair",
        market_id="1.200",
        market_title="Match Odds",
        category="sports",
        subcategory="soccer",
        event_start=selection.event_start,
        status="open",
        selections=[selection],
        event_name="Liverpool v Spurs",
        competition_name="Premier League",
        captured_at=now,
    )


def _signal(snapshot: MarketSnapshot) -> StrategySignal:
    return StrategySignal(
        strategy_name="betfair_pre_match_back_bucket",
        strategy_version="v1",
        market_id=snapshot.market_id,
        selection_id="101",
        side="back",
        confidence=0.7,
        reason="Dashboard test signal.",
        stake=2.0,
        requested_price=2.2,
        snapshot_timestamp=snapshot.captured_at,
        event_start=snapshot.event_start,
        holding_period_hours=24.0,
        tags=["betfair", "sports"],
    )


def _seed_open_position() -> str:
    store = JournalStore()
    snapshot = _snapshot()
    proposal = store.record_proposal(_signal(snapshot), snapshot)
    assert proposal is not None
    store.record_execution(
        proposal.proposal_id,
        ExecutionReport(
            accepted=True,
            exchange="betfair",
            mode="paper",
            message="Paper fill created successfully.",
            fill=PaperFill(
                market_id=snapshot.market_id,
                selection_id="101",
                side="back",
                stake=2.0,
                fill_price=2.21,
                commission_paid=0.04,
                slippage_paid=0.01,
                timestamp=datetime.now(timezone.utc),
            ),
        ),
        mode="paper",
    )
    return proposal.proposal_id


def _client(monkeypatch, tmp_path) -> TestClient:
    monkeypatch.setenv("RORY_TRADER_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("RORY_TRADER_DASHBOARD_TOKEN", "test-token")
    return TestClient(app)


def test_dashboard_overview_reads_current_journal(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    _seed_open_position()

    response = client.get("/api/dashboard/overview", headers={"X-Rory-Dashboard-Token": "test-token"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["overview"]["executed_positions"] == 1
    assert payload["overview"]["open_positions"] == 1
    assert payload["live_execution_available"] is False
    assert payload["live_enabled"] is False


def test_open_positions_include_latest_live_review(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    proposal_id = _seed_open_position()

    review_response = client.post(
        "/api/live-review",
        headers={"X-Rory-Dashboard-Token": "test-token"},
        json={
            "proposal_id": proposal_id,
            "status": "approved_for_operator_check",
            "note": "Review manually before any live action.",
        },
    )
    positions_response = client.get(
        "/api/dashboard/open-positions",
        headers={"X-Rory-Dashboard-Token": "test-token"},
    )

    assert review_response.status_code == 200
    assert review_response.json()["live_execution_available"] is False
    assert positions_response.status_code == 200
    positions = positions_response.json()["positions"]
    assert len(positions) == 1
    assert positions[0]["live_review"]["status"] == "approved_for_operator_check"


def test_dashboard_api_rejects_missing_and_invalid_tokens(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)

    missing = client.get("/api/dashboard/overview")
    invalid = client.get("/api/dashboard/overview", headers={"X-Rory-Dashboard-Token": "wrong"})

    assert missing.status_code == 401
    assert invalid.status_code == 401


def test_health_does_not_expose_secrets(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)

    def fake_validate_credentials(self):
        return ValidationResult(
            exchange="betfair",
            ok=False,
            approval_status="missing_credentials",
            message="Betfair credentials are incomplete.",
            details={"BETFAIR_PASSWORD": "should-not-appear"},
        )

    monkeypatch.setattr("src.exchanges.betfair.adapter.BetfairAdapter.validate_credentials", fake_validate_credentials)

    response = client.get("/api/health", headers={"X-Rory-Dashboard-Token": "test-token"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["supports_live_execution"] is False
    assert payload["live_execution_available"] is False
    assert "should-not-appear" not in response.text


def test_live_submission_endpoint_does_not_exist(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)

    response = client.post(
        "/api/live-submit",
        headers={"X-Rory-Dashboard-Token": "test-token"},
        json={"proposal_id": "abc"},
    )

    assert response.status_code == 404
