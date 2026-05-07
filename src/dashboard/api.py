from __future__ import annotations

import os
from typing import Annotated, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .service import (
    closed_positions,
    dashboard_health,
    dashboard_overview,
    open_positions,
    recent_events,
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


@app.get("/api/health", dependencies=[Depends(require_dashboard_token)])
def health() -> dict:
    return dashboard_health()


@app.get("/api/dashboard/overview", dependencies=[Depends(require_dashboard_token)])
def overview() -> dict:
    return dashboard_overview()


@app.get("/api/dashboard/open-positions", dependencies=[Depends(require_dashboard_token)])
def dashboard_open_positions() -> dict:
    return {"positions": open_positions()}


@app.get("/api/dashboard/closed-positions", dependencies=[Depends(require_dashboard_token)])
def dashboard_closed_positions() -> dict:
    return {"positions": closed_positions()}


@app.get("/api/dashboard/recent-events", dependencies=[Depends(require_dashboard_token)])
def dashboard_recent_events() -> dict:
    return {"events": recent_events()}


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
