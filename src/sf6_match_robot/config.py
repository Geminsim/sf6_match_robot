"""Configuration loading from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    discord_token: str
    guild_id: int | None
    command_prefix: str
    log_level: str
    cfn_session_cookie: str | None
    database_url: str


def load_config() -> Config:
    """Load configuration from a local .env file and process environment."""
    load_dotenv()

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is required in environment")

    guild_id_raw = os.getenv("DISCORD_GUILD_ID", "").strip()
    guild_id = int(guild_id_raw) if guild_id_raw else None

    return Config(
        discord_token=token,
        guild_id=guild_id,
        command_prefix=os.getenv("COMMAND_PREFIX", "!"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        cfn_session_cookie=os.getenv("CFN_SESSION_COOKIE") or None,
        database_url=os.getenv("DATABASE_URL", "sqlite:///data/sf6_match_robot.db"),
    )
