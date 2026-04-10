"""Entry point for the SF6 Match Robot Discord bot."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow running directly with `python main.py` without installing the package.
SRC = Path(__file__).parent / "src"
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sf6_match_robot.bot import SF6MatchBot
from sf6_match_robot.config import load_config
from sf6_match_robot.utils.logger import setup_logging


async def main() -> None:
    config = load_config()
    setup_logging(config.log_level)

    bot = SF6MatchBot(config)
    async with bot:
        await bot.start(config.discord_token)


if __name__ == "__main__":
    asyncio.run(main())
