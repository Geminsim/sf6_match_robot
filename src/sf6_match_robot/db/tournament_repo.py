from __future__ import annotations

import json
from typing import List, Optional

from sf6_match_robot.db.connection import get_db_connection
from sf6_match_robot.models.tournament import MatchData, Participant, Tournament


class TournamentRepository:
    """Async database operations for the tournament system."""

    def __init__(self, database_url: str):
        self.database_url = database_url

    async def create_tournament(
        self, guild_id: int, channel_id: int, name: str, created_by: int
    ) -> int:
        async with get_db_connection(self.database_url) as db:
            cursor = await db.execute(
                """
                INSERT INTO tournaments (guild_id, channel_id, name, created_by, status)
                VALUES (?, ?, ?, ?, 'registration')
                """,
                (guild_id, channel_id, name, created_by),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_active_tournament(self, channel_id: int) -> Optional[Tournament]:
        async with get_db_connection(self.database_url) as db:
            async with db.execute(
                """
                SELECT * FROM tournaments 
                WHERE channel_id = ? AND status IN ('registration', 'in_progress')
                """,
                (channel_id,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return Tournament(**dict(row))
                return None
                
    async def get_tournament_by_id(self, tournament_id: int) -> Optional[Tournament]:
        async with get_db_connection(self.database_url) as db:
            async with db.execute(
                "SELECT * FROM tournaments WHERE id = ?", (tournament_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return Tournament(**dict(row))
                return None

    async def get_completed_tournament_by_name(self, guild_id: int, name: str) -> Optional[Tournament]:
        async with get_db_connection(self.database_url) as db:
            async with db.execute(
                """
                SELECT * FROM tournaments 
                WHERE guild_id = ? AND name = ? AND status = 'completed'
                ORDER BY completed_at DESC LIMIT 1
                """,
                (guild_id, name),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return Tournament(**dict(row))
                return None

    async def update_tournament_status(self, tournament_id: int, status: str) -> None:
        async with get_db_connection(self.database_url) as db:
            if status == "completed":
                await db.execute(
                    "UPDATE tournaments SET status = ?, completed_at = datetime('now') WHERE id = ?",
                    (status, tournament_id),
                )
            else:
                await db.execute(
                    "UPDATE tournaments SET status = ? WHERE id = ?",
                    (status, tournament_id),
                )
            await db.commit()

    async def set_registration_message(self, tournament_id: int, message_id: int) -> None:
        async with get_db_connection(self.database_url) as db:
            await db.execute(
                "UPDATE tournaments SET registration_msg_id = ? WHERE id = ?",
                (message_id, tournament_id),
            )
            await db.commit()
            
    async def set_bracket_messages(self, tournament_id: int, message_ids: list[int]) -> None:
        async with get_db_connection(self.database_url) as db:
            msg_ids_json = json.dumps(message_ids)
            await db.execute(
                "UPDATE tournaments SET bracket_msg_ids = ? WHERE id = ?",
                (msg_ids_json, tournament_id),
            )
            await db.commit()

    # Participant Operations -> -> -> 

    async def add_participant(self, tournament_id: int, user_id: int, display_name: str) -> bool:
        async with get_db_connection(self.database_url) as db:
            try:
                await db.execute(
                    """
                    INSERT INTO participants (tournament_id, user_id, display_name)
                    VALUES (?, ?, ?)
                    """,
                    (tournament_id, user_id, display_name),
                )
                await db.commit()
                return True
            except Exception: # likely Unique constraint failed
                return False

    async def remove_participant(self, tournament_id: int, user_id: int) -> bool:
        async with get_db_connection(self.database_url) as db:
            cursor = await db.execute(
                "DELETE FROM participants WHERE tournament_id = ? AND user_id = ?",
                (tournament_id, user_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def get_participants(self, tournament_id: int) -> List[Participant]:
        async with get_db_connection(self.database_url) as db:
            async with db.execute(
                "SELECT * FROM participants WHERE tournament_id = ? ORDER BY seed ASC",
                (tournament_id,),
            ) as cursor:
                rows = await cursor.fetchall()
                return [Participant(**dict(row)) for row in rows]
                
    async def update_participant_seed(self, tournament_id: int, user_id: int, seed: int) -> None:
        async with get_db_connection(self.database_url) as db:
            await db.execute(
                "UPDATE participants SET seed = ? WHERE tournament_id = ? AND user_id = ?",
                (seed, tournament_id, user_id),
            )
            await db.commit()

    async def update_participant_placement(self, tournament_id: int, user_id: int, placement: int, eliminated: bool = False) -> None:
        async with get_db_connection(self.database_url) as db:
            if eliminated:
                await db.execute(
                    "UPDATE participants SET placement = ?, eliminated_at = datetime('now') WHERE tournament_id = ? AND user_id = ?",
                    (placement, tournament_id, user_id),
                )
            else:
                await db.execute(
                    "UPDATE participants SET placement = ? WHERE tournament_id = ? AND user_id = ?",
                    (placement, tournament_id, user_id),
                )
            await db.commit()

    # Match Operations

    async def create_match(self, match: MatchData) -> int:
        async with get_db_connection(self.database_url) as db:
            cursor = await db.execute(
                """
                INSERT INTO matches (
                    tournament_id, match_tag, bracket, round_num, match_num,
                    player1_id, player2_id, status, next_winner_match, next_winner_slot,
                    next_loser_match, next_loser_slot
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    match.tournament_id, match.match_tag, match.bracket, match.round_num, match.match_num,
                    match.player1_id, match.player2_id, match.status, match.next_winner_match, match.next_winner_slot,
                    match.next_loser_match, match.next_loser_slot
                )
            )
            await db.commit()
            return cursor.lastrowid

    async def get_match(self, tournament_id: int, match_tag: str) -> Optional[MatchData]:
        async with get_db_connection(self.database_url) as db:
            async with db.execute(
                "SELECT * FROM matches WHERE tournament_id = ? AND match_tag = ?",
                (tournament_id, match_tag)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return MatchData(**dict(row))
                return None

    async def get_all_matches(self, tournament_id: int) -> List[MatchData]:
        async with get_db_connection(self.database_url) as db:
            async with db.execute(
                "SELECT * FROM matches WHERE tournament_id = ?",
                (tournament_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [MatchData(**dict(row)) for row in rows]

    async def update_match_players(self, tournament_id: int, match_tag: str, slot: int, user_id: int) -> None:
        async with get_db_connection(self.database_url) as db:
            field = "player1_id" if slot == 1 else "player2_id"
            await db.execute(
                f"UPDATE matches SET {field} = ? WHERE tournament_id = ? AND match_tag = ?",
                (user_id, tournament_id, match_tag)
            )
            # Fetch players to see if match is READY
            async with db.execute(
                "SELECT player1_id, player2_id, status FROM matches WHERE tournament_id = ? AND match_tag = ?",
                (tournament_id, match_tag)
            ) as cursor:
                row = await cursor.fetchone()
                if row and row['player1_id'] is not None and row['player2_id'] is not None and row['status'] == 'pending':
                    await db.execute(
                        "UPDATE matches SET status = 'ready' WHERE tournament_id = ? AND match_tag = ?",
                        (tournament_id, match_tag)
                    )
            await db.commit()
            
    async def update_match_status(self, tournament_id: int, match_tag: str, status: str) -> None:
        async with get_db_connection(self.database_url) as db:
            await db.execute(
                "UPDATE matches SET status = ? WHERE tournament_id = ? AND match_tag = ?",
                (status, tournament_id, match_tag)
            )
            await db.commit()

    async def set_match_notification(self, tournament_id: int, match_tag: str, msg_id: int) -> None:
        async with get_db_connection(self.database_url) as db:
            await db.execute(
                "UPDATE matches SET notification_msg_id = ? WHERE tournament_id = ? AND match_tag = ?",
                (msg_id, tournament_id, match_tag)
            )
            await db.commit()
            
    async def set_match_report_state(self, tournament_id: int, match_tag: str, reported_by: int, p1_score: int, p2_score: int) -> None:
        async with get_db_connection(self.database_url) as db:
            await db.execute(
                """
                UPDATE matches 
                SET status = 'in_progress', reported_by = ?, player1_score = ?, player2_score = ?
                WHERE tournament_id = ? AND match_tag = ?
                """,
                (reported_by, p1_score, p2_score, tournament_id, match_tag)
            )
            await db.commit()

    async def record_match_result(self, tournament_id: int, match_tag: str, winner_id: int, loser_id: Optional[int], p1_score: int, p2_score: int) -> None:
        async with get_db_connection(self.database_url) as db:
            await db.execute(
                """
                UPDATE matches 
                SET winner_id = ?, loser_id = ?, player1_score = ?, player2_score = ?, status = 'completed', completed_at = datetime('now')
                WHERE tournament_id = ? AND match_tag = ?
                """,
                (winner_id, loser_id, p1_score, p2_score, tournament_id, match_tag)
            )
            await db.commit()
            
    async def batch_update_matches(self, tournament_id: int, matches: List[MatchData]) -> None:
        async with get_db_connection(self.database_url) as db:
            for match in matches:
                await db.execute(
                    """
                    UPDATE matches 
                    SET player1_id = ?, player2_id = ?, status = ?, winner_id = ?
                    WHERE tournament_id = ? AND match_tag = ?
                    """,
                    (match.player1_id, match.player2_id, match.status, match.winner_id, tournament_id, match.match_tag)
                )
            await db.commit()
