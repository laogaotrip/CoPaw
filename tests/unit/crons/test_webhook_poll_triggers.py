# -*- coding: utf-8 -*-
"""Unit tests for webhook/poll trigger matching and dispatch."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from copaw.app.crons.api import WebhookTriggerRequest, trigger_webhook
from copaw.app.crons.manager import CronManager
from copaw.app.crons.models import CronJobRequest, CronJobSpec, JobsFile
from copaw.app.crons.repo.base import BaseJobRepository


class _InMemoryRepo(BaseJobRepository):
    def __init__(self, jobs: list[CronJobSpec]) -> None:
        self._jobs_file = JobsFile(version=1, jobs=jobs)

    async def load(self) -> JobsFile:
        return self._jobs_file

    async def save(self, jobs_file: JobsFile) -> None:
        self._jobs_file = jobs_file


def _build_webhook_job(**schedule_overrides) -> CronJobSpec:
    schedule = {
        "type": "webhook",
        "webhook_event": "build.completed",
        "webhook_source": "github",
        "channel": None,
        "user_id": None,
        "session_id": None,
        "contains": None,
        "pattern": None,
        "timezone": "UTC",
    }
    schedule.update(schedule_overrides)
    return CronJobSpec(
        id="job-webhook-1",
        name="webhook-job",
        enabled=True,
        schedule=schedule,
        task_type="agent",
        request=CronJobRequest(input="triggered"),
        dispatch={
            "type": "channel",
            "channel": "feishu",
            "target": {"user_id": "u1", "session_id": "s1"},
            "mode": "stream",
            "meta": {},
        },
    )


def _build_poll_job(**schedule_overrides) -> CronJobSpec:
    schedule = {
        "type": "poll",
        "every_seconds": 30,
        "poll_url": "https://example.com/status",
        "poll_method": "GET",
        "poll_timeout_seconds": 10,
        "poll_expected_status": None,
        "poll_headers": None,
        "poll_body": None,
        "contains": None,
        "pattern": None,
        "timezone": "UTC",
    }
    schedule.update(schedule_overrides)
    return CronJobSpec(
        id="job-poll-1",
        name="poll-job",
        enabled=True,
        schedule=schedule,
        task_type="agent",
        request=CronJobRequest(input="poll-triggered"),
        dispatch={
            "type": "channel",
            "channel": "feishu",
            "target": {"user_id": "u1", "session_id": "s1"},
            "mode": "stream",
            "meta": {},
        },
    )


def test_webhook_matches_event_source_and_text_filters() -> None:
    job = _build_webhook_job(contains="release", pattern=r"v\d+\.\d+\.\d+")
    assert CronManager._webhook_matches(  # pylint: disable=protected-access
        job,
        event="build.completed",
        source="github",
        channel="feishu",
        user_id="u1",
        session_id="s1",
        text="release v1.2.3 done",
    )


def test_poll_response_match_with_expected_status_contains_and_pattern() -> None:
    job = _build_poll_job(
        poll_expected_status=200,
        contains="healthy",
        pattern=r"uptime:\s+\d+",
    )
    assert CronManager._poll_response_matches(  # pylint: disable=protected-access
        job,
        status_code=200,
        text="service healthy, uptime: 12345",
    )


@pytest.mark.asyncio
async def test_handle_webhook_event_dispatches_only_matching_jobs() -> None:
    matching = _build_webhook_job()
    not_matching = _build_webhook_job(
        webhook_event="build.started",
        pattern=r"start",
    )
    repo = _InMemoryRepo([matching, not_matching])
    mgr = CronManager(
        repo=repo,
        runner=object(),
        channel_manager=object(),
        timezone="UTC",
    )
    mgr._execute_once = AsyncMock()  # pylint: disable=protected-access

    fired = await mgr.handle_webhook_event(
        event="build.completed",
        source="github",
        channel="feishu",
        user_id="u1",
        session_id="s1",
        text="pipeline completed",
    )
    await asyncio.sleep(0)

    assert fired == 1
    assert mgr._execute_once.await_count == 1  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_trigger_webhook_api_forwards_fields_and_returns_fired_count() -> None:
    mgr = AsyncMock()
    mgr.handle_webhook_event.return_value = 2
    body = WebhookTriggerRequest(
        event="build.completed",
        source="github",
        channel="feishu",
        user_id="u1",
        session_id="s1",
        text="ok",
        payload={"id": 1},
    )

    result = await trigger_webhook(body=body, mgr=mgr)

    assert result == {"fired": 2}
    mgr.handle_webhook_event.assert_awaited_once_with(
        event="build.completed",
        source="github",
        channel="feishu",
        user_id="u1",
        session_id="s1",
        text="ok",
        payload={"id": 1},
    )
