# Tournament System Design Document

> **Version:** 1.0  
> **Date:** 2026-04-10  
> **Status:** Approved for Implementation

## 1. Overview

This document describes the design for a **1v1 fighting game tournament module** integrated into the existing SF6 Match Robot Discord bot. The module manages the full tournament lifecycle: registration, automatic double-elimination bracket generation (First to 3), match result reporting, bracket updates, and final placement announcements.

### 1.1 Design Decisions Summary

| Decision | Choice |
|----------|--------|
| Grand Finals Reset | **Enabled** — standard FGC rule |
| Seeding | **Random** — participants are shuffled randomly after registration closes |
| Score reporting | **Any participant** can report + opponent confirmation/dispute + admin override |
| Bracket visualization | **Embed** — round-by-round display using Discord embeds |
| Tournament name | **Required** — must be provided at creation time, no defaults |
| Bot language | **English** — all bot messages in English |

---

## 2. Tournament Lifecycle

### 2.1 State Machine

```
                /tournament create <name>
                        │
                        ▼
                  ┌───────────┐
                  │REGISTRATION│──── Users click [Join] / [Leave]
                  └─────┬─────┘
                        │  /tournament close
                        ▼
                  ┌───────────┐
                  │IN_PROGRESS │──── Bracket generated, matches ongoing
                  └─────┬─────┘
                        │  Champion determined
                        ▼
                  ┌───────────┐
                  │ COMPLETED  │──── Results announced, top 8 @mentioned
                  └───────────┘

        At any point (before COMPLETED):
            /tournament cancel → CANCELLED
```

### 2.2 State Definitions

| State | Description |
|-------|-------------|
| `REGISTRATION` | Tournament created, registration open. Users can join/leave via buttons on the announcement message. |
| `IN_PROGRESS` | Registration closed. Bracket generated with random seeding. Matches are played and results reported. |
| `COMPLETED` | Champion determined. Final standings announced with top 8 @mentions. |
| `CANCELLED` | Tournament cancelled by admin. No results recorded. |

### 2.3 Constraints

- Only **one active tournament per channel** at a time.
- Minimum **2 participants** required to close registration.
- No maximum participant cap enforced by default (but admin may set one via optional parameter).

---

## 3. Discord Interaction Design

### 3.1 Slash Commands

All tournament management is done through a `/tournament` command group with subcommands. Commands that modify tournament state require the `manage_guild` permission or being the tournament creator.

#### 3.1.1 Command Reference

| Command | Parameters | Permission | Description |
|---------|-----------|------------|-------------|
| `/tournament create` | `name: str` (required) | `manage_guild` | Create a new tournament and open registration |
| `/tournament close` | — | Creator or `manage_guild` | Close registration, generate bracket, start tournament |
| `/tournament status` | — | Everyone | Display current tournament state and bracket |
| `/tournament cancel` | `reason: str` (optional) | Creator or `manage_guild` | Cancel the active tournament |
| `/tournament override` | `match_id: str`, `winner: User`, `winner_score: int`, `loser_score: int` | `manage_guild` | Admin override for disputed results |

#### 3.1.2 Command Details

**`/tournament create <name>`**

```
Parameters:
  name (string, required): Tournament name. 1-100 characters.

Behavior:
  1. Check no active tournament exists in this channel.
  2. Create tournament record with status=REGISTRATION.
  3. Send an announcement embed with [Join Tournament] and [Leave Tournament] buttons.
  4. Pin the announcement message for visibility.

Response:
  Embed with tournament info + interactive buttons.

Error cases:
  - Active tournament already exists → ephemeral error message.
  - Missing permissions → ephemeral error message.
```

**`/tournament close`**

```
Behavior:
  1. Verify at least 2 participants registered.
  2. Set status=IN_PROGRESS.
  3. Randomly shuffle participants → assign seeds.
  4. Generate full double-elimination bracket (see §4).
  5. Update the announcement message (disable Join/Leave buttons).
  6. Send bracket embed showing all Round 1 matchups.
  7. Notify Round 1 participants with @mentions: "Your match is ready!"

Error cases:
  - No active tournament → ephemeral error.
  - Fewer than 2 participants → ephemeral error.
```

