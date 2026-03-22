# -*- coding: utf-8 -*-
"""Request/response schemas for config API endpoints."""

from typing import Optional

from pydantic import BaseModel, Field

from ...config.config import ActiveHoursConfig


class HeartbeatBody(BaseModel):
    """Request body for PUT /config/heartbeat."""

    enabled: bool = False
    every: str = "6h"
    target: str = "main"
    active_hours: Optional[ActiveHoursConfig] = Field(
        default=None,
        alias="activeHours",
    )

    model_config = {"populate_by_name": True, "extra": "allow"}


class EvolutionBody(BaseModel):
    """Request body for PUT /config/evolution."""

    enabled: bool = False
    mode: str = "manual"
    every: str = "24h"
    query_file: str = "SELF_EVOLUTION.md"
    timeout_seconds: int = 180
    session_id: str = "evolution"
    user_id: str = "evolution"

    model_config = {"extra": "allow"}
