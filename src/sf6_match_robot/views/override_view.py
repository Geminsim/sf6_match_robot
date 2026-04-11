import discord

class OverrideView(discord.ui.View):
    def __init__(self, match_tag: str, p1_id: int, p2_id: int, p1_name: str, p2_name: str):
        super().__init__(timeout=86400) # 24h
        self.match_tag = match_tag
        self.p1_id = p1_id
        self.p2_id = p2_id
        self.p1_name = p1_name
        self.p2_name = p2_name

    @discord.ui.button(label="Win: Player 1", style=discord.ButtonStyle.primary, custom_id="override_p1")
    async def override_p1(self, interaction: discord.Interaction, button: discord.ui.Button):
        # We handle logic in the Cog via a listener, so we just defer or dispatch.
        # But we need standard dynamic dispatch. The Cog can listen to interaction.
        # I'll just change the custom_id structure so `on_interaction` or specific `Cog.listener` handles it
        # Actually, let's just make the custom_id contain the data.
        pass

    @discord.ui.button(label="Win: Player 2", style=discord.ButtonStyle.danger, custom_id="override_p2")
    async def override_p2(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass
