# SF6 Match Robot

A Discord bot for Street Fighter 6 matchmaking and player stats, built with
[discord.py](https://discordpy.readthedocs.io/).

## Features

- Player profile lookup via CFN / Buckler's Boot Camp
- Match history tracking
- Matchmaking lobbies for server members
- Ranked stats reporting

## Quick Start

1. Copy `.env.example` to `.env` and fill in your Discord bot token.
2. Create a virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   # Linux/macOS
   source .venv/bin/activate
   # Windows
   .venv\Scripts\activate

   pip install -r requirements.txt
   ```

3. Run the bot:

   ```bash
   python main.py
   ```

See [docs/setup.md](docs/setup.md) for detailed setup instructions.

## Project Structure

```
sf6_match_robot/
├── main.py                 # Bot entry point
├── src/sf6_match_robot/    # Main package
│   ├── bot.py              # Bot class definition
│   ├── config.py           # Configuration loader
│   ├── cogs/               # Discord command modules
│   ├── services/           # External API clients (CFN, etc.)
│   ├── models/             # Data models
│   └── utils/              # Shared utilities
├── tests/                  # Unit and integration tests
├── docs/                   # Documentation
├── scripts/                # Dev/run scripts
└── data/                   # Local database and runtime files
```

## Documentation

- [Setup Guide](docs/setup.md)
- [Architecture](docs/architecture.md)
- [Commands Reference](docs/commands.md)

## License

TBD
