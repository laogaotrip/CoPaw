# -*- coding: utf-8 -*-
"""Self-evolution scheduler execution helpers."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from ...config import get_evolution_config

logger = logging.getLogger(__name__)


async def run_evolution_once(
    *,
    runner: Any,
    agent_id: Optional[str] = None,
    workspace_dir: Optional[Path] = None,
) -> None:
    """Run one self-evolution iteration with prompt from query file."""
    evo = get_evolution_config(agent_id)
    if not evo.enabled or evo.mode != "full_auto":
        logger.debug("evolution skipped: not enabled/full_auto")
        return

    if workspace_dir is None:
        logger.debug("evolution skipped: workspace_dir missing")
        return

    query_path = Path(workspace_dir) / evo.query_file
    if not query_path.is_file():
        logger.debug("evolution skipped: no file at %s", query_path)
        return

    query_text = query_path.read_text(encoding="utf-8").strip()
    if not query_text:
        logger.debug("evolution skipped: empty query file")
        return

    req: Dict[str, Any] = {
        "input": [
            {
                "role": "user",
                "content": [{"type": "text", "text": query_text}],
            },
        ],
        "session_id": evo.session_id,
        "user_id": evo.user_id,
        "source": "evolution",
    }

    async def _run_only() -> None:
        async for _ in runner.stream_query(req):
            pass

    try:
        await asyncio.wait_for(_run_only(), timeout=evo.timeout_seconds)
    except asyncio.TimeoutError:
        logger.warning("evolution run timed out after %ss", evo.timeout_seconds)
