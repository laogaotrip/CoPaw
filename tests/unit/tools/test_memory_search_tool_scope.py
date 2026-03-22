# -*- coding: utf-8 -*-
"""Unit tests for scoped memory search tool wrapper."""

from __future__ import annotations

import pytest
from agentscope.message import TextBlock
from agentscope.tool import ToolResponse

from copaw.agents.tools.memory_search import create_memory_search_tool


class _ScopedMemoryManager:
    def __init__(self) -> None:
        self.calls = []

    async def memory_search_scoped(
        self,
        *,
        query: str,
        max_results: int,
        min_score: float,
        scope: str,
    ) -> ToolResponse:
        self.calls.append((query, max_results, min_score, scope))
        return ToolResponse(
            content=[TextBlock(type="text", text=f"scoped:{scope}:{query}")],
        )


@pytest.mark.asyncio
async def test_memory_search_tool_forwards_scope_to_scoped_search() -> None:
    manager = _ScopedMemoryManager()
    tool = create_memory_search_tool(manager)

    result = await tool(query="deploy", scope="team")

    assert manager.calls == [("deploy", 5, 0.1, "team")]
    assert result.content[0]["text"] == "scoped:team:deploy"
