import asyncio
import os

import discord
import git
from discord.ext import commands
from sqlalchemy import select

from src.console import logger
from src.database import Server, Session, init_models


class EventsCog(commands.Cog):
    def __init__(self, bot: discord.Bot) -> None:
        self.bot = bot
        loop = asyncio.get_event_loop()

        loop.run_until_complete(init_models())

    @commands.Cog.listener()
    async def on_ready(self):
        await init_models()
        await self.update_guilds()
        await self.bot.change_presence(status=discord.Status.online)
        repo = git.Repo(os.getcwd())
        branch = repo.head.reference
        activity = discord.CustomActivity(
            name=f"Commit {branch.commit.hexsha[:7]} · {branch.commit.message}"
        )
        await self.bot.change_presence(activity=activity)
        logger.info(
            f"bot is ready: {len(self.bot.guilds)} guilds, {self.bot.user} ({self.bot.user.id})"
        )
        """logger.info(f"started successfully in approx. {round(time() - start_time, 2)} seconds")"""

    async def update_guilds(self) -> None:
        async with Session() as db_session:
            for guild in self.bot.guilds:
                stmt = select(Server).where(Server.id == guild.id)
                result = await db_session.execute(stmt)
                server_entry = result.scalar_one_or_none()

                if server_entry is None:
                    new_server = Server(id=guild.id)
                    db_session.add(new_server)

            await db_session.commit()


def setup(bot: discord.Bot):
    bot.add_cog(EventsCog(bot))
