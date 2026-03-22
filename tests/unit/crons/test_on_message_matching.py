# -*- coding: utf-8 -*-
"""Unit tests for on_message trigger matching."""

from __future__ import annotations

from copaw.app.crons.manager import CronManager
from copaw.app.crons.models import CronJobRequest, CronJobSpec


def _build_on_message_job(**schedule_overrides) -> CronJobSpec:
    schedule = {
        "type": "on_message",
        "channel": None,
        "user_id": None,
        "session_id": None,
        "contains": None,
        "pattern": None,
        "timezone": "UTC",
    }
    schedule.update(schedule_overrides)
    return CronJobSpec(
        id="job-1",
        name="on-message",
        enabled=True,
        schedule=schedule,
        task_type="agent",
        request=CronJobRequest(input="hello"),
        dispatch={
            "type": "channel",
            "channel": "feishu",
            "target": {"user_id": "u1", "session_id": "s1"},
            "mode": "stream",
            "meta": {},
        },
    )


def test_on_message_match_by_contains_case_insensitive() -> None:
    job = _build_on_message_job(channel="feishu", contains="deploy")
    assert CronManager._on_message_matches(
        job,
        channel="feishu",
        user_id="u1",
        session_id="s1",
        text="Please Deploy now",
    )


def test_on_message_match_with_regex_pattern() -> None:
    job = _build_on_message_job(channel="feishu", pattern=r"^build\s+#\d+$")
    assert CronManager._on_message_matches(
        job,
        channel="feishu",
        user_id="u1",
        session_id="s1",
        text="build #123",
    )


def test_on_message_mismatch_when_session_differs() -> None:
    job = _build_on_message_job(channel="feishu")
    assert not CronManager._on_message_matches(
        job,
        channel="feishu",
        user_id="u1",
        session_id="other-session",
        text="hello",
    )

