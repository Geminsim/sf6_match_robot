# Commands Reference

All commands are Discord slash commands unless noted otherwise.

## Stats

| Command | Description |
|---|---|
| `/profile <cfn_id>` | Look up an SF6 player profile by CFN ID |

## Matchmaking

| Command | Description |
|---|---|
| `/lobby` | Create or join a matchmaking lobby |

## Admin

| Command | Description |
|---|---|
| `/ping` | Check the bot's latency |
| `!reload <cog>` | (Owner only, prefix command) Reload a cog without restarting the bot |

## Adding New Commands

Commands live inside cogs in `src/sf6_match_robot/cogs/`. See
[architecture.md](architecture.md) for the cog layout and
[setup.md](setup.md) for how to get a local dev environment running.