**`/tournament override <match_id> <winner> <winner_score> <loser_score>`**

```
Parameters:
  match_id (string, required): e.g. "WB-R1-M1"
  winner (User, required): the winning player
  winner_score (integer, required): 0-3
  loser_score (integer, required): 0-3

Behavior:
  1. Validates scores (winner_score must be 3, loser_score must be 0-2).
  2. Overwrites any existing result for this match.
  3. Advances bracket accordingly.
  4. Sends confirmation message.
```

### 3.2 Interactive Components

#### 3.2.1 Registration View (Persistent)

Attached to the tournament announcement message. Uses persistent `discord.ui.View` with `timeout=None` and explicit `custom_id` values so buttons survive bot restarts.

```
┌─────────────────────────────────────────────────┐
│  🏆 Tournament: "Weekend Brawl"                 │
│  Format: FT3, Double Elimination                │
│  Status: Registration Open                      │
│  Participants: 8                                │
│                                                  │
│  1. @Player1    5. @Player5                     │
│  2. @Player2    6. @Player6                     │
│  3. @Player3    7. @Player7                     │
│  4. @Player4    8. @Player8                     │
│                                                  │
│  [🎮 Join Tournament]  [❌ Leave Tournament]     │
└─────────────────────────────────────────────────┘
```

**View class:** `RegistrationView`
- `custom_id="tournament:join:{tournament_id}"` — Join button
- `custom_id="tournament:leave:{tournament_id}"` — Leave button

**Button behaviors:**

| Button | Action |
|--------|--------|
| Join | Add user to participants table. Edit announcement embed to update participant list and count. Ephemeral confirmation: "You have joined the tournament!" |
| Leave | Remove user from participants table. Edit announcement embed. Ephemeral confirmation: "You have left the tournament." |

**Edge cases:**
- Already registered → ephemeral: "You are already registered."
- Not registered (leave) → ephemeral: "You are not registered."
- Tournament not in REGISTRATION → buttons disabled.

#### 3.2.2 Match Report Flow

When a match becomes `READY` (both players determined), the bot sends a match notification embed with a **[Report Result]** button.

**Step 1: Match Notification**

```
┌─────────────────────────────────────────────────┐
│  ⚔️ Match WB-R1-M1 — Winners Round 1            │
│                                                  │
│  @Player1  vs  @Player8                         │
│  Format: First to 3                             │
│                                                  │
│  [📝 Report Result]                              │
└─────────────────────────────────────────────────┘
```

**Step 2: Report Modal**

When a participant clicks [Report Result], a modal dialog appears:

```
Title: "Report Match Result — WB-R1-M1"

Fields:
  - Your Score (TextInput, short, placeholder="0-3", required)
  - Opponent's Score (TextInput, short, placeholder="0-3", required)
```

**View class:** `ReportView`
- `custom_id="tournament:report:{tournament_id}:{match_id}"`

**Modal class:** `ReportModal`
- `custom_id="tournament:report_modal:{tournament_id}:{match_id}"`

**Step 3: Confirmation Request**

After Player A submits, the bot sends a confirmation request to Player B:

```
┌─────────────────────────────────────────────────┐
│  📋 Match Result Reported — WB-R1-M1            │
│                                                  │
│  @Player1 reports: Player1 3 - 1 Player8        │
│                                                  │
│  @Player8, please confirm:                      │
│  [✅ Confirm]  [❌ Dispute]                      │
└─────────────────────────────────────────────────┘
```

**View class:** `ConfirmResultView`
- `custom_id="tournament:confirm:{tournament_id}:{match_id}"` — Confirm
- `custom_id="tournament:dispute:{tournament_id}:{match_id}"` — Dispute

**Step 4a: Confirmed**

If opponent confirms:
1. Record result in database.
2. Advance winner to next match.
3. If loser was in Winners bracket, drop them to appropriate Losers bracket match.
4. Update bracket display embed.
5. If next match is now `READY`, send new match notification.
6. Check if tournament is complete (champion determined).

