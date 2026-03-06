import asyncio
import os
from typing import Optional

from aiohttp import web
import discord
from discord.ext import commands

from member_role_batch import AutoRoleBatchService


class BatchBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.none()
        intents.guilds = True
        intents.members = True
        super().__init__(command_prefix="/", intents=intents)
        self.port = int(os.getenv("PORT", "8080"))
        self._health_runner: Optional[web.AppRunner] = None
        self._auto_role_service: Optional[AutoRoleBatchService] = None

    async def setup_hook(self) -> None:
        self._auto_role_service = AutoRoleBatchService(self)

    async def start_health_server(self) -> None:
        if self._health_runner:
            return

        async def handle_health(_request: web.Request) -> web.Response:
            return web.Response(text="ok")

        app = web.Application()
        app.router.add_get("/", handle_health)
        app.router.add_get("/healthz", handle_health)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", self.port)
        await site.start()
        self._health_runner = runner

    async def stop_health_server(self) -> None:
        if not self._health_runner:
            return
        await self._health_runner.cleanup()
        self._health_runner = None


async def run_bot() -> None:
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN is required")

    bot = BatchBot()
    await bot.start_health_server()
    try:
        await bot.start(token)
    finally:
        if bot._auto_role_service:
            bot._auto_role_service.stop()
        await bot.stop_health_server()


def main() -> None:
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
