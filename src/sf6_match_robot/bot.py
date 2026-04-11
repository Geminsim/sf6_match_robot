"""Core Bot class for the SF6 Match Robot."""
from __future__ import annotations

import logging
from pathlib import Path

import discord
from discord.ext import commands

from sf6_match_robot.config import Config

log = logging.getLogger(__name__)

COGS_DIR = Path(__file__).parent / "cogs"
COG_PACKAGE = "sf6_match_robot.cogs"


class SF6MatchBot(commands.Bot):
    """Bot subclass that auto-discovers cogs and syncs slash commands on startup."""

    def __init__(self, config: Config) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(
            command_prefix=config.command_prefix,
            intents=intents,
        )
        self.config = config

    async def setup_hook(self) -> None:
        await self._init_database()
        await self._load_cogs()

        # Register persistent views for button survival across restarts
        from sf6_match_robot.views.registration_view import RegistrationView
        # Note: ReportView and ConfirmResultView usually need dynamic custom_ids mapped to match tags.
        # For this setup we will register the static forms if needed, but discord.py typically allows fallback views.
        self.add_view(RegistrationView())

        if self.config.guild_id is not None:
            guild = discord.Object(id=self.config.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info("Synced slash commands to guild %s", self.config.guild_id)
        else:
            await self.tree.sync()
            log.info("Synced slash commands globally")

    async def _load_cogs(self) -> None:
        for path in sorted(COGS_DIR.glob("*.py")):
            if path.name.startswith("_"):
                continue
            module = f"{COG_PACKAGE}.{path.stem}"
            try:
                await self.load_extension(module)
                log.info("Loaded cog: %s", module)
            except Exception:
                log.exception("Failed to load cog: %s", module)

    async def on_ready(self) -> None:
        user = self.user
        if user is not None:
            log.info("Logged in as %s (id=%s)", user, user.id)

    async def _init_database(self) -> None:
        """Initialize database tables."""
        from sf6_match_robot.db.connection import init_db
        await init_db(self.config.database_url)
