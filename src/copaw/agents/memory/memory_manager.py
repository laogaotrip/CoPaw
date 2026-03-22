# -*- coding: utf-8 -*-
# pylint: disable=too-many-branches
"""Memory Manager for CoPaw agents.

Extends ReMeLight to provide memory management capabilities including:
- Message compaction with configurable ratio
- Memory summarization with tool support
- Vector and full-text search integration
- Embedding configuration from environment variables
"""
import logging
import os
import platform
from pathlib import Path
from typing import Optional

from agentscope.formatter import FormatterBase
from agentscope.message import Msg, TextBlock
from agentscope.model import ChatModelBase
from agentscope.tool import Toolkit, ToolResponse
from copaw.agents.model_factory import create_model_and_formatter
from copaw.agents.tools import read_file, write_file, edit_file
from copaw.agents.utils import get_copaw_token_counter
from copaw.config.config import load_agent_config

logger = logging.getLogger(__name__)

# Try to import reme, log warning if it fails
try:
    from reme.reme_light import ReMeLight

    _REME_AVAILABLE = True

except ImportError as e:
    _REME_AVAILABLE = False
    logger.warning(f"reme package not installed. {e}")

    class ReMeLight:  # type: ignore
        """Placeholder when reme is not available."""

        async def start(self) -> None:
            """No-op start when reme is unavailable."""


