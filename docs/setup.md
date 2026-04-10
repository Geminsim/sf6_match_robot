# Setup Guide

## Prerequisites

- Python 3.11 or newer
- A Discord bot application and token — create one at
  https://discord.com/developers/applications
- (Optional) A CFN / Buckler's Boot Camp session cookie, needed for profile
  lookups since the CFN backend is not publicly reachable

## Installation

1. Clone the repository:

   ```bash
   git clone <repo-url>
   cd sf6_match_robot
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   # Linux/macOS
   source .venv/bin/activate
   # Windows
   .venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

   For development (tests + linters):

   ```bash
   pip install -e ".[dev]"
   ```

4. Copy the environment template and fill in your values:

   ```bash
   cp .env.example .env
   ```

   Required keys:

   - `DISCORD_TOKEN` — the bot token from the Discord developer portal
   - `DISCORD_GUILD_ID` — optional; restricts slash command sync to a single
     guild for much faster iteration during development. Leave blank to sync
     globally (can take up to an hour to propagate).

## Enabling Privileged Intents

In the Discord developer portal, under your application's **Bot** settings,
enable the following **Privileged Gateway Intents**:

- **Message Content Intent**
- **Server Members Intent**

The bot requests these in `bot.py` and will fail to connect if they are not
authorized.

## Running the Bot

```bash
python main.py
```

Or use the convenience scripts in `scripts/`:

```bash
./scripts/run.sh    # Linux/macOS
scripts\run.bat     # Windows
```

## Inviting the Bot to a Server

Generate an OAuth2 URL in the Discord developer portal with the
`bot` and `applications.commands` scopes, and at minimum these permissions:

- Send Messages
- Embed Links
- Read Message History
- Use Slash Commands

## Running Tests

```bash
pytest
```
