# -*- coding: utf-8 -*-
"""Tests for primary/fallback chat model failover wrapper."""

from __future__ import annotations

import pytest
from agentscope.model import ChatModelBase
from agentscope.model._model_response import ChatResponse
from agentscope.message import TextBlock

from copaw.providers.fallback_chat_model import FallbackChatModel


class _DummyModel(ChatModelBase):
    def __init__(self, behavior: str, text: str = "") -> None:
        super().__init__(model_name="dummy", stream=False)
        self._behavior = behavior
        self._text = text
        self.calls = 0

    async def __call__(self, *_args, **_kwargs):
        self.calls += 1
        if self._behavior == "raise":
            raise RuntimeError("boom")
        return ChatResponse(
            content=[TextBlock(type="text", text=self._text)],
        )


@pytest.mark.asyncio
async def test_fallback_model_used_when_primary_fails() -> None:
    primary = _DummyModel("raise")
    fallback = _DummyModel("ok", text="from-fallback")
    wrapped = FallbackChatModel(primary=primary, fallback=fallback)

    response = await wrapped("hi")
    assert isinstance(response, ChatResponse)
    assert response.content[0]["text"] == "from-fallback"
    assert primary.calls == 1
    assert fallback.calls == 1


@pytest.mark.asyncio
async def test_exception_raised_when_both_primary_and_fallback_fail() -> None:
    primary = _DummyModel("raise")
    fallback = _DummyModel("raise")
    wrapped = FallbackChatModel(primary=primary, fallback=fallback)

    with pytest.raises(RuntimeError, match="boom"):
        await wrapped("hi")
    assert primary.calls == 1
    assert fallback.calls == 1
