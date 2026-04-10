"""Client for the Street Fighter 6 CFN / Buckler's Boot Camp data source.

Note: There is no official public CFN API. Community implementations typically
rely on authenticated scraping of https://www.streetfighter.com/6/buckler/.
Supply a logged-in session cookie via the CFN_SESSION_COOKIE environment
variable.
"""
from __future__ import annotations

from types import TracebackType
from typing import Self

import aiohttp

from sf6_match_robot.models.player import PlayerProfile


class CFNClient:
    BASE_URL = "https://www.streetfighter.com/6/buckler"

    def __init__(self, session_cookie: str | None = None) -> None:
        self._session_cookie = session_cookie
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> Self:
        headers: dict[str, str] = {}
        if self._session_cookie:
            headers["Cookie"] = self._session_cookie
        self._session = aiohttp.ClientSession(headers=headers)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def get_profile(self, cfn_id: str) -> PlayerProfile:
        raise NotImplementedError("CFN profile fetch is not yet implemented")
