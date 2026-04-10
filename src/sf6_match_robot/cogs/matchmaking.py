"""Matchmaking commands - lobbies and player search."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


class Matchmaking(commands.Cog):
    """Commands for organizing matches between server members."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="lobby", description="Create or join a matchmaking lobby")
    async def lobby(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            "Matchmaking lobby is not yet implemented.", ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Matchmaking(bot))
