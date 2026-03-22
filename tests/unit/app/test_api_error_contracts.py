# -*- coding: utf-8 -*-
"""API error-mapping contract tests for new endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from copaw.app.collaboration.api import AskRequest, NotifyRequest, consult, delegate, notify
from copaw.app.collaboration.service import CollaborationError
from copaw.app.crons.api import run_job


@pytest.mark.asyncio
async def test_collaboration_notify_maps_collaboration_error_to_400() -> None:
    svc = AsyncMock()
    svc.notify.side_effect = CollaborationError("bad target")
    body = NotifyRequest(target_agent_id="agent-b", text="hello")

    with pytest.raises(HTTPException) as exc:
        await notify(body=body, svc=svc)

    assert exc.value.status_code == 400
    assert "bad target" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_collaboration_consult_maps_unexpected_error_to_500() -> None:
    svc = AsyncMock()
    svc.consult.side_effect = RuntimeError("boom")
    body = AskRequest(target_agent_id="agent-b", prompt="help")

    with pytest.raises(HTTPException) as exc:
        await consult(body=body, svc=svc)

    assert exc.value.status_code == 500
    assert "boom" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_collaboration_delegate_maps_collaboration_error_to_400() -> None:
    svc = AsyncMock()
    svc.delegate.side_effect = CollaborationError("hop limit")
    body = AskRequest(target_agent_id="agent-b", prompt="task")

    with pytest.raises(HTTPException) as exc:
        await delegate(body=body, svc=svc)

    assert exc.value.status_code == 400
    assert "hop limit" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_cron_run_job_maps_key_error_to_404() -> None:
    mgr = AsyncMock()
    mgr.run_job.side_effect = KeyError("missing")

    with pytest.raises(HTTPException) as exc:
        await run_job(job_id="missing", mgr=mgr)

    assert exc.value.status_code == 404
    assert exc.value.detail == "job not found"


@pytest.mark.asyncio
async def test_cron_run_job_maps_unexpected_error_to_500() -> None:
    mgr = AsyncMock()
    mgr.run_job.side_effect = RuntimeError("internal")

    with pytest.raises(HTTPException) as exc:
        await run_job(job_id="j1", mgr=mgr)

    assert exc.value.status_code == 500
    assert "internal" in str(exc.value.detail)