**Step 4b: Disputed**

If opponent disputes:
1. Send alert to channel: "⚠️ Disputed result for match WB-R1-M1. An admin must resolve with `/tournament override`."
2. Match remains in `IN_PROGRESS` status until admin resolves.

**Validation rules:**
- Only the two participants in a match can click [Report Result].
- Exactly one score must be `3` (FT3 format).
- The other score must be `0`, `1`, or `2`.
- A completed match cannot be re-reported (unless via admin override).

#### 3.2.3 Persistent View Registration

All views must be registered in `setup_hook` for persistence across bot restarts:

```python
# In SF6MatchBot.setup_hook()
async def setup_hook(self) -> None:
    await self._load_cogs()
    # Register persistent views
    self.add_view(RegistrationView())
    self.add_view(ReportView())
    self.add_view(ConfirmResultView())
    # ... sync commands ...
```

---

## 4. Double Elimination Bracket Algorithm

### 4.1 Bracket Structure

A double-elimination bracket consists of three sections:

```
┌─────────────────────────────────────────────┐
│            WINNERS BRACKET                   │
│  Standard single-elimination.               │
│  Losers drop to the Losers Bracket.        │
├─────────────────────────────────────────────┤
│            LOSERS BRACKET                    │
│  Players who lost once compete here.        │
│  Alternates between "drop-down" rounds      │
│  (receiving losers from WB) and "reduction" │
│  rounds (losers-only matches).              │
├─────────────────────────────────────────────┤
│            GRAND FINALS                      │
│  WB Champion vs LB Champion.               │
│  If LB Champion wins → Reset match.         │
│  (WB Champion has not lost yet, so they     │
│   deserve a second chance.)                 │
└─────────────────────────────────────────────┘
```

### 4.2 Bracket Generation Algorithm

#### Input
- `participants: list[int]` — shuffled list of Discord user IDs (random seeding).

#### Step 1: Pad to next power of 2

```python
import math

n = len(participants)
bracket_size = 2 ** math.ceil(math.log2(n))  # next power of 2
num_byes = bracket_size - n
```

#### Step 2: Generate Winners Bracket Round 1

Pair participants using standard seeding order. Higher-seeded players (lower index after shuffle) receive byes.

```
For bracket_size = 8, participants = 6:
  Seed 1 vs BYE    → Seed 1 auto-advances
  Seed 4 vs Seed 5
  Seed 3 vs Seed 6
  Seed 2 vs BYE    → Seed 2 auto-advances
```

Standard seeding pairs for 8-player bracket: `(1,8), (4,5), (3,6), (2,7)`.
With byes, seeds 7 and 8 are empty → seeds 1 and 2 get byes.

#### Step 3: Build Winners Bracket tree

Each round reduces by half. Winners advance to the next round.

```
WB Round 1 (4 matches in 8-player bracket)
  → WB Round 2 (2 matches) — Semifinals
    → WB Round 3 (1 match) — WB Finals
```

#### Step 4: Build Losers Bracket

The losers bracket has roughly `2 * (num_wb_rounds - 1)` rounds, alternating between:

- **Drop-down round**: Players dropping from WB face existing LB players.
- **Reduction round**: LB players face each other.

For an 8-player bracket (3 WB rounds):

```
LB Round 1: WB-R1 losers play each other (2 matches)
LB Round 2: LB-R1 winners vs WB-R2 losers (2 matches, but "cross" paired)
LB Round 3: LB-R2 winners play each other (1 match) — LB Semifinals
LB Round 4: LB-R3 winner vs WB-R3 loser (1 match) — LB Finals
```

#### Step 5: Grand Finals

```
GF Match 1: WB Champion vs LB Champion
  → If WB Champion wins: Tournament over. WB Champion = 1st.
  → If LB Champion wins: GF Reset.

GF Reset: WB Champion vs LB Champion (one more match)
  → Winner = 1st place.
```

### 4.3 Match ID Convention

```
WB-R{round}-M{match}     Winners Bracket, e.g., WB-R1-M1
LB-R{round}-M{match}     Losers Bracket, e.g., LB-R2-M1
GF-1                      Grand Finals Match 1
GF-2                      Grand Finals Reset (if needed)
```

