# -*- coding: utf-8 -*-
"""Primary/fallback wrapper for chat models.

This wrapper tries the primary model first and automatically falls back to
the secondary model if the primary call fails.
"""

from __future__ import annotations

from typing import Any, AsyncGenerator

from agentscope.model import ChatModelBase
from agentscope.model._model_response import ChatResponse


class FallbackChatModel(ChatModelBase):
    """Call primary model first, then fallback model on failure."""

    def __init__(
        self,
        *,
        primary: ChatModelBase,
        fallback: ChatModelBase,
    ) -> None:
        super().__init__(model_name=primary.model_name, stream=primary.stream)
        self._primary = primary
        self._fallback = fallback

    async def __call__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> ChatResponse | AsyncGenerator[ChatResponse, None]:
        try:
            return await self._primary(*args, **kwargs)
        except Exception:
            return await self._fallback(*args, **kwargs)

