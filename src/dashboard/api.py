from __future__ import annotations

import os
from typing import Annotated, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .service import (
    closed_positions,
    dashboard_health,
    dashboard_overview,
    dashboard_summary,
    latest_markets,
    latest_strategy_evaluation,
    live_odds,
    open_positions,
    performance_breakdown,
    pnl_series,
    recent_events,
    recent_strategy_decisions,
    run_paper_session,
    strategy_context,
)
from .store import DashboardStore

load_dotenv()

DASHBOARD_TOKEN_ENV_VAR = "RORY_TRADER_DASHBOARD_TOKEN"
ALLOWED_ORIGINS_ENV_VAR = "RORY_TRADER_DASHBOARD_ALLOWED_ORIGINS"
LIVE_REVIEW_STATUSES = {
    "approved_for_operator_check",
    "rejected",
    "needs_more_context",
}


def _allowed_origins() -> list[str]:
    raw = os.getenv(ALLOWED_ORIGINS_ENV_VAR, "")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app = FastAPI(
    title="Rory TradeR Dashboard API",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
)

origins = _allowed_origins()
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["X-Rory-Dashboard-Token", "Content-Type"],
    )


def require_dashboard_token(
    x_rory_dashboard_token: Annotated[Optional[str], Header()] = None,  # noqa: UP045
) -> None:
    expected = os.getenv(DASHBOARD_TOKEN_ENV_VAR)
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dashboard API token is not configured.",
        )
    if x_rory_dashboard_token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid dashboard API token.",
        )


class LiveReviewRequest(BaseModel):
    proposal_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    note: str = ""


class PaperSessionRequest(BaseModel):
    category: str = Field(default="tennis", min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    max_results: int = Field(default=100, ge=1, le=100)


@app.get("/api/health", dependencies=[Depends(require_dashboard_token)])
def health() -> dict:
    return dashboard_health()


@app.get("/api/dashboard/overview", dependencies=[Depends(require_dashboard_token)])
def overview() -> dict:
    return dashboard_overview()


@app.get("/api/dashboard/summary", dependencies=[Depends(require_dashboard_token)])
def summary(
    open_limit: int = Query(default=12, ge=1, le=100),
    closed_limit: int = Query(default=8, ge=1, le=100),
    recent_limit: int = Query(default=12, ge=1, le=100),
    decision_limit: int = Query(default=100, ge=1, le=300),
) -> dict:
    return dashboard_summary(
        open_limit=open_limit,
        closed_limit=closed_limit,
        recent_limit=recent_limit,
        decision_limit=decision_limit,
    )


@app.get("/api/dashboard/open-positions", dependencies=[Depends(require_dashboard_token)])
def dashboard_open_positions(limit: Optional[int] = Query(default=None, ge=1, le=500)) -> dict:  # noqa: UP045
    return {"positions": open_positions(limit=limit)}


@app.get("/api/dashboard/closed-positions", dependencies=[Depends(require_dashboard_token)])
def dashboard_closed_positions(limit: Optional[int] = Query(default=None, ge=1, le=500)) -> dict:  # noqa: UP045
    return {"positions": closed_positions(limit=limit)}


@app.get("/api/dashboard/recent-events", dependencies=[Depends(require_dashboard_token)])
def dashboard_recent_events() -> dict:
    return {"events": recent_events()}


@app.get("/api/dashboard/latest-markets", dependencies=[Depends(require_dashboard_token)])
def dashboard_latest_markets() -> dict:
    return latest_markets()


@app.get("/api/dashboard/live-odds", dependencies=[Depends(require_dashboard_token)])
def dashboard_live_odds(
    category: str = Query(default="tennis", min_length=1),
    max_results: int = Query(default=50, ge=1, le=100),
) -> dict:
    return live_odds(category=category, max_results=max_results)


@app.get("/api/dashboard/pnl-series", dependencies=[Depends(require_dashboard_token)])
def dashboard_pnl_series(limit: Optional[int] = Query(default=None, ge=1, le=1000)) -> dict:  # noqa: UP045
    return pnl_series(limit=limit)


@app.get("/api/dashboard/performance", dependencies=[Depends(require_dashboard_token)])
def dashboard_performance() -> dict:
    return performance_breakdown()


@app.get("/api/dashboard/strategy-context", dependencies=[Depends(require_dashboard_token)])
def dashboard_strategy_context(category: str = Query(default="tennis", min_length=1)) -> dict:
    return strategy_context(category=category)


@app.get("/api/dashboard/strategy-decisions", dependencies=[Depends(require_dashboard_token)])
def dashboard_strategy_decisions(limit: int = Query(default=100, ge=1, le=300)) -> dict:
    return {
        "evaluation": latest_strategy_evaluation(),
        "decisions": recent_strategy_decisions(limit=limit),
    }


@app.post("/api/paper-session/run", dependencies=[Depends(require_dashboard_token)])
def paper_session_run(request: PaperSessionRequest) -> dict:
    return run_paper_session(category=request.category, max_results=request.max_results)


@app.post("/api/live-review", dependencies=[Depends(require_dashboard_token)])
def live_review(request: LiveReviewRequest) -> dict:
    if request.status not in LIVE_REVIEW_STATUSES:
        allowed = ", ".join(sorted(LIVE_REVIEW_STATUSES))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported live review status. Use one of: {allowed}.",
        )

    record = DashboardStore().record_live_review(
        request.proposal_id,
        request.status,
        request.note,
    )
    return {
        "proposal_id": record.proposal_id,
        "status": record.status,
        "note": record.note,
        "recorded_at": record.recorded_at.isoformat(),
        "live_execution_available": False,
    }
