"""Smoke tests for the SF6MatchBot."""
from __future__ import annotations

from sf6_match_robot.bot import SF6MatchBot
from sf6_match_robot.config import Config


def test_bot_constructs(test_config: Config) -> None:
    bot = SF6MatchBot(test_config)
    assert bot.command_prefix == test_config.command_prefix
    assert bot.config is test_config