### 4.4 Match Linking

Each match stores pointers to downstream matches:

| Field | Purpose |
|-------|---------|
| `next_winner_match` | Where the winner advances to |
| `next_loser_match` | Where the loser drops to (only for WB matches) |

**Example for 8-player bracket:**

```
WB-R1-M1  → winner → WB-R2-M1 (player1 slot)
          → loser  → LB-R1-M1 (player1 slot)

WB-R1-M2  → winner → WB-R2-M1 (player2 slot)
          → loser  → LB-R1-M1 (player2 slot)

WB-R1-M3  → winner → WB-R2-M2 (player1 slot)
          → loser  → LB-R1-M2 (player1 slot)

WB-R1-M4  → winner → WB-R2-M2 (player2 slot)
          → loser  → LB-R1-M2 (player2 slot)

...and so on for all rounds
```

### 4.5 Bye Handling

- Byes are assigned to the highest-seeded players (first in shuffled order).
- A match with a bye is immediately completed: the non-bye player auto-advances.
- The bye does NOT generate a loser (no one drops to losers bracket from a bye).

### 4.6 Seeding Algorithm (Random)

```python
import random

def generate_seeds(participants: list[int]) -> list[int]:
    """Randomly shuffle participants and assign seed numbers."""
    shuffled = participants.copy()
    random.shuffle(shuffled)
    return shuffled  # index 0 = seed 1, index 1 = seed 2, etc.
```

Standard bracket placement follows the classic seeding pattern to ensure that if seeds hold, the top 2 seeds meet in the finals:

```python
def seed_order(bracket_size: int) -> list[int]:
    """Generate standard tournament seeding order.
    
    For bracket_size=8: returns [1, 8, 4, 5, 3, 6, 2, 7]
    This ensures seed 1 vs 8, 4 vs 5, 3 vs 6, 2 vs 7 in round 1,
    and seed 1 vs seed 2 can only meet in the finals.
    """
    if bracket_size == 1:
        return [1]
    half = seed_order(bracket_size // 2)
    return [
        val for pair in [(s, bracket_size + 1 - s) for s in half]
        for val in pair
    ]
```

---

## 5. Bracket Visualization (Embed)

### 5.1 Strategy

Display the bracket using Discord Embeds, with each bracket section (Winners, Losers, Grand Finals) as a separate embed or embed field. The bracket is displayed round by round.

### 5.2 Embed Structure

When a user runs `/tournament status` or the bracket is automatically posted after bracket generation, the bot sends one or more embeds:

#### Embed 1: Tournament Header

```
Title: 🏆 Tournament: "Weekend Brawl"
Description: Format: FT3 | Double Elimination | 8 Players
Color: Gold (#FFD700)
Footer: Use /tournament status to refresh
```

#### Embed 2: Winners Bracket

```
Title: 📗 Winners Bracket
Color: Green (#2ECC71)

Fields:
  ─── Round 1 ───
  `WB-R1-M1` @Player1 **3** - 1 @Player8 ✅
  `WB-R1-M2` @Player4 vs @Player5 ⏳
  `WB-R1-M3` @Player3 **3** - 0 @Player6 ✅
  `WB-R1-M4` @Player2 [BYE] ✅

  ─── Round 2 (Semifinals) ───
  `WB-R2-M1` @Player1 vs ??? 🔜
  `WB-R2-M2` @Player3 vs @Player2 ⏳

  ─── Round 3 (WB Finals) ───
  `WB-R3-M1` ??? vs ??? 🔜
```

#### Embed 3: Losers Bracket

```
Title: 📕 Losers Bracket
Color: Red (#E74C3C)

Fields:
  ─── Round 1 ───
  `LB-R1-M1` @Player8 vs @Player6 ⏳
  `LB-R1-M2` [BYE]

  ─── Round 2 ───
  ...
```

#### Embed 4: Grand Finals

```
Title: 👑 Grand Finals
Color: Gold (#FFD700)

Fields:
  `GF-1` ??? vs ??? 🔜
  `GF-2` (Reset if needed)
```

