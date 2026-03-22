# -*- coding: utf-8 -*-
from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .manager import CronManager
from .models import CronJobSpec, CronJobView

router = APIRouter(prefix="/cron", tags=["cron"])


class WebhookTriggerRequest(BaseModel):
    event: str = Field(description="Webhook event name")
    source: str = Field(default="", description="Webhook source")
    channel: str = Field(default="", description="Optional channel filter value")
    user_id: str = Field(default="", description="Optional user id")
    session_id: str = Field(default="", description="Optional session id")
    text: str = Field(default="", description="Optional text for contains/pattern")
    payload: dict = Field(default_factory=dict, description="Raw webhook payload")


async def get_cron_manager(
    request: Request,
) -> CronManager:
    """Get cron manager for the active agent."""
    from ..agent_context import get_agent_for_request

    workspace = await get_agent_for_request(request)
    if workspace.cron_manager is None:
        raise HTTPException(
            status_code=500,
            detail="CronManager not initialized",
        )
    return workspace.cron_manager


@router.get("/jobs", response_model=list[CronJobSpec])
async def list_jobs(mgr: CronManager = Depends(get_cron_manager)):
    return await mgr.list_jobs()


@router.get("/jobs/{job_id}", response_model=CronJobView)
async def get_job(job_id: str, mgr: CronManager = Depends(get_cron_manager)):
    job = await mgr.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return CronJobView(spec=job, state=mgr.get_state(job_id))


@router.post("/jobs", response_model=CronJobSpec)
async def create_job(
    spec: CronJobSpec,
    mgr: CronManager = Depends(get_cron_manager),
):
    # server generates id; ignore client-provided spec.id
    job_id = str(uuid.uuid4())
    created = spec.model_copy(update={"id": job_id})
    await mgr.create_or_replace_job(created)
    return created


@router.put("/jobs/{job_id}", response_model=CronJobSpec)
async def replace_job(
    job_id: str,
    spec: CronJobSpec,
    mgr: CronManager = Depends(get_cron_manager),
):
    if spec.id != job_id:
        raise HTTPException(status_code=400, detail="job_id mismatch")
    await mgr.create_or_replace_job(spec)
    return spec


@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: str,
    mgr: CronManager = Depends(get_cron_manager),
):
    ok = await mgr.delete_job(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="job not found")
    return {"deleted": True}


@router.post("/jobs/{job_id}/pause")
async def pause_job(job_id: str, mgr: CronManager = Depends(get_cron_manager)):
    try:
        await mgr.pause_job(job_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"paused": True}


@router.post("/jobs/{job_id}/resume")
async def resume_job(
    job_id: str,
    mgr: CronManager = Depends(get_cron_manager),
):
    try:
        await mgr.resume_job(job_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"resumed": True}


@router.post("/jobs/{job_id}/run")
async def run_job(job_id: str, mgr: CronManager = Depends(get_cron_manager)):
    try:
        await mgr.run_job(job_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail="job not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {"started": True}


@router.get("/jobs/{job_id}/state")
async def get_job_state(
    job_id: str,
    mgr: CronManager = Depends(get_cron_manager),
):
    job = await mgr.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return mgr.get_state(job_id).model_dump(mode="json")


@router.get("/audit/events")
async def get_audit_events(
    limit: int = Query(default=100, ge=1, le=1000),
    job_id: str = Query(default=""),
    status: str = Query(default=""),
    trigger_type: str = Query(default=""),
    mgr: CronManager = Depends(get_cron_manager),
):
    events = mgr.list_audit_events(
        limit=limit,
        job_id=job_id,
        status=status,
        trigger_type=trigger_type,
    )
    return {"events": events}


@router.post("/webhook/trigger")
async def trigger_webhook(
    body: WebhookTriggerRequest,
    mgr: CronManager = Depends(get_cron_manager),
):
    try:
        fired = await mgr.handle_webhook_event(
            event=body.event,
            source=body.source,
            channel=body.channel,
            user_id=body.user_id,
            session_id=body.session_id,
            text=body.text,
            payload=body.payload,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {"fired": fired}