class MemoryManager(ReMeLight):
    """Memory manager that extends ReMeLight for CoPaw agents.

    This class provides memory management capabilities including:
    - Memory compaction for long conversations via compact_memory()
    - Memory summarization with file operation tools via summary_memory()
    - In-memory memory retrieval via get_in_memory_memory()
    - Configurable vector search and full-text search backends
    """

    def __init__(
        self,
        working_dir: str,
        agent_id: str,
    ):
        """Initialize MemoryManager with ReMeLight configuration.

        Args:
            working_dir: Working directory path for memory storage
            agent_id: Agent ID for loading configuration

        Embedding Config:
            api_key, base_url, model_name: config > env var > default
            Other params: from embedding_config only

        Environment Variables:
            EMBEDDING_API_KEY: API key (fallback if not in config)
            EMBEDDING_BASE_URL: Base URL (fallback if not in config)
            EMBEDDING_MODEL_NAME: Model name (fallback if not in config)
            FTS_ENABLED: Enable full-text search (default: true)
            MEMORY_STORE_BACKEND: Memory backend
            - auto/local/chroma (default: auto)

        Note:
            Vector search requires api_key, base_url, and model_name.
        """
        # Extract configuration from agent_config
        self.agent_id: str = agent_id
        self.working_dir = Path(working_dir)

        if not _REME_AVAILABLE:
            logger.warning(
                "reme package not available, memory features will be limited",
            )
            return

        # Get embedding config (supports hot-reload)
        emb_config = self.get_embedding_config()

        # Determine if vector search should be enabled based on configuration
        # Vector search requires base_url and model_name
        vector_enabled = bool(emb_config["base_url"]) and bool(
            emb_config["model_name"],
        )

        # Log embedding config (mask api_key for security)
        log_cfg = {
            **emb_config,
            "api_key": self.mask_key(emb_config["api_key"]),
        }
        logger.info(
            f"Embedding config: {log_cfg}, vector_enabled={vector_enabled}",
        )

        # Check if full-text search (FTS) is enabled via environment variable
        fts_enabled = os.environ.get("FTS_ENABLED", "true").lower() == "true"

        # Determine the memory store backend to use
        # "auto" selects based on platform
        # (local for Windows, chroma otherwise)
        memory_store_backend = os.environ.get("MEMORY_STORE_BACKEND", "auto")
        if memory_store_backend == "auto":
            memory_backend = (
                "local" if platform.system() == "Windows" else "chroma"
            )
        else:
            memory_backend = memory_store_backend

        # Initialize parent ReMeCopaw class
        super().__init__(
            working_dir=working_dir,
            default_embedding_model_config=emb_config,
            default_file_store_config={
                "backend": memory_backend,
                "store_name": "copaw",
                "vector_enabled": vector_enabled,
                "fts_enabled": fts_enabled,
            },
        )

        self.summary_toolkit = Toolkit()
        self.summary_toolkit.register_tool_function(read_file)
        self.summary_toolkit.register_tool_function(write_file)
        self.summary_toolkit.register_tool_function(edit_file)

        self.chat_model: ChatModelBase | None = None
        self.formatter: FormatterBase | None = None

    @staticmethod
    def mask_key(key: str) -> str:
        """Mask API key, showing first 5 chars and masking rest with *."""
        if not key:
            return ""
        if len(key) <= 5:
            return key
        return key[:5] + "*" * (len(key) - 5)

    def get_embedding_config(self) -> dict:
        """Get embedding config. Priority: config > env var > default."""
        cfg = load_agent_config(self.agent_id).running.embedding_config

        # "use_dimensions is used because some models in vLLM
        # do not support the dimensions parameter."
        return {
            "backend": cfg.backend,
            "api_key": cfg.api_key or os.getenv("EMBEDDING_API_KEY", ""),
            "base_url": cfg.base_url or os.getenv("EMBEDDING_BASE_URL", ""),
            "model_name": cfg.model_name
            or os.getenv("EMBEDDING_MODEL_NAME", ""),
            "dimensions": cfg.dimensions,
            "enable_cache": cfg.enable_cache,
            "use_dimensions": cfg.use_dimensions,
            "max_cache_size": cfg.max_cache_size,
            "max_input_length": cfg.max_input_length,
            "max_batch_size": cfg.max_batch_size,
        }

    def prepare_model_formatter(self) -> None:
        """Prepare and initialize the chat model and formatter.

        Lazily initializes the chat_model and formatter attributes if they
        haven't been set yet. This method is called before compaction or
        summarization operations that require model access.

        Note:
            Logs a warning if the model and formatter are not already
            initialized, as this indicates a potential configuration issue.
        """
        if self.chat_model is None or self.formatter is None:
            logger.warning("Model and formatter not initialized.")
            chat_model, formatter = create_model_and_formatter(self.agent_id)
            if self.chat_model is None:
                self.chat_model = chat_model
            if self.formatter is None:
                self.formatter = formatter

    async def restart_embedding_model(self):
        """Restart the embedding model with current config."""
        emb_config = self.get_embedding_config()
        restart_config = {
            "embedding_models": {
                "default": emb_config,
            },
        }
        await self.restart(restart_config=restart_config)

    async def compact_memory(
        self,
        messages: list[Msg],
        previous_summary: str = "",
        **_kwargs,
    ) -> str:
        """Compact a list of messages into a condensed summary.

        Args:
            messages: List of Msg objects to compact
            previous_summary: Optional previous summary to incorporate
            **_kwargs: Additional keyword arguments (ignored)

        Returns:
            str: Condensed summary of the messages
        """
        self.prepare_model_formatter()

        agent_config = load_agent_config(self.agent_id)
        token_counter = get_copaw_token_counter(agent_config)

        return await super().compact_memory(
            messages=messages,
            as_llm=self.chat_model,
            as_llm_formatter=self.formatter,
            as_token_counter=token_counter,
            language=agent_config.language,
            max_input_length=agent_config.running.max_input_length,
            compact_ratio=agent_config.running.memory_compact_ratio,
            previous_summary=previous_summary,
        )

    async def summary_memory(self, messages: list[Msg], **_kwargs) -> str:
        """Generate a comprehensive summary of the given messages.

        Uses file operation tools (read_file, write_file, edit_file) to support
        the summarization process.

        Args:
            messages: List of Msg objects to summarize
            **_kwargs: Additional keyword arguments (ignored)

        Returns:
            str: Comprehensive summary of the messages
        """
        self.prepare_model_formatter()

        agent_config = load_agent_config(self.agent_id)
        token_counter = get_copaw_token_counter(agent_config)

        return await super().summary_memory(
            messages=messages,
            as_llm=self.chat_model,
            as_llm_formatter=self.formatter,
            as_token_counter=token_counter,
            toolkit=self.summary_toolkit,
            language=agent_config.language,
            max_input_length=agent_config.running.max_input_length,
            compact_ratio=agent_config.running.memory_compact_ratio,
        )

    async def memory_search(
        self,
        query: str,
        max_results: int = 5,
        min_score: float = 0.1,
    ) -> ToolResponse:
        """Search through stored memories for relevant content.

        Performs a search across the memory store using vector similarity
        and/or full-text search depending on configuration.

        Args:
            query: The search query string
            max_results: Maximum number of results to return (default: 5)
            min_score: Minimum relevance score threshold (default: 0.1)

        Returns:
            ToolResponse containing the search results as TextBlock content,
            or an error message if ReMe has not been started.
        """
        if not self._started:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text="ReMe is not started, report github issue!",
                    ),
                ],
            )

        return await super().memory_search(
            query=query,
            max_results=max_results,
            min_score=min_score,
        )

    def _resolve_team_knowledge_root(self) -> Optional[Path]:
        """Resolve team knowledge directory from agent config."""
        knowledge_cfg = load_agent_config(self.agent_id).knowledge
        if not knowledge_cfg.enable_team or not knowledge_cfg.team_knowledge_dir:
            return None
        root = Path(knowledge_cfg.team_knowledge_dir).expanduser()
        if not root.is_absolute():
            root = (self.working_dir / root).resolve()
        if not root.exists() or not root.is_dir():
            return None
        return root

    def _search_team_knowledge(
        self,
        query: str,
        *,
        max_results: int,
    ) -> list[str]:
        """Lightweight full-text scan for shared team knowledge files."""
        root = self._resolve_team_knowledge_root()
        if root is None:
            return []

        knowledge_cfg = load_agent_config(self.agent_id).knowledge
        patterns = knowledge_cfg.team_file_globs or ["**/*.md", "**/*.txt"]
        max_scan = max(1, int(knowledge_cfg.team_max_scan_files))
        query_lc = query.lower()

        candidates: list[tuple[int, Path, str]] = []
        seen: set[Path] = set()
        scanned = 0
        for pattern in patterns:
            for path in root.glob(pattern):
                if scanned >= max_scan:
                    break
                if path in seen or not path.is_file():
                    continue
                seen.add(path)
                scanned += 1
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                idx = text.lower().find(query_lc)
                if idx < 0:
                    continue
                start = max(0, idx - 80)
                end = min(len(text), idx + len(query) + 120)
                snippet = " ".join(text[start:end].split())
                score = text.lower().count(query_lc)
                candidates.append((score, path, snippet))
            if scanned >= max_scan:
                break

        candidates.sort(key=lambda item: (-item[0], str(item[1])))
        results: list[str] = []
        for score, path, snippet in candidates[:max_results]:
            rel_path = path.relative_to(root).as_posix()
            results.append(f"[{score}] {rel_path}: {snippet}")
        return results

    async def memory_search_scoped(
        self,
        query: str,
        max_results: int = 5,
        min_score: float = 0.1,
        scope: str = "auto",
    ) -> ToolResponse:
        """Search personal/team knowledge with optional scope filter.

        Args:
            query: Search query.
            max_results: Maximum results for each enabled layer.
            min_score: Personal memory min score.
            scope: one of "auto", "personal", "team".
        """
        scope_normalized = (scope or "auto").strip().lower()
        if scope_normalized not in {"auto", "personal", "team"}:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=(
                            "Error: invalid scope. Use one of "
                            "'auto', 'personal', 'team'.\n"
                            "错误：scope 参数无效，可选值为 "
                            "'auto'、'personal'、'team'。"
                        ),
                    ),
                ],
            )

        knowledge_cfg = load_agent_config(self.agent_id).knowledge
        parts: list[str] = []

        if scope_normalized in {"auto", "personal"} and knowledge_cfg.enable_personal:
            personal = await self.memory_search(
                query=query,
                max_results=max_results,
                min_score=min_score,
            )
            personal_text = "\n".join(
                block.text
                for block in (personal.content or [])
                if getattr(block, "type", "") == "text"
                and getattr(block, "text", "")
            )
            if personal_text.strip():
                parts.append("## Personal Memory\n" + personal_text.strip())

        if scope_normalized in {"auto", "team"} and knowledge_cfg.enable_team:
            team_results = self._search_team_knowledge(
                query=query,
                max_results=max_results,
            )
            if team_results:
                parts.append("## Team Knowledge\n" + "\n".join(team_results))

        if not parts:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=(
                            "No results found in selected knowledge scope.\n"
                            "在所选知识域中未检索到结果。"
                        ),
                    ),
                ],
            )

        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text="\n\n".join(parts),
                ),
            ],
        )

    def get_in_memory_memory(self, **_kwargs):
        """Retrieve in-memory memory content.

        Args:
            **_kwargs: Additional keyword arguments (passed to parent)

        Returns:
            The in-memory memory content with token counting support
        """
        agent_config = load_agent_config(self.agent_id)
        token_counter = get_copaw_token_counter(agent_config)

        return super().get_in_memory_memory(
            as_token_counter=token_counter,
        )