### 5.3 Status Icons

| Icon | Meaning |
|------|---------|
| ✅ | Match completed |
| ⏳ | Match in progress / ready to play |
| 🔜 | Waiting for previous matches to complete |
| 🏆 | Tournament champion |

### 5.4 Character Limit Handling

Discord embeds have a 6000 character total limit. For large tournaments (16+ players):
- Split into multiple messages if needed.
- Collapse completed rounds into a summary line: "Round 1: 8 matches completed"
- Show only active/upcoming rounds in full detail.

---

## 6. Placement & Results Announcement

### 6.1 Placement Rules

Double elimination placement is determined by elimination order (reverse):

| Place | Determined by |
|-------|---------------|
| 🥇 1st | Grand Finals winner |
| 🥈 2nd | Grand Finals loser |
| 🥉 3rd | Loser of LB Finals (last LB round before GF) |
| 4th | Loser of LB Semifinals |
| 5th-6th | Losers of LB round before semifinals (tied) |
| 7th-8th | Losers of LB round before that (tied) |

For tournaments with fewer than 8 participants, unfilled places show `N/A`.

### 6.2 Results Announcement Message

When the champion is determined, the bot sends a results embed:

```
Title: 🏆 Tournament Complete: "Weekend Brawl"
Color: Gold (#FFD700)

Description:
  The tournament has concluded! Congratulations to all participants!

Fields:
  🥇 1st Place: @Champion
  🥈 2nd Place: @RunnerUp
  🥉 3rd Place: @ThirdPlace
  4th Place: @FourthPlace
  5th Place: @FifthA, @FifthB
  7th Place: @SeventhA, @SeventhB

  (If < 8 participants, remaining slots show N/A)

Footer: GG! Thanks for participating! 🎮
```

The bot will @mention all placed players in the message content (outside the embed) to ensure they receive notifications.

---

## 7. Data Persistence

### 7.1 Database

Uses the existing `aiosqlite` setup. Database file: `data/sf6_match_robot.db`.

### 7.2 Schema

#### `tournaments` table

```sql
CREATE TABLE IF NOT EXISTS tournaments (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id            INTEGER NOT NULL,
    channel_id          INTEGER NOT NULL,
    name                TEXT NOT NULL,
    created_by          INTEGER NOT NULL,
    status              TEXT NOT NULL DEFAULT 'registration'
                        CHECK(status IN ('registration','in_progress','completed','cancelled')),
    registration_msg_id INTEGER,
    bracket_msg_ids     TEXT,          -- JSON array of message IDs for bracket embeds
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at        TEXT,
    UNIQUE(channel_id, status)        -- enforced via application logic for active tournaments
);
```

#### `participants` table

```sql
CREATE TABLE IF NOT EXISTS participants (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id   INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
    user_id         INTEGER NOT NULL,
    display_name    TEXT NOT NULL,       -- cached Discord display name at registration time
    seed            INTEGER,            -- assigned when registration closes
    placement       INTEGER,           -- final placement (1-8), set when eliminated or wins
    eliminated_at   TEXT,              -- timestamp of elimination
    registered_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(tournament_id, user_id)
);
```

#### `matches` table

```sql
CREATE TABLE IF NOT EXISTS matches (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id       INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
    match_tag           TEXT NOT NULL,       -- "WB-R1-M1", "LB-R2-M3", "GF-1", "GF-2"
    bracket             TEXT NOT NULL        -- "winners", "losers", "grand_finals"
                        CHECK(bracket IN ('winners','losers','grand_finals')),
    round_num           INTEGER NOT NULL,
    match_num           INTEGER NOT NULL,    -- match number within round
    player1_id          INTEGER,            -- user_id (NULL if slot not yet filled)
    player2_id          INTEGER,
    player1_score       INTEGER DEFAULT 0,
    player2_score       INTEGER DEFAULT 0,
    winner_id           INTEGER,
    loser_id            INTEGER,
    status              TEXT NOT NULL DEFAULT 'pending'
                        CHECK(status IN ('pending','ready','in_progress','completed')),
    next_winner_match   TEXT,               -- match_tag the winner advances to
    next_winner_slot    INTEGER,            -- 1 or 2 (player1 or player2 slot in next match)
    next_loser_match    TEXT,               -- match_tag the loser drops to (WB only)
    next_loser_slot     INTEGER,            -- 1 or 2
    notification_msg_id INTEGER,            -- message ID of the match notification
    reported_by         INTEGER,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at        TEXT,
    UNIQUE(tournament_id, match_tag)
);
```

