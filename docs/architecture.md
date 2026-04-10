# Architecture

## Overview

SF6 Match Robot is a Discord bot built on
[discord.py](https://discordpy.readthedocs.io/) using the cogs extension
system for modular command organization.

## Layers

- **Entry point** (`main.py`) — loads configuration, sets up logging, starts
  the bot inside an asyncio event loop.
- **Bot core** (`src/sf6_match_robot/bot.py`) — a `commands.Bot` subclass
  that auto-discovers every `*.py` module in `cogs/` at startup and syncs
  slash commands (per-guild when `DISCORD_GUILD_ID` is set, otherwise
  globally).
- **Cogs** (`src/sf6_match_robot/cogs/`) — feature-level command groupings.
  Each cog is a self-contained module with its own `setup(bot)` function so
  it can be reloaded at runtime via the `!reload <cog>` prefix command.
  - `matchmaking.py` — lobby creation and player search
  - `stats.py` — CFN profile / match history lookups
  - `admin.py` — diagnostics (`/ping`) and cog reloading
- **Services** (`src/sf6_match_robot/services/`) — external integrations
  such as the CFN / Buckler's Boot Camp client. Cogs depend on services,
  not the other way around.
- **Models** (`src/sf6_match_robot/models/`) — Pydantic data classes for
  player profiles, matches, and other domain objects.
- **Utils** (`src/sf6_match_robot/utils/`) — cross-cutting helpers like
  logging setup.

## Data Flow

```
Discord user → slash command → Cog → Service → External API / DB
                                      ↓
                                   Model ← parsed response
                                      ↓
                            Cog builds Embed → Discord user
```

## Adding a New Cog

1. Create a new file in `src/sf6_match_robot/cogs/` (e.g., `tournaments.py`).
2. Define a class that subclasses `commands.Cog`.
3. Add an async module-level `setup(bot)` function that calls
   `bot.add_cog(YourCog(bot))`.
4. Restart the bot, or use `!reload tournaments` (owner only) to hot-reload.

The auto-loader in `bot.py` picks up any non-underscore-prefixed `.py` file
in the `cogs/` directory, so no registration step is needed.

## Configuration

All configuration comes from environment variables loaded via `python-dotenv`.
See `.env.example` for the full list. The `Config` dataclass in `config.py`
is the single source of truth for what settings the bot reads — add new
fields there rather than reading `os.getenv` from inside cogs.

## CFN Data Source

There is no official public CFN API. `CFNClient` in `services/cfn_client.py`
is a placeholder that expects an authenticated session cookie
(`CFN_SESSION_COOKIE`) to scrape `https://www.streetfighter.com/6/buckler/`.
Community projects like
[cfn-tracker](https://github.com/williamsjokvist/cfn-tracker) and the
[Apify CFN scraper](https://apify.com/3ternal/street-fighter-6-cfn-scraper)
are good references for how to structure the scraping logic.
