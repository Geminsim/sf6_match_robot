import discord

class RegistrationView(discord.ui.View):
    """Persistent view with Join/Leave buttons for tournament registration."""

    def __init__(self, tournament_repo=None, database_url: str = ""):
        super().__init__(timeout=None)
        # Note: In a real app we might need the repo attached, but for a global persistent view
        # recreated on reboot, we usually fetch dependencies dynamically or attach them to bot.
        # We will use bot.config to fetch db.

    @discord.ui.button(
        label="Join Tournament",
        emoji="🎮",
        style=discord.ButtonStyle.success,
        custom_id="tournament:join",
    )
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        interaction.client.dispatch("tournament_join", interaction)

    @discord.ui.button(
        label="Leave Tournament",
        emoji="❌",
        style=discord.ButtonStyle.danger,
        custom_id="tournament:leave",
    )
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        interaction.client.dispatch("tournament_leave", interaction)