### 7.3 Database Operations

All DB operations are encapsulated in `TournamentRepository` class:

```python
class TournamentRepository:
    """Async database operations for the tournament system."""

    async def create_tournament(guild_id, channel_id, name, created_by) -> int
    async def get_active_tournament(channel_id) -> Tournament | None
    async def update_tournament_status(tournament_id, status) -> None
    async def set_registration_message(tournament_id, message_id) -> None

    async def add_participant(tournament_id, user_id, display_name) -> bool
    async def remove_participant(tournament_id, user_id) -> bool
    async def get_participants(tournament_id) -> list[Participant]
    async def update_participant_seed(tournament_id, user_id, seed) -> None
    async def update_participant_placement(tournament_id, user_id, placement) -> None

    async def create_match(tournament_id, match_tag, bracket, round_num, ...) -> int
    async def get_match(tournament_id, match_tag) -> Match | None
    async def get_matches_by_status(tournament_id, status) -> list[Match]
    async def update_match_players(tournament_id, match_tag, slot, user_id) -> None
    async def record_match_result(tournament_id, match_tag, winner_id, loser_id, p1_score, p2_score) -> None
    async def get_all_matches(tournament_id) -> list[Match]
```

---

## 8. Code Architecture

### 8.1 New Modules

```
src/sf6_match_robot/
├── cogs/
│   └── tournament.py              # [NEW] Tournament slash commands cog
├── models/
│   └── tournament.py              # [NEW] Pydantic models for tournament entities
├── services/
│   └── bracket_engine.py          # [NEW] Pure bracket generation & advancement logic
├── views/
│   ├── __init__.py                # [NEW]
│   ├── registration_view.py       # [NEW] Join/Leave persistent buttons
│   ├── report_view.py             # [NEW] Report Result button + Modal
│   └── confirm_view.py            # [NEW] Confirm/Dispute result buttons
├── db/
│   ├── __init__.py                # [NEW]
│   ├── connection.py              # [NEW] aiosqlite connection manager
│   └── tournament_repo.py         # [NEW] Tournament CRUD operations
└── utils/
    └── bracket_embed.py           # [NEW] Embed builder for bracket display
```

### 8.2 Module Responsibilities

#### `cogs/tournament.py` — Command Layer

- Defines the `/tournament` command group with subcommands.
- Handles permission checks via `app_commands.checks`.
- Delegates all business logic to the service and repository layers.
- Sends responses using views from the `views/` package.

#### `services/bracket_engine.py` — Business Logic

Pure Python module with no Discord dependencies. Fully testable in isolation.

```python
class BracketEngine:
    """Generates and manages double-elimination brackets."""

    @staticmethod
    def generate_bracket(participants: list[int]) -> list[MatchData]:
        """Given a list of user IDs (already shuffled), generate all matches.
        
        Returns a list of MatchData objects representing the full bracket
        with all match linkages (next_winner_match, next_loser_match).
        """

    @staticmethod
    def advance_winner(matches: list[MatchData], completed_match_tag: str) -> list[str]:
        """Process a completed match: advance winner, drop loser.
        
        Returns list of match_tags that became READY as a result.
        """

    @staticmethod
    def calculate_placements(matches: list[MatchData]) -> dict[int, int]:
        """Calculate final placements (1st through 8th) from completed bracket.
        
        Returns {user_id: placement}.
        """

    @staticmethod
    def is_tournament_complete(matches: list[MatchData]) -> bool:
        """Check if the tournament has a champion."""
```

#### `views/registration_view.py` — Registration UI

