from typing import List, Dict

import discord

from sf6_match_robot.models.tournament import MatchData, Participant, Tournament


class BracketEmbedBuilder:
    """Builds Discord embeds for bracket visualization."""

    @staticmethod
    def build_registration_embed(tournament: Tournament, participants: List[Participant]) -> discord.Embed:
        embed = discord.Embed(
            title=f"🏆 Tournament: {tournament.name}",
            description="Format: FT3, Double Elimination\nStatus: **Registration Open**",
            color=0xFFD700
        )
        embed.add_field(name="Participants", value=str(len(participants)), inline=False)
        
        if participants:
            # Format participants in two columns if possible
            names = [f"{i+1}. {p.display_name}" for i, p in enumerate(participants)]
            col1 = "\n".join(names[:len(names)//2 + len(names)%2])
            col2 = "\n".join(names[len(names)//2 + len(names)%2:])
            
            if col1:
                embed.add_field(name="\u200b", value=col1, inline=True)
            if col2:
                embed.add_field(name="\u200b", value=col2, inline=True)
                
        return embed

    @staticmethod
    def build_bracket_embeds(tournament: Tournament, matches: List[MatchData], participant_map: Dict[int, Participant]) -> List[discord.Embed]:
        embeds = []
        
        # --- Tournament Header Embed ---
        header = discord.Embed(
            title=f"🏆 Tournament: {tournament.name}",
            description=f"Format: FT3 | Double Elimination",
            color=0xFFD700
        )
        header.set_footer(text="Use /tournament status to refresh")
        embeds.append(header)
        
        # Helper to format match
        def format_match(m: MatchData) -> str:
            p1 = participant_map.get(m.player1_id).display_name if m.player1_id and m.player1_id != -1 else "???"
            p2 = participant_map.get(m.player2_id).display_name if m.player2_id and m.player2_id != -1 else "???"
            
            icon = "🔜"
            if m.status == 'ready':
                icon = "⏳"
            elif m.status == 'in_progress':
                icon = "⚔️"
            elif m.status == 'completed':
                icon = "✅"
                
            if m.status == 'completed':
                if m.player1_id == -1 or m.player2_id == -1:
                    return f"`{m.match_tag}` [BYE] {icon}"
                return f"`{m.match_tag}` {p1} **{m.player1_score}** - **{m.player2_score}** {p2} {icon}"
                
            return f"`{m.match_tag}` {p1} vs {p2} {icon}"

        # --- Winners Bracket Embed ---
        wb_matches = [m for m in matches if m.bracket == 'winners']
        if wb_matches:
            wb_embed = discord.Embed(title="📗 Winners Bracket", color=0x2ECC71)
            rounds = sorted(list(set(m.round_num for m in wb_matches)))
            for r in rounds:
                r_matches = [m for m in wb_matches if m.round_num == r]
                r_matches.sort(key=lambda x: x.match_num)
                lines = [format_match(m) for m in r_matches]
                wb_embed.add_field(name=f"─── Round {r} ───", value="\n".join(lines), inline=False)
            embeds.append(wb_embed)

        # --- Losers Bracket Embed ---
        lb_matches = [m for m in matches if m.bracket == 'losers']
        if lb_matches:
            lb_embed = discord.Embed(title="📕 Losers Bracket", color=0xE74C3C)
            rounds = sorted(list(set(m.round_num for m in lb_matches)))
            for r in rounds:
                r_matches = [m for m in lb_matches if m.round_num == r]
                r_matches.sort(key=lambda x: x.match_num)
                lines = [format_match(m) for m in r_matches]
                lb_embed.add_field(name=f"─── Round {r} ───", value="\n".join(lines), inline=False)
            embeds.append(lb_embed)

        # --- Grand Finals Embed ---
        gf_matches = [m for m in matches if m.bracket == 'grand_finals']
        if gf_matches:
            gf_embed = discord.Embed(title="👑 Grand Finals", color=0xFFD700)
            gf_matches.sort(key=lambda x: x.match_num)
            lines = [format_match(m) for m in gf_matches]
            gf_embed.add_field(name="\u200b", value="\n".join(lines), inline=False)
            embeds.append(gf_embed)

        return embeds

    @staticmethod
    def build_match_notification_embed(match: MatchData, p1_name: str, p2_name: str) -> discord.Embed:
        embed = discord.Embed(
            title=f"⚔️ Match {match.match_tag}",
            description=f"{p1_name} vs {p2_name}\nFormat: First to 3",
            color=0x3498DB
        )
        return embed

    @staticmethod
    def build_results_embed(tournament: Tournament, placements: Dict[int, int], participant_map: Dict[int, Participant]) -> discord.Embed:
        embed = discord.Embed(
            title=f"🏆 Tournament Complete: {tournament.name}",
            description="The tournament has concluded! Congratulations to all participants!",
            color=0xFFD700
        )
        
        # Group by placement
        place_groups = {}
        for uid, p in placements.items():
            if p not in place_groups:
                place_groups[p] = []
            place_groups[p].append(participant_map[uid].display_name)
            
        places = sorted(place_groups.keys())
        for p in places:
            names = ", ".join(place_groups[p])
            medal = "🥇 " if p == 1 else "🥈 " if p == 2 else "🥉 " if p == 3 else ""
            embed.add_field(name=f"{medal}{p} Place", value=names, inline=False)
            
        embed.set_footer(text="GG! Thanks for participating! 🎮")
        return embed
