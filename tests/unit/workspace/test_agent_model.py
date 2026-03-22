# -*- coding: utf-8 -*-
"""Tests for per-agent model configuration."""
from pathlib import Path

import pytest

from copaw.config.config import (
    AgentProfileConfig,
    EvolutionConfig,
    load_agent_config,
    save_agent_config,
)
from copaw.providers.models import ModelSlotConfig


@pytest.fixture
def mock_agent_workspace(tmp_path, monkeypatch):
    """Create a temporary agent workspace for testing."""
    import json
    from copaw.config.utils import get_config_path
    from copaw.config.config import Config, AgentsConfig, AgentProfileRef

    # Setup workspace directory
    workspace_dir = tmp_path / "workspaces" / "test_agent"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    # Patch config path FIRST before any config operations
    monkeypatch.setenv(
        "COPAW_CONFIG_PATH",
        str(tmp_path / "config.json"),
    )

    # Create root config with this agent
    root_config = Config(
        agents=AgentsConfig(
            active_agent="test_agent",
            profiles={
                "test_agent": AgentProfileRef(
                    id="test_agent",
                    workspace_dir=str(workspace_dir),
                ),
            },
        ),
    )

    config_path = Path(get_config_path())
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(root_config.model_dump(exclude_none=True), f)

    # Now create agent.json
    agent_config = AgentProfileConfig(
        id="test_agent",
        name="Test Agent",
        description="Test agent for model config",
    )
    save_agent_config("test_agent", agent_config)

    return workspace_dir


def test_agent_model_config_defaults_to_none(
    mock_agent_workspace,
):  # pylint: disable=redefined-outer-name,unused-argument
    """Test that agent model config defaults to None."""
    agent_config = load_agent_config("test_agent")
    assert agent_config.active_model is None
    assert agent_config.primary_model is None
    assert agent_config.fallback_model is None
    assert agent_config.knowledge.enable_personal is True
    assert agent_config.knowledge.enable_team is False
    assert agent_config.autonomy.level == "L3"
    assert agent_config.evolution is None


def test_agent_model_config_can_be_set(
    mock_agent_workspace,
):  # pylint: disable=redefined-outer-name,unused-argument
    """Test setting agent-specific model config."""
    agent_config = load_agent_config("test_agent")

    # Set active model
    agent_config.active_model = ModelSlotConfig(
        provider_id="openai",
        model="gpt-4",
    )
    save_agent_config("test_agent", agent_config)

    # Reload and verify
    reloaded_config = load_agent_config("test_agent")
    assert reloaded_config.active_model is not None
    assert reloaded_config.active_model.provider_id == "openai"
    assert reloaded_config.active_model.model == "gpt-4"


def test_agent_model_config_persists_across_reloads(
    mock_agent_workspace,
):  # pylint: disable=redefined-outer-name,unused-argument
    """Test that model config persists across multiple save/load cycles."""
    agent_config = load_agent_config("test_agent")

    # Set model
    agent_config.active_model = ModelSlotConfig(
        provider_id="anthropic",
        model="claude-3-5-sonnet-20241022",
    )
    save_agent_config("test_agent", agent_config)

    # Reload multiple times
    for _ in range(3):
        reloaded = load_agent_config("test_agent")
        assert reloaded.active_model is not None
        assert reloaded.active_model.provider_id == "anthropic"
        assert reloaded.active_model.model == "claude-3-5-sonnet-20241022"


def test_agent_model_config_can_be_cleared(
    mock_agent_workspace,
):  # pylint: disable=redefined-outer-name,unused-argument
    """Test that model config can be set to None."""
    agent_config = load_agent_config("test_agent")

    # Set a model
    agent_config.active_model = ModelSlotConfig(
        provider_id="openai",
        model="gpt-4",
    )
    save_agent_config("test_agent", agent_config)

    # Clear it
    agent_config.active_model = None
    save_agent_config("test_agent", agent_config)

    # Verify it's cleared
    reloaded = load_agent_config("test_agent")
    assert reloaded.active_model is None