```python
class RegistrationView(discord.ui.View):
    """Persistent view with Join/Leave buttons for tournament registration."""

    def __init__(self):
        super().__init__(timeout=None)  # Persistent

    @discord.ui.button(
        label="Join Tournament",
        emoji="🎮",
        style=discord.ButtonStyle.success,
        custom_id="tournament:join",
    )
    async def join(self, interaction, button): ...

    @discord.ui.button(
        label="Leave Tournament",
        emoji="❌",
        style=discord.ButtonStyle.danger,
        custom_id="tournament:leave",
    )
    async def leave(self, interaction, button): ...
```

#### `views/report_view.py` — Match Reporting

```python
class ReportView(discord.ui.View):
    """Button to initiate match result reporting. Attached to match notifications."""

    @discord.ui.button(
        label="Report Result",
        emoji="📝",
        style=discord.ButtonStyle.primary,
        custom_id="tournament:report",
    )
    async def report(self, interaction, button):
        # Verify interaction.user is a participant of this match
        # Open ReportModal
        ...

class ReportModal(discord.ui.Modal, title="Report Match Result"):
    your_score = discord.ui.TextInput(label="Your Score", placeholder="0-3", max_length=1)
    opponent_score = discord.ui.TextInput(label="Opponent's Score", placeholder="0-3", max_length=1)

    async def on_submit(self, interaction):
        # Validate: one score must be 3, other must be 0-2
        # Send ConfirmResultView to opponent
        ...
```

#### `views/confirm_view.py` — Result Confirmation

```python
class ConfirmResultView(discord.ui.View):
    """Confirm or Dispute a reported match result."""

    @discord.ui.button(label="Confirm", emoji="✅", ...)
    async def confirm(self, interaction, button):
        # Record result, advance bracket
        ...

    @discord.ui.button(label="Dispute", emoji="❌", ...)
    async def dispute(self, interaction, button):
        # Flag for admin intervention
        ...
```

#### `utils/bracket_embed.py` — Display Logic

```python
class BracketEmbedBuilder:
    """Builds Discord embeds for bracket visualization."""

    @staticmethod
    def build_registration_embed(tournament, participants) -> discord.Embed: ...

    @staticmethod
    def build_bracket_embeds(tournament, matches) -> list[discord.Embed]:
        """Build one embed per bracket section (WB, LB, GF).
        
        Handles character limit by collapsing completed rounds.
        """

    @staticmethod
    def build_match_notification_embed(match) -> discord.Embed: ...

    @staticmethod
    def build_results_embed(tournament, placements) -> discord.Embed: ...
```

### 8.3 Bot Integration

Register persistent views and initialize DB in `setup_hook`:

```python
# bot.py additions
async def setup_hook(self) -> None:
    await self._load_cogs()
    await self._init_database()

    # Register persistent views for button survival across restarts
    from sf6_match_robot.views.registration_view import RegistrationView
    from sf6_match_robot.views.report_view import ReportView
    from sf6_match_robot.views.confirm_view import ConfirmResultView

    self.add_view(RegistrationView())
    self.add_view(ReportView())
    self.add_view(ConfirmResultView())

    # Sync slash commands
    if self.config.guild_id is not None:
        guild = discord.Object(id=self.config.guild_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
    else:
        await self.tree.sync()

async def _init_database(self) -> None:
    """Initialize database tables."""
    from sf6_match_robot.db.connection import init_db
    await init_db(self.config.database_url)
```

---

## 9. Concurrency & Edge Cases

| Scenario | Handling |
|----------|----------|
| Multiple tournaments in same channel | Application-level check: reject if active tournament exists in channel |
| Duplicate registration | `UNIQUE(tournament_id, user_id)` constraint + user-friendly error |
| Bot restart during active tournament | Persistent views + DB state → bot resumes from current state |
| Invalid score format in modal | Validate in `ReportModal.on_submit`: must be integer, one must be 3, other 0-2 |
| Concurrent score reports for same match | Use DB transaction; first valid report wins, second gets "already reported" error |
| Participant leaves Discord server | On `on_member_remove` event: if member is in active match, auto-forfeit (opponent wins 3-0) |
| Participant already eliminated tries to report | Check match participant list against interaction user |
| Tournament with exactly 2 players | Single WB match → Grand Finals-only bracket |
| Grand Finals Reset | GF-2 match created as `pending`; only becomes `ready` if LB champion wins GF-1 |

