from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from .contracts import BarTimeframe, Freshness, QuoteStatus


class HealthResponse(BaseModel):
    status: Literal["ok"]
    collectorConfigured: bool
    liveDataConfigured: bool


class ReadyResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    redis: Literal["disabled", "ok", "unavailable"]
    collector: Literal["disabled", "configured", "healthy", "stale"]


class QuoteResponse(BaseModel):
    symbol: str
    price: float
    timestamp: datetime
    source: str
    status: QuoteStatus
    freshness: Freshness


class BarResponse(BaseModel):
    symbol: str
    timeframe: BarTimeframe
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    source: str


class BarsResponse(BaseModel):
    symbol: str
    timeframe: BarTimeframe
    bars: list[BarResponse]
