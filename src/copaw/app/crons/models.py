# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Literal, Optional
import re

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from ..channels.schema import DEFAULT_CHANNEL

# ---------------------------------------------------------------------------
# APScheduler v3 uses ISO 8601 weekday numbering (0=Mon … 6=Sun) for
# CronTrigger(day_of_week=...), while standard crontab uses 0=Sun … 6=Sat.
# from_crontab() does NOT convert either.  Three-letter English abbreviations
# (mon, tue, …, sun) are unambiguous in both systems, so we normalise the
# 5th cron field to abbreviations at validation time.
# ---------------------------------------------------------------------------

_CRONTAB_NUM_TO_NAME: dict[str, str] = {
    "0": "sun",
    "1": "mon",
    "2": "tue",
    "3": "wed",
    "4": "thu",
    "5": "fri",
    "6": "sat",
    "7": "sun",
}


def _crontab_dow_to_name(field: str) -> str:
    """Convert the day-of-week field from crontab numbers to abbreviations.

    Handles: ``*``, single values, comma-separated lists, and ranges.
    Already-named values (``mon``, ``tue``, …) are passed through unchanged.
    """
    if field == "*":
        return field

    def _convert_token(tok: str) -> str:
        if "/" in tok:
            base, step = tok.rsplit("/", 1)
            return f"{_convert_token(base)}/{step}"
        if "-" in tok:
            parts = tok.split("-", 1)
            return "-".join(_CRONTAB_NUM_TO_NAME.get(p, p) for p in parts)
        return _CRONTAB_NUM_TO_NAME.get(tok, tok)

    return ",".join(_convert_token(t) for t in field.split(","))


