# -*- coding: utf-8 -*-
"""Unit tests for trigger security guardrails."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from copaw.app.crons.manager import CronManager
from copaw.app.crons.models import CronJobRequest, CronJobSpec, JobsFile
from copaw.app.crons.repo.base import BaseJobRepository
from copaw.app.crons.security import validate_poll_url
from copaw.config.config import AgentTriggerPolicyConfig


class _InMemoryRepo(BaseJobRepository):
    def __init__(self, jobs: list[CronJobSpec]):
        self._jobs_file = JobsFile(version=1, jobs=jobs)

    async def load(self) -> JobsFile:
        return self._jobs_file

    async def save(self, jobs_file: JobsFile) -> None:
        self._jobs_file = jobs_file


def _build_job(schedule: dict) -> CronJobSpec:
    return CronJobSpec(
        id="job-1",
        name="job",
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


def test_validate_poll_url_blocks_localhost_when_private_blocked() -> None:
    policy = AgentTriggerPolicyConfig(
        enable_poll=True,
        block_private_network=True,
        allowed_poll_domains=[],
    )
    with pytest.raises(ValueError, match="private/local network"):
        validate_poll_url("http://localhost:8080/health", policy=policy)


def test_validate_poll_url_rejects_domain_not_in_allowlist() -> None:
    policy = AgentTriggerPolicyConfig(
        enable_poll=True,
        block_private_network=False,
        allowed_poll_domains=["example.com"],
    )
    with pytest.raises(ValueError, match="not in allowed_poll_domains"):
        validate_poll_url("https://evil.com/check", policy=policy)


def test_validate_poll_url_allows_subdomain_in_allowlist() -> None:
    policy = AgentTriggerPolicyConfig(
        enable_poll=True,
        block_private_network=False,
        allowed_poll_domains=["example.com"],
    )
    validate_poll_url("https://api.example.com/check", policy=policy)


@pytest.mark.asyncio
async def test_register_webhook_job_rejected_when_webhook_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = _build_job(
        {
            "type": "webhook",
            "webhook_event": "build.completed",
            "webhook_source": "github",
            "timezone": "UTC",
        },
    )
    repo = _InMemoryRepo([job])
    mgr = CronManager(
        repo=repo,
        runner=SimpleNamespace(),
        channel_manager=SimpleNamespace(),
    )
    monkeypatch.setattr(
        "copaw.app.crons.manager.get_trigger_policy_config",
        lambda _agent_id: AgentTriggerPolicyConfig(
            enable_webhook=False,
            enable_poll=False,
        ),
    )

    with pytest.raises(ValueError, match="webhook trigger is disabled"):
        await mgr._register_or_update(job)  # pylint: disable=protected-access

