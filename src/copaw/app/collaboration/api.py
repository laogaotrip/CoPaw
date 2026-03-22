# -*- coding: utf-8 -*-
"""Collaboration API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .service import CollaborationError, CollaborationService

router = APIRouter(prefix="/collaboration", tags=["collaboration"])


async def get_workspace(request: Request):
    from ..agent_context import get_agent_for_request

    return await get_agent_for_request(request)


async def get_service(workspace=Depends(get_workspace)) -> CollaborationService:
    return CollaborationService(workspace)


class NotifyRequest(BaseModel):
    target_agent_id: str
    text: str
    channel: str = Field(default="console")
    user_id: str = Field(default="collaboration")
    session_id: str = Field(default="collaboration")


class AskRequest(BaseModel):
    target_agent_id: str
    prompt: str
    user_id: str = Field(default="collaboration")
    session_id: str = Field(default="collaboration")
    hop_count: int = Field(default=0, ge=0)


@router.post("/notify")
async def notify(
    body: NotifyRequest,
    svc: CollaborationService = Depends(get_service),
):
    try:
        await svc.notify(
            target_agent_id=body.target_agent_id,
            text=body.text,
            channel=body.channel,
            user_id=body.user_id,
            session_id=body.session_id,
        )
    except CollaborationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {"ok": True}


@router.post("/consult")
async def consult(
    body: AskRequest,
    svc: CollaborationService = Depends(get_service),
):
    try:
        result = await svc.consult(
            target_agent_id=body.target_agent_id,
            prompt=body.prompt,
            user_id=body.user_id,
            session_id=body.session_id,
            hop_count=body.hop_count,
        )
    except CollaborationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {
        "target_agent_id": result.target_agent_id,
        "response_text": result.response_text,
        "events": result.events,
    }


@router.post("/delegate")
async def delegate(
    body: AskRequest,
    svc: CollaborationService = Depends(get_service),
):
    try:
        result = await svc.delegate(
            target_agent_id=body.target_agent_id,
            task=body.prompt,
            user_id=body.user_id,
            session_id=body.session_id,
            hop_count=body.hop_count,
        )
    except CollaborationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {
        "target_agent_id": result.target_agent_id,
        "response_text": result.response_text,
        "events": result.events,
    }