class ScheduleSpec(BaseModel):
    type: Literal[
        "cron",
        "once",
        "interval",
        "on_message",
        "webhook",
        "poll",
    ] = "cron"
    cron: Optional[str] = Field(default=None)
    at: Optional[datetime] = Field(
        default=None,
        description="For type=once, exact trigger time (ISO datetime).",
    )
    every_seconds: Optional[int] = Field(
        default=None,
        ge=1,
        description="For type=interval, trigger interval in seconds.",
    )
    channel: Optional[str] = Field(
        default=None,
        description="For type=on_message, optional channel filter.",
    )
    user_id: Optional[str] = Field(
        default=None,
        description="For type=on_message, optional user_id filter.",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="For type=on_message, optional session_id filter.",
    )
    contains: Optional[str] = Field(
        default=None,
        description="For type=on_message, case-insensitive substring match.",
    )
    pattern: Optional[str] = Field(
        default=None,
        description="For type=on_message, regex pattern match.",
    )
    webhook_event: Optional[str] = Field(
        default=None,
        description="For type=webhook, optional event name filter.",
    )
    webhook_source: Optional[str] = Field(
        default=None,
        description="For type=webhook, optional source filter.",
    )
    poll_url: Optional[str] = Field(
        default=None,
        description="For type=poll, target URL to poll.",
    )
    poll_method: str = Field(
        default="GET",
        description="For type=poll, HTTP method.",
    )
    poll_timeout_seconds: int = Field(
        default=10,
        ge=1,
        le=300,
        description="For type=poll, request timeout in seconds.",
    )
    poll_expected_status: Optional[int] = Field(
        default=None,
        ge=100,
        le=599,
        description="For type=poll, optional expected HTTP status code.",
    )
    poll_headers: Optional[Dict[str, str]] = Field(
        default=None,
        description="For type=poll, optional HTTP headers.",
    )
    poll_body: Optional[str] = Field(
        default=None,
        description="For type=poll, optional request body.",
    )
    timezone: str = "UTC"

    @field_validator("poll_method")
    @classmethod
    def normalize_poll_method(cls, v: str) -> str:
        method = (v or "").strip().upper()
        return method or "GET"

    @field_validator("cron")
    @classmethod
    def normalize_cron_5_fields(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        parts = [p for p in v.split() if p]
        if len(parts) == 5:
            parts[4] = _crontab_dow_to_name(parts[4])
            return " ".join(parts)

        if len(parts) == 4:
            # treat as: hour dom month dow
            hour, dom, month, dow = parts
            return f"0 {hour} {dom} {month} {_crontab_dow_to_name(dow)}"

        if len(parts) == 3:
            # treat as: dom month dow
            dom, month, dow = parts
            return f"0 0 {dom} {month} {_crontab_dow_to_name(dow)}"

        # 6 fields (seconds) or too short: reject
        raise ValueError(
            "cron must have 5 fields "
            "(or 4/3 fields that can be normalized); seconds not supported.",
        )

    @model_validator(mode="after")
    def validate_schedule_by_type(self) -> "ScheduleSpec":
        if self.type == "cron":
            if not (self.cron and self.cron.strip()):
                raise ValueError("schedule.cron is required when type=cron")
            return self

        if self.type == "once":
            if self.at is None:
                raise ValueError("schedule.at is required when type=once")
            return self

        if self.type == "interval":
            if self.every_seconds is None:
                raise ValueError(
                    "schedule.every_seconds is required when type=interval",
                )
            return self

        if self.type in {"on_message", "webhook"}:
            if self.pattern:
                try:
                    re.compile(self.pattern)
                except re.error as e:  # pragma: no cover
                    raise ValueError(
                        f"invalid schedule.pattern regex: {e}",
                    ) from e
            return self

        if self.type == "poll":
            if self.every_seconds is None:
                raise ValueError(
                    "schedule.every_seconds is required when type=poll",
                )
            if not (self.poll_url and self.poll_url.strip()):
                raise ValueError(
                    "schedule.poll_url is required when type=poll",
                )
            if self.pattern:
                try:
                    re.compile(self.pattern)
                except re.error as e:  # pragma: no cover
                    raise ValueError(
                        f"invalid schedule.pattern regex: {e}",
                    ) from e
            return self

        return self


class DispatchTarget(BaseModel):
    user_id: str
    session_id: str


class DispatchSpec(BaseModel):
    type: Literal["channel"] = "channel"
    channel: str = Field(default=DEFAULT_CHANNEL)
    target: DispatchTarget
    mode: Literal["stream", "final"] = Field(default="stream")
    meta: Dict[str, Any] = Field(default_factory=dict)


class JobRuntimeSpec(BaseModel):
    max_concurrency: int = Field(default=1, ge=1)
    timeout_seconds: int = Field(default=120, ge=1)
    misfire_grace_seconds: int = Field(default=60, ge=0)


class CronJobRequest(BaseModel):
    """Passthrough payload to runner.stream_query(request=...).

    This is aligned with AgentRequest(extra="allow"). We keep it permissive.
    """

    model_config = ConfigDict(extra="allow")

    input: Any
    session_id: Optional[str] = None
    user_id: Optional[str] = None


TaskType = Literal["text", "agent"]


class CronJobSpec(BaseModel):
    id: str
    name: str
    enabled: bool = True

    schedule: ScheduleSpec
    task_type: TaskType = "agent"
    text: Optional[str] = None
    request: Optional[CronJobRequest] = None
    dispatch: DispatchSpec

    runtime: JobRuntimeSpec = Field(default_factory=JobRuntimeSpec)
    meta: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_task_type_fields(self) -> "CronJobSpec":
        if self.task_type == "text":
            if not (self.text and self.text.strip()):
                raise ValueError("task_type is text but text is empty")
        elif self.task_type == "agent":
            if self.request is None:
                raise ValueError("task_type is agent but request is missing")
            # Keep request.user_id and request.session_id in sync with target
            target = self.dispatch.target
            self.request = self.request.model_copy(
                update={
                    "user_id": target.user_id,
                    "session_id": target.session_id,
                },
            )
        return self


class JobsFile(BaseModel):
    version: int = 1
    jobs: list[CronJobSpec] = Field(default_factory=list)


class CronJobState(BaseModel):
    next_run_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    last_status: Optional[
        Literal["success", "error", "running", "skipped", "cancelled"]
    ] = None
    last_error: Optional[str] = None


class CronJobView(BaseModel):
    spec: CronJobSpec
    state: CronJobState = Field(default_factory=CronJobState)
