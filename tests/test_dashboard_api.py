from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from src.dashboard.api import app
from src.exchanges.common.adapter import ValidationResult
from src.exchanges.common.models import ExecutionReport, MarketSnapshot, PaperFill, SelectionSnapshot, StrategySignal
from src.trading.accounting import resolve_journal_position
from src.trading.journal import JournalStore
from src.trading.market_history import save_market_snapshots
from src.trading.strategy import BackPriceBucketConfig, BackPriceBucketStrategy


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
        best_back_size=250.0,
        best_lay_size=240.0,
        traded_volume=1000.0,
        total_matched=5000.0,
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
        total_matched=5000.0,
        total_available=1000.0,
        in_play=False,
        is_market_data_delayed=False,
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
    monkeypatch.setenv("RORY_TRADER_DATA_ROOT", str(tmp_path / "data"))
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


def test_dashboard_overview_handles_snapshot_only_journal(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    JournalStore().record_snapshot_collection(tmp_path / "snapshots.parquet", 25, "sports")

    response = client.get("/api/dashboard/overview", headers={"X-Rory-Dashboard-Token": "test-token"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["overview"]["journal_events"] == 1
    assert payload["overview"]["executed_positions"] == 0
    assert payload["overview"]["open_positions"] == 0


def test_dashboard_summary_limits_first_screen_payload(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    _seed_open_position()
    _seed_open_position()
    strategy = BackPriceBucketStrategy(BackPriceBucketConfig(max_spread=0.04))
    decisions = strategy.evaluate_decisions([_snapshot()])
    JournalStore().record_strategy_evaluation(strategy.definition, decisions, snapshots_seen=1)

    response = client.get(
        "/api/dashboard/summary?open_limit=1&closed_limit=1&recent_limit=1&decision_limit=1",
        headers={"X-Rory-Dashboard-Token": "test-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["overview"]["open_positions"] == 2
    assert payload["overview"]["overdue_unresolved_positions"] == 0
    assert len(payload["open_positions"]) == 1
    assert len(payload["closed_positions"]) == 0
    assert len(payload["recent_events"]) == 1
    assert payload["performance"]["strategy"][0]["executed_positions"] == 2
    assert payload["strategy_evaluation"]["snapshots_seen"] == 1
    assert len(payload["strategy_decisions"]) == 1


def test_strategy_decisions_endpoint_reads_latest_evaluation(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    store = JournalStore()
    strategy = BackPriceBucketStrategy(BackPriceBucketConfig(max_spread=0.04))
    decisions = strategy.evaluate_decisions([_snapshot()])
    store.record_strategy_evaluation(strategy.definition, decisions, snapshots_seen=1)

    response = client.get(
        "/api/dashboard/strategy-decisions",
        headers={"X-Rory-Dashboard-Token": "test-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["evaluation"]["snapshots_seen"] == 1
    assert payload["evaluation"]["accepted_count"] == 0
    assert payload["evaluation"]["rejected_count"] == 1
    assert payload["decisions"][0]["reason_code"] == "spread_too_wide"


def test_strategy_context_endpoint_explains_tennis_rules(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    JournalStore().record_snapshot_collection(tmp_path / "snapshots.parquet", 25, "tennis")

    def fail_full_journal_load(self):
        raise AssertionError("strategy context should not parse the full journal")

    monkeypatch.setattr("src.dashboard.service.JournalStore.load_events", fail_full_journal_load)

    response = client.get(
        "/api/dashboard/strategy-context",
        headers={"X-Rory-Dashboard-Token": "test-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["category"] == "tennis"
    assert payload["definition"]["name"] == "betfair_tennis_pre_match_back_bucket"
    assert payload["definition"]["allowed_subcategories"] == ["tennis"]
    assert payload["definition"]["fixed_stake"] == 2.0
    assert any(rule["label"] == "Price bucket" for rule in payload["rules"])
    assert payload["recent_snapshot_collections"][0]["snapshot_count"] == 25


def test_latest_markets_endpoint_reads_latest_snapshot(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    save_market_snapshots([_snapshot()], output_dir=tmp_path / "data" / "betfair" / "snapshots")

    response = client.get(
        "/api/dashboard/latest-markets",
        headers={"X-Rory-Dashboard-Token": "test-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["market_count"] == 1
    assert payload["selection_count"] == 1
    assert payload["data_quality"]["tradeable_selection_count"] == 1
    assert payload["markets"][0]["event_name"] == "Liverpool v Spurs"
    assert payload["markets"][0]["best_back_size"] == 250.0


def test_live_odds_endpoint_fetches_betfair_without_saving_snapshot(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    snapshot = _snapshot()

    class FakeBetfairAdapter:
        name = "betfair"

        def validate_credentials(self):
            return ValidationResult(
                exchange="betfair",
                ok=True,
                approval_status="ready",
                message="Betfair login status: SUCCESS (mode: cert)",
            )

        def list_markets(self, category: str | None = None, max_results: int = 10):
            assert category == "tennis"
            assert max_results == 50
            return [snapshot]

    monkeypatch.setattr("src.dashboard.service.BetfairAdapter", FakeBetfairAdapter)

    response = client.get(
        "/api/dashboard/live-odds",
        headers={"X-Rory-Dashboard-Token": "test-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "live"
    assert payload["read_only"] is True
    assert payload["category"] == "tennis"
    assert payload["max_results"] == 50
    assert payload["market_count"] == 1
    assert payload["selection_count"] == 1
    assert payload["data_quality"]["tradeable_selection_count"] == 1
    assert payload["markets"][0]["event_name"] == "Liverpool v Spurs"
    assert payload["live_execution_available"] is False


def test_paper_session_endpoint_runs_bounded_paper_script(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    calls = []

    class FakeCompletedProcess:
        returncode = 0
        stdout = "\n".join(
            [
                "Paper report:",
                "snapshot_path: /tmp/snapshots.parquet",
                "snapshots_collected: 12",
                "strategy_focus: tennis",
                "strategy: betfair_tennis_pre_match_back_bucket@v1",
                "strategy_acceptances: 2",
                "paper_fills_created: 2",
                "journal_path: /tmp/journal.jsonl",
            ]
        )
        stderr = ""

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return FakeCompletedProcess()

    monkeypatch.setattr("src.dashboard.service.subprocess.run", fake_run)

    response = client.post(
        "/api/paper-session/run",
        headers={"X-Rory-Dashboard-Token": "test-token"},
        json={"category": "tennis", "max_results": 100},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["category"] == "tennis"
    assert payload["max_results"] == 100
    assert payload["summary"]["paper_fills_created"] == 2
    assert payload["summary"]["strategy_focus"] == "tennis"
    assert payload["live_execution_available"] is False
    assert calls
    assert calls[0][0][-2:] == ["tennis", "100"]
    assert calls[0][1]["env"]["RORY_TRADER_LIVE_ENABLED"] == "false"


def test_paper_session_endpoint_rejects_when_live_enabled(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    monkeypatch.setenv("RORY_TRADER_LIVE_ENABLED", "true")

    response = client.post(
        "/api/paper-session/run",
        headers={"X-Rory-Dashboard-Token": "test-token"},
        json={"category": "tennis", "max_results": 100},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "rejected"
    assert payload["live_execution_available"] is False
    assert "paper sessions require live execution disabled" in payload["stderr"]


def test_pnl_series_endpoint_reads_journal_realized_pnl(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    proposal_id = _seed_open_position()
    resolve_journal_position(proposal_id, "won")

    response = client.get(
        "/api/dashboard/pnl-series",
        headers={"X-Rory-Dashboard-Token": "test-token"},
    )

    assert response.status_code == 200
    points = response.json()["points"]
    assert len(points) == 2
    assert points[-1]["cumulative_realized_pnl"] > 0


def test_limited_pnl_series_keeps_cumulative_totals(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    _seed_open_position()
    _seed_open_position()

    response = client.get(
        "/api/dashboard/pnl-series?limit=1",
        headers={"X-Rory-Dashboard-Token": "test-token"},
    )

    assert response.status_code == 200
    points = response.json()["points"]
    assert len(points) == 1
    assert points[0]["cumulative_stake"] == 4.0


def test_performance_endpoint_returns_learning_breakdowns(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    proposal_id = _seed_open_position()
    resolve_journal_position(proposal_id, "won")

    response = client.get(
        "/api/dashboard/performance",
        headers={"X-Rory-Dashboard-Token": "test-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["strategy"][0]["executed_positions"] == 1
    assert payload["strategy"][0]["closed_positions"] == 1
    assert payload["strategy"][0]["win_rate"] == 1
    assert payload["price_bucket"][0]["price_bucket"] == "2.0-3.0"
    assert payload["time_window"][0]["time_window"] == "12-24h"


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
    assert "data_quality" in payload
    assert "should-not-appear" not in response.text


def test_live_submission_endpoint_does_not_exist(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)

    response = client.post(
        "/api/live-submit",
        headers={"X-Rory-Dashboard-Token": "test-token"},
        json={"proposal_id": "abc"},
    )

    assert response.status_code == 404
