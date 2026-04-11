import json
import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from sf6_match_robot.db.tournament_repo import TournamentRepository
from sf6_match_robot.services.bracket_engine import BracketEngine
from sf6_match_robot.utils.bracket_embed import BracketEmbedBuilder
from sf6_match_robot.views.registration_view import RegistrationView
from sf6_match_robot.views.report_view import ReportView
from sf6_match_robot.views.confirm_view import ConfirmResultView
from sf6_match_robot.views.override_view import OverrideView


class TournamentCog(commands.Cog):
    """Cog for managing tournaments."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.repo = TournamentRepository(bot.config.database_url)
        self.disputed_matches = set()

    tournament = app_commands.Group(name="tournament", description="Manage SF6 Tournaments")

    # --- Slash Commands ---

    @tournament.command(name="create", description="Create a new tournament and open registration")
    @app_commands.describe(name="Tournament name")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def tournament_create(self, interaction: discord.Interaction, name: str):
        active = await self.repo.get_active_tournament(interaction.channel_id)
        if active:
            await interaction.response.send_message(
                "An active tournament already exists in this channel.", ephemeral=True
            )
            return

        tid = await self.repo.create_tournament(
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
            name=name,
            created_by=interaction.user.id
        )
        t = await self.repo.get_tournament_by_id(tid)

        embed = BracketEmbedBuilder.build_registration_embed(t, [])
        view = RegistrationView()
        
        await interaction.response.send_message(embed=embed, view=view)
        msg = await interaction.original_response()
        await msg.pin()
        
        await self.repo.set_registration_message(tid, msg.id)

    @tournament.command(name="close", description="Close registration and start tournament")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def tournament_close(self, interaction: discord.Interaction):
        active = await self.repo.get_active_tournament(interaction.channel_id)
        if not active or active.status != "registration":
            await interaction.response.send_message("No open tournament found in this channel.", ephemeral=True)
            return

        participants = await self.repo.get_participants(active.id)
        if len(participants) < 2:
            await interaction.response.send_message("Need at least 2 participants to start.", ephemeral=True)
            return

        await interaction.response.defer()

        # Update Status
        await self.repo.update_tournament_status(active.id, "in_progress")
        active.status = "in_progress"
        
        # Shuffle & Seed
        user_ids = [p.user_id for p in participants]
        shuffled = BracketEngine.generate_seeds(user_ids)
        for i, uid in enumerate(shuffled):
            await self.repo.update_participant_seed(active.id, uid, i+1)

        # Generate Bracket
        matches = BracketEngine.generate_bracket(active.id, shuffled)
        for m in matches:
            await self.repo.create_match(m) # simplified, real system needs DB ID back references if doing recursive

        # UI Update
        participant_map = {p.user_id: p for p in participants}
        # Update registration msg
        msg_id = active.registration_msg_id
        if msg_id:
            try:
                channel = interaction.guild.get_channel(interaction.channel_id)
                msg = await channel.fetch_message(msg_id)
                embed = BracketEmbedBuilder.build_registration_embed(active, participants)
                embed.description = "Format: FT3, Double Elimination\nStatus: **Registration Closed**"
                await msg.edit(embed=embed, view=None) # remove buttons
            except Exception:
                pass
                
        # Send Bracket
        embeds = BracketEmbedBuilder.build_bracket_embeds(active, matches, participant_map)
        msg_ids = []
        for em in embeds:
            ms = await interaction.followup.send(embed=em, wait=True)
            msg_ids.append(ms.id)
        await self.repo.set_bracket_messages(active.id, msg_ids)

        # Send Notifications for ready matches
        ready_matches = [m for m in matches if m.status == 'ready' and m.round_num == 1 and m.bracket == 'winners']
        for m in ready_matches:
            p1_name = participant_map[m.player1_id].display_name
            p2_name = participant_map[m.player2_id].display_name
            em = BracketEmbedBuilder.build_match_notification_embed(m, p1_name, p2_name)
            
            # Using view with state in custom_id for simplicity, normally it registers a dynamic callback pattern
            v = ReportView(m.match_tag)
            content = f"<@{m.player1_id}> <@{m.player2_id}> Your match is ready!"
            m_msg = await interaction.channel.send(content=content, embed=em, view=v)
            await self.repo.set_match_notification(active.id, m.match_tag, m_msg.id)

    @tournament.command(name="status", description="Display current bracket status")
    async def tournament_status(self, interaction: discord.Interaction):
        active = await self.repo.get_active_tournament(interaction.channel_id)
        if not active:
            await interaction.response.send_message("No active tournament here.", ephemeral=True)
            return
            
        participants = await self.repo.get_participants(active.id)
        participant_map = {p.user_id: p for p in participants}
        
        if active.status == "registration":
            embed = BracketEmbedBuilder.build_registration_embed(active, participants)
            await interaction.response.send_message(embed=embed)
        else:
            matches = await self.repo.get_all_matches(active.id)
            embeds = BracketEmbedBuilder.build_bracket_embeds(active, matches, participant_map)
            await interaction.response.send_message(embeds=embeds)

    @tournament.command(name="cancel", description="Cancel the active tournament")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def tournament_cancel(self, interaction: discord.Interaction):
        active = await self.repo.get_active_tournament(interaction.channel_id)
        if not active:
            await interaction.response.send_message("No active tournament here.", ephemeral=True)
            return

        await self.repo.update_tournament_status(active.id, "cancelled")
        await interaction.response.send_message(f"Tournament '{active.name}' has been cancelled.")

    @tournament.command(name="report", description="[Fallback] Retrieve your active match report/confirm buttons")
    async def tournament_report(self, interaction: discord.Interaction):
        active = await self.repo.get_active_tournament(interaction.channel_id)
        if not active or active.status != "in_progress":
            await interaction.response.send_message("❌ 当前频道没有正在进行的比赛。", ephemeral=True)
            return

        all_matches = await self.repo.get_all_matches(active.id)
        uid = interaction.user.id
        
        my_match = None
        for m in all_matches:
            if uid in [m.player1_id, m.player2_id] and m.status in ["ready", "in_progress"]:
                my_match = m
                break
                
        if not my_match:
            await interaction.response.send_message("❌ 你当前没有任何正在进行（或等待确认）的比赛。", ephemeral=True)
            return

        if my_match.status == "ready":
            view = ReportView(my_match.match_tag)
            opp_id = my_match.player2_id if uid == my_match.player1_id else my_match.player1_id
            await interaction.response.send_message(f"🎮 你的比分上报面板（对手：<@{opp_id}>，场次：{my_match.match_tag}）：", view=view, ephemeral=True)
            
        elif my_match.status == "in_progress":
            if uid == my_match.reported_by:
                await interaction.response.send_message("⏳ 你的比分已上报，正在等待对手确认！", ephemeral=True)
            else:
                view = ConfirmResultView(my_match.match_tag)
                ps = my_match.player1_score if my_match.reported_by == my_match.player1_id else my_match.player2_score
                os = my_match.player2_score if my_match.reported_by == my_match.player1_id else my_match.player1_score
                
                embed = discord.Embed(
                    title=f"📋 比赛结果确认 — {my_match.match_tag}",
                    description=f"<@{my_match.reported_by}> 刚刚上报了比分: 自己 **{ps}** - **{os}** 对手\n\n请确认此比分是否正确。",
                    color=0xF39C12
                )
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @tournament.command(name="override", description="Force set a match result (Admin only)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def tournament_override(self, interaction: discord.Interaction, match_tag: str):
        active = await self.repo.get_active_tournament(interaction.channel_id)
        if not active:
            await interaction.response.send_message("No active tournament here.", ephemeral=True)
            return

        match_data = await self.repo.get_match(active.id, match_tag)
        if not match_data or match_data.status not in ["ready", "in_progress"]:
            await interaction.response.send_message(f"Match {match_tag} is not active or doesn't exist.", ephemeral=True)
            return
            
        participants = await self.repo.get_participants(active.id)
        participant_map = {p.user_id: p for p in participants}
        
        p1_name = participant_map[match_data.player1_id].display_name if match_data.player1_id in participant_map else "Unknown"
        p2_name = participant_map[match_data.player2_id].display_name if match_data.player2_id in participant_map else "Unknown"

        # Create interactive view dynamically
        view = OverrideView(match_tag, match_data.player1_id, match_data.player2_id, p1_name, p2_name)
        # We need to forcefully inject the IDs so the listener knows what to parse
        view.children[0].custom_id = f"override_win_{match_tag}_{match_data.player1_id}"
        view.children[0].label = f"Win: {p1_name}"
        
        view.children[1].custom_id = f"override_win_{match_tag}_{match_data.player2_id}"
        view.children[1].label = f"Win: {p2_name}"

        embed = discord.Embed(
            title=f"⚠️ 管理员干预 - 强制结算 {match_tag}",
            description=f"请选择 **{p1_name}** 与 **{p2_name}** 之间的真实获胜者。\n系统将自动按照 3-0 为其分配比分并推进赛程。",
            color=0xE74C3C
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @tournament.command(name="history", description="Search and view the final result of a past tournament")
    @app_commands.describe(name="Exact name of the tournament")
    async def tournament_history(self, interaction: discord.Interaction, name: str):
        guild_id = interaction.guild_id
        if not guild_id:
            await interaction.response.send_message("❌ 仅能在服务器内使用此指令。", ephemeral=True)
            return

        t = await self.repo.get_completed_tournament_by_name(guild_id, name)
        if not t:
            await interaction.response.send_message(f"❌ 未找到名为 '{name}' 的已结束历史赛。", ephemeral=True)
            return

        all_matches = await self.repo.get_all_matches(t.id)
        if not all_matches:
            await interaction.response.send_message("❌ 该比赛没有对局数据。", ephemeral=True)
            return

        participants = await self.repo.get_participants(t.id)
        participant_map = {p.user_id: p for p in participants}

        placements = BracketEngine.calculate_placements(all_matches)
        
        gf2 = next((m for m in all_matches if m.match_tag == "GF-2"), None)
        gf1 = next((m for m in all_matches if m.match_tag == "GF-1"), None)
        
        champion_id = None
        if gf2 and gf2.status == 'completed' and gf2.winner_id:
            champion_id = gf2.winner_id
        elif gf1 and gf1.status == 'completed' and gf1.winner_id:
            champion_id = gf1.winner_id

        champ_name = participant_map[champion_id].display_name if champion_id and champion_id in participant_map else "Unknown"

        top8 = []
        sorted_placements = sorted(placements.items(), key=lambda x: x[1])
        for cid, rank in sorted_placements:
            if rank > 8: break
            cname = participant_map[cid].display_name if cid in participant_map else "Unknown"
            medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "🏅"
            top8.append(f"**第 {rank} 名** {medal} : {cname}")
            
        desc_text = f"恭喜 **{champ_name}** 获得总冠军！\n\n**【 Top 8 历史最终排名 】**\n" + "\n".join(top8)
        
        embed = discord.Embed(
            title=f"📜 历史档案：'{t.name}' 圆满收官", 
            description=desc_text,
            color=0x8E44AD
        )
        if t.completed_at:
            embed.set_footer(text=f"比赛ID: {t.id} | 于 {t.completed_at} 结束")
        else:
            embed.set_footer(text=f"比赛ID: {t.id} | 已结束")
            
        await interaction.response.send_message(embed=embed)

    # --- View Dispatch Events ---

    @commands.Cog.listener()
    async def on_tournament_join(self, interaction: discord.Interaction):
        active = await self.repo.get_active_tournament(interaction.channel_id)
        if not active or active.status != "registration":
            await interaction.response.send_message("Registration is not open.", ephemeral=True)
            return
            
        success = await self.repo.add_participant(active.id, interaction.user.id, interaction.user.display_name)
        if success:
            participants = await self.repo.get_participants(active.id)
            embed = BracketEmbedBuilder.build_registration_embed(active, participants)
            await interaction.message.edit(embed=embed)
            await interaction.response.send_message("Successfully joined!", ephemeral=True)
        else:
            await interaction.response.send_message("You are already registered.", ephemeral=True)

    @commands.Cog.listener()
    async def on_tournament_leave(self, interaction: discord.Interaction):
        active = await self.repo.get_active_tournament(interaction.channel_id)
        if not active or active.status != "registration":
            await interaction.response.send_message("Registration is not open.", ephemeral=True)
            return

        success = await self.repo.remove_participant(active.id, interaction.user.id)
        if success:
            participants = await self.repo.get_participants(active.id)
            embed = BracketEmbedBuilder.build_registration_embed(active, participants)
            await interaction.message.edit(embed=embed)
            await interaction.response.send_message("You left the tournament.", ephemeral=True)
        else:
            await interaction.response.send_message("You are not registered.", ephemeral=True)

    @commands.Cog.listener()
    async def on_tournament_report_submit(self, interaction: discord.Interaction, match_tag: str, p_score: str, o_score: str):
        # Basic validation (one must be 3, the other 0, 1, or 2)
        try:
            ps = int(p_score)
            os = int(o_score)
        except ValueError:
            await interaction.response.send_message("Scores must be numbers.", ephemeral=True)
            return

        if (ps == 3 and 0 <= os <= 2) or (os == 3 and 0 <= ps <= 2):
            pass
        else:
            await interaction.response.send_message("Invalid FT3 score. One player must score 3, the other 0-2.", ephemeral=True)
            return

        active = await self.repo.get_active_tournament(interaction.channel_id)
        if not active:
             await interaction.response.send_message("No active tournament.", ephemeral=True)
             return
             
        match_data = await self.repo.get_match(active.id, match_tag)
        if not match_data or match_data.status != "ready":
             await interaction.response.send_message("❌ 该比赛当前无法上报（可能已上报或已结束）。", ephemeral=True)
             return

        # Ensure user is part of the match
        uid = interaction.user.id
        if uid not in [match_data.player1_id, match_data.player2_id]:
             await interaction.response.send_message("❌ 你不是这场比赛的参赛者！", ephemeral=True)
             return
             
        # Store report state in DB
        # Determine strict p1 and p2 score allocations
        if uid == match_data.player1_id:
            db_p1_score, db_p2_score = ps, os
        else:
            db_p1_score, db_p2_score = os, ps

        await self.repo.set_match_report_state(active.id, match_tag, uid, db_p1_score, db_p2_score)

        # Remove the Report Result button from the original message so they can't report again
        if interaction.message:
            try:
                await interaction.message.edit(view=None)
            except Exception:
                pass

        opp_id = match_data.player2_id if uid == match_data.player1_id else match_data.player1_id
        
        embed = discord.Embed(
            title=f"📋 比赛结果确认 — {match_tag}",
            description=f"<@{uid}> 刚刚上报了比分: 自己 **{ps}** - **{os}** 对方\n\n<@{opp_id}>, 请确认此比分是否正确。",
            color=0xF39C12
        )
        
        view = ConfirmResultView(match_tag)
        await interaction.response.send_message(f"<@{opp_id}>", embed=embed, view=view)
        
        self.bot.loop.create_task(self.schedule_auto_confirm(interaction.channel, active.id, match_tag))

    @commands.Cog.listener()
    async def on_tournament_confirm_result(self, interaction: discord.Interaction, match_tag: str):
        active = await self.repo.get_active_tournament(interaction.channel_id)
        if not active: return
        match_data = await self.repo.get_match(active.id, match_tag)
        if not match_data or match_data.status != "in_progress": return

        # IMPORTANT: Only the opponent can confirm
        uid = interaction.user.id
        if uid not in [match_data.player1_id, match_data.player2_id]:
            await interaction.response.send_message("❌ 你不是这场比赛的参赛者！", ephemeral=True)
            return

        if uid == match_data.reported_by:
            await interaction.response.send_message("❌ 你不能确认你自己上报的比分，只能由对手确认！", ephemeral=True)
            return

        # Confirm logic passes
        if interaction.message:
            try:
                await interaction.message.edit(view=None)
            except Exception:
                pass
        
        await interaction.response.defer(ephemeral=False)
        await self._process_match_completion(
            interaction.channel, 
            active, 
            match_data, 
            match_data.player1_score, 
            match_data.player2_score,
            msg_format=f"✅ <@{uid}> 确认了上一场的比赛结果！赛程数据已更新入库。"
        )

    async def schedule_auto_confirm(self, channel, active_id: int, match_tag: str):
        await asyncio.sleep(30)
        dispute_key = f"{active_id}-{match_tag}"
        if dispute_key in self.disputed_matches:
            self.disputed_matches.remove(dispute_key)
            return
            
        match_data = await self.repo.get_match(active_id, match_tag)
        if match_data and match_data.status == "in_progress":
            active = await self.repo.get_tournament_by_id(active_id)
            if not active: return
            
            await self._process_match_completion(
                channel,
                active,
                match_data,
                match_data.player1_score,
                match_data.player2_score,
                msg_format=f"⏳ 30秒超时倒计时结束，系统已自动判定 **{match_tag}** 比分有效，赛程推进！"
            )

    async def _process_match_completion(self, channel, active, match_data, p1_score, p2_score, msg_format: str):
        match_tag = match_data.match_tag
        winner_id = match_data.player1_id if p1_score == 3 else match_data.player2_id
        loser_id = match_data.player2_id if p1_score == 3 else match_data.player1_id

        await self.repo.record_match_result(active.id, match_tag, winner_id, loser_id, p1_score, p2_score)

        all_matches = await self.repo.get_all_matches(active.id)
        ready_match_tags = BracketEngine.advance_winner(all_matches, match_tag)
        await self.repo.batch_update_matches(active.id, all_matches)

        participants = await self.repo.get_participants(active.id)
        participant_map = {p.user_id: p for p in participants}
        
        for rm_tag in ready_match_tags:
            rm = next(m for m in all_matches if m.match_tag == rm_tag)
            p1_name = participant_map[rm.player1_id].display_name
            p2_name = participant_map[rm.player2_id].display_name
            em = BracketEmbedBuilder.build_match_notification_embed(rm, p1_name, p2_name)
            v = ReportView(rm.match_tag)
            content = f"🔥 <@{rm.player1_id}> vs <@{rm.player2_id}>: Your next match is READY!"
            m_msg = await channel.send(content=content, embed=em, view=v)
            await self.repo.set_match_notification(active.id, rm.match_tag, m_msg.id)

        if active.bracket_msg_ids:
            try:
                msg_ids = json.loads(active.bracket_msg_ids)
                embeds = BracketEmbedBuilder.build_bracket_embeds(active, all_matches, participant_map)
                for em, mid in zip(embeds, msg_ids):
                    msg = await channel.fetch_message(mid)
                    await msg.edit(embed=em)
            except Exception:
                pass

        if BracketEngine.is_tournament_complete(all_matches):
            await self.repo.update_tournament_status(active.id, "completed")
            placements = BracketEngine.calculate_placements(all_matches)
            for cid, rank in placements.items():
                await self.repo.update_participant_placement(active.id, cid, rank, eliminated=(rank > 1))
            
            champ_id = next((cid for cid, rank in placements.items() if rank == 1), winner_id)
            champ_name = participant_map[champ_id].display_name if champ_id in participant_map else "Unknown"
            
            top8 = []
            sorted_placements = sorted(placements.items(), key=lambda x: x[1])
            for cid, rank in sorted_placements:
                if rank > 8: break
                cname = participant_map[cid].display_name if cid in participant_map else "Unknown"
                medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "🏅"
                top8.append(f"**第 {rank} 名** {medal} : {cname}")
                
            desc_text = f"恭喜 **{champ_name}** 获得总冠军！\n\n**【 Top 8 最终排名 】**\n" + "\n".join(top8)
            
            final_embed = discord.Embed(
                title=f"🏆 锦标赛 '{active.name}' 圆满收官！ 🏆", 
                description=desc_text,
                color=0xFFD700
            ) 
            await channel.send(embed=final_embed)

        await channel.send(msg_format)

    @commands.Cog.listener()
    async def on_tournament_dispute_result(self, interaction: discord.Interaction, match_tag: str):
        active = await self.repo.get_active_tournament(interaction.channel_id)
        if not active: return
        match_data = await self.repo.get_match(active.id, match_tag)
        if not match_data or match_data.status != "in_progress": return

        # IMPORTANT: Only the opponent can dispute
        uid = interaction.user.id
        if uid not in [match_data.player1_id, match_data.player2_id]:
            await interaction.response.send_message("❌ 你不是这场比赛的参赛者！", ephemeral=True)
            return

        if uid == match_data.reported_by:
            await interaction.response.send_message("❌ 你不能申诉你自己上报的比分！", ephemeral=True)
            return

        if interaction.message:
            try:
                await interaction.message.edit(view=None)
            except Exception:
                pass

        await interaction.response.send_message(f"⚠️ <@{uid}> 拒绝了该比分！比赛结果陷入争议，管理员需要使用 `/tournament override` 强制结算。")
        self.disputed_matches.add(f"{active.id}-{match_tag}")

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        # We handle dynamic override_win buttons here
        if interaction.type == discord.InteractionType.component and "custom_id" in interaction.data:
            custom_id = interaction.data["custom_id"]
            if custom_id.startswith("override_win_"):
                # verify admin
                if not interaction.user.guild_permissions.manage_guild:
                    await interaction.response.send_message("❌ Admin only.", ephemeral=True)
                    return
                
                parts = custom_id.split("_") # override_win_TAG_USERID
                match_tag = parts[2]
                winner_id = int(parts[3])
                
                active = await self.repo.get_active_tournament(interaction.channel_id)
                if not active: return
                match_data = await self.repo.get_match(active.id, match_tag)
                if not match_data: return

                if interaction.message:
                    try:
                        await interaction.message.edit(view=None)
                    except Exception:
                        pass
                
                await interaction.response.defer(ephemeral=False)
                
                if winner_id == match_data.player1_id:
                    ps, os = 3, 0
                else:
                    ps, os = 0, 3

                await self._process_match_completion(
                    interaction.channel, 
                    active, 
                    match_data, 
                    ps, 
                    os,
                    msg_format=f"🛡️ 管理员最高指令：已强制裁定 <@{winner_id}> 为 {match_tag} 比赛胜者，赛程推进！"
                )

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ 你没有足够的权限使用此指令（你需要拥有 '管理服务器 / Manage Server' 权限）。", ephemeral=True)
        else:
            # Optionally fallback or print
            raise error

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TournamentCog(bot))
