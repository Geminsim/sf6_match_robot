"""Admin commands - diagnostics and cog management."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


class Admin(commands.Cog):
    """Bot owner / admin utilities."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="ping", description="Check if the bot is responsive")
    async def ping(self, interaction: discord.Interaction) -> None:
        latency_ms = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong! ({latency_ms}ms)")

    @commands.command(name="reload")
    @commands.is_owner()
    async def reload(self, ctx: commands.Context, extension: str) -> None:
        """Reload a cog by name (owner only)."""
        try:
            await self.bot.reload_extension(f"sf6_match_robot.cogs.{extension}")
            await ctx.send(f"Reloaded `{extension}`.")
        except Exception as exc:  # noqa: BLE001 - surface reload errors to the owner
            await ctx.send(f"Failed to reload `{extension}`: {exc}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Admin(bot))
