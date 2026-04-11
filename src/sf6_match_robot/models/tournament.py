from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Tournament(BaseModel):
    id: Optional[int] = None
    guild_id: int
    channel_id: int
    name: str
    created_by: int
    status: str = "registration"  # 'registration', 'in_progress', 'completed', 'cancelled'
    registration_msg_id: Optional[int] = None
    bracket_msg_ids: Optional[str] = None  # JSON array string
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class Participant(BaseModel):
    id: Optional[int] = None
    tournament_id: int
    user_id: int
    display_name: str
    seed: Optional[int] = None
    placement: Optional[int] = None
    eliminated_at: Optional[str] = None
    registered_at: Optional[str] = None


class MatchData(BaseModel):
    id: Optional[int] = None
    tournament_id: int
    match_tag: str
    bracket: str  # 'winners', 'losers', 'grand_finals'
    round_num: int
    match_num: int
    player1_id: Optional[int] = None
    player2_id: Optional[int] = None
    player1_score: int = 0
    player2_score: int = 0
    winner_id: Optional[int] = None
    loser_id: Optional[int] = None
    status: str = "pending"  # 'pending', 'ready', 'in_progress', 'completed'
    next_winner_match: Optional[str] = None
    next_winner_slot: Optional[int] = None
    next_loser_match: Optional[str] = None
    next_loser_slot: Optional[int] = None
    notification_msg_id: Optional[int] = None
    reported_by: Optional[int] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
