"""Shared pytest fixtures."""
from __future__ import annotations

import pytest

from sf6_match_robot.config import Config


@pytest.fixture
def test_config() -> Config:
    return Config(
        discord_token="test-token",
        guild_id=None,
        command_prefix="!",
        log_level="DEBUG",
        cfn_session_cookie=None,
        database_url="sqlite:///:memory:",
    )
