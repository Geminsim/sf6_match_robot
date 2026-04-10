"""Player data models."""
from __future__ import annotations

from pydantic import BaseModel


class PlayerProfile(BaseModel):
    cfn_id: str
    display_name: str
    main_character: str | None = None
    league_rank: str | None = None
    league_points: int | None = None
