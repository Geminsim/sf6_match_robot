import discord

class ConfirmResultView(discord.ui.View):
    """Confirm or Dispute a reported match result."""

    def __init__(self, match_tag: str):
        super().__init__(timeout=None)
        self.match_tag = match_tag

    @discord.ui.button(
        label="Confirm", 
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="tournament:confirm"
    )
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        interaction.client.dispatch("tournament_confirm_result", interaction, self.match_tag)

    @discord.ui.button(
        label="Dispute", 
        emoji="❌",
        style=discord.ButtonStyle.danger,
        custom_id="tournament:dispute"
    )
    async def dispute(self, interaction: discord.Interaction, button: discord.ui.Button):
        interaction.client.dispatch("tournament_dispute_result", interaction, self.match_tag)
