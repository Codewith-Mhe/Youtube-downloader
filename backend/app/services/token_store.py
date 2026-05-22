"""Secure short-lived token store mapping opaque tokens to download params."""
from __future__ import annotations

import asyncio
import logging
import secrets
import time
from dataclasses import dataclass
from typing import Dict, Optional

log = logging.getLogger("clipfetch.tokens")

TOKEN_TTL_SECONDS = 60 * 30  # 30 minutes
MAX_TOKENS = 50_000


@dataclass
class DownloadTicket:
    url: str
    tier: str
    platform: str
    expires_at: float


class TokenStore:
    def __init__(self) -> None:
        self._data: Dict[str, DownloadTicket] = {}
        self._lock = asyncio.Lock()
        self._sweep_task: Optional[asyncio.Task] = None

    async def start_sweeper(self) -> None:
        if self._sweep_task is None or self._sweep_task.done():
            self._sweep_task = asyncio.create_task(self._sweep_loop())

    async def stop_sweeper(self) -> None:
        if self._sweep_task and not self._sweep_task.done():
            self._sweep_task.cancel()
            try:
                await self._sweep_task
            except asyncio.CancelledError:
                pass

    async def _sweep_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(60)
                await self._sweep()
        except asyncio.CancelledError:
            return

    async def _sweep(self) -> None:
        now = time.time()
        async with self._lock:
            expired = [t for t, tk in self._data.items() if tk.expires_at < now]
            for t in expired:
                self._data.pop(t, None)
            if expired:
                log.debug("Sweeper removed %d expired tokens", len(expired))

    async def put(self, *, url: str, tier: str, platform: str) -> str:
        async with self._lock:
            if len(self._data) >= MAX_TOKENS:
                # Evict oldest ~10%
                for t, _ in sorted(self._data.items(), key=lambda kv: kv[1].expires_at)[
                    : MAX_TOKENS // 10
                ]:
                    self._data.pop(t, None)
            token = secrets.token_urlsafe(32)
            self._data[token] = DownloadTicket(
                url=url,
                tier=tier,
                platform=platform,
                expires_at=time.time() + TOKEN_TTL_SECONDS,
            )
            return token

    async def get(self, token: str) -> Optional[DownloadTicket]:
        if not token or not isinstance(token, str) or len(token) > 128:
            return None
        async with self._lock:
            tk = self._data.get(token)
            if tk is None:
                return None
            if tk.expires_at < time.time():
                self._data.pop(token, None)
                return None
            return tk


token_store = TokenStore()