---

## 10. Permissions Matrix

| Operation | Required Permission |
|-----------|-------------------|
| `/tournament create` | `manage_guild` permission |
| `/tournament close` | Tournament creator OR `manage_guild` |
| `/tournament cancel` | Tournament creator OR `manage_guild` |
| `/tournament override` | `manage_guild` |
| `/tournament status` | Everyone |
| Join / Leave (buttons) | Everyone (must be server member) |
| Report Result (button) | Only the two match participants |
| Confirm / Dispute (buttons) | Only the opponent of the reporter |

---

## 11. Example: 6-Player Tournament Walkthrough

### Participants (after random shuffle)
1. Alice (seed 1)
2. Bob (seed 2)
3. Carol (seed 3)
4. Dave (seed 4)
5. Eve (seed 5)
6. Frank (seed 6)

### Bracket Size: 8 (next power of 2), Byes: 2

### Winners Bracket

```
Round 1 (bracket_size=8, seeding: 1v8, 4v5, 3v6, 2v7):
  WB-R1-M1: Alice (1) vs BYE (8)     → Alice auto-advances
  WB-R1-M2: Dave (4)  vs Eve (5)
  WB-R1-M3: Carol (3) vs Frank (6)
  WB-R1-M4: Bob (2)   vs BYE (7)     → Bob auto-advances

Round 2 (Semifinals):
  WB-R2-M1: Alice vs winner(WB-R1-M2)
  WB-R2-M2: winner(WB-R1-M3) vs Bob

Round 3 (WB Finals):
  WB-R3-M1: winner(WB-R2-M1) vs winner(WB-R2-M2)
```

### Losers Bracket

```
LB Round 1: WB-R1 losers face each other
  LB-R1-M1: loser(WB-R1-M2) vs loser(WB-R1-M3)
  (Note: WB-R1-M1 and M4 are byes → no losers generated)

LB Round 2: LB-R1 winners vs WB-R2 losers
  LB-R2-M1: winner(LB-R1-M1) vs loser(WB-R2-M1)
  LB-R2-M2: (if applicable) vs loser(WB-R2-M2)
  → Depending on bracket structure, may consolidate

LB Round 3 (LB Semis):
  LB-R3-M1: winner(LB-R2-M1) vs winner(LB-R2-M2)

LB Round 4 (LB Finals):
  LB-R4-M1: winner(LB-R3-M1) vs loser(WB-R3-M1)
```

### Grand Finals

```
GF-1: winner(WB-R3-M1) vs winner(LB-R4-M1)
  → If WB champ wins: Tournament over
  → If LB champ wins: Reset

GF-2 (if needed): WB champ vs LB champ again
  → Winner = Champion
```

### Placements for 6 players

| Place | Player |
|-------|--------|
| 🥇 1st | GF winner |
| 🥈 2nd | GF loser |
| 🥉 3rd | LB Finals loser |
| 4th | LB Semis loser |
| 5th | LB Round 2 losers (tied) |
| 7th | N/A |
| 8th | N/A |

---

## 12. Testing Strategy

### Unit Tests
- `test_bracket_engine.py`: Test bracket generation for 2, 3, 4, 5, 6, 7, 8, 16 players.
- Test bye assignment correctness.
- Test match advancement (winner advances, loser drops).
- Test Grand Finals and Reset logic.
- Test placement calculation.

### Integration Tests
- `test_tournament_repo.py`: Test full DB CRUD operations against in-memory SQLite.
- `test_tournament_cog.py`: Test slash command interactions with mocked Discord context.

### Manual Testing
- Run the bot in a test Discord server.
- Walk through a complete tournament lifecycle with 4-8 test users.
- Verify all button interactions, modals, and embed updates.
- Verify bot restart recovery (kill & restart mid-tournament).
