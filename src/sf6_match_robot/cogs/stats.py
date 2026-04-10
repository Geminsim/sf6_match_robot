"""Player stats commands - CFN profile lookups and match history."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


class Stats(commands.Cog):
    """Commands for looking up player data from CFN / Buckler's Boot Camp."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="profile", description="Look up an SF6 player profile")
    @app_commands.describe(cfn_id="The player's CFN ID")
    async def profile(self, interaction: discord.Interaction, cfn_id: str) -> None:
        await interaction.response.send_message(
            f"Profile lookup for `{cfn_id}` is not yet implemented.", ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Stats(bot))