def test_different_agents_have_independent_models(tmp_path, monkeypatch):
    """Test that different agents can have different model configs."""
    # Patch config path
    monkeypatch.setenv(
        "COPAW_CONFIG_PATH",
        str(tmp_path / "config.json"),
    )

    # Create two agents
    import json
    from copaw.config.config import (
        Config,
        AgentsConfig,
        AgentProfileRef,
    )
    from copaw.config.utils import get_config_path

    agent1_dir = tmp_path / "workspaces" / "agent1"
    agent2_dir = tmp_path / "workspaces" / "agent2"
    agent1_dir.mkdir(parents=True, exist_ok=True)
    agent2_dir.mkdir(parents=True, exist_ok=True)

    # Create root config
    root_config = Config(
        agents=AgentsConfig(
            active_agent="agent1",
            profiles={
                "agent1": AgentProfileRef(
                    id="agent1",
                    workspace_dir=str(agent1_dir),
                ),
                "agent2": AgentProfileRef(
                    id="agent2",
                    workspace_dir=str(agent2_dir),
                ),
            },
        ),
    )

    config_path = Path(get_config_path())
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(root_config.model_dump(exclude_none=True), f)

    # Create agent configs
    config1 = AgentProfileConfig(
        id="agent1",
        name="Agent 1",
    )
    config2 = AgentProfileConfig(
        id="agent2",
        name="Agent 2",
    )

    # Set different models
    config1.active_model = ModelSlotConfig(
        provider_id="openai",
        model="gpt-4",
    )
    config2.active_model = ModelSlotConfig(
        provider_id="anthropic",
        model="claude-3-5-sonnet-20241022",
    )

    save_agent_config("agent1", config1)
    save_agent_config("agent2", config2)

    # Verify they're independent
    reloaded1 = load_agent_config("agent1")
    reloaded2 = load_agent_config("agent2")

    assert reloaded1.active_model.provider_id == "openai"
    assert reloaded1.active_model.model == "gpt-4"

    assert reloaded2.active_model.provider_id == "anthropic"
    assert reloaded2.active_model.model == "claude-3-5-sonnet-20241022"


def test_model_config_excluded_when_none(
    mock_agent_workspace,
):  # pylint: disable=redefined-outer-name
    """Test that active_model is excluded from agent.json when None."""
    agent_config = load_agent_config("test_agent")
    agent_config.active_model = None
    save_agent_config("test_agent", agent_config)

    # Read the raw JSON file
    import json

    agent_json_path = mock_agent_workspace / "agent.json"
    with open(agent_json_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # active_model should not be in the JSON
    assert "active_model" not in raw_data


def test_model_config_included_when_set(
    mock_agent_workspace,
):  # pylint: disable=redefined-outer-name
    """Test that active_model is included in agent.json when set."""
    agent_config = load_agent_config("test_agent")
    agent_config.active_model = ModelSlotConfig(
        provider_id="openai",
        model="gpt-4-turbo",
    )
    save_agent_config("test_agent", agent_config)

    # Read the raw JSON file
    import json

    agent_json_path = mock_agent_workspace / "agent.json"
    with open(agent_json_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # active_model should be in the JSON
    assert "active_model" in raw_data
    assert raw_data["active_model"]["provider_id"] == "openai"
    assert raw_data["active_model"]["model"] == "gpt-4-turbo"


def test_primary_and_fallback_models_are_persisted(
    mock_agent_workspace,
):  # pylint: disable=redefined-outer-name
    """Test that primary/fallback model slots persist in agent.json."""
    agent_config = load_agent_config("test_agent")
    agent_config.primary_model = ModelSlotConfig(
        provider_id="openai",
        model="gpt-4.1",
    )
    agent_config.fallback_model = ModelSlotConfig(
        provider_id="anthropic",
        model="claude-3-5-sonnet-20241022",
    )
    save_agent_config("test_agent", agent_config)

    reloaded = load_agent_config("test_agent")
    assert reloaded.primary_model is not None
    assert reloaded.primary_model.provider_id == "openai"
    assert reloaded.primary_model.model == "gpt-4.1"
    assert reloaded.fallback_model is not None
    assert reloaded.fallback_model.provider_id == "anthropic"
    assert reloaded.fallback_model.model == "claude-3-5-sonnet-20241022"


def test_knowledge_config_is_persisted(
    mock_agent_workspace,
):  # pylint: disable=redefined-outer-name
    """Test that knowledge config persists in agent.json."""
    agent_config = load_agent_config("test_agent")
    agent_config.knowledge.enable_team = True
    agent_config.knowledge.team_knowledge_dir = "shared_kb"
    agent_config.knowledge.team_file_globs = ["**/*.md"]
    save_agent_config("test_agent", agent_config)

    reloaded = load_agent_config("test_agent")
    assert reloaded.knowledge.enable_team is True
    assert reloaded.knowledge.team_knowledge_dir == "shared_kb"
    assert reloaded.knowledge.team_file_globs == ["**/*.md"]


def test_autonomy_and_evolution_config_are_persisted(
    mock_agent_workspace,
):  # pylint: disable=redefined-outer-name
    """Test that autonomy and evolution config persist in agent.json."""
    agent_config = load_agent_config("test_agent")
    agent_config.autonomy.level = "L2"
    agent_config.evolution = EvolutionConfig(
        enabled=True,
        mode="full_auto",
        every="6h",
        query_file="SELF_EVOLUTION.md",
        timeout_seconds=120,
    )
    save_agent_config("test_agent", agent_config)

    reloaded = load_agent_config("test_agent")
    assert reloaded.autonomy.level == "L2"
    assert reloaded.evolution is not None
    assert reloaded.evolution.enabled is True
    assert reloaded.evolution.mode == "full_auto"
    assert reloaded.evolution.every == "6h"
