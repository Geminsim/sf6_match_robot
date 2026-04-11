import discord

class ReportModal(discord.ui.Modal, title="Report Match Result"):
    your_score = discord.ui.TextInput(
        label="Your Score", 
        placeholder="0-3", 
        max_length=1,
        required=True
    )
    opponent_score = discord.ui.TextInput(
        label="Opponent's Score", 
        placeholder="0-3", 
        max_length=1,
        required=True
    )

    def __init__(self, match_tag: str):
        super().__init__(title=f"Report Result — {match_tag}")
        self.match_tag = match_tag

    async def on_submit(self, interaction: discord.Interaction):
        # We dispatch to bot event to handle DB logic, so View doesn't need DB coupling.
        interaction.client.dispatch("tournament_report_submit", interaction, self.match_tag, self.your_score.value, self.opponent_score.value)


class ReportView(discord.ui.View):
    """Button to initiate match result reporting."""

    def __init__(self, match_tag: str):
        super().__init__(timeout=None)
        # Dynamic custom ID based on match tag would be standard, but we'll use a dispatch pattern
        # The button custom_id here is static just for UI creation, 
        # but in practice we'd map it if we used dynamic view tracking.
        self.match_tag = match_tag

    @discord.ui.button(
        label="Report Result",
        emoji="📝",
        style=discord.ButtonStyle.primary,
        custom_id="tournament:report", # Usually "tournament:report:{match_tag}"
    )
    async def report(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Open Modal
        await interaction.response.send_modal(ReportModal(self.match_tag))
