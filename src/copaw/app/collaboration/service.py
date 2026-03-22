# -*- coding: utf-8 -*-
"""Cross-agent collaboration service (notify/consult/delegate)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class CollaborationError(RuntimeError):
    """Raised when collaboration request is invalid."""


@dataclass
class CollaborationResult:
    target_agent_id: str
    response_text: str
    events: int


class CollaborationService:
    """Agent-to-agent collaboration entry point."""

    _MAX_HOP_COUNT = 3

    def __init__(self, workspace: Any):
        self._workspace = workspace

    async def notify(
        self,
        *,
        target_agent_id: str,
        text: str,
        channel: str,
        user_id: str,
        session_id: str,
    ) -> None:
        target = await self._resolve_target_workspace(target_agent_id)
        if target.channel_manager is None:
            raise CollaborationError(
                f"target agent channel_manager unavailable: {target_agent_id}",
            )
        await target.channel_manager.send_text(
            channel=channel,
            user_id=user_id,
            session_id=session_id,
            text=text,
            meta={
                "source": "collaboration",
                "source_agent_id": self._workspace.agent_id,
                "target_agent_id": target_agent_id,
                "mode": "notify",
            },
        )
        await self._write_event(
            mode="notify",
            target_agent_id=target_agent_id,
            payload={
                "channel": channel,
                "user_id": user_id,
                "session_id": session_id,
                "text": text,
            },
            response_text="",
        )

    async def consult(
        self,
        *,
        target_agent_id: str,
        prompt: str,
        user_id: str,
        session_id: str,
        hop_count: int = 0,
    ) -> CollaborationResult:
        return await self._ask_target(
            mode="consult",
            target_agent_id=target_agent_id,
            prompt=prompt,
            user_id=user_id,
            session_id=session_id,
            hop_count=hop_count,
        )

    async def delegate(
        self,
        *,
        target_agent_id: str,
        task: str,
        user_id: str,
        session_id: str,
        hop_count: int = 0,
    ) -> CollaborationResult:
        return await self._ask_target(
            mode="delegate",
            target_agent_id=target_agent_id,
            prompt=task,
            user_id=user_id,
            session_id=session_id,
            hop_count=hop_count,
        )

    async def _ask_target(
        self,
        *,
        mode: str,
        target_agent_id: str,
        prompt: str,
        user_id: str,
        session_id: str,
        hop_count: int,
    ) -> CollaborationResult:
        if hop_count > self._MAX_HOP_COUNT:
            raise CollaborationError("delegation hop limit exceeded")

        target = await self._resolve_target_workspace(target_agent_id)
        if target.runner is None:
            raise CollaborationError(
                f"target agent runner unavailable: {target_agent_id}",
            )

        req: Dict[str, Any] = {
            "input": prompt,
            "user_id": user_id or f"agent:{self._workspace.agent_id}",
            "session_id": session_id
            or f"collab:{self._workspace.agent_id}:{target_agent_id}",
            "channel": "collaboration",
            "source": "collaboration",
            "meta": {
                "source_agent_id": self._workspace.agent_id,
                "target_agent_id": target_agent_id,
                "mode": mode,
                "hop_count": hop_count + 1,
            },
        }

        chunks: list[str] = []
        event_count = 0
        async for event in target.runner.stream_query(req):
            event_count += 1
            text = self._extract_text(event)
            if text:
                chunks.append(text)

        response_text = "".join(chunks).strip()
        await self._write_event(
            mode=mode,
            target_agent_id=target_agent_id,
            payload={
                "prompt": prompt,
                "user_id": user_id,
                "session_id": session_id,
                "hop_count": hop_count,
            },
            response_text=response_text,
        )
        return CollaborationResult(
            target_agent_id=target_agent_id,
            response_text=response_text,
            events=event_count,
        )

    async def _resolve_target_workspace(self, target_agent_id: str) -> Any:
        if not target_agent_id:
            raise CollaborationError("target_agent_id is required")
        if target_agent_id == self._workspace.agent_id:
            raise CollaborationError("target_agent_id cannot be self")

        manager = getattr(self._workspace, "_manager", None)
        if manager is None:
            raise CollaborationError("multi-agent manager unavailable")
        target = await manager.get_agent(target_agent_id)
        self._validate_workspace_boundary(target)
        return target

    @staticmethod
    def _extract_text(event: Any) -> str:
        if isinstance(event, str):
            return event
        if not isinstance(event, dict):
            return ""
        for key in ("text", "delta", "content"):
            value = event.get(key)
            if isinstance(value, str):
                return value
        return ""

    async def _write_event(
        self,
        *,
        mode: str,
        target_agent_id: str,
        payload: Dict[str, Any],
        response_text: str,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "time": now,
            "source_agent_id": self._workspace.agent_id,
            "target_agent_id": target_agent_id,
            "mode": mode,
            "payload": payload,
            "response_text": response_text,
        }
        path = self._events_path()
        line = json.dumps(record, ensure_ascii=False) + "\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fp:
            fp.write(line)

    def list_events(
        self,
        *,
        limit: int = 50,
        mode: Optional[str] = None,
        target_agent_id: Optional[str] = None,
    ) -> list[Dict[str, Any]]:
        """Read collaboration audit records from local jsonl store."""
        max_limit = max(1, min(int(limit), 500))
        path = self._events_path()
        if not path.exists():
            return []

        rows: list[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if mode and row.get("mode") != mode:
                    continue
                if target_agent_id and row.get("target_agent_id") != target_agent_id:
                    continue
                rows.append(row)
        rows.reverse()  # latest first
        return rows[:max_limit]

    def get_stats(self, *, since_hours: int = 24) -> Dict[str, Any]:
        """Aggregate collaboration events for observability dashboards."""
        rows = self.list_events(limit=10000)
        cutoff = None
        if since_hours > 0:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)

        by_mode: Dict[str, int] = {}
        by_target: Dict[str, int] = {}
        total = 0
        for row in rows:
            if cutoff is not None:
                ts = self._parse_ts(row.get("time", ""))
                if ts is None or ts < cutoff:
                    continue
            total += 1
            mode = str(row.get("mode", "") or "unknown")
            target = str(row.get("target_agent_id", "") or "unknown")
            by_mode[mode] = by_mode.get(mode, 0) + 1
            by_target[target] = by_target.get(target, 0) + 1
        return {
            "total": total,
            "by_mode": by_mode,
            "by_target_agent": by_target,
            "since_hours": since_hours,
        }

    def _events_path(self) -> Path:
        return Path(self._workspace.workspace_dir) / "collaboration_events.jsonl"

    def _validate_workspace_boundary(self, target_workspace: Any) -> None:
        """Ensure source and target are under the same workspaces root."""
        src_root = Path(self._workspace.workspace_dir).expanduser().resolve().parent
        tgt_root = Path(target_workspace.workspace_dir).expanduser().resolve().parent
        if src_root != tgt_root:
            raise CollaborationError("target agent is outside workspace boundary")

    @staticmethod
    def _parse_ts(ts: str) -> Optional[datetime]:
        if not ts:
            return None
        fixed = ts.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(fixed)
        except ValueError:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
