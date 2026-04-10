"""Match data models."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class MatchResult(BaseModel):
    match_id: str
    played_at: datetime
    player_cfn_id: str
    opponent_cfn_id: str
    player_character: str
    opponent_character: str
    won: bool
